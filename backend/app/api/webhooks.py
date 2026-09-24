"""Webhook API endpoints."""

import json
import hmac
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.rate_limiter import rate_limiter
from app.core.encryption import decrypt_value
from app.services.webhook_service import webhook_service
from app.models.workflow import User, Workflow

router = APIRouter()

MAX_WEBHOOK_PAYLOAD_SIZE = 1_048_576  # 1MB


class WebhookCreate(BaseModel):
    secret: Optional[str] = Field(None, min_length=32, max_length=255)


class WebhookResponse(BaseModel):
    workflow_id: int
    webhook_key: str
    webhook_url: str
    is_active: bool


class WebhookCreateResponse(BaseModel):
    workflow_id: int
    webhook_key: str
    webhook_url: str
    webhook_secret: str
    is_active: bool


@router.post("/workflows/{workflow_id}/webhooks", response_model=WebhookCreateResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    workflow_id: int,
    webhook_data: WebhookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a webhook trigger for a workflow."""
    # Rate limit check
    rate_key = f"{current_user.id}:webhook_create"
    if not rate_limiter.is_allowed(rate_key, limit=10, window=60):
        retry_after = rate_limiter.get_retry_after(rate_key, window=60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
        )

    # Verify workflow ownership
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    try:
        result = webhook_service.create_webhook(db, workflow, webhook_data.secret)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/workflows/{workflow_id}/webhooks", response_model=List[WebhookResponse])
def list_webhooks(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List webhooks for a workflow."""
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    if not workflow.webhook_key:
        return []

    return [{
        "workflow_id": workflow_id,
        "webhook_key": workflow.webhook_key,
        "webhook_url": f"/api/webhooks/{workflow.webhook_key}/trigger",
        "is_active": workflow.is_active,
    }]


@router.delete("/webhooks/{webhook_key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a webhook."""
    workflow = db.query(Workflow).filter(Workflow.webhook_key == webhook_key).first()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    if workflow.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    workflow.webhook_key = None
    workflow.webhook_secret = None
    db.commit()

    return None


@router.post("/webhooks/{webhook_key}/trigger")
async def trigger_webhook(
    webhook_key: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Trigger a workflow via webhook (no auth required, uses webhook secret for validation)."""
    # Rate limit check by IP
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"webhook:{webhook_key}:{client_ip}"
    if not rate_limiter.is_allowed(rate_key, limit=60, window=60):
        retry_after = rate_limiter.get_retry_after(rate_key, window=60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
        )

    # Read body with size limit
    body = await request.body()
    if len(body) > MAX_WEBHOOK_PAYLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Payload too large (max 1MB)",
        )

    # Parse payload
    try:
        payload = json.loads(body)
    except Exception:
        payload = {}

    # Get headers
    headers = dict(request.headers)

    # Find workflow and validate signature
    workflow = db.query(Workflow).filter(Workflow.webhook_key == webhook_key).first()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    if not workflow.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    # Validate signature if secret is set
    if workflow.webhook_secret:
        signature = headers.get("x-webhook-signature", "")
        timestamp = headers.get("x-webhook-timestamp")

        if not signature:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature",
            )

        # Decrypt the stored secret
        try:
            raw_secret = decrypt_value(workflow.webhook_secret)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to decrypt webhook secret",
            )

        # Build signed payload
        signed_payload = body
        if timestamp:
            signed_payload = f"{timestamp}.".encode() + body

        # Compute expected HMAC
        expected = hmac.new(
            raw_secret.encode(),
            signed_payload,
            "sha256",
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

    # Trigger workflow
    execution_id = await webhook_service.trigger_webhook(db, webhook_key, payload, headers)

    if not execution_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger workflow",
        )

    return {"execution_id": execution_id, "status": "queued"}
