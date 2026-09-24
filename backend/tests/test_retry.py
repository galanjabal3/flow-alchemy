"""Tests for retry policy and error classification."""

import pytest
from app.core.error_types import (
    ErrorCategory,
    classify_error,
    classify_http_status,
    is_retryable,
    DEFAULT_RETRYABLE_CATEGORIES,
)


class TestErrorClassification:
    """Tests for error classification."""

    def test_timeout_error(self):
        error = TimeoutError("Connection timed out")
        assert classify_error(error) == ErrorCategory.TIMEOUT

    def test_connection_error(self):
        error = ConnectionError("Connection refused")
        assert classify_error(error) == ErrorCategory.TRANSIENT

    def test_connection_refused_error(self):
        error = ConnectionRefusedError("Connection refused")
        assert classify_error(error) == ErrorCategory.TRANSIENT

    def test_dns_error_in_message(self):
        error = Exception("Cannot resolve hostname example.com")
        assert classify_error(error) == ErrorCategory.TRANSIENT

    def test_network_error_in_message(self):
        error = Exception("Network unreachable")
        assert classify_error(error) == ErrorCategory.TRANSIENT

    def test_validation_error(self):
        error = ValueError("Invalid configuration")
        assert classify_error(error) == ErrorCategory.VALIDATION

    def test_graph_validation_error(self):
        from app.core.graph_validator import GraphValidationError
        error = GraphValidationError(["Cycle detected"])
        assert classify_error(error) == ErrorCategory.VALIDATION

    def test_cancelled_error(self):
        from app.core.workflow_engine import WorkflowCancelledError
        error = WorkflowCancelledError("Execution cancelled")
        assert classify_error(error) == ErrorCategory.CANCELLED

    def test_cancelled_in_message(self):
        error = Exception("Operation was cancelled")
        assert classify_error(error) == ErrorCategory.CANCELLED

    def test_unknown_error(self):
        error = RuntimeError("Something unexpected")
        assert classify_error(error) == ErrorCategory.UNKNOWN


class TestHttpStatusClassification:
    """Tests for HTTP status code classification."""

    def test_rate_limited(self):
        assert classify_http_status(429) == ErrorCategory.RATE_LIMITED

    def test_unauthorized(self):
        assert classify_http_status(401) == ErrorCategory.AUTH_ERROR

    def test_forbidden(self):
        assert classify_http_status(403) == ErrorCategory.AUTH_ERROR

    def test_bad_request(self):
        assert classify_http_status(400) == ErrorCategory.CLIENT_ERROR

    def test_not_found(self):
        assert classify_http_status(404) == ErrorCategory.CLIENT_ERROR

    def test_internal_server_error(self):
        assert classify_http_status(500) == ErrorCategory.SERVER_ERROR

    def test_bad_gateway(self):
        assert classify_http_status(502) == ErrorCategory.SERVER_ERROR

    def test_service_unavailable(self):
        assert classify_http_status(503) == ErrorCategory.SERVER_ERROR

    def test_ok(self):
        assert classify_http_status(200) == ErrorCategory.UNKNOWN


class TestRetryable:
    """Tests for is_retryable function."""

    def test_transient_is_retryable(self):
        error = ConnectionError("Connection refused")
        assert is_retryable(error) is True

    def test_rate_limited_is_retryable(self):
        error = Exception("Rate limited")
        # Manually set status_code for testing
        error.status_code = 429
        assert is_retryable(error) is True

    def test_server_error_is_retryable(self):
        error = Exception("Server error")
        error.status_code = 500
        assert is_retryable(error) is True

    def test_timeout_is_retryable(self):
        error = TimeoutError("Timed out")
        assert is_retryable(error) is True

    def test_client_error_not_retryable(self):
        error = Exception("Bad request")
        error.status_code = 400
        assert is_retryable(error) is False

    def test_auth_error_not_retryable(self):
        error = Exception("Unauthorized")
        error.status_code = 401
        assert is_retryable(error) is False

    def test_validation_not_retryable(self):
        error = ValueError("Invalid config")
        assert is_retryable(error) is False

    def test_cancelled_not_retryable(self):
        from app.core.workflow_engine import WorkflowCancelledError
        error = WorkflowCancelledError("Cancelled")
        assert is_retryable(error) is False

    def test_custom_retryable_categories(self):
        error = TimeoutError("Timed out")
        # Empty set = nothing retryable
        assert is_retryable(error, set()) is False
        # Only timeout
        assert is_retryable(error, {ErrorCategory.TIMEOUT}) is True
