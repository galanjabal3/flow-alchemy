"""Delay Node Executor with type validation."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict
from app.core.executors.base import BaseNodeExecutor
from app.core.execution_context import ExecutionContext


class DelayExecutor(BaseNodeExecutor):
    async def execute(
        self,
        node_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        duration_ms = config.get("duration_ms", 1000)
        data = config.get("data", {})

        try:
            duration_ms = int(duration_ms)
        except (TypeError, ValueError):
            duration_ms = 1000

        if duration_ms < 0:
            duration_ms = 0
        elif duration_ms > 300000:  # 5 minutes max
            duration_ms = 300000

        await asyncio.sleep(duration_ms / 1000)

        return {
            "data": data,
            "delayed_at": datetime.now(timezone.utc).isoformat(),
        }
