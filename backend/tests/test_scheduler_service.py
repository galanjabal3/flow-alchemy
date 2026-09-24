"""Tests for SchedulerService."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from app.services.scheduler_service import SchedulerService
from app.models.workflow import Workflow, Execution


@pytest.fixture
def scheduler():
    return SchedulerService()


def _make_workflow(db_session, **kwargs):
    """Create a workflow with a unique ID to avoid conflicts."""
    import random
    wf_id = random.randint(10000, 99999)
    defaults = {
        "id": wf_id,
        "user_id": 1,
        "name": f"Test-{wf_id}",
        "is_active": True,
        "definition": {"nodes": [], "edges": []},
    }
    defaults.update(kwargs)
    workflow = Workflow(**defaults)
    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)
    return workflow


class TestValidateCron:
    def test_valid_cron(self, scheduler):
        is_valid, msg = scheduler.validate_cron("0 9 * * 1-5")
        assert is_valid is True
        assert msg == ""

    def test_invalid_cron(self, scheduler):
        is_valid, msg = scheduler.validate_cron("invalid")
        assert is_valid is False
        assert "Invalid" in msg

    def test_too_frequent(self, scheduler):
        is_valid, msg = scheduler.validate_cron("* * * * *")
        assert is_valid is False
        assert "too frequent" in msg.lower()


class TestGetNextRun:
    def test_returns_future_datetime(self, scheduler):
        now = datetime.now(timezone.utc)
        next_run = scheduler.get_next_run("0 9 * * 1-5", now)
        assert next_run > now

    def test_consistent_results(self, scheduler):
        now = datetime.now(timezone.utc)
        next1 = scheduler.get_next_run("0 9 * * 1-5", now)
        next2 = scheduler.get_next_run("0 9 * * 1-5", now)
        assert next1 == next2


class TestSetSchedule:
    def test_sets_schedule(self, scheduler, db_session):
        workflow = _make_workflow(db_session)

        result = scheduler.set_schedule(db_session, workflow, "0 9 * * 1-5")
        assert result["schedule"] == "0 9 * * 1-5"
        assert "next_run_at" in result

    def test_invalid_schedule_raises(self, scheduler, db_session):
        workflow = _make_workflow(db_session)

        with pytest.raises(ValueError, match="Invalid cron"):
            scheduler.set_schedule(db_session, workflow, "invalid")


class TestRemoveSchedule:
    def test_removes_schedule(self, scheduler, db_session):
        workflow = _make_workflow(db_session, schedule="0 9 * * 1-5")

        scheduler.remove_schedule(db_session, workflow)
        assert workflow.schedule is None


class TestExecuteScheduledWorkflow:
    @pytest.mark.asyncio
    async def test_inactive_workflow_returns_none(self, scheduler, db_session):
        workflow = _make_workflow(db_session, is_active=False)

        result = await scheduler.execute_scheduled_workflow(db_session, workflow)
        assert result is None

    @pytest.mark.asyncio
    async def test_concurrency_limit_per_user(self, scheduler, db_session):
        workflow = _make_workflow(db_session)

        for i in range(5):
            ex = Execution(
                workflow_id=workflow.id, user_id=1, status="running",
                trigger="test", input_data={},
            )
            db_session.add(ex)
        db_session.commit()

        with patch("app.services.scheduler_service.settings") as mock_settings:
            mock_settings.MAX_CONCURRENT_PER_USER = 5
            mock_settings.MAX_CONCURRENT_TOTAL = 10

            result = await scheduler.execute_scheduled_workflow(db_session, workflow)
            assert result is None

    @pytest.mark.asyncio
    async def test_success_creates_execution(self, scheduler, db_session):
        workflow = _make_workflow(db_session)

        # Patch at the module level to avoid with_for_update issues with SQLite
        original_query = db_session.query

        def mock_query(*args, **kwargs):
            return original_query(*args, **kwargs)

        with patch("app.services.scheduler_service.settings") as mock_settings:
            mock_settings.MAX_CONCURRENT_PER_USER = 999
            mock_settings.MAX_CONCURRENT_TOTAL = 999
            mock_settings.MAX_RETRIES = 3

            with patch("app.services.scheduler_service.enqueue_job", new_callable=AsyncMock) as mock_enqueue:
                mock_enqueue.return_value = True

                with patch("app.services.scheduler_service.publish_event", new_callable=AsyncMock):
                    result = await scheduler.execute_scheduled_workflow(db_session, workflow)

        assert result is not None
        execution = db_session.query(Execution).filter(Execution.id == int(result)).first()
        assert execution.status == "queued"
        assert execution.trigger == "schedule"
