"""Scheduler service — manages cron-based workflow scheduling."""

from datetime import datetime, timezone
from typing import Optional, List
from croniter import croniter
from sqlalchemy.orm import Session
from app.models.workflow import Workflow, Execution
from app.core.queue import enqueue_job
from app.core.job import Job
from app.core.events import publish_event, ExecutionEvent
from app.core.config import settings
import uuid


class SchedulerService:
    """Handles cron scheduling for workflows."""

    MINIMUM_INTERVAL_SECONDS = 300  # 5 minutes

    def validate_cron(self, cron_expression: str) -> tuple[bool, str]:
        """Validate a cron expression and check minimum interval."""
        try:
            cron = croniter(cron_expression, datetime.now(timezone.utc))
            next1 = cron.get_next(datetime)
            next2 = cron.get_next(datetime)
            interval = (next2 - next1).total_seconds()
            if interval < self.MINIMUM_INTERVAL_SECONDS:
                return False, f"Schedule too frequent. Minimum interval is {self.MINIMUM_INTERVAL_SECONDS}s"
            return True, ""
        except (ValueError, KeyError):
            return False, "Invalid cron expression"

    def get_next_run(self, cron_expression: str, reference_time: Optional[datetime] = None) -> datetime:
        """Get the next run time for a cron expression."""
        cron = croniter(cron_expression, reference_time or datetime.now(timezone.utc))
        return cron.get_next(datetime)

    def get_prev_run(self, cron_expression: str, reference_time: Optional[datetime] = None) -> datetime:
        """Get the previous run time for a cron expression."""
        cron = croniter(cron_expression, reference_time or datetime.now(timezone.utc))
        return cron.get_prev(datetime)

    def set_schedule(self, db: Session, workflow: Workflow, cron_expression: str) -> dict:
        """Set a schedule for a workflow."""
        is_valid, error_msg = self.validate_cron(cron_expression)
        if not is_valid:
            raise ValueError(error_msg)

        next_run = self.get_next_run(cron_expression)

        workflow.schedule = cron_expression
        db.commit()

        return {
            "workflow_id": workflow.id,
            "schedule": cron_expression,
            "next_run_at": next_run.isoformat(),
            "is_active": workflow.is_active,
        }

    def remove_schedule(self, db: Session, workflow: Workflow) -> None:
        """Remove a schedule from a workflow."""
        workflow.schedule = None
        db.commit()

    def get_scheduled_workflows(self, db: Session, user_id: int) -> List[dict]:
        """Get all workflows with active schedules for a user."""
        workflows = db.query(Workflow).filter(
            Workflow.schedule.isnot(None),
            Workflow.user_id == user_id,
        ).all()

        result = []
        for wf in workflows:
            next_run = self.get_next_run(wf.schedule)
            result.append({
                "workflow_id": wf.id,
                "workflow_name": wf.name,
                "schedule": wf.schedule,
                "next_run_at": next_run.isoformat(),
                "is_active": wf.is_active,
            })

        return result

    async def execute_scheduled_workflow(self, db: Session, workflow: Workflow) -> Optional[str]:
        """Execute a scheduled workflow."""
        if not workflow.is_active:
            return None

        # Check concurrency limits (with lock to prevent race condition)
        user_running = (
            db.query(Execution)
            .filter(Execution.user_id == workflow.user_id, Execution.status.in_(["queued", "running"]))
            .with_for_update()
            .count()
        )
        if user_running >= settings.MAX_CONCURRENT_PER_USER:
            return None

        total_running = (
            db.query(Execution)
            .filter(Execution.status.in_(["queued", "running"]))
            .with_for_update()
            .count()
        )
        if total_running >= settings.MAX_CONCURRENT_TOTAL:
            return None

        # Create execution
        idempotency_key = str(uuid.uuid4())
        execution = Execution(
            workflow_id=workflow.id,
            user_id=workflow.user_id,
            status="queued",
            trigger="schedule",
            input_data={"scheduled_at": datetime.now(timezone.utc).isoformat()},
            idempotency_key=idempotency_key,
            started_at=datetime.now(timezone.utc),
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        # Create job
        job = Job(
            execution_id=str(execution.id),
            workflow_id=workflow.id,
            user_id=workflow.user_id,
            trigger_data={"scheduled_at": datetime.now(timezone.utc).isoformat()},
            idempotency_key=idempotency_key,
            max_retries=settings.MAX_RETRIES,
        )

        # Enqueue
        success = await enqueue_job(job)
        if not success:
            execution.status = "failed"
            execution.error_log = "Failed to enqueue scheduled workflow"
            execution.completed_at = datetime.now(timezone.utc)
            db.commit()
            return None

        # Publish event
        await publish_event(ExecutionEvent(
            execution_id=str(execution.id),
            event_type="queued",
        ))

        return str(execution.id)


scheduler_service = SchedulerService()
