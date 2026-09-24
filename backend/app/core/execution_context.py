"""Execution Context — state management for a running workflow execution.

Tracks node outputs, execution status, and errors.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class NodeExecution:
    node_id: str
    status: NodeStatus = NodeStatus.PENDING
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def duration_ms(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None


@dataclass
class ExecutionContext:
    """Manages state during workflow execution."""
    execution_id: str
    workflow_id: int
    trigger_data: Dict[str, Any] = field(default_factory=dict)
    node_executions: Dict[str, NodeExecution] = field(default_factory=dict)
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    _global_vars: Dict[str, Any] = field(default_factory=dict)

    def init_node(self, node_id: str) -> None:
        self.node_executions[node_id] = NodeExecution(node_id=node_id)

    def start_node(self, node_id: str, input_data: Dict[str, Any]) -> None:
        ne = self.node_executions[node_id]
        ne.status = NodeStatus.RUNNING
        ne.input_data = input_data
        ne.started_at = datetime.now(timezone.utc)

    def complete_node(self, node_id: str, output_data: Dict[str, Any]) -> None:
        ne = self.node_executions[node_id]
        ne.status = NodeStatus.COMPLETED
        ne.output_data = output_data
        ne.completed_at = datetime.now(timezone.utc)

    def fail_node(self, node_id: str, error: str) -> None:
        ne = self.node_executions[node_id]
        ne.status = NodeStatus.FAILED
        ne.error = error
        ne.completed_at = datetime.now(timezone.utc)

    def skip_node(self, node_id: str) -> None:
        ne = self.node_executions[node_id]
        ne.status = NodeStatus.SKIPPED
        ne.completed_at = datetime.now(timezone.utc)

    def get_node_output(self, node_id: str) -> Optional[Dict[str, Any]]:
        ne = self.node_executions.get(node_id)
        return ne.output_data if ne else None

    def get_node_input(self, node_id: str) -> Optional[Dict[str, Any]]:
        ne = self.node_executions.get(node_id)
        return ne.input_data if ne else None

    def set_var(self, key: str, value: Any) -> None:
        self._global_vars[key] = value

    def get_var(self, key: str, default: Any = None) -> Any:
        return self._global_vars.get(key, default)

    def start(self) -> None:
        self.status = ExecutionStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def complete(self) -> None:
        self.status = ExecutionStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)

    def fail(self) -> None:
        self.status = ExecutionStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)

    @property
    def duration_ms(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None

    @property
    def summary(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "nodes": {
                nid: {
                    "status": ne.status.value,
                    "duration_ms": ne.duration_ms,
                    "error": ne.error,
                }
                for nid, ne in self.node_executions.items()
            },
        }
