"""Tests for execution state machine."""

import pytest
from app.core.state_machine import (
    StateMachine,
    ExecutionState,
    InvalidTransitionError,
    VALID_TRANSITIONS,
    TERMINAL_STATES,
)
from app.services.execution_state_service import ExecutionStateService


class TestStateMachine:
    """Tests for the in-memory StateMachine class."""

    def test_initial_state(self):
        sm = StateMachine()
        assert sm.state == ExecutionState.QUEUED

    def test_initial_state_custom(self):
        sm = StateMachine(ExecutionState.RUNNING)
        assert sm.state == ExecutionState.RUNNING

    def test_queued_to_running(self):
        sm = StateMachine()
        sm.start()
        assert sm.state == ExecutionState.RUNNING

    def test_running_to_completed(self):
        sm = StateMachine(ExecutionState.RUNNING)
        sm.complete()
        assert sm.state == ExecutionState.COMPLETED

    def test_running_to_failed(self):
        sm = StateMachine(ExecutionState.RUNNING)
        sm.fail()
        assert sm.state == ExecutionState.FAILED

    def test_running_to_retrying(self):
        sm = StateMachine(ExecutionState.RUNNING)
        sm.retry()
        assert sm.state == ExecutionState.RETRYING

    def test_retrying_to_running(self):
        sm = StateMachine(ExecutionState.RETRYING)
        sm.resume()
        assert sm.state == ExecutionState.RUNNING

    def test_running_to_timed_out(self):
        sm = StateMachine(ExecutionState.RUNNING)
        sm.timeout()
        assert sm.state == ExecutionState.TIMED_OUT

    def test_queued_to_cancelled(self):
        sm = StateMachine()
        sm.cancel()
        assert sm.state == ExecutionState.CANCELLED

    def test_running_to_cancelled(self):
        sm = StateMachine(ExecutionState.RUNNING)
        sm.cancel()
        assert sm.state == ExecutionState.CANCELLED

    def test_retrying_to_cancelled(self):
        sm = StateMachine(ExecutionState.RETRYING)
        sm.cancel()
        assert sm.state == ExecutionState.CANCELLED

    def test_paused_to_running(self):
        sm = StateMachine(ExecutionState.PAUSED)
        sm.resume()
        assert sm.state == ExecutionState.RUNNING

    def test_paused_to_cancelled(self):
        sm = StateMachine(ExecutionState.PAUSED)
        sm.cancel()
        assert sm.state == ExecutionState.CANCELLED

    # Invalid transitions

    def test_invalid_queued_to_completed(self):
        sm = StateMachine()
        with pytest.raises(InvalidTransitionError):
            sm.complete()

    def test_invalid_queued_to_failed(self):
        sm = StateMachine()
        with pytest.raises(InvalidTransitionError):
            sm.fail()

    def test_invalid_completed_to_any(self):
        sm = StateMachine(ExecutionState.COMPLETED)
        with pytest.raises(InvalidTransitionError):
            sm.start()

    def test_invalid_failed_to_any(self):
        sm = StateMachine(ExecutionState.FAILED)
        with pytest.raises(InvalidTransitionError):
            sm.start()

    def test_invalid_cancelled_to_any(self):
        sm = StateMachine(ExecutionState.CANCELLED)
        with pytest.raises(InvalidTransitionError):
            sm.start()

    def test_invalid_timed_out_to_any(self):
        sm = StateMachine(ExecutionState.TIMED_OUT)
        with pytest.raises(InvalidTransitionError):
            sm.start()

    def test_invalid_retrying_to_completed(self):
        sm = StateMachine(ExecutionState.RETRYING)
        with pytest.raises(InvalidTransitionError):
            sm.complete()

    # Terminal state checks

    def test_completed_is_terminal(self):
        sm = StateMachine(ExecutionState.COMPLETED)
        assert sm.is_terminal()

    def test_failed_is_terminal(self):
        sm = StateMachine(ExecutionState.FAILED)
        assert sm.is_terminal()

    def test_cancelled_is_terminal(self):
        sm = StateMachine(ExecutionState.CANCELLED)
        assert sm.is_terminal()

    def test_timed_out_is_terminal(self):
        sm = StateMachine(ExecutionState.TIMED_OUT)
        assert sm.is_terminal()

    def test_queued_not_terminal(self):
        sm = StateMachine()
        assert not sm.is_terminal()

    def test_running_not_terminal(self):
        sm = StateMachine(ExecutionState.RUNNING)
        assert not sm.is_terminal()

    # can_transition checks

    def test_can_transition_valid(self):
        sm = StateMachine()
        assert sm.can_transition(ExecutionState.RUNNING)
        assert sm.can_transition(ExecutionState.CANCELLED)

    def test_can_transition_invalid(self):
        sm = StateMachine()
        assert not sm.can_transition(ExecutionState.COMPLETED)
        assert not sm.can_transition(ExecutionState.FAILED)

    # History tracking

    def test_history_tracking(self):
        sm = StateMachine()
        sm.start()
        sm.complete()
        assert sm.history == [
            ExecutionState.QUEUED,
            ExecutionState.RUNNING,
            ExecutionState.COMPLETED,
        ]

    def test_history_not_mutated(self):
        sm = StateMachine()
        history = sm.history
        sm.start()
        assert len(history) == 1

    # Serialization

    def test_to_dict(self):
        sm = StateMachine()
        sm.start()
        data = sm.to_dict()
        assert data["state"] == "running"
        assert data["history"] == ["queued", "running"]

    def test_from_dict(self):
        data = {"state": "running", "history": ["queued", "running"]}
        sm = StateMachine.from_dict(data)
        assert sm.state == ExecutionState.RUNNING
        assert len(sm.history) == 2


class TestExecutionStateEnum:
    """Tests for ExecutionState enum coverage."""

    def test_all_states_exist(self):
        expected = {"queued", "running", "retrying", "completed", "failed", "cancelled", "timed_out", "paused"}
        actual = {s.value for s in ExecutionState}
        assert expected == actual

    def test_all_non_terminal_states_have_transitions(self):
        for state in ExecutionState:
            if state not in TERMINAL_STATES:
                assert len(VALID_TRANSITIONS[state]) > 0, f"{state.value} has no transitions"

    def test_all_terminal_states_have_no_transitions(self):
        for state in TERMINAL_STATES:
            assert len(VALID_TRANSITIONS[state]) == 0, f"{state.value} should have no transitions"

    def test_terminal_states_set(self):
        assert TERMINAL_STATES == {
            ExecutionState.COMPLETED,
            ExecutionState.FAILED,
            ExecutionState.CANCELLED,
            ExecutionState.TIMED_OUT,
        }
