"""Tests for resource limits and SSRF hardening."""

import pytest
from app.core.ssrf_protection import validate_url
from app.core.executors.http_request import HttpRequestExecutor
from app.core.executors.output import OutputExecutor


class TestSSRFProtection:
    """Tests for SSRF protection."""

    def test_validate_url_blocks_localhost(self):
        with pytest.raises(ValueError, match="blocked"):
            validate_url("http://localhost/api")

    def test_validate_url_blocks_127(self):
        with pytest.raises(ValueError, match="blocked"):
            validate_url("http://127.0.0.1/api")

    def test_validate_url_blocks_private_ip(self):
        with pytest.raises(ValueError, match="blocked network"):
            validate_url("http://10.0.0.1/api")

    def test_validate_url_blocks_172_16(self):
        with pytest.raises(ValueError, match="blocked network"):
            validate_url("http://172.16.0.1/api")

    def test_validate_url_blocks_192_168(self):
        with pytest.raises(ValueError, match="blocked network"):
            validate_url("http://192.168.1.1/api")

    def test_validate_url_blocks_metadata(self):
        with pytest.raises(ValueError, match="blocked"):
            validate_url("http://169.254.169.254/metadata")

    def test_validate_url_blocks_non_http(self):
        with pytest.raises(ValueError, match="not allowed"):
            validate_url("ftp://example.com/file")

    def test_validate_url_blocks_empty(self):
        with pytest.raises(ValueError, match="required"):
            validate_url("")

    def test_validate_url_blocks_no_hostname(self):
        with pytest.raises(ValueError, match="no hostname"):
            validate_url("http://")

    def test_validate_url_returns_resolved_ip(self):
        hostname, ip, port = validate_url("http://example.com/api")
        assert hostname == "example.com"
        assert port == 80

    def test_validate_url_returns_correct_port(self):
        hostname, ip, port = validate_url("https://example.com:8443/api")
        assert port == 8443


class TestResourceLimits:
    """Tests for resource limits."""

    def test_http_request_executor_imports_ssrf_protection(self):
        """HttpRequestExecutor should use shared SSRF protection."""
        from app.core.ssrf_protection import validate_url
        with pytest.raises(ValueError, match="blocked"):
            validate_url("http://127.0.0.1/api")

    @pytest.mark.asyncio
    async def test_output_executor_validates_webhook_url(self):
        """OutputExecutor should validate webhook URLs for SSRF."""
        executor = OutputExecutor()
        with pytest.raises(ValueError, match="blocked"):
            await executor._send_webhook({"url": "http://10.0.0.1/webhook"}, {})

    @pytest.mark.asyncio
    async def test_output_executor_validates_slack_url(self):
        """OutputExecutor should validate Slack URLs for SSRF."""
        executor = OutputExecutor()
        with pytest.raises(ValueError, match="blocked"):
            await executor._send_slack({"webhook_url": "http://192.168.1.1/slack"}, "test")
