"""Tests for the Worker class."""

import pytest
import asyncio
import random
from unittest.mock import AsyncMock, MagicMock, patch
from app.worker import Worker
from app.core.job import Job
from app.core.state_machine import ExecutionState
from app.models.workflow import Execution


@pytest.fixture
def worker():
    return Worker()


def _make_execution(db_session, **kwargs):
    """Create an execution with a unique ID."""
    ex_id = random.randint(10000, 99999)
    defaults = {
        "id": ex_id,
        "workflow_id": 1,
        "user_id": 1,
        "status": "queued",
        "trigger": "test",
        "input_data": {},
    }
    defaults.update(kwargs)
    execution = Execution(**defaults)
    db_session.add(execution)
    db_session.commit()
    db_session.refresh(execution)
    return execution


@pytest.fixture
def mock_job():
    return Job(
        execution_id="99999",
        workflow_id=1,
        user_id=1,
        trigger_data={"source": "test"},
        idempotency_key="test-key-123",
        max_retries=2,
    )


class TestWorkerProcessJob:
    @pytest.mark.asyncio
    async def test_process_job_execution_not_found(self, worker, db_session):
        """Should return False when execution not found."""
        job = Job(
            execution_id="99999",
            workflow_id=1,
            user_id=1,
            trigger_data={},
            max_retries=2,
        )
        with patch("app.worker.SessionLocal", return_value=db_session):
            with patch("app.worker.publish_event", new_callable=AsyncMock):
                result = await worker.process_job(job)
        assert result is False

    @pytest.mark.asyncio
    async def test_process_job_terminal_skips(self, worker, db_session):
        """Should return True if execution already in terminal state."""
        execution = _make_execution(db_session, status="completed")

        job = Job(
            execution_id=str(execution.id),
            workflow_id=1,
            user_id=1,
            trigger_data={},
            max_retries=2,
        )

        with patch("app.worker.SessionLocal", return_value=db_session):
            with patch("app.worker.publish_event", new_callable=AsyncMock):
                with patch("app.worker.ExecutionStateService") as mock_sm:
                    mock_sm.is_terminal.return_value = True
                    result = await worker.process_job(job)

        assert result is True

    @pytest.mark.asyncio
    async def test_process_job_transition_failure(self, worker, db_session):
        """Should return False when state transition fails."""
        execution = _make_execution(db_session, status="queued")

        job = Job(
            execution_id=str(execution.id),
            workflow_id=1,
            user_id=1,
            trigger_data={},
            max_retries=2,
        )

        with patch("app.worker.SessionLocal", return_value=db_session):
            with patch("app.worker.publish_event", new_callable=AsyncMock):
                with patch("app.worker.ExecutionStateService") as mock_sm:
                    mock_sm.is_terminal.return_value = False
                    mock_sm.transition.return_value = False
                    result = await worker.process_job(job)

        assert result is False
