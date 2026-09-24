"""Condition Node Executor with improved expression evaluator."""

from typing import Any, Dict
from app.core.executors.base import BaseNodeExecutor
from app.core.execution_context import ExecutionContext


class ConditionExecutor(BaseNodeExecutor):
    async def execute(
        self,
        node_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        data = config.get("data", {})
        condition = config.get("condition", "")
        operator = config.get("operator", "equals")
        value = config.get("value")
        field = config.get("field")

        if condition:
            result = self._eval_expression(data, condition)
        else:
            # If a `field` path is configured (e.g. "ticket.priority"),
            # evaluate the operator against that path inside the input data
            # instead of the whole data object.
            target = self._resolve_path(data, field) if field else data
            result = self._eval_operator(target, operator, value)

        return {
            "result": result,
            "data": data,
        }

    def _eval_operator(self, data: Any, operator: str, value: Any) -> bool:
        try:
            if operator == "equals":
                return data == value
            elif operator == "not_equals":
                return data != value
            elif operator == "greater_than":
                return float(data) > float(value)
            elif operator == "less_than":
                return float(data) < float(value)
            elif operator == "greater_equal":
                return float(data) >= float(value)
            elif operator == "less_equal":
                return float(data) <= float(value)
            elif operator == "contains":
                return str(value) in str(data)
            elif operator == "not_contains":
                return str(value) not in str(data)
            elif operator == "starts_with":
                return str(data).startswith(str(value))
            elif operator == "ends_with":
                return str(data).endswith(str(value))
            elif operator == "is_empty":
                return data is None or data == "" or data == []
            elif operator == "is_not_empty":
                return data is not None and data != "" and data != []
        except (ValueError, TypeError):
            return False
        return False

    def _eval_expression(self, data: Any, condition: str) -> bool:
        """Safe expression evaluator supporting common operators."""
        condition = condition.strip()

        # Handle parenthesized expressions (strip outer parens before AND/OR)
        if condition.startswith("(") and condition.endswith(")"):
            return self._eval_expression(data, condition[1:-1])

        # Handle AND/OR (simple split, not nested)
        if " AND " in condition:
            parts = condition.split(" AND ", 1)
            return self._eval_expression(data, parts[0]) and self._eval_expression(data, parts[1])
        if " OR " in condition:
            parts = condition.split(" OR ", 1)
            return self._eval_expression(data, parts[0]) or self._eval_expression(data, parts[1])

        # Handle NOT
        if condition.startswith("NOT "):
            return not self._eval_expression(data, condition[4:])

        # Comparison operators
        for op in ("===", "!=", "==", "!=", ">=", "<=", ">", "<"):
            if f" {op} " in condition:
                left_str, right_str = condition.split(f" {op} ", 1)
                left_val = self._resolve_path(data, left_str.strip())
                right_val = self._parse_literal(right_str.strip())
                return self._compare(left_val, op, right_val)

        return False

    def _compare(self, left: Any, op: str, right: Any) -> bool:
        try:
            if op in ("===", "=="):
                return str(left) == str(right)
            elif op == "!=":
                return str(left) != str(right)
            elif op == ">":
                return float(left) > float(right)
            elif op == "<":
                return float(left) < float(right)
            elif op == ">=":
                return float(left) >= float(right)
            elif op == "<=":
                return float(left) <= float(right)
        except (ValueError, TypeError):
            return False
        return False

    def _parse_literal(self, value: str) -> Any:
        """Parse a string literal to its Python value."""
        if value.startswith("'") and value.endswith("'"):
            return value[1:-1]
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        if value.lower() == "none" or value.lower() == "null":
            return None
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    def _resolve_path(self, data: Any, path: str) -> Any:
        """Resolve dot-notation path like 'data.status'."""
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current
