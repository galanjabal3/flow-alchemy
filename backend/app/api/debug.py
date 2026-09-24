"""Debug API endpoints for visual debugging."""

import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel, model_validator
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.rate_limiter import rate_limiter
from app.core.debugger import debug_manager
from app.core.workflow_definition import WorkflowDefinition
from app.core.events import publish_event, ExecutionEvent
from app.models.workflow import User, Workflow, Execution
import structlog

logger = structlog.get_logger()

router = APIRouter()


class DebugStartRequest(BaseModel):
    trigger_data: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_trigger_data_size(self):
        if self.trigger_data:
            size = len(json.dumps(self.trigger_data))
            if size > 1024 * 100:
                raise ValueError("trigger_data exceeds maximum allowed size (100KB)")
        return self


class BreakpointRequest(BaseModel):
    node_id: str


class DebugStateResponse(BaseModel):
    execution_id: str
    workflow_id: int
    state: str
    current_node_index: int
    total_nodes: int
    breakpoints: list
    node_results: Dict[str, Any]
    context: Dict[str, Any]
    started_at: Optional[str]
    paused_at: Optional[str]


@router.post("/executions/{execution_id}/debug", response_model=DebugStateResponse)
async def start_debug(
    execution_id: int,
    request: DebugStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a debug session for an execution."""
    rate_key = f"{current_user.id}:debug_start"
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

    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == execution.workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    try:
        definition = WorkflowDefinition(**workflow.definition)
        session = debug_manager.create_session(
            execution_id=str(execution_id),
            workflow_id=workflow.id,
            user_id=current_user.id,
            definition=definition,
        )

        await debug_manager.start_debug(str(execution_id), request.trigger_data)

        execution.status = "running"
        execution.started_at = datetime.now(timezone.utc)
        db.commit()

        await publish_event(ExecutionEvent(
            execution_id=str(execution_id),
            event_type="debug_started",
            status="running",
        ))

        state = debug_manager.get_debug_state(str(execution_id))
        return state

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("debug_start_failed", execution_id=execution_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while starting the debug session.",
        )


@router.post("/executions/{execution_id}/step")
async def step_debug(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Step to the next node in debug mode."""
    rate_key = f"{current_user.id}:debug_step"
    if not rate_limiter.is_allowed(rate_key, limit=30, window=60):
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

    try:
        node_id = await debug_manager.step(str(execution_id))

        if node_id is None:
            execution.status = "completed"
            execution.completed_at = datetime.now(timezone.utc)
            db.commit()

            await publish_event(ExecutionEvent(
                execution_id=str(execution_id),
                event_type="debug_completed",
                status="completed",
            ))

        state = debug_manager.get_debug_state(str(execution_id))
        return {"node_id": node_id, "state": state}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("debug_step_failed", execution_id=execution_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while stepping.",
        )


@router.post("/executions/{execution_id}/resume")
async def resume_debug(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resume execution until next breakpoint or completion."""
    rate_key = f"{current_user.id}:debug_resume"
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

    try:
        node_id = await debug_manager.continue_execution(str(execution_id))

        if node_id is None:
            execution.status = "completed"
            execution.completed_at = datetime.now(timezone.utc)
            db.commit()

            await publish_event(ExecutionEvent(
                execution_id=str(execution_id),
                event_type="debug_completed",
                status="completed",
            ))

        state = debug_manager.get_debug_state(str(execution_id))
        return {"node_id": node_id, "state": state}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("debug_resume_failed", execution_id=execution_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while resuming.",
        )


@router.post("/executions/{execution_id}/breakpoint")
def add_breakpoint(
    execution_id: int,
    request: BreakpointRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a breakpoint to a node."""
    rate_key = f"{current_user.id}:debug_breakpoint"
    if not rate_limiter.is_allowed(rate_key, limit=50, window=60):
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

    # Validate node_id exists in workflow
    session = debug_manager.get_session(str(execution_id))
    if session and request.node_id not in session.node_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Node '{request.node_id}' not found in workflow",
        )

    try:
        success = debug_manager.add_breakpoint(str(execution_id), request.node_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debug session not found")

    state = debug_manager.get_debug_state(str(execution_id))
    return {"success": True, "state": state}


@router.delete("/executions/{execution_id}/breakpoint/{node_id}")
def remove_breakpoint(
    execution_id: int,
    node_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a breakpoint from a node."""
    execution = (
        db.query(Execution)
        .filter(Execution.id == execution_id, Execution.user_id == current_user.id)
        .first()
    )
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    success = debug_manager.remove_breakpoint(str(execution_id), node_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debug session not found")

    state = debug_manager.get_debug_state(str(execution_id))
    return {"success": True, "state": state}


@router.get("/executions/{execution_id}/debug-state", response_model=DebugStateResponse)
def get_debug_state(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current debug state."""
    execution = (
        db.query(Execution)
        .filter(Execution.id == execution_id, Execution.user_id == current_user.id)
        .first()
    )
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    state = debug_manager.get_debug_state(str(execution_id))
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debug session not found")

    return state


@router.delete("/executions/{execution_id}/debug")
def stop_debug(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stop and clean up a debug session."""
    execution = (
        db.query(Execution)
        .filter(Execution.id == execution_id, Execution.user_id == current_user.id)
        .first()
    )
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    debug_manager.remove_session(str(execution_id))
    return {"success": True}
