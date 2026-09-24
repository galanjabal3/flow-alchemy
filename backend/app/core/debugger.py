"""Visual debugger — step-through execution with breakpoints."""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.orm import Session
from app.models.workflow import Workflow, Execution, NodeExecution
from app.core.workflow_definition import WorkflowDefinition
from app.core.execution_planner import ExecutionPlanner
from app.core.executors import get_executor
from app.core.events import publish_event, ExecutionEvent
import structlog

logger = structlog.get_logger()

MAX_SESSIONS_PER_USER = 5
SESSION_TTL_SECONDS = 1800  # 30 minutes
MAX_BREAKPOINTS = 50


class DebugState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STEPPING = "stepping"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Breakpoint:
    node_id: str
    enabled: bool = True


@dataclass
class DebugSession:
    execution_id: str
    workflow_id: int
    user_id: int
    state: DebugState = DebugState.IDLE
    breakpoints: List[Breakpoint] = field(default_factory=list)
    current_node_index: int = 0
    execution_order: List[List[str]] = field(default_factory=list)
    node_map: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    node_results: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)


class DebugManager:
    """Manages debug sessions."""

    def __init__(self):
        self._sessions: Dict[str, DebugSession] = {}

    def _cleanup_expired_sessions(self) -> None:
        """Remove expired sessions."""
        now = datetime.now(timezone.utc)
        expired = [
            eid for eid, session in self._sessions.items()
            if (now - session.created_at).total_seconds() > SESSION_TTL_SECONDS
        ]
        for eid in expired:
            del self._sessions[eid]

    def create_session(
        self,
        execution_id: str,
        workflow_id: int,
        user_id: int,
        definition: WorkflowDefinition,
    ) -> DebugSession:
        """Create a new debug session."""
        # Cleanup expired sessions
        self._cleanup_expired_sessions()

        # Check session limit per user
        user_sessions = [s for s in self._sessions.values() if s.user_id == user_id]
        if len(user_sessions) >= MAX_SESSIONS_PER_USER:
            raise ValueError(f"Maximum debug sessions ({MAX_SESSIONS_PER_USER}) reached for user")

        # Build execution order
        planner = ExecutionPlanner(definition.nodes, definition.edges)
        plan = planner.plan()

        # Build node map
        node_map = {n.id: n for n in definition.nodes}

        session = DebugSession(
            execution_id=execution_id,
            workflow_id=workflow_id,
            user_id=user_id,
            execution_order=plan.execution_order,
            node_map=node_map,
            context={"trigger_data": {}},
        )

        self._sessions[execution_id] = session
        return session

    def get_session(self, execution_id: str, user_id: Optional[int] = None) -> Optional[DebugSession]:
        """Get a debug session with optional ownership check."""
        session = self._sessions.get(execution_id)
        if session and user_id is not None and session.user_id != user_id:
            return None
        return session

    def remove_session(self, execution_id: str) -> None:
        """Remove a debug session."""
        self._sessions.pop(execution_id, None)

    def add_breakpoint(self, execution_id: str, node_id: str) -> bool:
        """Add a breakpoint to a node."""
        session = self._sessions.get(execution_id)
        if not session:
            return False

        # Check if breakpoint already exists
        for bp in session.breakpoints:
            if bp.node_id == node_id:
                bp.enabled = True
                return True

        # Check breakpoint limit
        if len(session.breakpoints) >= MAX_BREAKPOINTS:
            raise ValueError(f"Maximum breakpoints ({MAX_BREAKPOINTS}) reached")

        session.breakpoints.append(Breakpoint(node_id=node_id))
        return True

    def remove_breakpoint(self, execution_id: str, node_id: str) -> bool:
        """Remove a breakpoint from a node."""
        session = self._sessions.get(execution_id)
        if not session:
            return False

        session.breakpoints = [bp for bp in session.breakpoints if bp.node_id != node_id]
        return True

    def has_breakpoint(self, execution_id: str, node_id: str) -> bool:
        """Check if a node has a breakpoint."""
        session = self._sessions.get(execution_id)
        if not session:
            return False

        return any(bp.node_id == node_id and bp.enabled for bp in session.breakpoints)

    async def start_debug(
        self,
        execution_id: str,
        trigger_data: Optional[Dict[str, Any]] = None,
    ) -> DebugSession:
        """Start a debug session."""
        session = self._sessions.get(execution_id)
        if not session:
            raise ValueError("Debug session not found")

        async with session._lock:
            # Validate state
            if session.state not in (DebugState.IDLE, DebugState.FAILED, DebugState.COMPLETED):
                raise ValueError(f"Cannot start session in state: {session.state.value}")

            session.state = DebugState.RUNNING
            session.started_at = datetime.now(timezone.utc)
            if trigger_data:
                session.context["trigger_data"] = trigger_data

            # Initialize node results
            for node_id in session.node_map:
                session.node_results[node_id] = {"status": "pending"}

            return session

    async def step(self, execution_id: str) -> Optional[str]:
        """Step to the next node. Returns node_id if paused, None if completed."""
        session = self._sessions.get(execution_id)
        if not session:
            raise ValueError("Debug session not found")

        async with session._lock:
            if session.state not in (DebugState.RUNNING, DebugState.STEPPING, DebugState.PAUSED):
                raise ValueError("Session is not in a steppable state")

            # Find next node to execute
            while session.current_node_index < len(session.execution_order):
                level = session.execution_order[session.current_node_index]

                for node_id in level:
                    # Check for breakpoint
                    if self.has_breakpoint(execution_id, node_id):
                        session.state = DebugState.PAUSED
                        session.paused_at = datetime.now(timezone.utc)
                        return node_id

                    # Execute node
                    node = session.node_map.get(node_id)
                    if node:
                        await self._execute_node(session, node)
                        session.current_node_index += 1
                        return node_id

                session.current_node_index += 1

            # No more nodes
            session.state = DebugState.COMPLETED
            return None

    async def continue_execution(self, execution_id: str) -> Optional[str]:
        """Continue execution until next breakpoint or completion."""
        session = self._sessions.get(execution_id)
        if not session:
            raise ValueError("Debug session not found")

        async with session._lock:
            if session.state not in (DebugState.RUNNING, DebugState.PAUSED):
                raise ValueError("Session is not in a resumable state")

            session.state = DebugState.RUNNING

            # Step through until breakpoint or completion
            while session.current_node_index < len(session.execution_order):
                level = session.execution_order[session.current_node_index]

                for node_id in level:
                    # Check for breakpoint
                    if self.has_breakpoint(execution_id, node_id):
                        session.state = DebugState.PAUSED
                        session.paused_at = datetime.now(timezone.utc)
                        return node_id

                    # Execute node
                    node = session.node_map.get(node_id)
                    if node:
                        await self._execute_node(session, node)
                        session.current_node_index += 1
                        return node_id

                session.current_node_index += 1

            # No more nodes
            session.state = DebugState.COMPLETED
            return None

    async def _execute_node(self, session: DebugSession, node: Any) -> None:
        """Execute a single node."""
        node_id = node.id
        node_type = node.node_type.value
        config = dict(node.config)

        session.node_results[node_id] = {
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            executor = get_executor(node_type)
            output = await executor.execute(node_id, config, session.context)

            session.node_results[node_id] = {
                "status": "completed",
                "output": output,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            session.context[node_id] = output
            session.context["input"] = output

            # Publish event
            await publish_event(ExecutionEvent(
                execution_id=session.execution_id,
                event_type="node_completed",
                node_id=node_id,
                status="completed",
                data={"output": output, "debug": True},
            ))

        except Exception as e:
            logger.error("node_execution_failed", node_id=node_id, error=str(e), exc_info=True)
            safe_error = "Node execution failed"
            session.node_results[node_id] = {
                "status": "failed",
                "error": safe_error,
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }
            session.state = DebugState.FAILED

            # Publish event with sanitized error
            await publish_event(ExecutionEvent(
                execution_id=session.execution_id,
                event_type="node_failed",
                node_id=node_id,
                status="failed",
                data={"error": safe_error, "debug": True},
            ))
            raise

    def get_debug_state(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get current debug state."""
        session = self._sessions.get(execution_id)
        if not session:
            return None

        # Sanitize context and node_results
        safe_context = {k: v for k, v in session.context.items() if not k.startswith("_")}
        safe_results = {}
        for nid, result in session.node_results.items():
            safe_results[nid] = {
                "status": result.get("status", "unknown"),
            }
            if result.get("status") == "completed":
                safe_results[nid]["output"] = result.get("output")
            # Don't expose raw error messages

        return {
            "execution_id": session.execution_id,
            "workflow_id": session.workflow_id,
            "state": session.state.value,
            "current_node_index": session.current_node_index,
            "total_nodes": len(session.execution_order),
            "breakpoints": [{"node_id": bp.node_id, "enabled": bp.enabled} for bp in session.breakpoints],
            "node_results": safe_results,
            "context": safe_context,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "paused_at": session.paused_at.isoformat() if session.paused_at else None,
        }


debug_manager = DebugManager()
