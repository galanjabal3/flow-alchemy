"""Trigger Node Executor."""

from datetime import datetime, timezone
from typing import Any, Dict
from app.core.executors.base import BaseNodeExecutor
from app.core.execution_context import ExecutionContext


class TriggerExecutor(BaseNodeExecutor):
    async def execute(
        self,
        node_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        return {
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "trigger_data": context.trigger_data,
        }
