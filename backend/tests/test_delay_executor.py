"""Tests for DelayExecutor."""

import pytest
import asyncio
import time
from app.core.executors.delay import DelayExecutor
from app.core.execution_context import ExecutionContext


@pytest.fixture
def executor():
    return DelayExecutor()


@pytest.fixture
def context():
    return ExecutionContext(execution_id="1", workflow_id=1)


class TestDelayExecutor:
    @pytest.mark.asyncio
    async def test_delay_zero_ms(self, executor, context):
        """Zero delay should complete instantly."""
        start = time.monotonic()
        result = await executor.execute("n1", {"duration_ms": 0, "data": {"key": "value"}}, context)
        elapsed = time.monotonic() - start
        assert elapsed < 0.1
        assert result["data"] == {"key": "value"}
        assert "delayed_at" in result

    @pytest.mark.asyncio
    async def test_delay_short(self, executor, context):
        """Short delay should wait approximately the specified time."""
        start = time.monotonic()
        result = await executor.execute("n1", {"duration_ms": 100, "data": {}}, context)
        elapsed = time.monotonic() - start
        assert elapsed >= 0.08  # Allow some tolerance
        assert "delayed_at" in result

    @pytest.mark.asyncio
    async def test_delay_negative_clamps_to_zero(self, executor, context):
        """Negative duration should be clamped to 0."""
        start = time.monotonic()
        result = await executor.execute("n1", {"duration_ms": -1000, "data": {}}, context)
        elapsed = time.monotonic() - start
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_delay_exceeds_max_clamps(self, executor, context, monkeypatch):
        """Duration > 5min should be clamped to 5min (verified without waiting 5 min)."""
        waits = []

        async def fake_sleep(seconds):
            waits.append(seconds)

        monkeypatch.setattr("asyncio.sleep", fake_sleep)
        start = time.monotonic()
        result = await executor.execute("n1", {"duration_ms": 999999, "data": {}}, context)
        elapsed = time.monotonic() - start
        assert elapsed < 1.0  # did not actually wait
        assert waits == [300.0]  # clamped to 5 minutes
        assert "delayed_at" in result

    @pytest.mark.asyncio
    async def test_delay_invalid_type(self, executor, context):
        """Non-numeric duration should default to 1000ms."""
        result = await executor.execute("n1", {"duration_ms": "invalid", "data": {}}, context)
        assert "delayed_at" in result

    @pytest.mark.asyncio
    async def test_delay_none_duration(self, executor, context):
        """Missing duration should default to 1000ms."""
        result = await executor.execute("n1", {"data": {}}, context)
        assert "delayed_at" in result
