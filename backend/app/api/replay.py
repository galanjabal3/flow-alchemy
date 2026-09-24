"""Execution replay endpoints."""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.rate_limiter import rate_limiter
from app.core.queue import enqueue_job
from app.core.job import Job
from app.core.events import publish_event, ExecutionEvent
from app.core.config import settings
from app.models.workflow import User, Workflow, Execution
from app.schemas.workflow import ExecutionResponse

router = APIRouter()


def _check_concurrency_limits(db: Session, user_id: int) -> None:
    """Check both per-user and global concurrency limits."""
    # Per-user limit (with lock to prevent TOCTOU)
    user_running = (
        db.query(Execution)
        .filter(Execution.user_id == user_id, Execution.status.in_(["queued", "running"]))
        .with_for_update()
        .count()
    )
    if user_running >= settings.MAX_CONCURRENT_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Max concurrent executions per user reached ({settings.MAX_CONCURRENT_PER_USER}).",
        )

    # Global limit (with lock)
    total_running = (
        db.query(Execution)
        .filter(Execution.status.in_(["queued", "running"]))
        .with_for_update()
        .count()
    )
    if total_running >= settings.MAX_CONCURRENT_TOTAL:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Max concurrent executions total reached ({settings.MAX_CONCURRENT_TOTAL}).",
        )


@router.post("/executions/{execution_id}/replay", response_model=ExecutionResponse)
async def replay_execution(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Replay an execution with the same input data."""
    # Rate limit check
    rate_key = f"{current_user.id}:replay"
    if not rate_limiter.is_allowed(rate_key, limit=10, window=60):
        retry_after = rate_limiter.get_retry_after(rate_key, window=60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
        )

    execution = (
        db.query(Execution)
        .filter(Execution.id == execution_id, Execution.user_id == current_user.id)
        .first()
    )
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    # Check concurrency limits
    _check_concurrency_limits(db, current_user.id)

    # Create new execution from previous
    idempotency_key = str(uuid.uuid4())
    new_execution = Execution(
        workflow_id=execution.workflow_id,
        user_id=current_user.id,
        status="queued",
        trigger="replay",
        input_data=execution.input_data,
        idempotency_key=idempotency_key,
        started_at=datetime.utcnow(),
    )
    db.add(new_execution)
    db.commit()
    db.refresh(new_execution)

    execution_id_str = str(new_execution.id)

    # Create job
    job = Job(
        execution_id=execution_id_str,
        workflow_id=execution.workflow_id,
        user_id=current_user.id,
        trigger_data=execution.input_data or {},
        idempotency_key=idempotency_key,
        max_retries=settings.MAX_RETRIES,
    )

    # Enqueue job
    success = await enqueue_job(job)
    if not success:
        new_execution.status = "failed"
        new_execution.error_log = "Failed to enqueue job"
        new_execution.completed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue workflow replay",
        )

    # Publish queued event
    await publish_event(ExecutionEvent(
        execution_id=execution_id_str,
        event_type="queued",
    ))

    return ExecutionResponse(
        id=new_execution.id,
        workflow_id=execution.workflow_id,
        status="queued",
        trigger="replay",
        input_data=new_execution.input_data,
        output_data=None,
        error_log=None,
        started_at=new_execution.started_at,
        completed_at=None,
    )


@router.post("/executions/{execution_id}/replay-with-input", response_model=ExecutionResponse)
async def replay_execution_with_input(
    execution_id: int,
    input_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Replay an execution with modified input data."""
    # Rate limit check
    rate_key = f"{current_user.id}:replay"
    if not rate_limiter.is_allowed(rate_key, limit=10, window=60):
        retry_after = rate_limiter.get_retry_after(rate_key, window=60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
        )

    # Validate input size
    import json
    from app.core.config import settings
    serialized = json.dumps(input_data)
    if len(serialized) > settings.MAX_PAYLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"input_data exceeds maximum size of {settings.MAX_PAYLOAD_SIZE} bytes",
        )

    execution = (
        db.query(Execution)
        .filter(Execution.id == execution_id, Execution.user_id == current_user.id)
        .first()
    )
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    # Check concurrency limits
    _check_concurrency_limits(db, current_user.id)

    # Create new execution with new input
    idempotency_key = str(uuid.uuid4())
    new_execution = Execution(
        workflow_id=execution.workflow_id,
        user_id=current_user.id,
        status="queued",
        trigger="replay_with_input",
        input_data=input_data,
        idempotency_key=idempotency_key,
        started_at=datetime.utcnow(),
    )
    db.add(new_execution)
    db.commit()
    db.refresh(new_execution)

    execution_id_str = str(new_execution.id)

    # Create job
    job = Job(
        execution_id=execution_id_str,
        workflow_id=execution.workflow_id,
        user_id=current_user.id,
        trigger_data=input_data,
        idempotency_key=idempotency_key,
        max_retries=settings.MAX_RETRIES,
    )

    # Enqueue job
    success = await enqueue_job(job)
    if not success:
        new_execution.status = "failed"
        new_execution.error_log = "Failed to enqueue job"
        new_execution.completed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue workflow replay",
        )

    # Publish queued event
    await publish_event(ExecutionEvent(
        execution_id=execution_id_str,
        event_type="queued",
    ))

    return ExecutionResponse(
        id=new_execution.id,
        workflow_id=execution.workflow_id,
        status="queued",
        trigger="replay_with_input",
        input_data=new_execution.input_data,
        output_data=None,
        error_log=None,
        started_at=new_execution.started_at,
        completed_at=None,
    )
