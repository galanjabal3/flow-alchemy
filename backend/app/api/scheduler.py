"""Scheduler endpoints for workflow scheduling."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.rate_limiter import rate_limiter
from app.services.scheduler_service import scheduler_service
from app.models.workflow import User, Workflow

router = APIRouter()


class ScheduleCreate(BaseModel):
    schedule: str = Field(..., max_length=100)


class ScheduleResponse(BaseModel):
    workflow_id: int
    schedule: str
    next_run_at: str
    is_active: bool


class ScheduledWorkflowsResponse(BaseModel):
    workflow_id: int
    workflow_name: str
    schedule: str
    next_run_at: str
    is_active: bool


@router.post("/workflows/{workflow_id}/schedule", response_model=ScheduleResponse)
def set_schedule(
    workflow_id: int,
    schedule_data: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set a cron schedule for a workflow."""
    # Rate limit check
    rate_key = f"{current_user.id}:schedule_set"
    if not rate_limiter.is_allowed(rate_key, limit=10, window=60):
        retry_after = rate_limiter.get_retry_after(rate_key, window=60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
        )

    # Verify workflow ownership
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    try:
        result = scheduler_service.set_schedule(db, workflow, schedule_data.schedule)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/workflows/{workflow_id}/schedule", status_code=status.HTTP_204_NO_CONTENT)
def remove_schedule(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove schedule from a workflow."""
    # Rate limit check
    rate_key = f"{current_user.id}:schedule_delete"
    if not rate_limiter.is_allowed(rate_key, limit=10, window=60):
        retry_after = rate_limiter.get_retry_after(rate_key, window=60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
        )

    # Verify workflow ownership
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    scheduler_service.remove_schedule(db, workflow)
    return None


@router.get("/workflows/{workflow_id}/schedule", response_model=ScheduleResponse)
def get_schedule(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get schedule for a workflow."""
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    if not workflow.schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No schedule set")

    next_run = scheduler_service.get_next_run(workflow.schedule)
    return {
        "workflow_id": workflow_id,
        "schedule": workflow.schedule,
        "next_run_at": next_run.isoformat(),
        "is_active": workflow.is_active,
    }


@router.get("/schedules", response_model=List[ScheduledWorkflowsResponse])
def list_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all scheduled workflows for the current user."""
    return scheduler_service.get_scheduled_workflows(db, current_user.id)
