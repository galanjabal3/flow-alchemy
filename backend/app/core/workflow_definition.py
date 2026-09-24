"""Canonical Workflow Definition format.

This module defines the internal representation of a workflow,
independent from any frontend library (React Flow, etc.).

Architecture:
    React Flow (UI) → Adapter → FlowAlchemy Definition → Execution Engine

The canonical format is what gets stored in the database and used
by the execution engine.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class NodeType(str, Enum):
    TRIGGER = "trigger"
    HTTP_REQUEST = "http_request"
    TRANSFORM = "transform"
    CONDITION = "condition"
    DELAY = "delay"
    OUTPUT = "output"


class NodePosition(BaseModel):
    x: float = 0.0
    y: float = 0.0


class WorkflowNode(BaseModel):
    id: str
    node_type: NodeType
    config: Dict[str, Any] = Field(default_factory=dict)
    position: NodePosition = Field(default_factory=NodePosition)


class WorkflowEdge(BaseModel):
    id: str
    source_node_id: str
    target_node_id: str
    condition: Optional[str] = None


class WorkflowDefinition(BaseModel):
    """Canonical workflow definition format.

    This is the source of truth for a workflow's structure.
    The frontend (React Flow) converts to/from this format via an adapter.

    Example:
        {
            "nodes": [
                {"id": "n1", "node_type": "trigger", "config": {}},
                {"id": "n2", "node_type": "http_request", "config": {"url": "...", "method": "GET"}},
                {"id": "n3", "node_type": "output", "config": {"destination": "webhook"}}
            ],
            "edges": [
                {"id": "e1", "source_node_id": "n1", "target_node_id": "n2"},
                {"id": "e2", "source_node_id": "n2", "target_node_id": "n3"}
            ]
        }
    """
    nodes: List[WorkflowNode] = Field(default_factory=list)
    edges: List[WorkflowEdge] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_node_by_id(self, node_id: str) -> Optional[WorkflowNode]:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_edges_from_node(self, node_id: str) -> List[WorkflowEdge]:
        return [e for e in self.edges if e.source_node_id == node_id]

    def get_edges_to_node(self, node_id: str) -> List[WorkflowEdge]:
        return [e for e in self.edges if e.target_node_id == node_id]

    def get_root_nodes(self) -> List[WorkflowNode]:
        """Nodes with no incoming edges (entry points)."""
        targets = {e.target_node_id for e in self.edges}
        return [n for n in self.nodes if n.id not in targets]

    def to_dict(self) -> dict:
        return self.model_dump()
