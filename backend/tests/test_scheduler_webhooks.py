"""Tests for scheduler and webhook features."""

import pytest
from datetime import datetime, timezone


class TestSchedulerService:
    """Test scheduler service."""

    def test_validate_cron_valid(self):
        from app.services.scheduler_service import scheduler_service
        is_valid, msg = scheduler_service.validate_cron("0 9 * * 1")
        assert is_valid is True
        is_valid, msg = scheduler_service.validate_cron("*/5 * * * *")
        assert is_valid is True

    def test_validate_cron_invalid(self):
        from app.services.scheduler_service import scheduler_service
        is_valid, msg = scheduler_service.validate_cron("invalid")
        assert is_valid is False
        is_valid, msg = scheduler_service.validate_cron("")
        assert is_valid is False

    def test_validate_cron_too_frequent(self):
        from app.services.scheduler_service import scheduler_service
        is_valid, msg = scheduler_service.validate_cron("* * * * *")
        assert is_valid is False
        assert "too frequent" in msg.lower()

    def test_get_next_run(self):
        from app.services.scheduler_service import scheduler_service
        next_run = scheduler_service.get_next_run("0 9 * * 1")
        assert isinstance(next_run, datetime)

    def test_get_prev_run(self):
        from app.services.scheduler_service import scheduler_service
        prev_run = scheduler_service.get_prev_run("0 9 * * 1")
        assert isinstance(prev_run, datetime)
        assert prev_run < datetime.now(timezone.utc)


class TestWebhookService:
    """Test webhook service."""

    def test_generate_webhook_key(self):
        from app.services.webhook_service import webhook_service
        key1 = webhook_service.generate_webhook_key()
        key2 = webhook_service.generate_webhook_key()

        assert key1.startswith("wh_")
        assert key1 != key2

    def test_generate_webhook_secret(self):
        from app.services.webhook_service import webhook_service
        secret = webhook_service.generate_webhook_secret()
        assert len(secret) > 20

    def test_validate_webhook_secret_no_secret(self):
        from app.services.webhook_service import webhook_service
        assert webhook_service.validate_webhook_secret("", b"payload", "sig") is False

    def test_validate_webhook_secret_valid(self):
        import hmac
        import hashlib
        from app.services.webhook_service import webhook_service

        secret = "test-secret-key-for-hmac-validation"
        payload = b"test-payload"
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        assert webhook_service.validate_webhook_secret(secret, payload, signature) is True

    def test_validate_webhook_secret_invalid(self):
        from app.services.webhook_service import webhook_service
        assert webhook_service.validate_webhook_secret("secret", b"payload", "wrong-sig") is False

    def test_filter_headers(self):
        from app.services.webhook_service import webhook_service
        headers = {
            "content-type": "application/json",
            "authorization": "Bearer token123",
            "x-webhook-signature": "sig",
            "cookie": "session=abc",
        }
        filtered = webhook_service.filter_headers(headers)
        assert "content-type" in filtered
        assert "x-webhook-signature" in filtered
        assert "authorization" not in filtered
        assert "cookie" not in filtered


class TestSchedulerAPI:
    """Test scheduler API endpoints."""

    def test_list_schedules_empty(self, client, auth_headers):
        response = client.get("/api/schedules", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_set_schedule_invalid_cron(self, client, auth_headers):
        response = client.post(
            "/api/workflows/1/schedule",
            headers=auth_headers,
            json={"schedule": "invalid-cron"},
        )
        assert response.status_code in [400, 404]

    def test_get_schedule_not_found(self, client, auth_headers):
        response = client.get("/api/workflows/999/schedule", headers=auth_headers)
        assert response.status_code == 404


class TestWebhookAPI:
    """Test webhook API endpoints."""

    def test_trigger_webhook_not_found(self, client):
        response = client.post(
            "/api/webhooks/wh_nonexistent/trigger",
            json={"data": "test"},
        )
        assert response.status_code == 404
