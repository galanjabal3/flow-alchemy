"""Tests for ConditionExecutor."""

import pytest
from app.core.executors.condition import ConditionExecutor
from app.core.execution_context import ExecutionContext


@pytest.fixture
def executor():
    return ConditionExecutor()


@pytest.fixture
def context():
    return ExecutionContext(execution_id="1", workflow_id=1)


class TestConditionOperators:
    @pytest.mark.asyncio
    async def test_equals(self, executor, context):
        result = await executor.execute("n1", {"data": "hello", "operator": "equals", "value": "hello"}, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_not_equals(self, executor, context):
        result = await executor.execute("n1", {"data": "hello", "operator": "not_equals", "value": "world"}, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_greater_than(self, executor, context):
        result = await executor.execute("n1", {"data": 10, "operator": "greater_than", "value": 5}, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_less_than(self, executor, context):
        result = await executor.execute("n1", {"data": 3, "operator": "less_than", "value": 5}, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_greater_equal(self, executor, context):
        result = await executor.execute("n1", {"data": 5, "operator": "greater_equal", "value": 5}, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_less_equal(self, executor, context):
        result = await executor.execute("n1", {"data": 5, "operator": "less_equal", "value": 5}, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_contains(self, executor, context):
        result = await executor.execute("n1", {"data": "hello world", "operator": "contains", "value": "world"}, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_not_contains(self, executor, context):
        result = await executor.execute("n1", {"data": "hello", "operator": "not_contains", "value": "xyz"}, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_starts_with(self, executor, context):
        result = await executor.execute("n1", {"data": "hello", "operator": "starts_with", "value": "hel"}, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_ends_with(self, executor, context):
        result = await executor.execute("n1", {"data": "hello", "operator": "ends_with", "value": "llo"}, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_is_empty(self, executor, context):
        result = await executor.execute("n1", {"data": "", "operator": "is_empty"}, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_is_not_empty(self, executor, context):
        result = await executor.execute("n1", {"data": "hello", "operator": "is_not_empty"}, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_invalid_comparison_returns_false(self, executor, context):
        result = await executor.execute("n1", {"data": "abc", "operator": "greater_than", "value": "def"}, context)
        assert result["result"] is False


class TestConditionExpressions:
    @pytest.mark.asyncio
    async def test_simple_equality(self, executor, context):
        result = await executor.execute("n1", {"data": {"status": "ok"}, "condition": "status == 'ok'"}, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_and_expression(self, executor, context):
        result = await executor.execute("n1", {
            "data": {"a": 1, "b": 2},
            "condition": "a == 1 AND b == 2",
        }, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_or_expression(self, executor, context):
        result = await executor.execute("n1", {
            "data": {"a": 1, "b": 99},
            "condition": "a == 1 OR b == 1",
        }, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_not_expression(self, executor, context):
        result = await executor.execute("n1", {
            "data": {"x": 0},
            "condition": "NOT x == 1",
        }, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_nested_parentheses(self, executor, context):
        result = await executor.execute("n1", {
            "data": {"a": 1, "b": 2},
            "condition": "(a == 1 AND b == 2)",
        }, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_dot_notation_path(self, executor, context):
        result = await executor.execute("n1", {
            "data": {"response": {"status": 200}},
            "condition": "response.status == 200",
        }, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_boolean_literal(self, executor, context):
        result = await executor.execute("n1", {
            "data": {"ok": True},
            "condition": "ok == true",
        }, context)
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_no_condition_uses_operator(self, executor, context):
        result = await executor.execute("n1", {
            "data": "hello",
            "operator": "equals",
            "value": "hello",
        }, context)
        assert result["result"] is True
