"""Tests for idempotency features."""

import pytest
import uuid
from app.models.workflow import Execution
from app.core.state_machine import ExecutionState


class TestIdempotency:
    """Tests for execution idempotency."""

    def test_duplicate_idempotency_key_returns_existing(self, db_session):
        """Same idempotency key should return existing execution."""
        key = str(uuid.uuid4())

        execution1 = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.COMPLETED.value,
            trigger="manual",
            idempotency_key=key,
        )
        db_session.add(execution1)
        db_session.commit()

        # Query for same key
        existing = (
            db_session.query(Execution)
            .filter(Execution.idempotency_key == key)
            .first()
        )
        assert existing is not None
        assert existing.id == execution1.id

    def test_different_idempotency_keys_create_separate_executions(self, db_session):
        """Different keys should create separate executions."""
        key1 = str(uuid.uuid4())
        key2 = str(uuid.uuid4())

        exec1 = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.QUEUED.value,
            trigger="manual",
            idempotency_key=key1,
        )
        exec2 = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.QUEUED.value,
            trigger="manual",
            idempotency_key=key2,
        )
        db_session.add(exec1)
        db_session.add(exec2)
        db_session.commit()

        assert exec1.id != exec2.id

    def test_null_idempotency_key_allows_duplicates(self, db_session):
        """NULL idempotency keys should allow multiple executions."""
        exec1 = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.QUEUED.value,
            trigger="manual",
            idempotency_key=None,
        )
        exec2 = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.QUEUED.value,
            trigger="manual",
            idempotency_key=None,
        )
        db_session.add(exec1)
        db_session.add(exec2)
        db_session.commit()

        assert exec1.id != exec2.id

    def test_idempotency_key_unique_constraint(self, db_session):
        """Duplicate non-null idempotency keys should violate unique constraint."""
        key = str(uuid.uuid4())

        exec1 = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.QUEUED.value,
            trigger="manual",
            idempotency_key=key,
        )
        db_session.add(exec1)
        db_session.commit()

        exec2 = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.QUEUED.value,
            trigger="manual",
            idempotency_key=key,
        )
        db_session.add(exec2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_idempotent_response_matches_existing(self, db_session):
        """Idempotent response should match existing execution fields."""
        key = str(uuid.uuid4())

        execution = Execution(
            workflow_id=1,
            user_id=1,
            status=ExecutionState.RUNNING.value,
            trigger="manual",
            input_data={"foo": "bar"},
            idempotency_key=key,
        )
        db_session.add(execution)
        db_session.commit()

        # Simulate idempotent lookup
        existing = (
            db_session.query(Execution)
            .filter(Execution.idempotency_key == key)
            .first()
        )

        assert existing.status == ExecutionState.RUNNING.value
        assert existing.input_data == {"foo": "bar"}
        assert existing.workflow_id == 1
