"""Tests for workflow snapshot and version pinning."""

import pytest
from datetime import datetime, timezone
from app.models.workflow import Execution, Workflow
from app.core.state_machine import ExecutionState


class TestWorkflowSnapshot:
    """Tests that execution uses immutable workflow snapshot."""

    def test_execution_has_snapshot(self, db_session):
        """Execution should store workflow definition at time of creation."""
        workflow = Workflow(
            user_id=1,
            name="Test Workflow",
            definition={"nodes": [{"id": "1", "type": "trigger"}], "edges": []},
        )
        db_session.add(workflow)
        db_session.commit()

        definition_snapshot = workflow.definition.copy()
        execution = Execution(
            workflow_id=workflow.id,
            user_id=1,
            status=ExecutionState.QUEUED.value,
            trigger="manual",
            definition_snapshot=definition_snapshot,
        )
        db_session.add(execution)
        db_session.commit()
        db_session.refresh(execution)

        assert execution.definition_snapshot is not None
        assert execution.definition_snapshot == definition_snapshot

    def test_snapshot_is_independent_of_workflow(self, db_session):
        """Editing workflow should not affect existing execution snapshot."""
        workflow = Workflow(
            user_id=1,
            name="Test Workflow",
            definition={"nodes": [{"id": "1", "type": "trigger"}], "edges": []},
        )
        db_session.add(workflow)
        db_session.commit()

        # Create execution with snapshot
        original_snapshot = {"nodes": [{"id": "1", "type": "trigger"}], "edges": []}
        execution = Execution(
            workflow_id=workflow.id,
            user_id=1,
            status=ExecutionState.QUEUED.value,
            trigger="manual",
            definition_snapshot=original_snapshot,
        )
        db_session.add(execution)
        db_session.commit()

        # Edit workflow
        workflow.definition = {"nodes": [{"id": "1", "type": "trigger"}, {"id": "2", "type": "http"}], "edges": []}
        db_session.commit()

        # Snapshot should be unchanged
        db_session.refresh(execution)
        assert execution.definition_snapshot == original_snapshot
        assert len(execution.definition_snapshot["nodes"]) == 1

    def test_execution_without_snapshot_uses_workflow(self, db_session):
        """Legacy executions without snapshot should fall back to workflow definition."""
        workflow = Workflow(
            user_id=1,
            name="Test Workflow",
            definition={"nodes": [{"id": "1", "type": "trigger"}], "edges": []},
        )
        db_session.add(workflow)
        db_session.commit()

        # Create execution without snapshot (legacy)
        execution = Execution(
            workflow_id=workflow.id,
            user_id=1,
            status=ExecutionState.QUEUED.value,
            trigger="manual",
            definition_snapshot=None,
        )
        db_session.add(execution)
        db_session.commit()
        db_session.refresh(execution)

        assert execution.definition_snapshot is None

    def test_multiple_executions_same_workflow(self, db_session):
        """Multiple executions should each have their own snapshot."""
        workflow = Workflow(
            user_id=1,
            name="Test Workflow",
            definition={"nodes": [{"id": "1", "type": "trigger"}], "edges": []},
        )
        db_session.add(workflow)
        db_session.commit()

        # Create first execution
        exec1 = Execution(
            workflow_id=workflow.id,
            user_id=1,
            status=ExecutionState.COMPLETED.value,
            trigger="manual",
            definition_snapshot=workflow.definition.copy(),
        )
        db_session.add(exec1)

        # Edit workflow
        workflow.definition = {"nodes": [{"id": "1", "type": "trigger"}, {"id": "2", "type": "http"}], "edges": []}

        # Create second execution with new definition
        exec2 = Execution(
            workflow_id=workflow.id,
            user_id=1,
            status=ExecutionState.QUEUED.value,
            trigger="manual",
            definition_snapshot=workflow.definition.copy(),
        )
        db_session.add(exec2)
        db_session.commit()

        db_session.refresh(exec1)
        db_session.refresh(exec2)

        assert len(exec1.definition_snapshot["nodes"]) == 1
        assert len(exec2.definition_snapshot["nodes"]) == 2
