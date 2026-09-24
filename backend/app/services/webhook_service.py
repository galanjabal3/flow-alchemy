"""Webhook triggers for external workflow invocation."""

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.workflow import Workflow, Execution
from app.core.queue import enqueue_job
from app.core.job import Job
from app.core.events import publish_event, ExecutionEvent
from app.core.config import settings
from app.core.encryption import encrypt_value, decrypt_value

# Safe headers to store (no auth/sensitive headers)
SAFE_HEADERS = {"content-type", "x-webhook-signature", "x-webhook-timestamp", "user-agent", "x-request-id"}


class WebhookService:
    """Handles webhook triggers for workflows."""

    def generate_webhook_key(self) -> str:
        """Generate a unique webhook key."""
        return f"wh_{uuid.uuid4().hex[:32]}"

    def generate_webhook_secret(self) -> str:
        """Generate a cryptographically secure webhook secret."""
        return secrets.token_urlsafe(32)

    def validate_webhook_secret(self, secret: str, payload: bytes, signature: str) -> bool:
        """Validate HMAC-SHA256 webhook signature."""
        if not secret:
            return False
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def create_webhook(self, db: Session, workflow: Workflow, secret: Optional[str] = None) -> dict:
        """Create a webhook trigger for a workflow."""
        # Generate or use provided secret
        if not secret:
            secret = self.generate_webhook_secret()

        webhook_key = self.generate_webhook_key()

        # Store encrypted secret (not hashed) so we can decrypt for HMAC validation
        workflow.webhook_key = webhook_key
        workflow.webhook_secret = encrypt_value(secret)
        db.commit()

        return {
            "workflow_id": workflow.id,
            "webhook_key": webhook_key,
            "webhook_url": f"/api/webhooks/{webhook_key}/trigger",
            "webhook_secret": secret,  # Return raw secret only at creation time
            "is_active": True,
        }

    def filter_headers(self, headers: dict) -> dict:
        """Filter headers to safe allowlist."""
        return {k: v for k, v in headers.items() if k.lower() in SAFE_HEADERS}

    async def trigger_webhook(
        self,
        db: Session,
        webhook_key: str,
        payload: dict,
        headers: Optional[dict] = None,
    ) -> Optional[str]:
        """Trigger a workflow via webhook."""
        # Find workflow by webhook key
        workflow = db.query(Workflow).filter(Workflow.webhook_key == webhook_key).first()
        if not workflow:
            return None

        if not workflow.is_active:
            return None

        # Check concurrency limits (with lock)
        user_running = (
            db.query(Execution)
            .filter(Execution.user_id == workflow.user_id, Execution.status.in_(["queued", "running"]))
            .with_for_update()
            .count()
        )
        if user_running >= settings.MAX_CONCURRENT_PER_USER:
            return None

        total_running = (
            db.query(Execution)
            .filter(Execution.status.in_(["queued", "running"]))
            .with_for_update()
            .count()
        )
        if total_running >= settings.MAX_CONCURRENT_TOTAL:
            return None

        # Filter headers
        safe_headers = self.filter_headers(headers) if headers else {}

        # Create execution
        idempotency_key = str(uuid.uuid4())
        execution = Execution(
            workflow_id=workflow.id,
            user_id=workflow.user_id,
            status="queued",
            trigger="webhook",
            input_data={
                "payload": payload,
                "headers": safe_headers,
                "triggered_at": datetime.now(timezone.utc).isoformat(),
            },
            idempotency_key=idempotency_key,
            started_at=datetime.now(timezone.utc),
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        # Create job
        job = Job(
            execution_id=str(execution.id),
            workflow_id=workflow.id,
            user_id=workflow.user_id,
            trigger_data={
                "payload": payload,
                "headers": safe_headers,
            },
            idempotency_key=idempotency_key,
            max_retries=settings.MAX_RETRIES,
        )

        # Enqueue
        success = await enqueue_job(job)
        if not success:
            execution.status = "failed"
            execution.error_log = "Failed to enqueue webhook trigger"
            execution.completed_at = datetime.now(timezone.utc)
            db.commit()
            return None

        # Publish event
        await publish_event(ExecutionEvent(
            execution_id=str(execution.id),
            event_type="queued",
        ))

        return str(execution.id)


webhook_service = WebhookService()
