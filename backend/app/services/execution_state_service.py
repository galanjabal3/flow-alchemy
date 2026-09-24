"""Execution state service — atomic state transitions with DB persistence."""

from datetime import datetime, timezone
from typing import Optional
import structlog
from sqlalchemy.orm import Session
from sqlalchemy import update
from app.core.state_machine import (
    ExecutionState,
    VALID_TRANSITIONS,
    TERMINAL_STATES,
    InvalidTransitionError,
)
from app.models.workflow import Execution

logger = structlog.get_logger()


class ExecutionStateService:
    """Handles atomic state transitions for executions in the database.

    Uses optimistic locking via WHERE clause to prevent race conditions.
    """

    @staticmethod
    def transition(
        db: Session,
        execution_id: int,
        to_state: ExecutionState,
        error_log: Optional[str] = None,
        worker_id: Optional[str] = None,
    ) -> bool:
        """Atomically transition execution to a new state.

        Returns True if transition succeeded, False if rejected.
        """
        # Get current execution
        execution = db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            logger.error("execution_not_found", execution_id=execution_id)
            return False

        from_state = ExecutionState(execution.status)

        # Validate transition
        if to_state not in VALID_TRANSITIONS.get(from_state, set()):
            logger.warning(
                "invalid_state_transition",
                execution_id=execution_id,
                from_state=from_state.value,
                to_state=to_state.value,
            )
            return False

        # Atomic update with optimistic locking
        stmt = (
            update(Execution)
            .where(Execution.id == execution_id, Execution.status == from_state.value)
            .values(
                status=to_state.value,
                updated_at=datetime.now(timezone.utc),
            )
        )

        # Add optional fields based on target state
        if to_state == ExecutionState.RUNNING:
            stmt = stmt.values(
                started_at=execution.started_at or datetime.now(timezone.utc),
                worker_id=worker_id or execution.worker_id,
            )
        elif to_state in TERMINAL_STATES:
            stmt = stmt.values(completed_at=datetime.now(timezone.utc))
            if error_log:
                stmt = stmt.values(error_log=error_log)

        result = db.execute(stmt)
        db.commit()

        if result.rowcount == 0:
            # Race condition — another worker transitioned first
            logger.warning(
                "state_transition_race_condition",
                execution_id=execution_id,
                from_state=from_state.value,
                to_state=to_state.value,
            )
            return False

        logger.info(
            "state_transition_success",
            execution_id=execution_id,
            from_state=from_state.value,
            to_state=to_state.value,
        )
        return True

    @staticmethod
    def can_transition(db: Session, execution_id: int, to_state: ExecutionState) -> bool:
        """Check if a transition is valid without executing it."""
        execution = db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            return False
        from_state = ExecutionState(execution.status)
        return to_state in VALID_TRANSITIONS.get(from_state, set())

    @staticmethod
    def get_state(db: Session, execution_id: int) -> Optional[ExecutionState]:
        """Get current state of an execution."""
        execution = db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            return None
        return ExecutionState(execution.status)

    @staticmethod
    def is_terminal(db: Session, execution_id: int) -> bool:
        """Check if execution is in a terminal state."""
        state = ExecutionStateService.get_state(db, execution_id)
        return state in TERMINAL_STATES if state else True
