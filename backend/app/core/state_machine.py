"""Execution state machine for workflow execution."""

from enum import Enum
from typing import Optional, Set
import structlog

logger = structlog.get_logger()


class ExecutionState(str, Enum):
    """Possible states for a workflow execution."""
    QUEUED = "queued"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    PAUSED = "paused"


# Valid state transitions
VALID_TRANSITIONS = {
    ExecutionState.QUEUED: {ExecutionState.RUNNING, ExecutionState.CANCELLED},
    ExecutionState.RUNNING: {ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.CANCELLED, ExecutionState.RETRYING, ExecutionState.TIMED_OUT},
    ExecutionState.RETRYING: {ExecutionState.RUNNING, ExecutionState.FAILED, ExecutionState.CANCELLED},
    ExecutionState.COMPLETED: set(),  # Terminal state
    ExecutionState.FAILED: set(),     # Terminal state
    ExecutionState.CANCELLED: set(),  # Terminal state
    ExecutionState.TIMED_OUT: set(),  # Terminal state
    ExecutionState.PAUSED: {ExecutionState.RUNNING, ExecutionState.CANCELLED},
}

# Terminal states — no transitions allowed out
TERMINAL_STATES: Set[ExecutionState] = {
    ExecutionState.COMPLETED,
    ExecutionState.FAILED,
    ExecutionState.CANCELLED,
    ExecutionState.TIMED_OUT,
}


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, from_state: ExecutionState, to_state: ExecutionState):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(f"Cannot transition from {from_state.value} to {to_state.value}")


class StateMachine:
    """State machine for execution lifecycle."""

    def __init__(self, initial_state: ExecutionState = ExecutionState.QUEUED):
        self._state = initial_state
        self._history = [initial_state]

    @property
    def state(self) -> ExecutionState:
        """Get current state."""
        return self._state

    @property
    def history(self):
        """Get state transition history."""
        return self._history.copy()

    def can_transition(self, to_state: ExecutionState) -> bool:
        """Check if transition to target state is valid."""
        return to_state in VALID_TRANSITIONS.get(self._state, set())

    def transition(self, to_state: ExecutionState) -> None:
        """Transition to a new state."""
        if not self.can_transition(to_state):
            raise InvalidTransitionError(self._state, to_state)

        old_state = self._state
        self._state = to_state
        self._history.append(to_state)

        logger.info(
            "state_transition",
            from_state=old_state.value,
            to_state=to_state.value,
        )

    def start(self) -> None:
        """Transition from QUEUED to RUNNING."""
        self.transition(ExecutionState.RUNNING)

    def complete(self) -> None:
        """Transition from RUNNING to COMPLETED."""
        self.transition(ExecutionState.COMPLETED)

    def fail(self) -> None:
        """Transition from RUNNING to FAILED."""
        self.transition(ExecutionState.FAILED)

    def retry(self) -> None:
        """Transition from RUNNING to RETRYING."""
        self.transition(ExecutionState.RETRYING)

    def cancel(self) -> None:
        """Transition to CANCELLED (valid from QUEUED, RUNNING, or RETRYING)."""
        self.transition(ExecutionState.CANCELLED)

    def timeout(self) -> None:
        """Transition from RUNNING to TIMED_OUT."""
        self.transition(ExecutionState.TIMED_OUT)

    def resume(self) -> None:
        """Transition from PAUSED to RUNNING."""
        self.transition(ExecutionState.RUNNING)

    def is_terminal(self) -> bool:
        """Check if current state is terminal (no more transitions possible)."""
        return self._state in TERMINAL_STATES

    def to_dict(self) -> dict:
        """Serialize state machine to dictionary."""
        return {
            "state": self._state.value,
            "history": [s.value for s in self._history],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StateMachine":
        """Deserialize state machine from dictionary."""
        sm = cls(ExecutionState(data["state"]))
        sm._history = [ExecutionState(s) for s in data["history"]]
        return sm
