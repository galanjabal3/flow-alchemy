"""Workflow Engine — orchestrates workflow execution."""

import re
import json
import asyncio
import random
import structlog
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.workflow_definition import WorkflowDefinition, WorkflowNode, WorkflowEdge
from app.core.graph_validator import validate_graph, GraphValidationError
from app.core.execution_planner import ExecutionPlanner
from app.core.execution_context import ExecutionContext, ExecutionStatus, NodeStatus
from app.core.executors import get_executor
from app.core.executors.condition import ConditionExecutor
from app.core.events import publish_event, ExecutionEvent
from app.core.config import settings
from app.core.error_types import classify_error, is_retryable, ErrorCategory
from app.api.credentials import get_credential_value, redact_config_credentials, redact_output_values

logger = structlog.get_logger()


CREDENTIAL_PATTERN = re.compile(r"\{\{cred:(\d+)\}\}")
TEMPLATE_PATTERN = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


class NodeTimeoutError(Exception):
    """Raised when a node execution exceeds its timeout."""
    pass


class WorkflowTimeoutError(Exception):
    """Raised when a workflow execution exceeds its timeout."""
    pass


class WorkflowCancelledError(Exception):
    """Raised when a workflow execution is cancelled."""
    pass


class WorkflowEngine:
    async def execute(
        self,
        execution_id: str,
        workflow_id: int,
        definition: WorkflowDefinition,
        trigger_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> ExecutionContext:
        ctx = ExecutionContext(
            execution_id=execution_id,
            workflow_id=workflow_id,
            trigger_data=trigger_data or {},
        )

        for node in definition.nodes:
            ctx.init_node(node.id)

        try:
            validate_graph(definition.nodes, definition.edges)
        except GraphValidationError as e:
            logger.error("workflow_validation_failed", errors=e.errors)
            ctx.fail()
            raise

        planner = ExecutionPlanner(definition.nodes, definition.edges)
        plan = planner.plan()

        logger.info(
            "workflow_execution_started",
            workflow_id=workflow_id,
            execution_id=execution_id,
            total_steps=plan.total_steps,
            max_parallelism=plan.max_parallelism,
        )

        ctx.start()
        node_map = {n.id: n for n in definition.nodes}

        # Incoming/outgoing edge maps used for data flow & conditional branching.
        incoming: Dict[str, List[WorkflowEdge]] = {n.id: [] for n in definition.nodes}
        outgoing: Dict[str, List[WorkflowEdge]] = {n.id: [] for n in definition.nodes}
        in_degree: Dict[str, int] = {n.id: 0 for n in definition.nodes}
        for edge in definition.edges:
            incoming[edge.target_node_id].append(edge)
            outgoing[edge.source_node_id].append(edge)
            in_degree[edge.target_node_id] = in_degree.get(edge.target_node_id, 0) + 1

        # edge_key ("source->target") -> bool (was the edge's condition satisfied)
        edge_active: Dict[str, bool] = {}

        try:
            for level in plan.execution_order:
                # Check for cancellation between levels
                if self._is_cancelled(execution_id, db):
                    raise WorkflowCancelledError(f"Execution {execution_id} was cancelled")

                runnable, skipped = [], []
                for node_id in level:
                    if in_degree[node_id] == 0:
                        # Triggers / roots always run.
                        runnable.append(node_id)
                        continue
                    satisfied = any(
                        edge_active.get(f"{e.source_node_id}->{node_id}")
                        for e in incoming.get(node_id, [])
                    )
                    if satisfied:
                        runnable.append(node_id)
                    else:
                        skipped.append(node_id)

                # Mark skipped nodes (their outgoing edges stay inactive).
                for node_id in skipped:
                    ctx.skip_node(node_id)
                    await publish_event(ExecutionEvent(
                        execution_id=execution_id,
                        event_type="node_skipped",
                        node_id=node_id,
                        status="skipped",
                    ))
                    logger.info("node_skipped", node_id=node_id)

                tasks = []
                for node_id in runnable:
                    node = node_map[node_id]
                    tasks.append(self._execute_node(node, ctx, execution_id, user_id, db, incoming.get(node_id, [])))
                await asyncio.gather(*tasks)

                # After the level completes, evaluate each executed node's
                # outgoing edge conditions against its output.
                for node_id in runnable:
                    node_output = ctx.get_node_output(node_id)
                    for edge in outgoing.get(node_id, []):
                        edge_active[f"{edge.source_node_id}->{edge.target_node_id}"] = (
                            self._evaluate_edge_condition(edge.condition, node_output)
                        )

            # Nodes that were never reachable remain in PENDING → mark SKIPPED.
            for node_id, ne in ctx.node_executions.items():
                if ne.status == NodeStatus.PENDING:
                    ctx.skip_node(node_id)

            ctx.complete()

            # Publish workflow completed event
            await publish_event(ExecutionEvent(
                execution_id=execution_id,
                event_type="workflow_completed",
                status="completed",
            ))

        except WorkflowCancelledError:
            logger.info("workflow_execution_cancelled", execution_id=execution_id)
            ctx.fail()
            raise

        except WorkflowTimeoutError as e:
            logger.error("workflow_timeout", execution_id=execution_id, error=str(e))
            ctx.fail()
            raise

        except Exception as e:
            logger.error("workflow_execution_failed", error=str(e))
            ctx.fail()

            # Publish workflow failed event
            await publish_event(ExecutionEvent(
                execution_id=execution_id,
                event_type="workflow_failed",
                status="failed",
                data={"error": str(e)},
            ))
            raise

        logger.info(
            "workflow_execution_finished",
            workflow_id=workflow_id,
            execution_id=execution_id,
            status=ctx.status.value,
            duration_ms=ctx.duration_ms,
        )

        return ctx

    def _evaluate_edge_condition(self, condition: Optional[str], source_output: Optional[Dict[str, Any]]) -> bool:
        """Evaluate a workflow edge condition against a source node's output.

        - Empty / missing condition → the edge is always active.
        - Common truthy/falsy keywords are short-circuited.
        - Otherwise the condition is treated as an expression evaluated with
          the source output as the data context (trigger_data is flattened in
          too, so paths like ``event.type`` work).
        """
        if not condition or not str(condition).strip():
            return True

        cond = str(condition).strip()
        low = cond.lower()

        if low in ("true", "false"):
            want = low == "true"
            # If the source node is a condition node (its output carries
            # "result"), branch on that result. Otherwise treat the label as
            # a literal boolean.
            if isinstance(source_output, dict) and "result" in source_output:
                return bool(source_output["result"]) == want
            return want

        if low in ("success", "yes", "pass", "ok", "completed"):
            return True
        if low in ("fail", "failed", "no", "error", "skipped"):
            return False

        src = source_output or {}
        eval_data: Dict[str, Any] = dict(src.get("trigger_data") or {})
        eval_data.update(src)
        return bool(ConditionExecutor()._eval_expression(eval_data, cond))

    @staticmethod
    def _resolve_path(data: Any, path: str) -> Any:
        """Resolve a dot-notation path (e.g. ``event.customer.id``) in data."""
        current = data
        for part in path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                current = current[int(part)]
            else:
                return None
        return current

    def _resolve_templates(self, value: Any, context: Dict[str, Any]) -> Any:
        """Recursively replace ``{{path}}`` placeholders with values from context."""
        if isinstance(value, str):
            def replace(match: re.Match) -> str:
                resolved = self._resolve_path(context, match.group(1).strip())
                if resolved is None:
                    # Leave unresolved placeholders untouched.
                    return match.group(0)
                if isinstance(resolved, (dict, list)):
                    return json.dumps(resolved)
                if isinstance(resolved, bool):
                    return "true" if resolved else "false"
                return str(resolved)
            return TEMPLATE_PATTERN.sub(replace, value)
        if isinstance(value, dict):
            return {k: self._resolve_templates(v, context) for k, v in value.items()}
        if isinstance(value, list):
            return [self._resolve_templates(v, context) for v in value]
        return value

    def _is_cancelled(self, execution_id: str, db: Optional[Session]) -> bool:
        """Check if execution has been cancelled in the database."""
        if not db:
            return False
        from app.models.workflow import Execution
        from app.core.state_machine import ExecutionState
        execution = db.query(Execution).filter(Execution.id == int(execution_id)).first()
        if not execution:
            return False
        return execution.status == ExecutionState.CANCELLED.value

    def _resolve_credentials(self, config: Dict[str, Any], user_id: int, db: Session) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """Replace {{cred:ID}} placeholders with decrypted credential values.

        Also returns a mapping of actual resolved values to masked versions,
        for redacting output data before storage/event publication.

        Returns:
            Tuple of (resolved_config, credential_map) where credential_map maps
            actual plaintext credential values to their masked equivalents.
        """
        credential_values: List[str] = []

        def replace_match(match: re.Match) -> str:
            cred_id = int(match.group(1))
            value = get_credential_value(cred_id, user_id, db)
            if value is None:
                raise ValueError(f"Credential {cred_id} not found or not owned by user")
            credential_values.append(value)
            return value

        def resolve_value(val: Any) -> Any:
            if isinstance(val, str):
                return CREDENTIAL_PATTERN.sub(replace_match, val)
            elif isinstance(val, dict):
                return {k: resolve_value(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [resolve_value(item) for item in val]
            return val

        resolved = resolve_value(config)

        # Build mapping: actual value -> masked value (same masking logic as redact_config_credentials)
        credential_map: Dict[str, str] = {}
        for val in credential_values:
            if len(val) < 4:
                masked = "***"
            else:
                masked = val[:2] + "*" * (len(val) - 4) + val[-2:]
            credential_map[val] = masked  # last duplicate value gets same mask

        return resolved, credential_map

    async def _execute_node(
        self,
        node: WorkflowNode,
        context: ExecutionContext,
        execution_id: str,
        user_id: Optional[int] = None,
        db: Optional[Session] = None,
        incoming_edges: Optional[List[WorkflowEdge]] = None,
    ) -> None:
        node_type = node.node_type.value
        original_config = dict(node.config)
        resolved_config = original_config
        credential_map: Dict[str, str] = {}

        # ── Resolve credential placeholders before execution ──
        if user_id and db and CREDENTIAL_PATTERN.search(str(original_config)):
            resolved_config, credential_map = self._resolve_credentials(original_config, user_id, db)

        # ── Data flow: merge trigger data + every upstream node's output ──
        # Build the input context for this node from all source nodes feeding it.
        input_context: Dict[str, Any] = dict(context.trigger_data or {})
        for edge in incoming_edges or []:
            upstream_output = context.get_node_output(edge.source_node_id)
            if isinstance(upstream_output, dict):
                input_context.update(upstream_output)

        # Resolve {{path}} templates in the config against the merged context.
        resolved_config = self._resolve_templates(resolved_config, input_context)

        # Inject the computed input into config["data"] so executors that read
        # config.data (condition/transform/output/delay) see real upstream data.
        existing_data = resolved_config.get("data")
        if isinstance(existing_data, dict):
            resolved_config["data"] = {**existing_data, **input_context}
        else:
            resolved_config["data"] = input_context

        logger.info("node_execution_started", node_id=node.id, node_type=node_type)

        # Basic config schema validation before execution
        if not isinstance(resolved_config, dict):
            raise ValueError(f"Node config must be a dict, got {type(resolved_config).__name__}")

        NODE_REQUIRED_FIELDS = {
            "http_request": ["url"],
            "output": ["destination"],
            "condition": [],
            "transform": [],
            "delay": [],
            "trigger": [],
        }
        required = NODE_REQUIRED_FIELDS.get(node_type, [])
        for field in required:
            if field not in resolved_config:
                raise ValueError(f"Node {node_type} requires '{field}' in config")

        # Store redacted config in context (for execution history) — never store plaintext secrets
        redacted_config = original_config
        if user_id and db and CREDENTIAL_PATTERN.search(str(original_config)):
            redacted_config = redact_config_credentials(original_config, user_id, db)
        context.start_node(node.id, {"node_type": node_type, **redacted_config})

        # Publish node started event
        await publish_event(ExecutionEvent(
            execution_id=execution_id,
            event_type="node_started",
            node_id=node.id,
            status="running",
            data={"node_type": node_type},
        ))

        last_error = None
        max_retries = settings.NODE_MAX_RETRIES

        for attempt in range(max_retries + 1):
            try:
                executor = get_executor(node_type)

                # Apply node-level timeout
                node_timeout = settings.NODE_TIMEOUT
                try:
                    output = await asyncio.wait_for(
                        executor.execute(node.id, resolved_config, context),
                        timeout=node_timeout,
                    )

                    # Redact credential values from output before storing/publishing.
                    # This prevents plaintext secrets from leaking into execution history
                    # and WebSocket/Redis events, even though the input config was already
                    # redacted via redact_config_credentials. The credential_map contains
                    # the actual values resolved during _resolve_credentials, so we can
                    # accurately mask them in the output layer without re-querying the DB.
                    redacted_output = redact_output_values(output, credential_map)

                except asyncio.TimeoutError:
                    raise NodeTimeoutError(
                        f"Node {node.id} ({node_type}) exceeded timeout of {node_timeout}s"
                    )

                context.complete_node(node.id, redacted_output)
                logger.info(
                    "node_execution_completed",
                    node_id=node.id,
                    attempt=attempt,
                )

                # Publish node completed event
                await publish_event(ExecutionEvent(
                    execution_id=execution_id,
                    event_type="node_completed",
                    node_id=node.id,
                    status="completed",
                    data={"output": redacted_output, "attempt": attempt},
                ))
                return  # Success — exit retry loop

            except NodeTimeoutError:
                last_error = NodeTimeoutError(
                    f"Node {node.id} ({node_type}) exceeded timeout of {node_timeout}s"
                )
                category = ErrorCategory.TIMEOUT

                if attempt < max_retries and is_retryable(last_error):
                    delay = settings.RETRY_BACKOFF_BASE ** (attempt + 1)
                    jitter = delay * settings.RETRY_JITTER * random.random()
                    wait_time = delay + jitter
                    logger.warning(
                        "node_retry_timeout",
                        node_id=node.id,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        wait_seconds=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                    continue

                context.fail_node(node.id, str(last_error))
                logger.error("node_timeout", node_id=node.id, timeout=node_timeout)

                await publish_event(ExecutionEvent(
                    execution_id=execution_id,
                    event_type="node_failed",
                    node_id=node.id,
                    status="failed",
                    data={"error": str(last_error), "category": category.value, "attempt": attempt},
                ))
                raise

            except Exception as e:
                last_error = e
                category = classify_error(e)

                if attempt < max_retries and is_retryable(e):
                    delay = settings.RETRY_BACKOFF_BASE ** (attempt + 1)
                    jitter = delay * settings.RETRY_JITTER * random.random()
                    wait_time = delay + jitter
                    logger.warning(
                        "node_retry",
                        node_id=node.id,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error=str(e),
                        category=category.value,
                        wait_seconds=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                    continue

                context.fail_node(node.id, str(e))
                logger.error("node_execution_failed", node_id=node.id, error=str(e))

                # Publish node failed event
                await publish_event(ExecutionEvent(
                    execution_id=execution_id,
                    event_type="node_failed",
                    node_id=node.id,
                    status="failed",
                    data={"error": str(e), "category": category.value, "attempt": attempt},
                ))
                raise
