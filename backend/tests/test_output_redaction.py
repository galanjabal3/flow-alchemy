"""Tests for output credential redaction (security: no plaintext in execution history).

Verifies that credential values which appear in node *output* are masked before
being stored in the execution context or published via events — closing the gap
where input config was redacted but executor output was stored raw.
"""

import asyncio

import pytest

from app.api.credentials import redact_output_values
from app.core.execution_context import ExecutionContext
from app.core.workflow_definition import WorkflowNode


SECRET = "sk-ant-abcdefghij"
# Same masking logic as redact_credential_value: first 2 + stars + last 2
MASKED = SECRET[:2] + "*" * (len(SECRET) - 4) + SECRET[-2:]


class TestRedactOutputValues:
    """Unit tests for the pure redaction helper."""

    def test_masks_plaintext_in_string(self):
        output = f"Authorization: Bearer {SECRET}"
        result = redact_output_values(output, {SECRET: MASKED})
        assert SECRET not in result
        assert result == f"Authorization: Bearer {MASKED}"

    def test_masks_within_dict(self):
        output = {"headers": {"Authorization": f"Bearer {SECRET}"}, "ok": True}
        result = redact_output_values(output, {SECRET: MASKED})
        assert SECRET not in str(result)
        assert "Bearer " + MASKED in str(result)
        assert result["ok"] is True  # non-matching values untouched

    def test_masks_within_list(self):
        output = ["first", {"token": SECRET}, SECRET]
        result = redact_output_values(output, {SECRET: MASKED})
        assert SECRET not in str(result)
        assert result[1]["token"] == MASKED
        assert result[2] == MASKED
        assert result[0] == "first"

    def test_longer_values_replaced_first(self):
        short = "key-123"
        long = "key-12345"
        output = f"prefix {long} suffix"
        result = redact_output_values(output, {short: "SHORT", long: "LONG"})
        # Must become LONG, not SHORT-45 (avoid partial replacement)
        assert result == "prefix LONG suffix"

    def test_non_matching_values_unchanged(self):
        output = {"url": "https://api.example.com", "count": 42, "ok": None}
        result = redact_output_values(output, {SECRET: MASKED})
        assert result == output

    def test_empty_map_is_noop(self):
        output = {"a": SECRET}
        assert redact_output_values(output, {}) == output

    def test_primitive_non_string_passthrough(self):
        assert redact_output_values(42, {SECRET: MASKED}) == 42
        assert redact_output_values(None, {SECRET: MASKED}) is None


class TestEngineOutputRedaction:
    """Integration: node output containing resolved credential is redacted
    before landing in execution context and events."""

    class FakeCredentialExecutor:
        """Executor that naively echoes the resolved config (worst case:
        output contains the plaintext secret)."""

        async def execute(self, node_id, config, context):
            # Echo the resolved secret back into the output
            return {"echo": config.get("url"), "headers_sent": config.get("headers", {})}

    def _run_node(self, monkeypatch):
        from app.core import workflow_engine as we

        secret = SECRET
        captured_events = []

        # Avoid DB + Redis entirely; seal credential resolution to known value
        monkeypatch.setattr(we, "get_credential_value", lambda cid, uid, db: secret)
        monkeypatch.setattr(
            we, "redact_config_credentials",
            lambda config, uid, db: config,  # input path not under test here
        )
        monkeypatch.setattr(we, "get_executor", lambda node_type: self.FakeCredentialExecutor())

        async def fake_publish(event):
            captured_events.append(event)

        monkeypatch.setattr(we, "publish_event", fake_publish)

        node = WorkflowNode(
            id="n1",
            node_type="http_request",
            config={"url": "{{cred:1}}", "headers": {"Authorization": "Bearer {{cred:1}}"}},
        )
        ctx = ExecutionContext(execution_id="exec-1", workflow_id=1, trigger_data={})
        ctx.init_node("n1")

        engine = we.WorkflowEngine()
        # db must be truthy for the engine's credential-resolution path to run;
        # all DB-touching functions are monkeypatched, so a dummy object suffices.
        asyncio.run(engine._execute_node(node, ctx, "exec-1", user_id=7, db=object()))

        return ctx, captured_events

    def test_output_stored_in_context_is_redacted(self, monkeypatch):
        ctx, _ = self._run_node(monkeypatch)
        output_data = ctx.get_node_output("n1")
        assert output_data is not None
        serialized = str(output_data)
        assert SECRET not in serialized
        # Masked value present (either as value or inside the echoed string)
        assert MASKED in serialized or "***" in serialized

    def test_published_event_output_is_redacted(self, monkeypatch):
        _, captured_events = self._run_node(monkeypatch)
        completed = [e for e in captured_events if e.event_type == "node_completed"]
        assert completed, "expected a node_completed event"
        assert SECRET not in str(completed[0].data["output"])