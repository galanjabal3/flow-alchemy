"""Base Node Executor — abstract base for all node type executors."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from app.core.execution_context import ExecutionContext


class BaseNodeExecutor(ABC):
    """Base class for node executors. Each node type implements its own executor."""

    @abstractmethod
    async def execute(
        self,
        node_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """Execute this node.

        Args:
            node_id: The ID of the node being executed
            config: The node's configuration (from workflow definition)
            context: The execution context for this run

        Returns:
            Node output data dict
        """
        ...

    def resolve_input(
        self,
        node_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """Resolve input by merging config with upstream outputs.

        Override this to customize input resolution.
        """
        return config
