import uuid
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.rate_limiter import rate_limiter
from app.core.workflow_definition import WorkflowDefinition
from app.core.workflow_adapter import react_flow_to_definition
from app.core.graph_validator import GraphValidationError
from app.core.queue import enqueue_job, is_duplicate_job
from app.core.job import Job
from app.core.events import publish_event, ExecutionEvent
from app.core.state_machine import ExecutionState
from app.core.config import settings
from app.services.execution_state_service import ExecutionStateService
from app.models.workflow import User, Workflow, Execution, NodeDefinition
from app.schemas.workflow import (
    WorkflowCreate, WorkflowUpdate, WorkflowResponse,
    WorkflowRunRequest, ExecutionResponse, ExecutionHistoryResponse,
    ExecutionNodeDetailResponse,
)

router = APIRouter()


@router.get("/", response_model=List[WorkflowResponse])
def list_workflows(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workflows = db.query(Workflow).filter(Workflow.user_id == current_user.id).all()
    return workflows


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(
    workflow_data: WorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workflow = Workflow(
        user_id=current_user.id,
        name=workflow_data.name,
        description=workflow_data.description,
        definition=workflow_data.definition,
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return workflow


@router.put("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: int,
    workflow_data: WorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    if workflow_data.name is not None:
        workflow.name = workflow_data.name
    if workflow_data.description is not None:
        workflow.description = workflow_data.description
    if workflow_data.definition is not None:
        workflow.definition = workflow_data.definition
    if workflow_data.schedule is not None:
        workflow.schedule = workflow_data.schedule

    db.commit()
    db.refresh(workflow)
    return workflow


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    db.delete(workflow)
    db.commit()
    return None


@router.post("/{workflow_id}/run", response_model=ExecutionResponse)
async def run_workflow(
    workflow_id: int,
    run_request: WorkflowRunRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Rate limit: 30 executions per minute per user (generous enough for
    # interactive demo runs without removing abuse protection).
    rate_key = f"{current_user.id}:run"
    if not rate_limiter.is_allowed(rate_key, limit=30, window=60):
        retry_after = rate_limiter.get_retry_after(rate_key, window=60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after or 60)},
        )

    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    # Parse definition using adapter (React Flow → canonical format)
    defn_data = workflow.definition or {"nodes": [], "edges": []}
    try:
        workflow_def = react_flow_to_definition(defn_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow definition: {str(e)}",
        )

    # Resource limits: max nodes per workflow
    if len(workflow_def.nodes) > settings.MAX_NODES_PER_WORKFLOW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow exceeds maximum node count ({settings.MAX_NODES_PER_WORKFLOW}).",
        )

    # Resource limits: max payload size
    if run_request.input_data:
        payload_size = len(json.dumps(run_request.input_data))
        if payload_size > settings.MAX_PAYLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Payload size ({payload_size} bytes) exceeds maximum ({settings.MAX_PAYLOAD_SIZE} bytes).",
            )

    # Serialize concurrent runs per user to prevent TOCTOU.
    # NOTE: `FOR UPDATE` cannot be applied to aggregate (count) queries on
    # PostgreSQL, so we lock the user's row instead and then run plain counts.
    db.query(User).filter(User.id == current_user.id).with_for_update().first()
    user_running = (
        db.query(Execution)
        .filter(Execution.user_id == current_user.id, Execution.status.in_(["queued", "running"]))
        .count()
    )
    if user_running >= settings.MAX_CONCURRENT_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Max concurrent executions per user reached ({settings.MAX_CONCURRENT_PER_USER}).",
        )

    total_running = (
        db.query(Execution)
        .filter(Execution.status.in_(["queued", "running"]))
        .count()
    )
    if total_running >= settings.MAX_CONCURRENT_TOTAL:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Max concurrent executions total reached ({settings.MAX_CONCURRENT_TOTAL}).",
        )

    # Use client-supplied idempotency key or generate UUID
    idempotency_key = run_request.idempotency_key or str(uuid.uuid4())

    # Check for duplicate in DB (client-supplied keys only)
    if run_request.idempotency_key:
        existing = (
            db.query(Execution)
            .filter(Execution.idempotency_key == idempotency_key)
            .first()
        )
        if existing:
            # Return existing execution (idempotent response)
            return ExecutionResponse(
                id=existing.id,
                workflow_id=existing.workflow_id,
                status=existing.status,
                trigger=existing.trigger,
                input_data=existing.input_data,
                output_data=existing.output_data,
                error_log=existing.error_log,
                started_at=existing.started_at,
                completed_at=existing.completed_at,
            )

    # Check for duplicate in Redis processing set
    if await is_duplicate_job(idempotency_key):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate execution detected.",
        )

    # Persist execution record with QUEUED state and workflow snapshot
    execution = Execution(
        workflow_id=workflow_id,
        user_id=current_user.id,
        status=ExecutionState.QUEUED.value,
        trigger="manual",
        input_data=run_request.input_data,
        definition_snapshot=defn_data,  # Immutable snapshot at time of execution
        idempotency_key=idempotency_key,
        started_at=datetime.utcnow(),
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    execution_id = str(execution.id)

    # Create job
    job = Job(
        execution_id=execution_id,
        workflow_id=workflow_id,
        user_id=current_user.id,
        trigger_data=run_request.input_data or {},
        idempotency_key=idempotency_key,
        max_retries=settings.MAX_RETRIES,
    )

    # Enqueue job
    success = await enqueue_job(job)
    if not success:
        ExecutionStateService.transition(
            db, execution.id, ExecutionState.FAILED, error_log="Failed to enqueue job"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue workflow execution",
        )

    # Publish queued event
    await publish_event(ExecutionEvent(
        execution_id=execution_id,
        event_type="queued",
    ))

    return ExecutionResponse(
        id=execution.id,
        workflow_id=workflow_id,
        status=ExecutionState.QUEUED.value,
        trigger="manual",
        input_data=execution.input_data,
        output_data=None,
        error_log=None,
        started_at=execution.started_at,
        completed_at=None,
    )


@router.post("/{workflow_id}/executions/{execution_id}/cancel", response_model=ExecutionResponse)
async def cancel_execution(
    workflow_id: int,
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a queued or running execution."""
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    execution = (
        db.query(Execution)
        .filter(Execution.id == execution_id, Execution.workflow_id == workflow_id)
        .first()
    )
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    # Try to transition to CANCELLED
    transitioned = ExecutionStateService.transition(
        db, execution_id, ExecutionState.CANCELLED
    )
    if not transitioned:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel execution in '{execution.status}' state.",
        )

    # Publish cancelled event
    await publish_event(ExecutionEvent(
        execution_id=str(execution_id),
        event_type="cancelled",
        status="cancelled",
    ))

    db.refresh(execution)
    return execution


@router.get("/{workflow_id}/executions", response_model=List[ExecutionHistoryResponse])
def list_executions(
    workflow_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Clamp limit to prevent abuse
    limit = min(max(limit, 1), 100)
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    executions = (
        db.query(Execution)
        .filter(Execution.workflow_id == workflow_id)
        .order_by(Execution.started_at.desc())
        .limit(limit)
        .all()
    )
    return executions


@router.get("/executions/{execution_id}/nodes", response_model=List[ExecutionNodeDetailResponse])
def list_execution_nodes(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Per-node execution history for a given execution (owned by current user)."""
    execution = (
        db.query(Execution)
        .join(Workflow)
        .filter(Execution.id == execution_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    from app.models.workflow import NodeExecution

    nodes = (
        db.query(NodeExecution)
        .filter(NodeExecution.execution_id == execution_id)
        .order_by(NodeExecution.id.asc())
        .all()
    )
    return nodes
