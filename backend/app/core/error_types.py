"""Error types and classification for retry policy."""

from enum import Enum
from typing import Optional


class ErrorCategory(str, Enum):
    """Categories of errors for retry classification."""
    TRANSIENT = "transient"          # network timeout, connection error, DNS failure
    RATE_LIMITED = "rate_limited"    # HTTP 429
    SERVER_ERROR = "server_error"    # HTTP 5xx
    CLIENT_ERROR = "client_error"    # HTTP 4xx (non-429)
    AUTH_ERROR = "auth_error"        # HTTP 401/403
    VALIDATION = "validation"        # config/graph validation error
    TIMEOUT = "timeout"              # node/workflow timeout
    CANCELLED = "cancelled"          # execution cancelled
    UNKNOWN = "unknown"              # unclassified


def classify_http_status(status_code: int) -> ErrorCategory:
    """Classify an HTTP status code into an error category."""
    if status_code == 429:
        return ErrorCategory.RATE_LIMITED
    if status_code in (401, 403):
        return ErrorCategory.AUTH_ERROR
    if 400 <= status_code < 500:
        return ErrorCategory.CLIENT_ERROR
    if 500 <= status_code < 600:
        return ErrorCategory.SERVER_ERROR
    return ErrorCategory.UNKNOWN


def classify_error(error: Exception) -> ErrorCategory:
    """Classify an exception into an error category for retry decisions."""
    error_type = type(error).__name__
    error_msg = str(error).lower()

    # Timeout errors
    if error_type in ("TimeoutError", "NodeTimeoutError", "WorkflowTimeoutError"):
        return ErrorCategory.TIMEOUT
    if "timeout" in error_msg:
        return ErrorCategory.TIMEOUT

    # Cancelled
    if error_type == "WorkflowCancelledError" or "cancelled" in error_msg:
        return ErrorCategory.CANCELLED

    # Network / connection errors (transient)
    if error_type in ("ConnectionError", "ConnectionRefusedError", "ConnectTimeout"):
        return ErrorCategory.TRANSIENT
    if any(x in error_msg for x in ("connection", "network", "dns", "resolve", "socket")):
        return ErrorCategory.TRANSIENT

    # HTTP response errors — check for status_code attribute
    status_code = getattr(error, "status_code", None)
    if status_code is not None:
        return classify_http_status(status_code)

    # Check error message for HTTP status patterns
    import re
    http_match = re.search(r"status[_ ]?(?:code)?[_ ]?(\d{3})", error_msg)
    if http_match:
        return classify_http_status(int(http_match.group(1)))

    # Validation errors (not retryable)
    if error_type in ("GraphValidationError", "ValueError", "ValidationError"):
        return ErrorCategory.VALIDATION
    if "validation" in error_msg or "invalid" in error_msg:
        return ErrorCategory.VALIDATION

    return ErrorCategory.UNKNOWN


# Default retryable categories
DEFAULT_RETRYABLE_CATEGORIES = {
    ErrorCategory.TRANSIENT,
    ErrorCategory.RATE_LIMITED,
    ErrorCategory.SERVER_ERROR,
    ErrorCategory.TIMEOUT,
}


def is_retryable(error: Exception, retryable_categories: Optional[set] = None) -> bool:
    """Check if an error is retryable based on its category."""
    if retryable_categories is None:
        retryable_categories = DEFAULT_RETRYABLE_CATEGORIES
    category = classify_error(error)
    return category in retryable_categories
