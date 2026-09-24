"""Tests for the Redis-backed rate limiter (in-memory fallback path).

These run without touching a live Redis: `_get_redis` is forced to raise, so
every call transparently falls back to the in-memory window — which is
exactly the behavior the API layer depends on in tests/local dev.

Keys are unique per test so no state leaks even if Redis were reachable.
"""

import time as _time

import pytest

from app.core.rate_limiter import RateLimiter


@pytest.fixture(autouse=True)
def _force_memory_mode(monkeypatch):
    """Make every RateLimiter instance fall back to in-memory windows."""

    def _no_redis(self):
        raise ConnectionError("redis disabled in tests")

    monkeypatch.setattr(RateLimiter, "_get_redis", _no_redis)


class TestRateLimiterFallback:
    def test_allows_requests_under_limit(self):
        limiter = RateLimiter()
        assert limiter.is_allowed("k1", limit=3, window=60) is True
        assert limiter.is_allowed("k1", limit=3, window=60) is True

    def test_blocks_after_limit(self):
        limiter = RateLimiter()
        for _ in range(3):
            assert limiter.is_allowed("k2", limit=3, window=60) is True
        assert limiter.is_allowed("k2", limit=3, window=60) is False

    def test_get_retry_after_returns_none_before_limit(self):
        limiter = RateLimiter()
        assert limiter.get_retry_after("k3", window=60) is None

    def test_get_retry_after_positive_after_limit(self):
        limiter = RateLimiter()
        for _ in range(3):
            limiter.is_allowed("k4", limit=3, window=60)
        retry_after = limiter.get_retry_after("k4", window=60)
        assert retry_after is not None
        assert retry_after > 0
        assert retry_after <= 60

    def test_keys_are_isolated(self):
        limiter = RateLimiter()
        for _ in range(3):
            limiter.is_allowed("k5a", limit=3, window=60)
        assert limiter.is_allowed("k5a", limit=3, window=60) is False
        assert limiter.is_allowed("k5b", limit=3, window=60) is True

    def test_window_expiry_clears_state(self):
        limiter = RateLimiter()
        limiter.is_allowed("k6", limit=1, window=1)
        assert limiter.is_allowed("k6", limit=1, window=1) is False
        # Simulate the window having elapsed.
        limiter._requests["k6"] = [_time.time() - 2]
        assert limiter.is_allowed("k6", limit=1, window=1) is True

    def test_reset_clears_state(self):
        limiter = RateLimiter()
        for _ in range(3):
            limiter.is_allowed("k7", limit=3, window=60)
        assert limiter.is_allowed("k7", limit=3, window=60) is False
        limiter.reset()
        assert limiter.is_allowed("k7", limit=3, window=60) is True

    def test_global_instance_api_unchanged(self):
        """The global instance must keep the same public API callers rely on."""
        from app.core.rate_limiter import rate_limiter

        assert hasattr(rate_limiter, "is_allowed")
        assert hasattr(rate_limiter, "get_retry_after")
        assert hasattr(rate_limiter, "_requests")  # backward-compat attribute
        rate_limiter.reset()