"""Tests for the Execution Engine components."""

import pytest
import asyncio
from app.core.workflow_definition import WorkflowNode, WorkflowEdge, WorkflowDefinition
from app.core.graph_validator import validate_graph, GraphValidationError
from app.core.execution_planner import ExecutionPlanner
from app.core.execution_context import ExecutionContext, ExecutionStatus, NodeStatus
from app.core.workflow_engine import WorkflowEngine


# ── Graph Validator Tests ──

class TestGraphValidator:
    def test_valid_simple_workflow(self):
        nodes = [
            WorkflowNode(id="trigger", node_type="trigger", config={}),
            WorkflowNode(id="output", node_type="output", config={}),
        ]
        edges = [WorkflowEdge(id="e1", source_node_id="trigger", target_node_id="output")]
        validate_graph(nodes, edges)

    def test_empty_workflow_fails(self):
        with pytest.raises(GraphValidationError) as exc_info:
            validate_graph([], [])
        errors = exc_info.value.errors
        assert any("no nodes" in e.lower() for e in errors)

    def test_no_trigger_fails(self):
        nodes = [WorkflowNode(id="a", node_type="output", config={})]
        with pytest.raises(GraphValidationError) as exc_info:
            validate_graph(nodes, [])
        errors = exc_info.value.errors
        assert any("trigger" in e.lower() for e in errors)

    def test_multiple_triggers_fails(self):
        nodes = [
            WorkflowNode(id="t1", node_type="trigger", config={}),
            WorkflowNode(id="t2", node_type="trigger", config={}),
        ]
        with pytest.raises(GraphValidationError) as exc_info:
            validate_graph(nodes, [])
        errors = exc_info.value.errors
        assert any("only have one" in e.lower() for e in errors)

    def test_orphan_node_fails(self):
        nodes = [
            WorkflowNode(id="trigger", node_type="trigger", config={}),
            WorkflowNode(id="orphan", node_type="output", config={}),
        ]
        with pytest.raises(GraphValidationError) as exc_info:
            validate_graph(nodes, [])
        errors = exc_info.value.errors
        assert any("not connected" in e.lower() for e in errors)

    def test_cycle_detected(self):
        nodes = [
            WorkflowNode(id="a", node_type="transform", config={}),
            WorkflowNode(id="b", node_type="transform", config={}),
        ]
        edges = [
            WorkflowEdge(id="e1", source_node_id="a", target_node_id="b"),
            WorkflowEdge(id="e2", source_node_id="b", target_node_id="a"),
        ]
        with pytest.raises(GraphValidationError) as exc_info:
            validate_graph(nodes, edges)
        errors = exc_info.value.errors
        assert any("cycle" in e.lower() for e in errors)

    def test_invalid_edge_reference(self):
        nodes = [WorkflowNode(id="a", node_type="trigger", config={})]
        edges = [WorkflowEdge(id="e1", source_node_id="a", target_node_id="missing")]
        with pytest.raises(GraphValidationError) as exc_info:
            validate_graph(nodes, edges)
        errors = exc_info.value.errors
        assert any("unknown" in e.lower() for e in errors)


# ── Execution Planner Tests ──

class TestExecutionPlanner:
    def test_linear_workflow(self):
        nodes = [
            WorkflowNode(id="t", node_type="trigger", config={}),
            WorkflowNode(id="a", node_type="transform", config={}),
            WorkflowNode(id="b", node_type="output", config={}),
        ]
        edges = [
            WorkflowEdge(id="e1", source_node_id="t", target_node_id="a"),
            WorkflowEdge(id="e2", source_node_id="a", target_node_id="b"),
        ]
        plan = ExecutionPlanner(nodes, edges).plan()
        assert plan.total_steps == 3
        assert plan.execution_order == [["t"], ["a"], ["b"]]

    def test_parallel_workflow(self):
        nodes = [
            WorkflowNode(id="t", node_type="trigger", config={}),
            WorkflowNode(id="a", node_type="transform", config={}),
            WorkflowNode(id="b", node_type="transform", config={}),
            WorkflowNode(id="out", node_type="output", config={}),
        ]
        edges = [
            WorkflowEdge(id="e1", source_node_id="t", target_node_id="a"),
            WorkflowEdge(id="e2", source_node_id="t", target_node_id="b"),
            WorkflowEdge(id="e3", source_node_id="a", target_node_id="out"),
            WorkflowEdge(id="e4", source_node_id="b", target_node_id="out"),
        ]
        plan = ExecutionPlanner(nodes, edges).plan()
        assert plan.total_steps == 4
        assert plan.max_parallelism == 2


# ── Execution Context Tests ──

class TestExecutionContext:
    def test_node_lifecycle(self):
        ctx = ExecutionContext(execution_id="test-1", workflow_id=1)
        ctx.init_node("n1")
        ctx.start_node("n1", {"data": 1})
        assert ctx.get_node_output("n1") is None
        ctx.complete_node("n1", {"result": 42})
        assert ctx.get_node_output("n1") == {"result": 42}

    def test_node_failure(self):
        ctx = ExecutionContext(execution_id="test-2", workflow_id=1)
        ctx.init_node("n1")
        ctx.start_node("n1", {})
        ctx.fail_node("n1", "boom")
        ne = ctx.node_executions["n1"]
        assert ne.status == NodeStatus.FAILED
        assert ne.error == "boom"

    def test_global_vars(self):
        ctx = ExecutionContext(execution_id="test-3", workflow_id=1)
        ctx.set_var("counter", 0)
        ctx.set_var("counter", ctx.get_var("counter") + 1)
        assert ctx.get_var("counter") == 1

    def test_summary(self):
        ctx = ExecutionContext(execution_id="test-4", workflow_id=1)
        ctx.init_node("n1")
        ctx.start()
        ctx.complete()
        s = ctx.summary
        assert s["status"] == "completed"


# ── Workflow Engine Integration Tests ──

class TestWorkflowEngine:
    def test_simple_workflow_execution(self):
        defn = WorkflowDefinition(
            nodes=[
                WorkflowNode(id="trigger", node_type="trigger", config={}),
                WorkflowNode(id="transform", node_type="transform", config={"data": {"hello": "world"}, "operation": "identity"}),
            ],
            edges=[
                WorkflowEdge(id="e1", source_node_id="trigger", target_node_id="transform"),
            ],
        )
        engine = WorkflowEngine()
        ctx = asyncio.run(
            engine.execute("exec-test-1", 1, defn, {"hello": "world"})
        )
        assert ctx.status == ExecutionStatus.COMPLETED
        trigger_out = ctx.get_node_output("trigger")
        assert trigger_out is not None
        assert trigger_out["trigger_data"]["hello"] == "world"
        transform_out = ctx.get_node_output("transform")
        assert transform_out is not None
        assert transform_out["data"]["hello"] == "world"

    def test_validation_error_on_run(self):
        defn = WorkflowDefinition(nodes=[], edges=[])
        engine = WorkflowEngine()
        with pytest.raises(GraphValidationError):
            asyncio.run(
                engine.execute("exec-test-2", 1, defn)
            )


# ── SSRF Protection Tests ──

class TestSSRFProtection:
    """Regression tests for SSRF protection (shared module)."""

    def test_block_private_ip_127(self):
        """Request to 127.0.0.1 must be blocked."""
        from app.core.ssrf_protection import validate_url
        with pytest.raises(ValueError, match="blocked"):
            validate_url("http://127.0.0.1/secret")

    def test_block_private_ip_10(self):
        """Request to 10.x.x.x must be blocked."""
        from app.core.ssrf_protection import validate_url
        with pytest.raises(ValueError, match="blocked"):
            validate_url("http://10.0.0.1/admin")

    def test_block_link_local_cloud_metadata(self):
        """Request to 169.254.169.254 (cloud metadata) must be blocked."""
        from app.core.ssrf_protection import validate_url
        with pytest.raises(ValueError, match="blocked|resolves"):
            validate_url("http://169.254.169.254/latest/meta-data/")

    def test_block_localhost(self):
        """Request to localhost must be blocked."""
        from app.core.ssrf_protection import validate_url
        with pytest.raises(ValueError, match="blocked"):
            validate_url("http://localhost:8080/internal")

    def test_block_private_ip_192(self):
        """Request to 192.168.x.x must be blocked."""
        from app.core.ssrf_protection import validate_url
        with pytest.raises(ValueError, match="blocked"):
            validate_url("http://192.168.1.1/router")

    def test_block_private_ip_172(self):
        """Request to 172.16.x.x must be blocked."""
        from app.core.ssrf_protection import validate_url
        with pytest.raises(ValueError, match="blocked"):
            validate_url("http://172.16.0.1/gateway")

    def test_block_ipv6_loopback(self):
        """Request to [::1] (IPv6 loopback) must be blocked."""
        from app.core.ssrf_protection import validate_url
        with pytest.raises(ValueError, match="blocked|resolve"):
            validate_url("http://[::1]/secret")

    def test_block_non_http_scheme(self):
        """Request with ftp:// scheme must be blocked."""
        from app.core.ssrf_protection import validate_url
        with pytest.raises(ValueError, match="not allowed"):
            validate_url("ftp://example.com/file")

    def test_block_hex_ip_127(self):
        """Request with hex IP 0x7f000001 (127.0.0.1) must be blocked."""
        from app.core.ssrf_protection import validate_url
        with pytest.raises(ValueError, match="blocked"):
            validate_url("http://0x7f000001/secret")

    def test_block_decimal_ip_127(self):
        """Request with decimal IP 2130706433 (127.0.0.1) must be blocked."""
        from app.core.ssrf_protection import validate_url
        with pytest.raises(ValueError, match="blocked"):
            validate_url("http://2130706433/secret")

    def test_block_ipv4_mapped_ipv6(self):
        """Request with ::ffff:127.0.0.1 must be blocked."""
        from app.core.ssrf_protection import validate_url
        with pytest.raises(ValueError, match="blocked|resolve"):
            validate_url("http://[::ffff:127.0.0.1]/secret")

    @pytest.mark.asyncio
    async def test_redirect_to_private_ip_is_blocked(self, monkeypatch):
        """A redirect hop pointing at an internal host must be rejected."""
        from app.core.executors import http_request

        class FakeResponse:
            status_code = 302
            headers = {"location": "http://127.0.0.1/internal"}
            text = ""
            content = b""

            def json(self):
                raise ValueError("no json")

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def request(self, *args, **kwargs):
                return FakeResponse()

        monkeypatch.setattr(http_request.httpx, "AsyncClient", lambda *a, **k: FakeClient())
        executor = http_request.HttpRequestExecutor()
        config = {"url": "http://example.com/start", "method": "GET"}
        with pytest.raises(ValueError, match="blocked"):
            await executor.execute("node1", config, None)

    @pytest.mark.asyncio
    async def test_redirect_loop_exceeds_max_hops(self, monkeypatch):
        """A redirect chain longer than MAX_REDIRECTS must be rejected."""
        from app.core.executors import http_request

        class FakeResponse:
            status_code = 302
            headers = {"location": "http://example.com/next"}
            text = ""
            content = b""

            def json(self):
                raise ValueError("no json")

        class FakeClient:
            call_count = 0

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def request(self, *args, **kwargs):
                FakeClient.call_count += 1
                return FakeResponse()

        monkeypatch.setattr(http_request.httpx, "AsyncClient", lambda *a, **k: FakeClient())
        executor = http_request.HttpRequestExecutor()
        config = {"url": "http://example.com/start", "method": "GET"}
        with pytest.raises(ValueError, match="Too many redirects"):
            await executor.execute("node1", config, None)
