"""Execution Planner — determines execution order via topological sort."""

from typing import List, Dict
from dataclasses import dataclass, field
from app.core.workflow_definition import WorkflowNode, WorkflowEdge


@dataclass
class ExecutionStep:
    node_id: str
    depends_on: List[str] = field(default_factory=list)
    can_parallel: bool = False


@dataclass
class ExecutionPlan:
    steps: List[ExecutionStep]
    parallel_groups: List[List[str]]
    execution_order: List[List[str]]

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def max_parallelism(self) -> int:
        return max(len(group) for group in self.execution_order) if self.execution_order else 0


class ExecutionPlanner:
    def __init__(self, nodes: List[WorkflowNode], edges: List[WorkflowEdge]):
        self.nodes = nodes
        self.edges = edges
        self.node_map = {n.id: n for n in nodes}
        self.adj: Dict[str, List[str]] = {n.id: [] for n in nodes}
        self.in_degree: Dict[str, int] = {n.id: 0 for n in nodes}

        for edge in edges:
            self.adj[edge.source_node_id].append(edge.target_node_id)
            self.in_degree[edge.target_node_id] = self.in_degree.get(edge.target_node_id, 0) + 1

    def plan(self) -> ExecutionPlan:
        steps = self._build_steps()
        execution_order = self._topological_levels()
        parallel_groups = [level for level in execution_order if len(level) > 1]

        return ExecutionPlan(
            steps=steps,
            parallel_groups=parallel_groups,
            execution_order=execution_order,
        )

    def _build_steps(self) -> List[ExecutionStep]:
        steps = []
        for node in self.nodes:
            deps = [
                edge.source_node_id
                for edge in self.edges
                if edge.target_node_id == node.id
            ]
            steps.append(ExecutionStep(
                node_id=node.id,
                depends_on=deps,
                can_parallel=len(deps) > 1,
            ))
        return steps

    def _topological_levels(self) -> List[List[str]]:
        in_deg = dict(self.in_degree)
        queue = [nid for nid, deg in in_deg.items() if deg == 0]
        levels: List[List[str]] = []

        while queue:
            levels.append(sorted(queue))
            next_queue = []
            for nid in queue:
                for neighbor in self.adj.get(nid, []):
                    in_deg[neighbor] -= 1
                    if in_deg[neighbor] == 0:
                        next_queue.append(neighbor)
            queue = next_queue

        return levels
