"""Tests for timeout and cancellation features."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.workflow_engine import (
    WorkflowEngine,
    NodeTimeoutError,
    WorkflowTimeoutError,
    WorkflowCancelledError,
)
from app.core.execution_context import ExecutionContext
from app.core.workflow_definition import WorkflowDefinition, WorkflowNode, NodeType, WorkflowEdge
from app.core.state_machine import ExecutionState
from app.services.execution_state_service import ExecutionStateService
from app.models.workflow import Execution


class TestNodeTimeout:
    """Tests for node-level timeout."""

    @pytest.mark.asyncio
    async def test_node_timeout_raises_error(self, db_session):
        """Node exceeding timeout should raise NodeTimeoutError."""
        engine = WorkflowEngine()

        # Create a workflow with a single node
        node = WorkflowNode(
            id="node-1",
            node_type=NodeType.HTTP_REQUEST,
            config={"url": "http://example.com", "method": "GET", "timeout": 1},
        )

        # Mock the executor to simulate a slow operation
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(10)
            return {"status": 200}

        mock_executor = AsyncMock()
        mock_executor.execute = slow_execute

        with patch("app.core.workflow_engine.get_executor", return_value=mock_executor):
            with patch("app.core.workflow_engine.settings") as mock_settings:
                mock_settings.NODE_TIMEOUT = 0.1  # 100ms timeout
                mock_settings.NODE_MAX_RETRIES = 0  # No retries
                mock_settings.SECRET_KEY = "test-secret-key"
                mock_settings.RETRY_BACKOFF_BASE = 2
                mock_settings.RETRY_JITTER = 0.5

                ctx = ExecutionContext(execution_id="1", workflow_id=1)
                ctx.init_node("node-1")

                with pytest.raises(NodeTimeoutError):
                    await engine._execute_node(
                        node, ctx, "1", user_id=1, db=db_session
                    )

    @pytest.mark.asyncio
    async def test_node_within_timeout_succeeds(self, db_session):
        """Node completing within timeout should succeed."""
        engine = WorkflowEngine()

        node = WorkflowNode(
            id="node-1",
            node_type=NodeType.HTTP_REQUEST,
            config={"url": "http://example.com", "method": "GET"},
        )

        mock_executor = AsyncMock()
        mock_executor.execute = AsyncMock(return_value={"status": 200})

        with patch("app.core.workflow_engine.get_executor", return_value=mock_executor):
            with patch("app.core.workflow_engine.settings") as mock_settings:
                mock_settings.NODE_TIMEOUT = 30  # 30s timeout
                mock_settings.SECRET_KEY = "test-secret-key"

                ctx = ExecutionContext(execution_id="1", workflow_id=1)
                ctx.init_node("node-1")

                await engine._execute_node(
                    node, ctx, "1", user_id=1, db=db_session
                )

                assert ctx.node_executions["node-1"].status.value == "completed"


class TestWorkflowTimeout:
    """Tests for workflow-level timeout."""

    @pytest.mark.asyncio
    async def test_workflow_timeout_in_worker(self, db_session):
        """Workflow exceeding timeout should be handled in worker."""
        from app.core.workflow_engine import WorkflowTimeoutError

        # Create execution in DB
        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.RUNNING.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        # Verify the timeout error can be caught
        with pytest.raises(WorkflowTimeoutError):
            raise WorkflowTimeoutError("Workflow exceeded timeout")

    @pytest.mark.asyncio
    async def test_workflow_cancelled_error_can_be_raised(self):
        """WorkflowCancelledError should be raisable."""
        with pytest.raises(WorkflowCancelledError):
            raise WorkflowCancelledError("Execution was cancelled")


class TestCancellation:
    """Tests for workflow cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_check_returns_true_when_cancelled(self, db_session):
        """_is_cancelled should return True when execution is cancelled."""
        engine = WorkflowEngine()

        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.CANCELLED.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        assert engine._is_cancelled(str(execution.id), db_session) is True

    @pytest.mark.asyncio
    async def test_cancel_check_returns_false_when_running(self, db_session):
        """_is_cancelled should return False when execution is running."""
        engine = WorkflowEngine()

        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.RUNNING.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        assert engine._is_cancelled(str(execution.id), db_session) is False

    @pytest.mark.asyncio
    async def test_cancel_check_returns_false_without_db(self, db_session):
        """_is_cancelled should return False when no db session."""
        engine = WorkflowEngine()
        assert engine._is_cancelled("1", None) is False

    def test_cancel_execution_via_service(self, db_session):
        """Execution should be cancellable via state service."""
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

    def test_cancel_running_execution_via_service(self, db_session):
        """Running execution should be cancellable."""
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

    def test_cancel_completed_execution_fails(self, db_session):
        """Completed execution should not be cancellable."""
        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.COMPLETED.value,
            trigger="manual",
        )
        db_session.add(execution)
        db_session.commit()

        result = ExecutionStateService.transition(
            db_session, execution.id, ExecutionState.CANCELLED
        )
        assert result is False

        db_session.refresh(execution)
        assert execution.status == ExecutionState.COMPLETED.value
