"""Transform Node Executor."""

from typing import Any, Dict
from app.core.executors.base import BaseNodeExecutor
from app.core.execution_context import ExecutionContext


class TransformExecutor(BaseNodeExecutor):
    async def execute(
        self,
        node_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        data = config.get("data", {})
        operation = config.get("operation", "identity")
        params = config.get("params", {})

        if operation == "identity":
            result = data
        elif operation == "filter":
            result = self._filter(data, params)
        elif operation == "map":
            result = self._map(data, params)
        elif operation == "merge":
            result = self._merge(data, params)
        elif operation == "split":
            result = self._split(data, params)
        else:
            result = data

        return {"data": result}

    def _filter(self, data: Any, params: Dict[str, Any]) -> Any:
        if isinstance(data, list):
            key = params.get("key")
            value = params.get("value")
            if key and value is not None:
                return [item for item in data if item.get(key) == value]
        return data

    def _map(self, data: Any, params: Dict[str, Any]) -> Any:
        if isinstance(data, list):
            field = params.get("field")
            if field:
                return [item.get(field) for item in data if isinstance(item, dict)]
        return data

    def _merge(self, data: Any, params: Dict[str, Any]) -> Any:
        sources = params.get("sources", [])
        if isinstance(data, dict):
            return {**data, **{k: v for s in sources for k, v in s.items()}}
        return data

    def _split(self, data: Any, params: Dict[str, Any]) -> Any:
        delimiter = params.get("delimiter", ",")
        if isinstance(data, str):
            return data.split(delimiter)
        return data
