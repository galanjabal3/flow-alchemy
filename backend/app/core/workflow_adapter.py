"""Adapter to convert between React Flow format and FlowAlchemy canonical format.

Architecture:
    React Flow (UI) → Adapter → FlowAlchemy Definition → Execution Engine
"""

from typing import Dict, Any, List
from app.core.workflow_definition import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowEdge,
    NodePosition,
    NodeType,
)


def react_flow_to_definition(react_flow_data: Dict[str, Any]) -> WorkflowDefinition:
    """Convert React Flow JSON to canonical WorkflowDefinition.

    React Flow format:
        {
            "nodes": [{"id": "1", "type": "http_request", "position": {"x": 0, "y": 0}, "data": {...}}],
            "edges": [{"id": "e1", "source": "1", "target": "2", "label": "..."}]
        }

    Canonical format:
        {
            "nodes": [{"id": "1", "node_type": "http_request", "position": {"x": 0, "y": 0}, "config": {...}}],
            "edges": [{"id": "e1", "source_node_id": "1", "target_node_id": "2", "condition": "..."}]
        }
    """
    nodes = []
    for rf_node in react_flow_data.get("nodes", []):
        # Read actual node type from data.nodeType (UI stores type="custom" for rendering)
        node_type_str = rf_node.get("data", {}).get("nodeType") or rf_node.get("type", "trigger")
        try:
            node_type = NodeType(node_type_str)
        except ValueError:
            node_type = NodeType.TRIGGER

        position = NodePosition(
            x=rf_node.get("position", {}).get("x", 0),
            y=rf_node.get("position", {}).get("y", 0),
        )

        # Canonical config lives at data.config (UI format). Some legacy
        # definitions stored config keys directly on data — support both.
        raw_data = rf_node.get("data", {})
        if isinstance(raw_data, dict):
            if "config" in raw_data:
                config = raw_data.get("config") or {}
            else:
                # Legacy flat format: strip UI-only metadata keys, keep the rest.
                config = {k: v for k, v in raw_data.items() if k not in ("label", "nodeType", "inputSchema")}
        else:
            config = {}

        nodes.append(WorkflowNode(
            id=rf_node["id"],
            node_type=node_type,
            config=config,
            position=position,
        ))

    edges = []
    for rf_edge in react_flow_data.get("edges", []):
        edges.append(WorkflowEdge(
            id=rf_edge["id"],
            source_node_id=rf_edge["source"],
            target_node_id=rf_edge["target"],
            condition=rf_edge.get("label") or rf_edge.get("data", {}).get("condition"),
        ))

    return WorkflowDefinition(nodes=nodes, edges=edges)


def definition_to_react_flow(definition: WorkflowDefinition) -> Dict[str, Any]:
    """Convert canonical WorkflowDefinition to React Flow JSON.

    This is used when loading a workflow from the backend into the UI.
    """
    nodes = []
    for node in definition.nodes:
        rf_node = {
            "id": node.id,
            "type": node.node_type.value,
            "position": {"x": node.position.x, "y": node.position.y},
            "data": node.config,
        }
        nodes.append(rf_node)

    edges = []
    for edge in definition.edges:
        rf_edge = {
            "id": edge.id,
            "source": edge.source_node_id,
            "target": edge.target_node_id,
        }
        if edge.condition:
            rf_edge["label"] = edge.condition
            rf_edge["data"] = {"condition": edge.condition}
        edges.append(rf_edge)

    return {"nodes": nodes, "edges": edges}
