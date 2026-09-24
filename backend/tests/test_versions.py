"""Tests for versioning and replay features."""

import pytest
from datetime import datetime


class TestWorkflowVersion:
    """Test workflow versioning schemas."""

    def test_version_response_fields(self):
        from app.schemas.workflow import WorkflowVersionResponse
        now = datetime.utcnow()
        v = WorkflowVersionResponse(
            id=1, workflow_id=1, version=1,
            definition={"nodes": [], "edges": []},
            change_summary="Initial", created_by=1, created_at=now,
        )
        assert v.version == 1
        assert v.change_summary == "Initial"

    def test_version_diff_fields(self):
        from app.schemas.workflow import WorkflowVersionResponse, WorkflowVersionDiff
        now = datetime.utcnow()
        va = WorkflowVersionResponse(
            id=1, workflow_id=1, version=1,
            definition={"nodes": [], "edges": []},
            change_summary="v1", created_by=1, created_at=now,
        )
        vb = WorkflowVersionResponse(
            id=2, workflow_id=1, version=2,
            definition={"nodes": [], "edges": []},
            change_summary="v2", created_by=1, created_at=now,
        )
        diff = WorkflowVersionDiff(
            version_a=va, version_b=vb,
            added_nodes=["n2"], removed_nodes=["n1"],
            modified_nodes=[], added_edges=[], removed_edges=[],
        )
        assert diff.added_nodes == ["n2"]
        assert diff.removed_nodes == ["n1"]

    def test_version_create_schema(self):
        from app.schemas.workflow import WorkflowVersionCreate
        v = WorkflowVersionCreate(change_summary="Test change")
        assert v.change_summary == "Test change"

    def test_version_create_no_summary(self):
        from app.schemas.workflow import WorkflowVersionCreate
        v = WorkflowVersionCreate()
        assert v.change_summary is None


class TestReplayAPI:
    """Test replay API endpoints."""

    def test_replay_requires_valid_execution(self, client, auth_headers):
        response = client.post("/api/executions/999999/replay", headers=auth_headers)
        assert response.status_code == 404

    def test_replay_with_input_requires_valid_execution(self, client, auth_headers):
        response = client.post(
            "/api/executions/999999/replay-with-input",
            headers=auth_headers,
            json={"key": "value"},
        )
        assert response.status_code == 404
