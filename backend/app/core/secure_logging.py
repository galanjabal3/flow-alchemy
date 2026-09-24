"""Secure logging utilities — redact sensitive data from logs."""

import re
from typing import Any


# Patterns to redact
_CRED_PATTERN = re.compile(r"\{\{cred:\d+\}\}")
_API_KEY_PATTERN = re.compile(r"(?i)(api[_-]?key|apikey)[=:]\s*[\"']?([A-Za-z0-9_\-]{20,})[\"']?")
_BEARER_PATTERN = re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}")
_PASSWORD_PATTERN = re.compile(r"(?i)(password|passwd|pwd)[=:]\s*[\"']?([^\s\"',}{]+)[\"']?")


def redact_sensitive(value: str) -> str:
    """Redact sensitive patterns in a string."""
    value = _CRED_PATTERN.sub("{{cred:***}}", value)
    value = _API_KEY_PATTERN.sub(r"\1=***REDACTED***", value)
    value = _BEARER_PATTERN.sub("Bearer ***REDACTED***", value)
    value = _PASSWORD_PATTERN.sub(r"\1=***REDACTED***", value)
    return value


def redact_processor(logger: Any, method_name: str, event_dict: dict) -> dict:
    """Structlog processor that redacts sensitive data from log events."""
    for key, value in event_dict.items():
        if isinstance(value, str):
            event_dict[key] = redact_sensitive(value)
    return event_dict
