"""Seed realistic demo data into FlowAlchemy.

Populates: demo user, node-definition catalog, 6 workflows (nodes + edges in
both relational tables AND the React Flow `definition` JSON), version history,
execution history with per-node results, schedules, webhooks, and credentials.

Idempotent: if the demo user already exists, only that user's data is wiped
and re-seeded (nothing else in the database is touched).

Usage (from the backend/ directory):

    DATABASE_URL="sqlite:///./flowalchemy_demo.db" \
    SECRET_KEY="demo-seed-2026-super-secret-key" \
    .venv/bin/python scripts/seed_demo_data.py

Both env vars are required (settings validator rejects empty values).
Any DATABASE_URL supported by SQLAlchemy works (SQLite, PostgreSQL, ...).
"""

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

# Make `app` importable when running the script from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Settings are read from the environment OR the `.env` file next to the
# backend package (matching how the app itself is configured).
from app.core.config import settings

if not settings.DATABASE_URL or not settings.SECRET_KEY:
    print(
        "ERROR: DATABASE_URL and SECRET_KEY must be set (env vars or backend/.env), e.g.\n"
        '  DATABASE_URL="sqlite:///./flowalchemy_demo.db" '
        'SECRET_KEY="demo-seed-2026-super-secret-key" '
        ".venv/bin/python scripts/seed_demo_data.py",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy.orm import Session

import app.core.database as database
from app.core.security import hash_password
from app.core.encryption import encrypt_value
from app.core.workflow_definition import NodeType
from app.core.workflow_adapter import react_flow_to_definition
from app.models.workflow import (
    User,
    Workflow,
    NodeDefinition,
    WorkflowNode,
    WorkflowEdge,
    Execution,
    NodeExecution,
    WorkflowVersion,
    Credential,
)

DEMO_EMAIL = "demo@flowalchemy.ai"
DEMO_PASSWORD = "DemoPass123"

# ──────────────────────────────────────────────────────────────────────────
# Node definition catalog (upserted; matches the palette in the editor)
# ──────────────────────────────────────────────────────────────────────────

CATALOG: List[Dict[str, Any]] = [
    {
        "node_type": "trigger",
        "name": "Trigger",
        "description": "Starts the workflow. Supports manual, schedule and webhook triggers.",
        "icon": "zap",
        "category": "Core",
        "input_schema": {
            "type": "object",
            "properties": {
                "trigger": {"type": "string", "title": "Trigger type", "enum": ["manual", "schedule", "webhook"]},
            },
        },
        "output_schema": {"type": "object", "properties": {"trigger": {"type": "string"}}},
    },
    {
        "node_type": "http_request",
        "name": "HTTP Request",
        "description": "Send an HTTP request to any public URL with optional headers and JSON body.",
        "icon": "globe",
        "category": "Network",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "title": "URL", "format": "uri"},
                "method": {"type": "string", "title": "Method", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]},
                "headers": {"type": "object", "title": "Headers"},
                "body": {"type": "object", "title": "Body (JSON)"},
                "timeout": {"type": "integer", "title": "Timeout (ms)", "minimum": 100, "maximum": 300000},
            },
        },
        "output_schema": {"type": "object", "properties": {"status": {"type": "integer"}, "data": {"type": "object"}, "headers": {"type": "object"}}},
    },
    {
        "node_type": "transform",
        "name": "Transform",
        "description": "Shape data: filter, map, merge or split the incoming payload.",
        "icon": "filter",
        "category": "Data",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "title": "Operation", "enum": ["identity", "filter", "map", "merge", "split"]},
                "params": {"type": "object", "title": "Parameters"},
            },
        },
        "output_schema": {"type": "object", "properties": {"result": {"type": "object"}, "count": {"type": "integer"}}},
    },
    {
        "node_type": "condition",
        "name": "Condition",
        "description": "Branch the workflow based on a field comparison.",
        "icon": "git-branch",
        "category": "Logic",
        "input_schema": {
            "type": "object",
            "properties": {
                "field": {"type": "string", "title": "Field path"},
                "operator": {"type": "string", "title": "Operator", "enum": ["equals", "not_equals", "greater_than", "less_than", "contains"]},
                "value": {"type": "string", "title": "Value"},
            },
        },
        "output_schema": {"type": "object", "properties": {"matched": {"type": "boolean"}}},
    },
    {
        "node_type": "delay",
        "name": "Delay",
        "description": "Wait for a given duration before continuing.",
        "icon": "clock",
        "category": "Flow",
        "input_schema": {"type": "object", "properties": {"duration_ms": {"type": "integer", "title": "Duration (ms)", "minimum": 0}}},
        "output_schema": {"type": "object", "properties": {"slept_ms": {"type": "integer"}}},
    },
    {
        "node_type": "output",
        "name": "Output",
        "description": "Deliver the result to a destination: log, email, Slack or webhook.",
        "icon": "send",
        "category": "Core",
        "input_schema": {
            "type": "object",
            "properties": {
                "destination": {"type": "string", "title": "Destination", "enum": ["log", "email", "slack", "webhook"]},
                "message": {"type": "string", "title": "Message"},
            },
        },
        "output_schema": {"type": "object", "properties": {"message": {"type": "string"}, "destination": {"type": "string"}}},
    },
]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def days_ago(days: float, hour: int = 9, minute: int = 30) -> datetime:
    """A plausible past timestamp (days ago, at a fixed clock time, UTC)."""
    base = utcnow() - timedelta(days=days)
    return base.replace(hour=hour, minute=minute, second=0, microsecond=0)


# ──────────────────────────────────────────────────────────────────────────
# React Flow helpers (the format the editor reads/writes)
# ──────────────────────────────────────────────────────────────────────────

ALL_NODE_TYPES = {nt.value for nt in NodeType}


def rf_node(node_id: str, node_type: str, x: int, y: int, label: str, config: Dict[str, Any]) -> Dict[str, Any]:
    assert node_type in ALL_NODE_TYPES, f"invalid node type {node_type!r}"
    schema = next(c for c in CATALOG if c["node_type"] == node_type)["input_schema"]
    return {
        "id": node_id,
        "type": "custom",
        "position": {"x": x, "y": y},
        "data": {"label": label, "nodeType": node_type, "inputSchema": schema, "config": config or {}},
    }


def rf_edge(edge_id: str, source: str, target: str, label: str | None = None) -> Dict[str, Any]:
    edge: Dict[str, Any] = {"id": edge_id, "source": source, "target": target}
    if label:
        edge["label"] = label
        edge["data"] = {"condition": label}
    return edge


def reactive_definition(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"nodes": nodes, "edges": edges}


# ──────────────────────────────────────────────────────────────────────────
# Seed contents
# ──────────────────────────────────────────────────────────────────────────

CREDENTIALS = [
    ("Stripe Secret Key (test)", "api_key", "STRIPE_TEST_KEY_PLACEHOLDER"),
    ("Slack Workspace Token", "token", "SLACK_BOT_TOKEN_PLACEHOLDER"),
]


def _execution(
    status: str,
    trigger: str,
    days: float,
    input_data: Dict[str, Any],
    node_runs: List[tuple],
    output: Dict[str, Any] | None,
    error: Optional[str],
    worker: str = "worker-1",
    retry: int = 0,
    hour: int = 9,
    minute: int = 30,
) -> Dict[str, Any]:
    return {
        "status": status,
        "trigger": trigger,
        "days": days,
        "hour": hour,
        "minute": minute,
        "input": input_data,
        "node_runs": node_runs,
        "output": output,
        "error": error,
        "worker": worker,
        "retry": retry,
    }


def build_full_dataset() -> Dict[str, Any]:
    specs = []
    # 1 ── Customer Support Auto-Triage ─────────────────────────────
    specs.append({
        "name": "Customer Support Auto-Triage",
        "description": "Classifies urgent support tickets and routes them to the response log with a priority summary.",
        "is_active": True,
        "schedule": None,
        "webhook": False,
        "nodes": [
            rf_node("n1", "trigger", 40, 150, "Manual Trigger", {"trigger": "manual"}),
            rf_node("n2", "condition", 230, 150, "Is Urgent?", {"field": "ticket.priority", "operator": "equals", "value": "high"}),
            rf_node("n3", "transform", 430, 60, "Build Summary", {"operation": "map", "params": {"summary": "{{ticket.subject}} ({{ticket.id}})"}}),
            rf_node("n4", "output", 640, 60, "Log Response", {"destination": "log", "message": "URGENT: {{summary}}"}),
        ],
        "edges": [
            rf_edge("e1", "n1", "n2"),
            rf_edge("e2", "n2", "n3", "true"),
            rf_edge("e3", "n3", "n4"),
        ],
        "versions": [
            ("Initial version", "n1", "n2", "n3"),
            ("Add summary transform", "n1", "n2", "n3", "n4"),
            ("Improve summary template", "n1", "n2", "n3", "n4"),
            ("Switch to log destination", "n1", "n2", "n3", "n4"),
        ],
        "executions": [
            _execution("completed", "manual", 14.0,
                       {"ticket": {"id": "T-1201", "priority": "high", "subject": "Payment failed for invoice #8871"}},
                       [("n1", "completed", {"trigger": "manual", "input": {"ticket": {"id": "T-1201", "priority": "high"}}}, None, 40),
                        ("n2", "completed", {"matched": True, "field": "ticket.priority", "value": "high"}, None, 90),
                        ("n3", "completed", {"result": {"summary": "Payment failed for invoice #8871 (T-1201)"}, "count": 1}, None, 210),
                        ("n4", "completed", {"message": "URGENT: Payment failed for invoice #8871 (T-1201)", "destination": "log"}, None, 60)],
                       {"success": True, "summary": "URGENT: Payment failed for invoice #8871 (T-1201)", "node_count": 4}, None),
            _execution("completed", "manual", 11.0,
                       {"ticket": {"id": "T-1210", "priority": "low", "subject": "Question about billing details"}},
                       [("n1", "completed", {"trigger": "manual", "input": {"ticket": {"id": "T-1210", "priority": "low"}}}, None, 35),
                        ("n2", "completed", {"matched": False, "field": "ticket.priority", "value": "high"}, None, 85)],
                       {"success": True, "summary": "Not urgent, skipped", "node_count": 2}, None, hour=10, minute=12),
            _execution("completed", "manual", 8.0,
                       {"ticket": {"id": "T-1233", "priority": "high", "subject": "Account locked after 3 failed logins"}},
                       [("n1", "completed", {"trigger": "manual", "input": {"ticket": {"id": "T-1233", "priority": "high"}}}, None, 38),
                        ("n2", "completed", {"matched": True, "field": "ticket.priority", "value": "high"}, None, 88),
                        ("n3", "completed", {"result": {"summary": "Account locked after 3 failed logins (T-1233)"}, "count": 1}, None, 195),
                        ("n4", "completed", {"message": "URGENT: Account locked after 3 failed logins (T-1233)", "destination": "log"}, None, 58)],
                       {"success": True, "summary": "URGENT: Account locked after 3 failed logins (T-1233)", "node_count": 4}, None, hour=11, minute=45),
            _execution("completed", "manual", 5.0,
                       {"ticket": {"id": "T-1250", "priority": "high", "subject": "Refund not received after 5 days"}},
                       [("n1", "completed", {"trigger": "manual", "input": {"ticket": {"id": "T-1250", "priority": "high"}}}, None, 41),
                        ("n2", "completed", {"matched": True, "field": "ticket.priority", "value": "high"}, None, 92),
                        ("n3", "completed", {"result": {"summary": "Refund not received after 5 days (T-1250)"}, "count": 1}, None, 212),
                        ("n4", "completed", {"message": "URGENT: Refund not received after 5 days (T-1250)", "destination": "log"}, None, 61)],
                       {"success": True, "summary": "URGENT: Refund not received after 5 days (T-1250)", "node_count": 4}, None, hour=8, minute=3),
            _execution("completed", "manual", 2.0,
                       {"ticket": {"id": "T-1261", "priority": "normal", "subject": "Feature request: dark mode"}},
                       [("n1", "completed", {"trigger": "manual", "input": {"ticket": {"id": "T-1261", "priority": "normal"}}}, None, 36),
                        ("n2", "completed", {"matched": False, "field": "ticket.priority", "value": "high"}, None, 87)],
                       {"success": True, "summary": "Not urgent, skipped", "node_count": 2}, None, hour=15, minute=40),
            _execution("failed", "manual", 1.0,
                       {"ticket": {"id": "T-1270", "priority": "high", "subject": "Cannot reset password"}},
                       [("n1", "completed", {"trigger": "manual", "input": {"ticket": {"id": "T-1270", "priority": "high"}}}, None, 39),
                        ("n2", "failed", {}, "Invalid field path 'ticket.priority'", 12)],
                       None,
                       "Node 'Is Urgent?' failed: Invalid field path 'ticket.priority'. Check the condition config.",
                       worker="worker-2", retry=1, hour=9, minute=18),
        ],
    })

    # 2 ── Daily Sales Report ───────────────────────────────────────
    specs.append({
        "name": "Daily Sales Report",
        "description": "Fetches the Stripe balance every weekday morning and emails a compact summary to finance.",
        "is_active": True,
        "schedule": "0 8 * * 1-5",
        "webhook": False,
        "nodes": [
            rf_node("n1", "trigger", 40, 150, "Schedule Trigger", {"trigger": "schedule"}),
            rf_node("n2", "http_request", 240, 150, "Fetch Balance", {"url": "https://httpbin.org/json", "method": "GET", "timeout": 20000}),
            rf_node("n3", "transform", 450, 150, "Format Report", {"operation": "merge", "params": {"lines": ["Available: {{available}}", "Pending: {{pending}}"]}}),
            rf_node("n4", "output", 660, 150, "Log Report", {"destination": "log", "message": "Daily sales report generated"}),
        ],
        "edges": [rf_edge("e1", "n1", "n2"), rf_edge("e2", "n2", "n3"), rf_edge("e3", "n3", "n4")],
        "versions": [
            ("Initial version", "n1", "n2"),
            ("Add report formatting", "n1", "n2", "n3"),
            ("Include pending balance", "n1", "n2", "n3", "n4"),
            ("Switch to email destination", "n1", "n2", "n3", "n4"),
            ("Tighten weekday schedule", "n1", "n2", "n3", "n4"),
        ],
        "executions": [
            _execution("completed", "schedule", 14.0,
                       {"period": "2026-09-05"},
                       [("n1", "completed", {"trigger": "schedule", "input": {"period": "2026-09-05"}}, None, 30),
                        ("n2", "completed", {"status": 200, "data": {"available": [{"amount": 482930, "currency": "usd", "source_types": {"card": 482930}}], "pending": [{"amount": 12450, "currency": "usd"}]}, "headers": {"content-type": "application/json"}}, None, 840),
                        ("n3", "completed", {"result": {"lines": ["Available: $4,829.30", "Pending: $124.50"]}, "count": 2}, None, 160),
                        ("n4", "completed", {"message": "Daily sales report: Available: $4,829.30 / Pending: $124.50", "destination": "email"}, None, 75)],
                       {"success": True, "summary": "Available: $4,829.30 / Pending: $124.50", "node_count": 4}, None, hour=8, minute=1),
            _execution("completed", "schedule", 12.0,
                       {"period": "2026-09-07"},
                       [("n1", "completed", {"trigger": "schedule", "input": {"period": "2026-09-07"}}, None, 31),
                        ("n2", "completed", {"status": 200, "data": {"available": [{"amount": 510220, "currency": "usd"}], "pending": [{"amount": 9800, "currency": "usd"}]}, "headers": {"content-type": "application/json"}}, None, 910),
                        ("n3", "completed", {"result": {"lines": ["Available: $5,102.20", "Pending: $98.00"]}, "count": 2}, None, 152),
                        ("n4", "completed", {"message": "Daily sales report: Available: $5,102.20 / Pending: $98.00", "destination": "email"}, None, 70)],
                       {"success": True, "summary": "Available: $5,102.20 / Pending: $98.00", "node_count": 4}, None, hour=8, minute=0),
            _execution("completed", "schedule", 9.0,
                       {"period": "2026-09-10"},
                       [("n1", "completed", {"trigger": "schedule", "input": {"period": "2026-09-10"}}, None, 29),
                        ("n2", "completed", {"status": 200, "data": {"available": [{"amount": 498010, "currency": "usd"}], "pending": [{"amount": 0, "currency": "usd"}]}, "headers": {"content-type": "application/json"}}, None, 780),
                        ("n3", "completed", {"result": {"lines": ["Available: $4,980.10", "Pending: $0.00"]}, "count": 2}, None, 148),
                        ("n4", "completed", {"message": "Daily sales report: Available: $4,980.10 / Pending: $0.00", "destination": "email"}, None, 66)],
                       {"success": True, "summary": "Available: $4,980.10 / Pending: $0.00", "node_count": 4}, None, hour=8, minute=1),
            _execution("failed", "schedule", 6.0,
                       {"period": "2026-09-13"},
                       [("n1", "completed", {"trigger": "schedule", "input": {"period": "2026-09-13"}}, None, 30),
                        ("n2", "failed", {}, "HTTP 500 from upstream (api.stripe.com)", 4200)],
                       None,
                       "Node 'Fetch Balance' failed: HTTP 500 from upstream (api.stripe.com). Retry 1 of 3 will run in ~8s.",
                       worker="worker-1", retry=1, hour=8, minute=2),
            _execution("completed", "schedule", 4.0,
                       {"period": "2026-09-15"},
                       [("n1", "completed", {"trigger": "schedule", "input": {"period": "2026-09-15"}}, None, 28),
                        ("n2", "completed", {"status": 200, "data": {"available": [{"amount": 521390, "currency": "usd"}], "pending": [{"amount": 22000, "currency": "usd"}]}, "headers": {"content-type": "application/json"}}, None, 900),
                        ("n3", "completed", {"result": {"lines": ["Available: $5,213.90", "Pending: $220.00"]}, "count": 2}, None, 155),
                        ("n4", "completed", {"message": "Daily sales report: Available: $5,213.90 / Pending: $220.00", "destination": "email"}, None, 68)],
                       {"success": True, "summary": "Available: $5,213.90 / Pending: $220.00", "node_count": 4}, None, hour=8, minute=0),
            _execution("completed", "schedule", 2.5,
                       {"period": "2026-09-17"},
                       [("n1", "completed", {"trigger": "schedule", "input": {"period": "2026-09-17"}}, None, 30),
                        ("n2", "completed", {"status": 200, "data": {"available": [{"amount": 478340, "currency": "usd"}], "pending": [{"amount": 5500, "currency": "usd"}]}, "headers": {"content-type": "application/json"}}, None, 820),
                        ("n3", "completed", {"result": {"lines": ["Available: $4,783.40", "Pending: $55.00"]}, "count": 2}, None, 150),
                        ("n4", "completed", {"message": "Daily sales report: Available: $4,783.40 / Pending: $55.00", "destination": "email"}, None, 72)],
                       {"success": True, "summary": "Available: $4,783.40 / Pending: $55.00", "node_count": 4}, None, hour=8, minute=1),
            _execution("cancelled", "schedule", 1.5,
                       {"period": "2026-09-19"},
                       [("n1", "completed", {"trigger": "schedule", "input": {"period": "2026-09-19"}}, None, 27),
                        ("n2", "completed", {"status": 200, "data": {"available": [{"amount": 501000, "currency": "usd"}], "pending": [{"amount": 3300, "currency": "usd"}]}, "headers": {"content-type": "application/json"}}, None, 870)],
                       None,
                       "Execution cancelled by user before report dispatch.",
                       worker="worker-2", retry=0, hour=8, minute=5),
            _execution("completed", "schedule", 0.5,
                       {"period": "2026-09-21"},
                       [("n1", "completed", {"trigger": "schedule", "input": {"period": "2026-09-21"}}, None, 31),
                        ("n2", "completed", {"status": 200, "data": {"available": [{"amount": 533210, "currency": "usd"}], "pending": [{"amount": 8800, "currency": "usd"}]}, "headers": {"content-type": "application/json"}}, None, 890),
                        ("n3", "completed", {"result": {"lines": ["Available: $5,332.10", "Pending: $88.00"]}, "count": 2}, None, 158),
                        ("n4", "completed", {"message": "Daily sales report: Available: $5,332.10 / Pending: $88.00", "destination": "email"}, None, 69)],
                       {"success": True, "summary": "Available: $5,332.10 / Pending: $88.00", "node_count": 4}, None, hour=8, minute=0),
        ],
    })

    # 3 ── Content Moderation Pipeline ─────────────────────────────
    specs.append({
        "name": "Content Moderation Pipeline",
        "description": "Screens user-submitted content through the moderation API and alerts the team on Slack for flagged items.",
        "is_active": True,
        "schedule": None,
        "webhook": True,
        "nodes": [
            rf_node("n1", "trigger", 40, 150, "Webhook Trigger", {"trigger": "webhook"}),
            rf_node("n2", "http_request", 250, 150, "Moderation API", {"url": "https://httpbin.org/post", "method": "POST", "body": {"input": "{{content.text}}"}, "timeout": 20000}),
            rf_node("n3", "condition", 460, 150, "Flagged?", {"field": "result.flagged", "operator": "equals", "value": "true"}),
            rf_node("n4", "output", 670, 150, "Notify Team", {"destination": "log", "message": "Flagged content detected — team notified"}),
        ],
        "edges": [rf_edge("e1", "n1", "n2"), rf_edge("e2", "n2", "n3"), rf_edge("e3", "n3", "n4", "true")],
        "versions": [
            ("Initial version", "n1", "n2"),
            ("Add flag condition", "n1", "n2", "n3"),
            ("Route flagged items to Slack", "n1", "n2", "n3", "n4"),
        ],
        "executions": [
            _execution("completed", "webhook", 13.0,
                       {"content": {"text": "Free shipping promo for the weekend!", "author": "user_991"}},
                       [("n1", "completed", {"trigger": "webhook", "input": {"content": {"text": "Free shipping promo for the weekend!"}}}, None, 33),
                        ("n2", "completed", {"status": 200, "data": {"results": [{"flagged": False, "categories": {"harassment": False}}]}, "headers": {"content-type": "application/json"}}, None, 2400),
                        ("n3", "completed", {"matched": False, "field": "result.flagged", "value": True}, None, 95)],
                       {"success": True, "summary": "Content approved", "node_count": 3}, None, worker="worker-1"),
            _execution("completed", "webhook", 9.0,
                       {"content": {"text": "You should definitely check out this amazing investment opportunity", "author": "user_145"}},
                       [("n1", "completed", {"trigger": "webhook", "input": {"content": {"text": "You should definitely check out this amazing investment opportunity"}}}, None, 30),
                        ("n2", "completed", {"status": 200, "data": {"results": [{"flagged": True, "categories": {"harassment": False, "self-harm": False, "financial": True}}]}, "headers": {"content-type": "application/json"}}, None, 3100),
                        ("n3", "completed", {"matched": True, "field": "result.flagged", "value": True}, None, 88),
                        ("n4", "completed", {"message": "⚠️ Flagged content: You should definitely check out this amazing investment opportunity", "destination": "slack"}, None, 140)],
                       {"success": True, "summary": "Flagged & alerted to Slack", "node_count": 4}, None, hour=13, minute=22),
            _execution("completed", "webhook", 4.0,
                       {"content": {"text": "How do I reset my account password?", "author": "user_310"}},
                       [("n1", "completed", {"trigger": "webhook", "input": {"content": {"text": "How do I reset my account password?"}}}, None, 34),
                        ("n2", "completed", {"status": 200, "data": {"results": [{"flagged": False, "categories": {}}]}, "headers": {"content-type": "application/json"}}, None, 1900),
                        ("n3", "completed", {"matched": False, "field": "result.flagged", "value": True}, None, 84)],
                       {"success": True, "summary": "Content approved", "node_count": 3}, None, hour=17, minute=48),
            _execution("failed", "webhook", 1.2,
                       {"content": {"text": "Quick question about my order status"}},
                       [("n1", "completed", {"trigger": "webhook", "input": {"content": {"text": "Quick question about my order status"}}}, None, 31),
                        ("n2", "failed", {}, "Request timed out after 45000ms", 15000)],
                       None,
                       "Node 'Moderation API' failed: Request timed out after 45000ms (url=https://api.openai.com/v1/moderations)",
                       worker="worker-2", retry=2, hour=10, minute=5),
        ],
    })

    # 4 ── Payment Retry Handler ───────────────────────────────────
    specs.append({
        "name": "Payment Retry Handler",
        "description": "Retries failed Stripe charges automatically every 30 minutes during the day.",
        "is_active": True,
        "schedule": "*/30 * * * *",
        "webhook": True,
        "nodes": [
            rf_node("n1", "trigger", 40, 150, "Webhook Trigger", {"trigger": "webhook"}),
            rf_node("n2", "condition", 250, 150, "Is Payment Failed?", {"field": "event.type", "operator": "equals", "value": "payment.failed"}),
            rf_node("n3", "http_request", 460, 150, "Retry Charge", {"url": "https://httpbin.org/post", "method": "POST", "body": {"amount": "{{event.amount}}", "currency": "usd"}, "timeout": 20000}),
        ],
        "edges": [rf_edge("e1", "n1", "n2"), rf_edge("e2", "n2", "n3", "true")],
        "versions": [
            ("Initial version", "n1", "n2", "n3"),
            ("Guard on event type", "n1", "n2", "n3"),
            ("Close idempotency with customer id", "n1", "n2", "n3"),
        ],
        "executions": [
            _execution("completed", "webhook", 7.0,
                       {"event": {"type": "payment.failed", "amount": 24900, "customer": "cus_AbCdEf123456"}},
                       [("n1", "completed", {"trigger": "webhook", "input": {"event": {"type": "payment.failed", "amount": 24900}}}, None, 29),
                        ("n2", "completed", {"matched": True, "field": "event.type", "value": "payment.failed"}, None, 82),
                        ("n3", "completed", {"status": 200, "data": {"id": "ch_1H5Demo", "status": "succeeded", "amount": 24900}, "headers": {"content-type": "application/json"}}, None, 1250)],
                       {"success": True, "summary": "Charge retried: ch_1H5Demo", "node_count": 3}, None, hour=14, minute=30),
            _execution("failed", "webhook", 3.0,
                       {"event": {"type": "payment.failed", "amount": 8990, "customer": "cus_ZzYyXx98765"}},
                       [("n1", "completed", {"trigger": "webhook", "input": {"event": {"type": "payment.failed", "amount": 8990}}}, None, 30),
                        ("n2", "completed", {"matched": True, "field": "event.type", "value": "payment.failed"}, None, 85),
                        ("n3", "failed", {}, "Connection error: timed out", 30000)],
                       None,
                       "Node 'Retry Charge' failed: Connection error: timed out (url=https://api.stripe.com/v1/charges)",
                       worker="worker-2", retry=1, hour=18, minute=0),
            _execution("cancelled", "webhook", 1.0,
                       {"event": {"type": "invoice.payment_failed", "amount": 15000, "customer": "cus_AbCdEf123456"}},
                       [("n1", "completed", {"trigger": "webhook", "input": {"event": {"type": "invoice.payment_failed", "amount": 15000}}}, None, 32),
                        ("n2", "completed", {"matched": False, "field": "event.type", "value": "payment.failed"}, None, 80)],
                       None,
                       "Not a retryable event; cancelled by policy.",
                       worker="worker-1", retry=0, hour=9, minute=0),
        ],
    })

    # 5 ── Infra Uptime Monitor ────────────────────────────────────
    specs.append({
        "name": "Infra Uptime Monitor",
        "description": "Pings the status endpoint every 5 minutes, waits before reporting, then notifies the webhook channel.",
        "is_active": True,
        "schedule": "*/5 * * * *",
        "webhook": False,
        "nodes": [
            rf_node("n1", "trigger", 40, 150, "Schedule Trigger", {"trigger": "schedule"}),
            rf_node("n2", "http_request", 230, 150, "Ping Status", {"url": "https://httpbin.org/json", "method": "GET", "timeout": 15000}),
            rf_node("n3", "condition", 420, 150, "Is 200?", {"field": "slideshow.title", "operator": "equals", "value": "Sample Slide Show"}),
            rf_node("n4", "delay", 610, 60, "Cooldown", {"duration_ms": 2000}),
            rf_node("n5", "output", 800, 60, "Notify", {"destination": "log", "message": "Uptime check: OK (200)"}),
        ],
        "edges": [rf_edge("e1", "n1", "n2"), rf_edge("e2", "n2", "n3"), rf_edge("e3", "n3", "n4", "true"), rf_edge("e4", "n4", "n5")],
        "versions": [
            ("Initial version", "n1", "n2", "n3"),
            ("Add cooldown & notification", "n1", "n2", "n3", "n4", "n5"),
        ],
        "executions": [
            _execution("completed", "schedule", 3.0,
                       {"check": "status.example.com"},
                       [("n1", "completed", {"trigger": "schedule", "input": {"check": "status.example.com"}}, None, 30),
                        ("n2", "completed", {"status": 200, "data": {"status": {"code": 200, "latency_ms": 120}}, "headers": {"content-type": "application/json"}}, None, 260),
                        ("n3", "completed", {"matched": True, "field": "status.code", "value": 200}, None, 80),
                        ("n4", "completed", {"slept_ms": 10000}, None, 10020),
                        ("n5", "completed", {"message": "Uptime check: 200", "destination": "webhook"}, None, 120)],
                       {"success": True, "summary": "Uptime check: 200", "node_count": 5}, None, hour=6, minute=0),
            _execution("completed", "schedule", 2.6,
                       {"check": "status.example.com"},
                       [("n1", "completed", {"trigger": "schedule", "input": {"check": "status.example.com"}}, None, 31),
                        ("n2", "completed", {"status": 200, "data": {"status": {"code": 200, "latency_ms": 140}}, "headers": {"content-type": "application/json"}}, None, 275),
                        ("n3", "completed", {"matched": True, "field": "status.code", "value": 200}, None, 79),
                        ("n4", "completed", {"slept_ms": 10000}, None, 10015),
                        ("n5", "completed", {"message": "Uptime check: 200", "destination": "webhook"}, None, 118)],
                       {"success": True, "summary": "Uptime check: 200", "node_count": 5}, None, hour=6, minute=5),
            _execution("completed", "schedule", 2.2,
                       {"check": "status.example.com"},
                       [("n1", "completed", {"trigger": "schedule", "input": {"check": "status.example.com"}}, None, 29),
                        ("n2", "completed", {"status": 200, "data": {"status": {"code": 200, "latency_ms": 155}}, "headers": {"content-type": "application/json"}}, None, 282),
                        ("n3", "completed", {"matched": True, "field": "status.code", "value": 200}, None, 81),
                        ("n4", "completed", {"slept_ms": 10000}, None, 10018),
                        ("n5", "completed", {"message": "Uptime check: 200", "destination": "webhook"}, None, 122)],
                       {"success": True, "summary": "Uptime check: 200", "node_count": 5}, None, hour=6, minute=10),
            _execution("completed", "schedule", 1.8,
                       {"check": "status.example.com"},
                       [("n1", "completed", {"trigger": "schedule", "input": {"check": "status.example.com"}}, None, 30),
                        ("n2", "completed", {"status": 200, "data": {"status": {"code": 200, "latency_ms": 131}}, "headers": {"content-type": "application/json"}}, None, 268),
                        ("n3", "completed", {"matched": True, "field": "status.code", "value": 200}, None, 78),
                        ("n4", "completed", {"slept_ms": 10000}, None, 10021),
                        ("n5", "completed", {"message": "Uptime check: 200", "destination": "webhook"}, None, 119)],
                       {"success": True, "summary": "Uptime check: 200", "node_count": 5}, None, hour=6, minute=15),
            _execution("completed", "schedule", 1.4,
                       {"check": "status.example.com"},
                       [("n1", "completed", {"trigger": "schedule", "input": {"check": "status.example.com"}}, None, 31),
                        ("n2", "completed", {"status": 200, "data": {"status": {"code": 200, "latency_ms": 128}}, "headers": {"content-type": "application/json"}}, None, 264),
                        ("n3", "completed", {"matched": True, "field": "status.code", "value": 200}, None, 82),
                        ("n4", "completed", {"slept_ms": 10000}, None, 10016),
                        ("n5", "completed", {"message": "Uptime check: 200", "destination": "webhook"}, None, 121)],
                       {"success": True, "summary": "Uptime check: 200", "node_count": 5}, None, hour=6, minute=20),
        ],
    })

    # 6 ── Lead Enrichment (Draft) ─────────────────────────────────
    specs.append({
        "name": "Lead Enrichment (Draft)",
        "description": "Enriches new CRM leads with company data. Draft: waiting for the CRM source to be connected.",
        "is_active": True,
        "schedule": None,
        "webhook": False,
        "nodes": [
            rf_node("n1", "trigger", 40, 150, "Manual Trigger", {"trigger": "manual"}),
            rf_node("n2", "http_request", 230, 150, "Fetch Company", {"url": "https://httpbin.org/json", "method": "GET", "timeout": 15000}),
            rf_node("n3", "transform", 420, 150, "Extract Fields", {"operation": "identity"}),
            rf_node("n4", "output", 620, 150, "Update CRM", {"destination": "log", "message": "Lead enriched: company data stored"}),
        ],
        "edges": [rf_edge("e1", "n1", "n2"), rf_edge("e2", "n2", "n3"), rf_edge("e3", "n3", "n4")],
        "versions": [("Initial draft", "n1", "n2", "n3", "n4")],
        "executions": [],
    })

    return {"credentials": CREDENTIALS, "workflows": specs}


# ──────────────────────────────────────────────────────────────────────────
# Seeding
# ──────────────────────────────────────────────────────────────────────────


def upsert_catalog(session: Session) -> Dict[str, int]:
    type_to_id: Dict[str, int] = {}
    for entry in CATALOG:
        existing = session.query(NodeDefinition).filter(NodeDefinition.node_type == entry["node_type"]).first()
        if existing:
            existing.name = entry["name"]
            existing.description = entry["description"]
            existing.input_schema = entry["input_schema"]
            existing.output_schema = entry["output_schema"]
            existing.icon = entry["icon"]
            existing.category = entry["category"]
            type_to_id[entry["node_type"]] = existing.id
        else:
            node_def = NodeDefinition(**entry)
            session.add(node_def)
            session.flush()
            type_to_id[entry["node_type"]] = node_def.id
    session.commit()
    return type_to_id


def wipe_demo_user(session: Session, user: Optional[User]) -> None:
    if user is None:
        return
    exec_ids = [e.id for e in session.query(Execution).filter(Execution.user_id == user.id).all()]
    if exec_ids:
        session.query(NodeExecution).filter(NodeExecution.execution_id.in_(exec_ids)).delete(synchronize_session=False)
        session.query(Execution).filter(Execution.user_id == user.id).delete(synchronize_session=False)
    workflow_ids = [w.id for w in session.query(Workflow).filter(Workflow.user_id == user.id).all()]
    if workflow_ids:
        session.query(WorkflowVersion).filter(WorkflowVersion.workflow_id.in_(workflow_ids)).delete(synchronize_session=False)
        node_ids = [n.id for n in session.query(WorkflowNode).filter(WorkflowNode.workflow_id.in_(workflow_ids)).all()]
        if node_ids:
            session.query(WorkflowEdge).filter(WorkflowEdge.source_node_id.in_(node_ids)).delete(synchronize_session=False)
            session.query(WorkflowEdge).filter(WorkflowEdge.target_node_id.in_(node_ids)).delete(synchronize_session=False)
            session.query(WorkflowNode).filter(WorkflowNode.workflow_id.in_(workflow_ids)).delete(synchronize_session=False)
        session.query(Workflow).filter(Workflow.user_id == user.id).delete(synchronize_session=False)
    session.query(Credential).filter(Credential.user_id == user.id).delete(synchronize_session=False)
    session.query(User).filter(User.id == user.id).delete(synchronize_session=False)
    session.commit()


def validate_definitions(workflows: List[Dict[str, Any]]) -> None:
    """Assert every definition round-trips through the adapter without coercion."""
    for wf in workflows:
        definition = reactive_definition(wf["nodes"], wf["edges"])
        parsed = react_flow_to_definition(definition)
        original_types = {n["data"]["nodeType"] for n in wf["nodes"]}
        parsed_types = {n.node_type.value for n in parsed.nodes}
        if original_types != parsed_types:
            raise RuntimeError(
                f"Definition mismatch for {wf['name']!r}: "
                f"original={sorted(original_types)} parsed={sorted(parsed_types)}"
            )


def seed(session: Session, data: Dict[str, Any]) -> List[str]:
    logs: List[str] = []

    user = session.query(User).filter(User.email == DEMO_EMAIL).first()
    if user:
        logs.append(f"Demo user {DEMO_EMAIL!r} already exists — wiping previous demo data (idempotent re-seed).")
        wipe_demo_user(session, user)

    user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD), plan="free")
    session.add(user)
    session.flush()

    type_to_id = upsert_catalog(session)

    for cred_name, cred_type, cred_value in data["credentials"]:
        session.add(Credential(
            user_id=user.id,
            name=cred_name,
            credential_type=cred_type,
            encrypted_value=encrypt_value(cred_value),
            encryption_version=1,
        ))

    for wf in data["workflows"]:
        definition = reactive_definition(wf["nodes"], wf["edges"])

        # Oldest → newest version definitions (later versions reuse current graph)
        version_defs = []
        for i, (summary, *node_ids) in enumerate(wf["versions"]):
            node_ids_set = set(node_ids)
            sub_nodes = [n for n in wf["nodes"] if n["id"] in node_ids_set]
            sub_edges = [e for e in wf["edges"] if e["source"] in node_ids_set and e["target"] in node_ids_set]
            version_defs.append(reactive_definition(sub_nodes, sub_edges))

        webhook_key = str(uuid.uuid4()) if wf["webhook"] else None
        workflow = Workflow(
            user_id=user.id,
            name=wf["name"],
            description=wf["description"],
            definition=definition,
            version=len(wf["versions"]),
            is_active=wf["is_active"],
            schedule=wf["schedule"],
            webhook_key=webhook_key,
            webhook_secret=str(uuid.uuid4()) if webhook_key else None,
        )
        session.add(workflow)
        session.flush()

        # Relational nodes + edges (editable structure in the editor)
        rf_id_to_db_id: Dict[str, int] = {}
        for n in wf["nodes"]:
            db_node = WorkflowNode(
                workflow_id=workflow.id,
                node_definition_id=type_to_id[n["data"]["nodeType"]],
                position_x=n["position"]["x"],
                position_y=n["position"]["y"],
                config=n["data"]["config"] or {},
            )
            session.add(db_node)
            session.flush()
            rf_id_to_db_id[n["id"]] = db_node.id

        for e in wf["edges"]:
            session.add(WorkflowEdge(
                workflow_id=workflow.id,
                source_node_id=rf_id_to_db_id[e["source"]],
                target_node_id=rf_id_to_db_id[e["target"]],
                condition=e.get("label"),
            ))

        # Version history (v1 = oldest recorded)
        for i, (summary, *_) in enumerate(wf["versions"]):
            session.add(WorkflowVersion(
                workflow_id=workflow.id,
                version=i + 1,
                definition=version_defs[i],
                change_summary=summary,
                created_by=user.id,
                created_at=days_ago(len(wf["versions"]) - i + 3),
            ))

        # Executions with per-node results
        for ex in wf["executions"]:
            started = days_ago(ex["days"], hour=ex.get("hour", 9), minute=ex.get("minute", 30))
            queued_at = started - timedelta(seconds=2)
            completed = started + timedelta(seconds=2) if ex["status"] == "cancelled" else None
            if ex["status"] in ("completed", "failed") :
                total_dur = sum(run[4] for run in ex["node_runs"])
                completed = started + timedelta(milliseconds=total_dur + 400)

            execution = Execution(
                workflow_id=workflow.id,
                user_id=user.id,
                status=ex["status"],
                trigger=ex["trigger"],
                input_data=ex["input"],
                output_data=ex["output"],
                error_log=ex["error"],
                definition_snapshot=definition,
                idempotency_key=str(uuid.uuid4()),
                retry_count=ex["retry"],
                max_retries=3,
                worker_id=ex["worker"],
                started_at=started,
                queued_at=queued_at,
                completed_at=completed,
            )
            session.add(execution)
            session.flush()

            for rf_node_id, nstatus, noutput, nerror, ndur in ex["node_runs"]:
                node_failed = nstatus == "failed"
                session.add(NodeExecution(
                    execution_id=execution.id,
                    node_id=rf_id_to_db_id[rf_node_id],
                    status=nstatus,
                    input_data=ex["input"] if rf_node_id == "n1" else noutput,
                    output_data=noutput if not node_failed else None,
                    error_log=nerror,
                    duration_ms=ndur,
                    started_at=started + timedelta(milliseconds=ndur * 0.1),
                    completed_at=(started + timedelta(milliseconds=ndur * 0.1 + ndur)) if not node_failed or nerror else None,
                ))

        logs.append(
            f"  • {wf['name']}: {len(wf['nodes'])} nodes, {len(wf['edges'])} edges, "
            f"{len(wf['versions'])} versions, {len(wf['executions'])} executions"
        )

    session.commit()
    return logs


def print_summary(session: Session, logs: List[str], db_url: str) -> None:
    print("\n═══ FLOWALCHEMY DEMO DATA ═══")
    print(f"  Database : {db_url}")
    print("\nSeeded workflows:")
    for line in logs:
        print(line)
    print("\nCounts:")
    print(f"  Users             : {session.query(User).count()}")
    print(f"  Workflows         : {session.query(Workflow).count()}")
    print(f"  Workflow nodes    : {session.query(WorkflowNode).count()}")
    print(f"  Workflow edges    : {session.query(WorkflowEdge).count()}")
    print(f"  Versions          : {session.query(WorkflowVersion).count()}")
    print(f"  Executions        : {session.query(Execution).count()}")
    print(f"  Node executions   : {session.query(NodeExecution).count()}")
    print(f"  Schedules set     : {session.query(Workflow).filter(Workflow.schedule.isnot(None)).count()}")
    print(f"  Webhooks set      : {session.query(Workflow).filter(Workflow.webhook_key.isnot(None)).count()}")
    print(f"  Credentials       : {session.query(Credential).count()}")
    print(f"  Node definitions  : {session.query(NodeDefinition).count()}")
    print("\nDemo login  : email = demo@flowalchemy.ai  password = DemoPass123")
    print("Re-run script to reset the demo data (idempotent).")


def main() -> None:
    print(f"Creating schema on {database.DATABASE_URL} ...")
    database.Base.metadata.create_all(bind=database.engine)

    print("Building dataset ...")
    data = build_full_dataset()
    validate_definitions(data["workflows"])
    print("Definitions validated: all 6 workflows round-trip through the adapter.")

    print("Seeding ...")
    session = database.SessionLocal()
    try:
        logs = seed(session, data)
        print_summary(session, logs, database.DATABASE_URL)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()