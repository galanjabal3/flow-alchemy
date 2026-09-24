"""Tests for WorkflowAdapter (React Flow ↔ canonical format)."""

import pytest
from app.core.workflow_adapter import react_flow_to_definition, definition_to_react_flow
from app.core.workflow_definition import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowEdge,
    NodePosition,
    NodeType,
)


class TestReactFlowToDefinition:
    def test_empty_workflow(self):
        result = react_flow_to_definition({"nodes": [], "edges": []})
        assert len(result.nodes) == 0
        assert len(result.edges) == 0

    def test_single_trigger_node(self):
        rf_data = {
            "nodes": [
                {"id": "1", "type": "trigger", "position": {"x": 0, "y": 0}, "data": {"label": "Start"}}
            ],
            "edges": [],
        }
        result = react_flow_to_definition(rf_data)
        assert len(result.nodes) == 1
        assert result.nodes[0].id == "1"
        assert result.nodes[0].node_type == NodeType.TRIGGER
        assert result.nodes[0].position.x == 0

    def test_http_request_node(self):
        rf_data = {
            "nodes": [
                {"id": "1", "type": "http_request", "data": {"url": "http://example.com", "method": "GET"}}
            ],
            "edges": [],
        }
        result = react_flow_to_definition(rf_data)
        assert result.nodes[0].node_type == NodeType.HTTP_REQUEST
        assert result.nodes[0].config["url"] == "http://example.com"

    def test_node_type_fallback(self):
        """Unknown node type should fallback to TRIGGER."""
        rf_data = {
            "nodes": [{"id": "1", "type": "unknown_type", "data": {}}],
            "edges": [],
        }
        result = react_flow_to_definition(rf_data)
        assert result.nodes[0].node_type == NodeType.TRIGGER

    def test_datanode_type_takes_priority(self):
        """data.nodeType should take priority over type attribute."""
        rf_data = {
            "nodes": [
                {"id": "1", "type": "custom", "data": {"nodeType": "http_request", "url": "http://test.com"}}
            ],
            "edges": [],
        }
        result = react_flow_to_definition(rf_data)
        assert result.nodes[0].node_type == NodeType.HTTP_REQUEST

    def test_edges_conversion(self):
        rf_data = {
            "nodes": [
                {"id": "1", "type": "trigger", "data": {}},
                {"id": "2", "type": "http_request", "data": {}},
            ],
            "edges": [
                {"id": "e1", "source": "1", "target": "2", "label": "success"}
            ],
        }
        result = react_flow_to_definition(rf_data)
        assert len(result.edges) == 1
        assert result.edges[0].source_node_id == "1"
        assert result.edges[0].target_node_id == "2"
        assert result.edges[0].condition == "success"

    def test_missing_position_defaults_zero(self):
        rf_data = {
            "nodes": [{"id": "1", "type": "trigger", "data": {}}],
            "edges": [],
        }
        result = react_flow_to_definition(rf_data)
        assert result.nodes[0].position.x == 0
        assert result.nodes[0].position.y == 0

    def test_full_workflow(self):
        rf_data = {
            "nodes": [
                {"id": "1", "type": "trigger", "position": {"x": 100, "y": 200}, "data": {"event": "manual"}},
                {"id": "2", "type": "http_request", "position": {"x": 300, "y": 200}, "data": {"url": "http://api.example.com"}},
                {"id": "3", "type": "output", "position": {"x": 500, "y": 200}, "data": {"destination": "webhook"}},
            ],
            "edges": [
                {"id": "e1", "source": "1", "target": "2"},
                {"id": "e2", "source": "2", "target": "3", "label": "success"},
            ],
        }
        result = react_flow_to_definition(rf_data)
        assert len(result.nodes) == 3
        assert len(result.edges) == 2
        assert result.nodes[0].node_type == NodeType.TRIGGER
        assert result.nodes[1].node_type == NodeType.HTTP_REQUEST
        assert result.nodes[2].node_type == NodeType.OUTPUT


class TestDefinitionToReactFlow:
    def test_roundtrip(self):
        """Convert to canonical and back should preserve data."""
        rf_data = {
            "nodes": [
                {"id": "1", "type": "trigger", "position": {"x": 0, "y": 0}, "data": {"event": "manual"}},
            ],
            "edges": [],
        }
        canonical = react_flow_to_definition(rf_data)
        back = definition_to_react_flow(canonical)

        assert len(back["nodes"]) == 1
        assert back["nodes"][0]["id"] == "1"
        assert back["nodes"][0]["type"] == "trigger"

    def test_edges_with_condition(self):
        canonical = WorkflowDefinition(
            nodes=[],
            edges=[
                WorkflowEdge(id="e1", source_node_id="1", target_node_id="2", condition="status == 200")
            ],
        )
        back = definition_to_react_flow(canonical)
        assert back["edges"][0]["label"] == "status == 200"
        assert back["edges"][0]["data"]["condition"] == "status == 200"
