"""Tests for ExecutionStateService (DB-backed state transitions)."""

import pytest
from datetime import datetime, timezone
from app.core.state_machine import ExecutionState
from app.services.execution_state_service import ExecutionStateService
from app.models.workflow import Execution


class TestExecutionStateService:
    """Tests for atomic DB state transitions."""

    def test_transition_queued_to_running(self, db_session):
        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.QUEUED.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        result = ExecutionStateService.transition(
            db_session, execution.id, ExecutionState.RUNNING, worker_id="worker-1"
        )
        assert result is True

        db_session.refresh(execution)
        assert execution.status == ExecutionState.RUNNING.value
        assert execution.worker_id == "worker-1"

    def test_transition_running_to_completed(self, db_session):
        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.RUNNING.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        result = ExecutionStateService.transition(
            db_session, execution.id, ExecutionState.COMPLETED
        )
        assert result is True

        db_session.refresh(execution)
        assert execution.status == ExecutionState.COMPLETED.value
        assert execution.completed_at is not None

    def test_transition_running_to_failed_with_error(self, db_session):
        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.RUNNING.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        result = ExecutionStateService.transition(
            db_session, execution.id, ExecutionState.FAILED, error_log="Node failed"
        )
        assert result is True

        db_session.refresh(execution)
        assert execution.status == ExecutionState.FAILED.value
        assert execution.error_log == "Node failed"

    def test_transition_running_to_retrying(self, db_session):
        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.RUNNING.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        result = ExecutionStateService.transition(
            db_session, execution.id, ExecutionState.RETRYING
        )
        assert result is True

        db_session.refresh(execution)
        assert execution.status == ExecutionState.RETRYING.value

    def test_transition_retrying_to_running(self, db_session):
        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.RETRYING.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        result = ExecutionStateService.transition(
            db_session, execution.id, ExecutionState.RUNNING, worker_id="worker-2"
        )
        assert result is True

        db_session.refresh(execution)
        assert execution.status == ExecutionState.RUNNING.value

    def test_transition_running_to_timed_out(self, db_session):
        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.RUNNING.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        result = ExecutionStateService.transition(
            db_session, execution.id, ExecutionState.TIMED_OUT
        )
        assert result is True

        db_session.refresh(execution)
        assert execution.status == ExecutionState.TIMED_OUT.value

    def test_transition_queued_to_cancelled(self, db_session):
        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.QUEUED.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        result = ExecutionStateService.transition(
            db_session, execution.id, ExecutionState.CANCELLED
        )
        assert result is True

        db_session.refresh(execution)
        assert execution.status == ExecutionState.CANCELLED.value

    def test_transition_running_to_cancelled(self, db_session):
        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.RUNNING.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        result = ExecutionStateService.transition(
            db_session, execution.id, ExecutionState.CANCELLED
        )
        assert result is True

        db_session.refresh(execution)
        assert execution.status == ExecutionState.CANCELLED.value

    # Invalid transitions

    def test_invalid_transition_queued_to_completed(self, db_session):
        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.QUEUED.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        result = ExecutionStateService.transition(
            db_session, execution.id, ExecutionState.COMPLETED
        )
        assert result is False

        db_session.refresh(execution)
        assert execution.status == ExecutionState.QUEUED.value

    def test_invalid_transition_completed_to_running(self, db_session):
        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.COMPLETED.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        result = ExecutionStateService.transition(
            db_session, execution.id, ExecutionState.RUNNING
        )
        assert result is False

        db_session.refresh(execution)
        assert execution.status == ExecutionState.COMPLETED.value

    def test_invalid_transition_failed_to_completed(self, db_session):
        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.FAILED.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        result = ExecutionStateService.transition(
            db_session, execution.id, ExecutionState.COMPLETED
        )
        assert result is False

    # Non-existent execution

    def test_transition_nonexistent_execution(self, db_session):
        result = ExecutionStateService.transition(
            db_session, 99999, ExecutionState.RUNNING
        )
        assert result is False

    # can_transition

    def test_can_transition_valid(self, db_session):
        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.QUEUED.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        assert ExecutionStateService.can_transition(db_session, execution.id, ExecutionState.RUNNING)
        assert ExecutionStateService.can_transition(db_session, execution.id, ExecutionState.CANCELLED)

    def test_can_transition_invalid(self, db_session):
        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.QUEUED.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        assert not ExecutionStateService.can_transition(db_session, execution.id, ExecutionState.COMPLETED)

    # get_state

    def test_get_state(self, db_session):
        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.RUNNING.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        state = ExecutionStateService.get_state(db_session, execution.id)
        assert state == ExecutionState.RUNNING

    def test_get_state_nonexistent(self, db_session):
        state = ExecutionStateService.get_state(db_session, 99999)
        assert state is None

    # is_terminal

    def test_is_terminal_true(self, db_session):
        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.COMPLETED.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        assert ExecutionStateService.is_terminal(db_session, execution.id)

    def test_is_terminal_false(self, db_session):
        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.RUNNING.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        assert not ExecutionStateService.is_terminal(db_session, execution.id)
