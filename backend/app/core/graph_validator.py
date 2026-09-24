"""Graph Validator — validates workflow definition before execution.

Checks:
1. Has at least one trigger node
2. All nodes are connected (no orphans)
3. No cycles
4. All edges reference valid nodes
"""

from typing import List, Dict, Set
from app.core.workflow_definition import WorkflowNode, WorkflowEdge


class GraphValidationError(Exception):
    def __init__(self, message: str, errors: List[str] = None):
        self.message = message
        self.errors = errors or []
        super().__init__(self.message)


class GraphValidator:
    def __init__(self, nodes: List[WorkflowNode], edges: List[WorkflowEdge]):
        self.nodes = nodes
        self.edges = edges
        self.node_map = {n.id: n for n in nodes}
        self.errors: List[str] = []

    def validate(self) -> None:
        self._check_empty()
        self._check_trigger_exists()
        self._check_edges_reference_valid_nodes()
        self._check_no_orphans()
        self._check_no_cycles()

        if self.errors:
            raise GraphValidationError(
                f"Workflow validation failed with {len(self.errors)} error(s)",
                self.errors,
            )

    def _check_empty(self) -> None:
        if len(self.nodes) == 0:
            self.errors.append("Workflow has no nodes")

    def _check_trigger_exists(self) -> None:
        triggers = [n for n in self.nodes if n.node_type.value == "trigger"]
        if len(triggers) == 0:
            self.errors.append("Workflow must have at least one trigger node")
        elif len(triggers) > 1:
            self.errors.append("Workflow can only have one trigger node")

    def _check_edges_reference_valid_nodes(self) -> None:
        node_ids = set(self.node_map.keys())
        for edge in self.edges:
            if edge.source_node_id not in node_ids:
                self.errors.append(f"Edge '{edge.id}' references unknown source node '{edge.source_node_id}'")
            if edge.target_node_id not in node_ids:
                self.errors.append(f"Edge '{edge.id}' references unknown target node '{edge.target_node_id}'")

    def _check_no_orphans(self) -> None:
        connected: Set[str] = set()
        for edge in self.edges:
            connected.add(edge.source_node_id)
            connected.add(edge.target_node_id)

        for node in self.nodes:
            if node.id not in connected:
                self.errors.append(f"Node '{node.id}' is not connected to any other node")

    def _check_no_cycles(self) -> None:
        adj: Dict[str, List[str]] = {n.id: [] for n in self.nodes}
        for edge in self.edges:
            if edge.source_node_id in adj:
                adj[edge.source_node_id].append(edge.target_node_id)

        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n.id: WHITE for n in self.nodes}
        cycle_nodes: List[str] = []

        def dfs(node_id: str) -> bool:
            color[node_id] = GRAY
            for neighbor in adj.get(node_id, []):
                if color.get(neighbor) == GRAY:
                    cycle_nodes.append(neighbor)
                    return True
                if color.get(neighbor) == WHITE:
                    if dfs(neighbor):
                        return True
            color[node_id] = BLACK
            return False

        for node in self.nodes:
            if color[node.id] == WHITE:
                if dfs(node.id):
                    self.errors.append(f"Cycle detected involving node '{cycle_nodes[0]}'")
                    return


def validate_graph(nodes: List[WorkflowNode], edges: List[WorkflowEdge]) -> None:
    GraphValidator(nodes, edges).validate()
