"""Job queue abstraction using Redis."""

import structlog
from typing import Optional
from app.core.redis import get_redis
from app.core.job import Job

logger = structlog.get_logger()

# Queue names
EXECUTION_QUEUE = "flowalchemy:executions:pending"
FAILED_QUEUE = "flowalchemy:executions:failed"
PROCESSING_SET = "flowalchemy:executions:processing"


async def enqueue_job(job: Job) -> bool:
    """Add a job to the execution queue."""
    try:
        client = await get_redis()
        job_json = job.to_json()

        # Add to pending queue
        await client.rpush(EXECUTION_QUEUE, job_json)

        # Track in processing set (for idempotency) with 1 hour TTL
        if job.idempotency_key:
            await client.sadd(PROCESSING_SET, job.idempotency_key)
            await client.expire(PROCESSING_SET, 3600)  # 1 hour TTL

        logger.info(
            "job_enqueued",
            execution_id=job.execution_id,
            workflow_id=job.workflow_id,
            queue_length=await client.llen(EXECUTION_QUEUE),
        )
        return True

    except Exception as e:
        logger.error("enqueue_failed", error=str(e), execution_id=job.execution_id)
        return False


async def dequeue_job() -> Optional[Job]:
    """Remove and return the next job from the queue."""
    try:
        client = await get_redis()
        job_json = await client.lpop(EXECUTION_QUEUE)

        if job_json is None:
            return None

        job = Job.from_json(job_json)
        logger.info(
            "job_dequeued",
            execution_id=job.execution_id,
            workflow_id=job.workflow_id,
        )
        return job

    except Exception as e:
        logger.error("dequeue_failed", error=str(e))
        return None


async def requeue_job(job: Job) -> bool:
    """Re-add a failed job to the queue (for retry)."""
    try:
        client = await get_redis()
        job_json = job.to_json()
        await client.rpush(EXECUTION_QUEUE, job_json)

        logger.info(
            "job_requeued",
            execution_id=job.execution_id,
            retry_count=job.retry_count,
            max_retries=job.max_retries,
        )
        return True

    except Exception as e:
        logger.error("requeue_failed", error=str(e), execution_id=job.execution_id)
        return False


async def move_to_failed_queue(job: Job, error: str) -> bool:
    """Move a job to the failed queue."""
    try:
        client = await get_redis()
        job_json = job.to_json()
        await client.rpush(FAILED_QUEUE, job_json)

        # Remove from processing set
        if job.idempotency_key:
            await client.srem(PROCESSING_SET, job.idempotency_key)

        logger.info("job_failed", execution_id=job.execution_id, error=error)
        return True

    except Exception as e:
        logger.error("move_to_failed_failed", error=str(e), execution_id=job.execution_id)
        return False


async def is_duplicate_job(idempotency_key: str) -> bool:
    """Check if a job with this idempotency key is already processing."""
    try:
        client = await get_redis()
        return bool(await client.sismember(PROCESSING_SET, idempotency_key))
    except Exception as e:
        logger.error("idempotency_check_failed", error=str(e))
        return False


async def get_queue_length() -> int:
    """Get the current queue length."""
    try:
        client = await get_redis()
        return await client.llen(EXECUTION_QUEUE)
    except Exception as e:
        logger.error("queue_length_failed", error=str(e))
        return 0


async def clear_processing_set(idempotency_key: str) -> None:
    """Remove a job from the processing set."""
    try:
        client = await get_redis()
        await client.srem(PROCESSING_SET, idempotency_key)
    except Exception as e:
        logger.error("clear_processing_failed", error=str(e))
