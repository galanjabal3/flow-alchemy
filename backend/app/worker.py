"""Worker for async workflow execution."""

import asyncio
import random
import signal
import structlog
from typing import Optional
from app.core.config import settings
from app.core.redis import get_redis, close_redis
from app.core.queue import dequeue_job, requeue_job, move_to_failed_queue, clear_processing_set
from app.core.job import Job
from app.core.events import publish_event, ExecutionEvent
from app.core.workflow_adapter import react_flow_to_definition
from app.core.workflow_engine import WorkflowEngine, WorkflowTimeoutError, WorkflowCancelledError
from app.core.graph_validator import GraphValidationError
from app.core.state_machine import ExecutionState
from app.services.execution_state_service import ExecutionStateService
from app.models.workflow import Execution
from app.core.database import SessionLocal

logger = structlog.get_logger()

# Global flag for graceful shutdown
_shutdown = False


def handle_signal(signum, frame):
    """Handle shutdown signal."""
    global _shutdown
    logger.info("worker_shutdown_signal", signal=signum)
    _shutdown = True


class Worker:
    """Background worker that processes workflow execution jobs."""

    def __init__(self):
        self.engine = WorkflowEngine()
        self.poll_interval = settings.WORKER_POLL_INTERVAL

    async def process_job(self, job: Job) -> bool:
        """Process a single job."""
        logger.info(
            "worker_processing_job",
            execution_id=job.execution_id,
            workflow_id=job.workflow_id,
            retry_count=job.retry_count,
        )

        # Publish started event
        await publish_event(ExecutionEvent(
            execution_id=job.execution_id,
            event_type="started",
        ))

        db = SessionLocal()
        try:
            # Get execution record
            execution = db.query(Execution).filter(Execution.id == int(job.execution_id)).first()
            if not execution:
                logger.error("execution_not_found", execution_id=job.execution_id)
                return False

            # Check if execution is already in terminal state (race condition guard)
            if ExecutionStateService.is_terminal(db, int(job.execution_id)):
                logger.warning(
                    "execution_already_terminal",
                    execution_id=job.execution_id,
                    current_status=execution.status,
                )
                return True

            # Transition to RUNNING via state machine
            worker_id = f"worker-{asyncio.current_task().get_name()}"
            transitioned = ExecutionStateService.transition(
                db, int(job.execution_id), ExecutionState.RUNNING, worker_id=worker_id
            )
            if not transitioned:
                logger.warning(
                    "state_transition_failed",
                    execution_id=job.execution_id,
                    target_state="running",
                )
                return False

            # Refresh execution after state change
            db.refresh(execution)

            # Get workflow definition from snapshot (immutable, not live definition)
            defn_data = execution.definition_snapshot or execution.workflow.definition or {"nodes": [], "edges": []}
            workflow_def = react_flow_to_definition(defn_data)

            # Execute workflow with timeout
            try:
                ctx = await asyncio.wait_for(
                    self.engine.execute(
                        execution_id=job.execution_id,
                        workflow_id=job.workflow_id,
                        definition=workflow_def,
                        trigger_data=job.trigger_data or {},
                        user_id=execution.user_id,
                        db=db,
                    ),
                    timeout=settings.WORKFLOW_TIMEOUT,
                )
            except asyncio.TimeoutError:
                raise WorkflowTimeoutError(
                    f"Workflow {job.workflow_id} exceeded timeout of {settings.WORKFLOW_TIMEOUT}s"
                )

            # Find output
            output_data = None
            for node_id, ne in ctx.node_executions.items():
                if ne.status.value == "completed":
                    output_data = ne.output_data

            error_log = next((ne.error for ne in ctx.node_executions.values() if ne.error), None)

            # Persist per-node execution history (all statuses incl. skipped).
            # Node type comes from the executed definition; node_id (FK to
            # workflow_nodes) may not exist for user-created workflows, so we
            # store node_ref (React Flow node id) instead — the editor uses
            # these string ids to locate nodes on the canvas.
            from app.models.workflow import NodeExecution

            type_by_id = {n.id: n.node_type.value for n in workflow_def.nodes}

            for node_id, ne in ctx.node_executions.items():
                db.add(NodeExecution(
                    execution_id=int(job.execution_id),
                    node_id=None,
                    node_ref=str(node_id),
                    node_type=type_by_id.get(node_id),
                    status=ne.status.value,
                    input_data=ne.input_data,
                    output_data=ne.output_data,
                    error_log=ne.error,
                    duration_ms=int(ne.duration_ms) if ne.duration_ms else None,
                    started_at=ne.started_at,
                    completed_at=ne.completed_at,
                ))

            db.flush()

            # Transition to final state via state machine
            if ctx.status.value == "completed":
                ExecutionStateService.transition(
                    db, int(job.execution_id), ExecutionState.COMPLETED
                )
                status = "completed"
            else:
                ExecutionStateService.transition(
                    db, int(job.execution_id), ExecutionState.FAILED, error_log=error_log
                )
                status = "failed"

            # Update output data separately (not part of state transition)
            execution.output_data = output_data
            db.commit()

            # Publish completed event
            await publish_event(ExecutionEvent(
                execution_id=job.execution_id,
                event_type="completed",
                status=status,
                data={"output": output_data},
            ))

            # Clear from processing set
            if job.idempotency_key:
                await clear_processing_set(job.idempotency_key)

            logger.info(
                "worker_job_completed",
                execution_id=job.execution_id,
                status=status,
                duration_ms=ctx.duration_ms,
            )
            return True

        except WorkflowCancelledError:
            # Execution was cancelled — transition to CANCELLED
            ExecutionStateService.transition(
                db, int(job.execution_id), ExecutionState.CANCELLED
            )
            await publish_event(ExecutionEvent(
                execution_id=job.execution_id,
                event_type="cancelled",
                status="cancelled",
            ))
            if job.idempotency_key:
                await clear_processing_set(job.idempotency_key)
            logger.info("worker_job_cancelled", execution_id=job.execution_id)
            return True

        except WorkflowTimeoutError as e:
            # Workflow timeout — transition to TIMED_OUT
            ExecutionStateService.transition(
                db, int(job.execution_id), ExecutionState.TIMED_OUT, error_log=str(e)
            )
            await publish_event(ExecutionEvent(
                execution_id=job.execution_id,
                event_type="timed_out",
                status="timed_out",
                data={"error": str(e)},
            ))
            if job.idempotency_key:
                await clear_processing_set(job.idempotency_key)
            await move_to_failed_queue(job, str(e))
            logger.error("worker_job_timeout", execution_id=job.execution_id, error=str(e))
            return False

        except GraphValidationError as e:
            # Validation error — don't retry
            ExecutionStateService.transition(
                db, int(job.execution_id), ExecutionState.FAILED, error_log=e.message
            )

            await publish_event(ExecutionEvent(
                execution_id=job.execution_id,
                event_type="failed",
                status="failed",
                data={"error": e.message},
            ))

            await move_to_failed_queue(job, e.message)
            logger.error("worker_job_validation_failed", execution_id=job.execution_id, error=e.message)
            return False

        except Exception as e:
            # Other error — retry if possible
            error_msg = str(e)

            if job.retry_count < job.max_retries:
                # Transition to RETRYING
                ExecutionStateService.transition(
                    db, int(job.execution_id), ExecutionState.RETRYING
                )

                job.retry_count += 1
                base_delay = settings.RETRY_BACKOFF_BASE ** job.retry_count
                jitter = base_delay * settings.RETRY_JITTER * random.random()
                backoff = base_delay + jitter
                logger.info(
                    "worker_job_retrying",
                    execution_id=job.execution_id,
                    retry_count=job.retry_count,
                    backoff_seconds=backoff,
                )

                await publish_event(ExecutionEvent(
                    execution_id=job.execution_id,
                    event_type="retrying",
                    status="retrying",
                    data={"retry_count": job.retry_count, "backoff": backoff},
                ))

                # Wait before retry
                await asyncio.sleep(backoff)

                # Requeue
                await requeue_job(job)
                return True
            else:
                # Max retries exceeded
                ExecutionStateService.transition(
                    db, int(job.execution_id), ExecutionState.FAILED, error_log=error_msg
                )

                await publish_event(ExecutionEvent(
                    execution_id=job.execution_id,
                    event_type="failed",
                    status="failed",
                    data={"error": error_msg},
                ))

                await move_to_failed_queue(job, error_msg)
                logger.error(
                    "worker_job_max_retries",
                    execution_id=job.execution_id,
                    retry_count=job.retry_count,
                )
                return False

        finally:
            db.close()

    async def run(self):
        """Main worker loop."""
        global _shutdown

        logger.info("worker_started", poll_interval=self.poll_interval)

        # Set up signal handlers
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

        while not _shutdown:
            try:
                # Dequeue next job
                job = await dequeue_job()
                if job is None:
                    # No jobs — wait before polling again
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Process the job
                await self.process_job(job)

            except Exception as e:
                logger.error("worker_loop_error", error=str(e))
                await asyncio.sleep(self.poll_interval)

        logger.info("worker_stopped")


async def run_worker():
    """Entry point for running the worker."""
    worker = Worker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
