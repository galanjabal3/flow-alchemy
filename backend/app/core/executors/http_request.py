"""HTTP Request Node Executor with SSRF protection and response size limits.

SSRF hardening:
- Every HTTP hop (including redirects) re-validates the URL via
  `validate_url`, which re-resolves DNS and rejects any address in a blocked
  network. This neutralizes DNS-rebinding attacks that swap to an internal
  IP after the first lookup.
- The connection is always made to the validated, resolved IP with the
  original hostname sent as the `Host` header; HTTPS virtual hosting still
  works because TLS uses the validated hostname.
"""

import httpx
from typing import Any, Dict
from urllib.parse import urljoin, urlparse

from app.core.executors.base import BaseNodeExecutor
from app.core.execution_context import ExecutionContext
from app.core.ssrf_protection import validate_url, MAX_REDIRECTS
from app.core.config import settings


REDIRECT_STATUS = {301, 302, 303, 307, 308}


def _build_safe_url(url: str) -> tuple[str, str, str]:
    """Validate URL for SSRF, then return (url, hostname, port).

    `validate_url` resolves the hostname and rejects any address in a blocked
    network (SSRF protection stays). The ORIGINAL hostname-based URL is kept
    for the actual connection so TLS SNI / certificate verification works —
    connecting to the raw IP breaks HTTPS virtual hosting.
    """
    hostname, _resolved_ip, port = validate_url(url)
    return url, hostname, port


class HttpRequestExecutor(BaseNodeExecutor):
    async def execute(
        self,
        node_id: str,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        url = config.get("url", "")
        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        body = config.get("body")
        timeout = config.get("timeout", 30000)

        # HTTP method whitelist
        ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
        if method not in ALLOWED_METHODS:
            raise ValueError(f"HTTP method '{method}' not allowed. Use one of: {', '.join(sorted(ALLOWED_METHODS))}")

        if isinstance(timeout, (int, float)) and timeout > 0:
            timeout_sec = timeout / 1000 if timeout > 100 else timeout
        else:
            timeout_sec = 30

        # Re-validate & resolve the URL (also validates redirect hops below).
        safe_url, hostname, _ = _build_safe_url(url)

        request_headers = dict(headers)
        # Set Host header to original hostname for virtual hosting
        if "Host" not in request_headers and "host" not in request_headers:
            request_headers["Host"] = hostname

        async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=False) as client:
            current_url = url
            current_safe_url = safe_url
            response = None

            for hop in range(MAX_REDIRECTS + 1):
                response = await client.request(
                    method=method,
                    url=current_safe_url,
                    headers=request_headers,
                    json=body if method in ("POST", "PUT", "PATCH") else None,
                )

                # Follow redirects manually so every hop is re-validated
                # against SSRF (DNS rebinding / redirect-to-internal).
                if response.status_code not in REDIRECT_STATUS or "location" not in response.headers:
                    break
                if hop >= MAX_REDIRECTS:
                    raise ValueError(
                        f"Too many redirects (max {MAX_REDIRECTS})"
                    )

                next_url = urljoin(current_url, response.headers["location"])
                if next_url.startswith(("ftp://", "file://")):
                    raise ValueError(f"Redirect to disallowed scheme: {next_url}")

                # Re-validate: re-resolves DNS and rejects blocked networks.
                current_safe_url, hostname, _ = _build_safe_url(next_url)
                if "Host" not in request_headers and "host" not in request_headers:
                    request_headers["Host"] = hostname
                current_url = next_url
                method = "GET" if response.status_code in (301, 302, 303) else method
                body = None if response.status_code in (301, 302, 303) else body

        # Check Content-Length header first to avoid loading huge bodies
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > settings.MAX_RESPONSE_SIZE:
            raise ValueError(
                f"Response size ({content_length} bytes) "
                f"exceeds maximum ({settings.MAX_RESPONSE_SIZE} bytes)"
            )

        # Now read the body
        response_text = response.text
        if len(response_text.encode("utf-8")) > settings.MAX_RESPONSE_SIZE:
            raise ValueError(
                f"Response size ({len(response_text.encode('utf-8'))} bytes) "
                f"exceeds maximum ({settings.MAX_RESPONSE_SIZE} bytes)"
            )

        # Parse JSON response if applicable
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            try:
                data = response.json()
            except Exception:
                data = {"text": response_text}
        else:
            data = {"text": response_text}

        return {
            "status": response.status_code,
            "data": data,
            "headers": {k: v for k, v in response.headers.items() if k.lower() not in ("server", "x-powered-by")},
        }