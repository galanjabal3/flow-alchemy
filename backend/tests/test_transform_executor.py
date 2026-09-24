"""Tests for TransformExecutor."""

import pytest
from app.core.executors.transform import TransformExecutor
from app.core.execution_context import ExecutionContext


@pytest.fixture
def executor():
    return TransformExecutor()


@pytest.fixture
def context():
    return ExecutionContext(execution_id="1", workflow_id=1)


class TestTransformIdentity:
    @pytest.mark.asyncio
    async def test_identity_returns_data(self, executor, context):
        result = await executor.execute("n1", {"data": {"key": "value"}, "operation": "identity"}, context)
        assert result["data"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_unknown_operation_returns_data(self, executor, context):
        result = await executor.execute("n1", {"data": [1, 2, 3], "operation": "unknown"}, context)
        assert result["data"] == [1, 2, 3]


class TestTransformFilter:
    @pytest.mark.asyncio
    async def test_filter_by_key_value(self, executor, context):
        data = [
            {"name": "Alice", "active": True},
            {"name": "Bob", "active": False},
            {"name": "Charlie", "active": True},
        ]
        params = {"key": "active", "value": True}
        result = await executor.execute("n1", {"data": data, "operation": "filter", "params": params}, context)
        assert len(result["data"]) == 2
        assert all(item["active"] is True for item in result["data"])

    @pytest.mark.asyncio
    async def test_filter_non_list_returns_data(self, executor, context):
        result = await executor.execute("n1", {"data": "not a list", "operation": "filter", "params": {"key": "x", "value": 1}}, context)
        assert result["data"] == "not a list"


class TestTransformMap:
    @pytest.mark.asyncio
    async def test_map_extracts_field(self, executor, context):
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        params = {"field": "name"}
        result = await executor.execute("n1", {"data": data, "operation": "map", "params": params}, context)
        assert result["data"] == ["Alice", "Bob"]

    @pytest.mark.asyncio
    async def test_map_non_list(self, executor, context):
        result = await executor.execute("n1", {"data": 42, "operation": "map", "params": {"field": "x"}}, context)
        assert result["data"] == 42


class TestTransformMerge:
    @pytest.mark.asyncio
    async def test_merge_dicts(self, executor, context):
        data = {"a": 1}
        params = {"sources": [{"b": 2}, {"c": 3}]}
        result = await executor.execute("n1", {"data": data, "operation": "merge", "params": params}, context)
        assert result["data"] == {"a": 1, "b": 2, "c": 3}

    @pytest.mark.asyncio
    async def test_merge_non_dict(self, executor, context):
        result = await executor.execute("n1", {"data": [1], "operation": "merge", "params": {"sources": []}}, context)
        assert result["data"] == [1]


class TestTransformSplit:
    @pytest.mark.asyncio
    async def test_split_string(self, executor, context):
        result = await executor.execute("n1", {"data": "a,b,c", "operation": "split", "params": {"delimiter": ","}}, context)
        assert result["data"] == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_split_default_delimiter(self, executor, context):
        result = await executor.execute("n1", {"data": "x-y-z", "operation": "split", "params": {}}, context)
        assert result["data"] == ["x-y-z"]

    @pytest.mark.asyncio
    async def test_split_non_string(self, executor, context):
        result = await executor.execute("n1", {"data": 42, "operation": "split", "params": {}}, context)
        assert result["data"] == 42
