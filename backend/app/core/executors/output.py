"""Output Node Executor with SSRF protection."""

import httpx
from datetime import datetime, timezone
from typing import Any, Dict
from urllib.parse import urlparse
from app.core.executors.base import BaseNodeExecutor
from app.core.execution_context import ExecutionContext
from app.core.ssrf_protection import validate_url
from app.core.config import settings


class OutputExecutor(BaseNodeExecutor):
    async def execute(
        self,
        node_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        data = config.get("data", {})
        destination = config.get("destination", "webhook")
        cfg = config.get("config", {})

        if destination == "webhook":
            await self._send_webhook(cfg, data)
        elif destination == "email":
            await self._send_email(cfg, data)
        elif destination == "slack":
            await self._send_slack(cfg, data)

        return {
            "status": "sent",
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _send_webhook(self, config: Dict[str, Any], data: Any) -> None:
        url = config.get("url", "")
        # SSRF validation (resolve + blocked-network check) stays; connect
        # using the original hostname so TLS SNI stays valid.
        validate_url(url)

        headers = {}
        payload = data if isinstance(data, dict) else {"payload": data}

        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            response = await client.post(url, json=payload, headers=headers)
            # Check response size
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > settings.MAX_RESPONSE_SIZE:
                raise ValueError(f"Response size ({content_length} bytes) exceeds maximum ({settings.MAX_RESPONSE_SIZE} bytes)")
            response.raise_for_status()

    async def _send_email(self, config: Dict[str, Any], data: Any) -> None:
        raise NotImplementedError(
            "Email output is not yet implemented. Use webhook or slack destination."
        )

    async def _send_slack(self, config: Dict[str, Any], data: Any) -> None:
        webhook_url = config.get("webhook_url", "")
        # SSRF validation stays; connect via hostname so TLS stays valid.
        validate_url(webhook_url)

        message = config.get("message", str(data))
        headers = {}

        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            response = await client.post(webhook_url, json={"text": message}, headers=headers)
            # Check response size
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > settings.MAX_RESPONSE_SIZE:
                raise ValueError(f"Response size ({content_length} bytes) exceeds maximum ({settings.MAX_RESPONSE_SIZE} bytes)")
            response.raise_for_status()
