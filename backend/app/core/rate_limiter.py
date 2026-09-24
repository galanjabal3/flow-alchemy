"""Rate limiter — Redis-backed sliding window with in-memory fallback.

Uses a Redis sorted set per key when Redis is reachable (accurate across
multiple API workers/processes). Falls back to an in-memory window when
Redis is unavailable (e.g. unit tests, local dev without Redis), so the
public API (`is_allowed`, `get_retry_after`) never changes for callers.
"""

import time
import uuid
from collections import defaultdict
from typing import Optional

import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Extra TTL safety so expired keys are cleaned after the window ends.
_WINDOW_SAFETY = 300


class RateLimiter:
    """Sliding-window rate limiter with automatic Redis → memory fallback."""

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._redis_client = None
        self._redis_keys: set[str] = set()
        self._last_fallback_key: Optional[str] = None

    # ── lifecycle ──────────────────────────────────────────────

    def reset(self) -> None:
        """Clear rate-limit state: in-memory windows and only the Redis keys
        this limiter created (never flushes the whole database)."""
        self._requests.clear()
        if self._redis_client is not None:
            for redis_key in list(self._redis_keys):
                try:
                    self._redis_client.delete(redis_key)
                except Exception:
                    pass
        self._redis_keys.clear()

    def _get_redis(self):
        """Lazily build a synchronous Redis client (kept for the sync API)."""
        if self._redis_client is None:
            import redis as sync_redis  # local import: sync client only needed here

            self._redis_client = sync_redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2.0,
                socket_timeout=2.0,
            )
        return self._redis_client

    # ── public API ─────────────────────────────────────────────

    def is_allowed(self, key: str, limit: int, window: int = 60) -> bool:
        """Return True if a request for ``key`` is allowed within ``window`` seconds."""
        try:
            return self._redis_allowed(key, limit, window)
        except Exception as exc:
            self._log_fallback_once(key, exc)
            return self._memory_allowed(key, limit, window)

    def get_retry_after(self, key: str, window: int = 60) -> Optional[int]:
        """Seconds until the next request would be allowed (None if no wait needed)."""
        try:
            return self._redis_retry_after(key, window)
        except Exception as exc:
            self._log_fallback_once(key, exc)
            return self._memory_retry_after(key, window)

    # ── Redis implementation (sliding window via sorted set) ────

    def _redis_allowed(self, key: str, limit: int, window: int) -> bool:
        client = self._get_redis()
        redis_key = f"rl:{key}"
        now_ms = int(time.time() * 1000)
        window_ms = window * 1000
        cutoff_ms = now_ms - window_ms

        client.zremrangebyscore(redis_key, 0, cutoff_ms)
        count = client.zcard(redis_key)
        if count >= limit:
            return False
        client.zadd(redis_key, {f"{now_ms}-{uuid.uuid4().hex}": now_ms})
        client.expire(redis_key, window + _WINDOW_SAFETY)
        self._redis_keys.add(redis_key)
        return True

    def _redis_retry_after(self, key: str, window: int) -> Optional[int]:
        client = self._get_redis()
        redis_key = f"rl:{key}"
        now_ms = int(time.time() * 1000)
        window_ms = window * 1000
        cutoff_ms = now_ms - window_ms

        client.zremrangebyscore(redis_key, 0, cutoff_ms)
        entries = client.zrange(redis_key, 0, 0, withscores=True)
        if not entries:
            return None
        oldest_ms = float(entries[0][1])
        wait_ms = window_ms - (now_ms - oldest_ms)
        if wait_ms <= 0:
            return None
        return max(0, int(wait_ms / 1000))

    # ── In-memory fallback (original sliding-window behavior) ──

    def _memory_allowed(self, key: str, limit: int, window: int) -> bool:
        now = time.time()
        cutoff = now - window
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]
        if len(self._requests[key]) >= limit:
            return False
        self._requests[key].append(now)
        return True

    def _memory_retry_after(self, key: str, window: int) -> Optional[int]:
        if not self._requests[key]:
            return None
        oldest = min(self._requests[key])
        wait_time = window - (time.time() - oldest)
        return max(0, int(wait_time)) if wait_time > 0 else None

    # ── helpers ────────────────────────────────────────────────

    def _log_fallback_once(self, key: str, exc: Exception) -> None:
        """Avoid spamming logs when Redis is down for an extended period."""
        if self._last_fallback_key != key:
            self._last_fallback_key = key
            logger.warning("rate_limiter_redis_unavailable_fallback_to_memory", key=key, error=str(exc))


# Global rate limiter instance
rate_limiter = RateLimiter()