"""Tests for async runtime features."""

import pytest
import json
from app.core.job import Job
from app.core.state_machine import StateMachine, ExecutionState, InvalidTransitionError
from app.core.queue import (
    enqueue_job, dequeue_job, requeue_job, move_to_failed_queue,
    is_duplicate_job, get_queue_length, clear_processing_set,
    EXECUTION_QUEUE, FAILED_QUEUE, PROCESSING_SET
)
from app.core.events import ExecutionEvent
from app.core.redis import get_redis


class TestJob:
    """Test Job serialization."""

    def test_job_creation(self):
        """Job can be created with required fields."""
        job = Job(
            execution_id="123",
            workflow_id=1,
            user_id=1,
            trigger_data={"key": "value"},
        )
        assert job.execution_id == "123"
        assert job.workflow_id == 1
        assert job.user_id == 1
        assert job.trigger_data == {"key": "value"}

    def test_job_serialization(self):
        """Job can be serialized to JSON."""
        job = Job(
            execution_id="123",
            workflow_id=1,
            user_id=1,
        )
        json_str = job.to_json()
        data = json.loads(json_str)
        assert data["execution_id"] == "123"
        assert data["workflow_id"] == 1

    def test_job_deserialization(self):
        """Job can be deserialized from JSON."""
        job = Job(
            execution_id="123",
            workflow_id=1,
            user_id=1,
            trigger_data={"key": "value"},
        )
        json_str = job.to_json()
        job2 = Job.from_json(json_str)
        assert job2.execution_id == job.execution_id
        assert job2.workflow_id == job.workflow_id
        assert job2.trigger_data == job.trigger_data

    def test_job_to_dict(self):
        """Job can be converted to dictionary."""
        job = Job(
            execution_id="123",
            workflow_id=1,
            user_id=1,
        )
        data = job.to_dict()
        assert isinstance(data, dict)
        assert data["execution_id"] == "123"


class TestStateMachine:
    """Test execution state machine."""

    def test_initial_state(self):
        """State machine starts in QUEUED state."""
        sm = StateMachine()
        assert sm.state == ExecutionState.QUEUED

    def test_valid_transition_queued_to_running(self):
        """Can transition from QUEUED to RUNNING."""
        sm = StateMachine()
        sm.start()
        assert sm.state == ExecutionState.RUNNING

    def test_valid_transition_running_to_completed(self):
        """Can transition from RUNNING to COMPLETED."""
        sm = StateMachine()
        sm.start()
        sm.complete()
        assert sm.state == ExecutionState.COMPLETED

    def test_valid_transition_running_to_failed(self):
        """Can transition from RUNNING to FAILED."""
        sm = StateMachine()
        sm.start()
        sm.fail()
        assert sm.state == ExecutionState.FAILED

    def test_valid_transition_queued_to_cancelled(self):
        """Can transition from QUEUED to CANCELLED."""
        sm = StateMachine()
        sm.cancel()
        assert sm.state == ExecutionState.CANCELLED

    def test_valid_transition_running_to_cancelled(self):
        """Can transition from RUNNING to CANCELLED."""
        sm = StateMachine()
        sm.start()
        sm.cancel()
        assert sm.state == ExecutionState.CANCELLED

    def test_invalid_transition_completed_to_running(self):
        """Cannot transition from COMPLETED to RUNNING."""
        sm = StateMachine()
        sm.start()
        sm.complete()
        with pytest.raises(InvalidTransitionError):
            sm.start()

    def test_invalid_transition_failed_to_running(self):
        """Cannot transition from FAILED to RUNNING."""
        sm = StateMachine()
        sm.start()
        sm.fail()
        with pytest.raises(InvalidTransitionError):
            sm.start()

    def test_can_transition_check(self):
        """can_transition returns correct boolean."""
        sm = StateMachine()
        assert sm.can_transition(ExecutionState.RUNNING) is True
        assert sm.can_transition(ExecutionState.COMPLETED) is False

    def test_is_terminal(self):
        """Terminal states are correctly identified."""
        sm_queued = StateMachine()
        assert sm_queued.is_terminal() is False

        sm_running = StateMachine(ExecutionState.RUNNING)
        assert sm_running.is_terminal() is False

        sm_completed = StateMachine(ExecutionState.COMPLETED)
        assert sm_completed.is_terminal() is True

        sm_failed = StateMachine(ExecutionState.FAILED)
        assert sm_failed.is_terminal() is True

    def test_history(self):
        """State transitions are recorded in history."""
        sm = StateMachine()
        sm.start()
        sm.complete()
        assert len(sm.history) == 3
        assert sm.history[0] == ExecutionState.QUEUED
        assert sm.history[1] == ExecutionState.RUNNING
        assert sm.history[2] == ExecutionState.COMPLETED

    def test_serialization(self):
        """State machine can be serialized and deserialized."""
        sm = StateMachine()
        sm.start()
        sm.complete()

        data = sm.to_dict()
        sm2 = StateMachine.from_dict(data)
        assert sm2.state == ExecutionState.COMPLETED
        assert len(sm2.history) == 3


class TestExecutionEvent:
    """Test execution events."""

    def test_event_creation(self):
        """Event can be created."""
        event = ExecutionEvent(
            execution_id="123",
            event_type="started",
        )
        assert event.execution_id == "123"
        assert event.event_type == "started"

    def test_event_serialization(self):
        """Event can be serialized to JSON."""
        event = ExecutionEvent(
            execution_id="123",
            event_type="started",
            node_id="node-1",
            data={"key": "value"},
        )
        json_str = event.to_json()
        data = json.loads(json_str)
        assert data["execution_id"] == "123"
        assert data["event_type"] == "started"
        assert data["node_id"] == "node-1"
        assert data["data"] == {"key": "value"}


class TestQueueWithRedis:
    """Test queue operations with Redis (integration tests)."""

    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self):
        """Job can be enqueued and dequeued."""
        # Clean up first
        client = await get_redis()
        await client.delete(EXECUTION_QUEUE)

        job = Job(
            execution_id="123",
            workflow_id=1,
            user_id=1,
        )

        # Enqueue
        success = await enqueue_job(job)
        assert success is True

        # Check queue length
        length = await get_queue_length()
        assert length == 1

        # Dequeue
        dequeued_job = await dequeue_job()
        assert dequeued_job is not None
        assert dequeued_job.execution_id == "123"

        # Queue should be empty
        length = await get_queue_length()
        assert length == 0

    @pytest.mark.asyncio
    async def test_requeue(self):
        """Job can be requeued for retry."""
        client = await get_redis()
        await client.delete(EXECUTION_QUEUE)

        job = Job(
            execution_id="456",
            workflow_id=1,
            user_id=1,
            retry_count=1,
            max_retries=3,
        )

        # Requeue
        success = await requeue_job(job)
        assert success is True

        # Dequeue
        dequeued_job = await dequeue_job()
        assert dequeued_job is not None
        assert dequeued_job.retry_count == 1

    @pytest.mark.asyncio
    async def test_move_to_failed_queue(self):
        """Job can be moved to failed queue."""
        client = await get_redis()
        await client.delete(FAILED_QUEUE)

        job = Job(
            execution_id="789",
            workflow_id=1,
            user_id=1,
        )

        # Move to failed
        success = await move_to_failed_queue(job, "Test error")
        assert success is True

        # Check failed queue
        failed_json = await client.lpop(FAILED_QUEUE)
        assert failed_json is not None
        failed_job = Job.from_json(failed_json)
        assert failed_job.execution_id == "789"

    @pytest.mark.asyncio
    async def test_idempotency_check(self):
        """Idempotency key is tracked."""
        client = await get_redis()
        key = "test-idempotency-key"

        # Clean up
        await client.srem(PROCESSING_SET, key)

        # Check - should not exist
        exists = await is_duplicate_job(key)
        assert exists is False

        # Add to processing set
        await client.sadd(PROCESSING_SET, key)

        # Check - should exist
        exists = await is_duplicate_job(key)
        assert exists is True

        # Clean up
        await clear_processing_set(key)


class TestRedisConnection:
    """Test Redis connection."""

    @pytest.mark.asyncio
    async def test_redis_ping(self):
        """Redis can be pinged."""
        from app.core.redis import redis_ping
        result = await redis_ping()
        assert result is True
