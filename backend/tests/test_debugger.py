"""Tests for visual debugger feature."""

import pytest
from datetime import datetime, timezone


class TestDebugManager:
    """Test debug manager."""

    def test_create_session(self):
        from app.core.debugger import debug_manager, DebugState
        from app.core.workflow_definition import WorkflowDefinition, WorkflowNode, WorkflowEdge, NodeType

        definition = WorkflowDefinition(
            nodes=[
                WorkflowNode(id="n1", node_type=NodeType.TRIGGER, config={}),
                WorkflowNode(id="n2", node_type=NodeType.OUTPUT, config={"destination": "log"}),
            ],
            edges=[
                WorkflowEdge(id="e1", source_node_id="n1", target_node_id="n2"),
            ],
        )

        session = debug_manager.create_session(
            execution_id="test-123",
            workflow_id=1,
            user_id=1,
            definition=definition,
        )

        assert session.execution_id == "test-123"
        assert session.state == DebugState.IDLE
        assert len(session.execution_order) > 0

        # Cleanup
        debug_manager.remove_session("test-123")

    def test_add_remove_breakpoint(self):
        from app.core.debugger import debug_manager
        from app.core.workflow_definition import WorkflowDefinition, WorkflowNode, NodeType

        definition = WorkflowDefinition(
            nodes=[WorkflowNode(id="n1", node_type=NodeType.TRIGGER, config={})],
            edges=[],
        )

        session = debug_manager.create_session("test-bp", 1, 1, definition)

        # Add breakpoint
        assert debug_manager.add_breakpoint("test-bp", "n1") is True
        assert debug_manager.has_breakpoint("test-bp", "n1") is True

        # Remove breakpoint
        assert debug_manager.remove_breakpoint("test-bp", "n1") is True
        assert debug_manager.has_breakpoint("test-bp", "n1") is False

        # Cleanup
        debug_manager.remove_session("test-bp")

    def test_get_debug_state(self):
        from app.core.debugger import debug_manager
        from app.core.workflow_definition import WorkflowDefinition, WorkflowNode, NodeType

        definition = WorkflowDefinition(
            nodes=[WorkflowNode(id="n1", node_type=NodeType.TRIGGER, config={})],
            edges=[],
        )

        debug_manager.create_session("test-state", 1, 1, definition)

        state = debug_manager.get_debug_state("test-state")
        assert state is not None
        assert state["execution_id"] == "test-state"
        assert state["state"] == "idle"

        # Cleanup
        debug_manager.remove_session("test-state")

    def test_nonexistent_session(self):
        from app.core.debugger import debug_manager

        assert debug_manager.get_session("nonexistent") is None
        assert debug_manager.get_debug_state("nonexistent") is None
        assert debug_manager.add_breakpoint("nonexistent", "n1") is False
        assert debug_manager.remove_breakpoint("nonexistent", "n1") is False


class TestDebugAPI:
    """Test debug API endpoints."""

    def test_start_debug_not_found(self, client, auth_headers):
        response = client.post(
            "/api/executions/999999/debug",
            headers=auth_headers,
            json={"trigger_data": {}},
        )
        assert response.status_code == 404

    def test_step_debug_not_found(self, client, auth_headers):
        response = client.post("/api/executions/999999/step", headers=auth_headers)
        assert response.status_code == 404

    def test_resume_debug_not_found(self, client, auth_headers):
        response = client.post("/api/executions/999999/resume", headers=auth_headers)
        assert response.status_code == 404

    def test_get_debug_state_not_found(self, client, auth_headers):
        response = client.get("/api/executions/999999/debug-state", headers=auth_headers)
        assert response.status_code == 404

    def test_add_breakpoint_not_found(self, client, auth_headers):
        response = client.post(
            "/api/executions/999999/breakpoint",
            headers=auth_headers,
            json={"node_id": "n1"},
        )
        assert response.status_code == 404

    def test_stop_debug_not_found(self, client, auth_headers):
        response = client.delete("/api/executions/999999/debug", headers=auth_headers)
        assert response.status_code == 404
