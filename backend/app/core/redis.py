"""Redis connection pool and client."""

import redis.asyncio as aioredis
import structlog
from urllib.parse import urlparse
from app.core.config import settings

logger = structlog.get_logger()

# Global Redis connection pool
_redis_pool: aioredis.Redis | None = None
_redis_loop = None


def _safe_redis_url(url: str) -> str:
    """Redact credentials from Redis URL for logging."""
    try:
        parsed = urlparse(url)
        if parsed.password:
            return url.replace(f":{parsed.password}@", ":***@")
        return url
    except Exception:
        return "redis://***"


async def get_redis() -> aioredis.Redis:
    """Get Redis client from connection pool."""
    global _redis_pool, _redis_loop
    import asyncio
    current_loop = asyncio.get_event_loop()

    # If the event loop changed, close old connection and create new one
    if _redis_pool is not None and _redis_loop != id(current_loop):
        try:
            await _redis_pool.close()
        except Exception:
            pass
        _redis_pool = None

    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        _redis_loop = id(current_loop)
        logger.info("redis_connected", url=_safe_redis_url(settings.REDIS_URL))
    return _redis_pool


async def close_redis():
    """Close Redis connection pool."""
    global _redis_pool, _redis_loop
    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None
        _redis_loop = None
        logger.info("redis_disconnected")


async def redis_ping() -> bool:
    """Check if Redis is reachable."""
    try:
        client = await get_redis()
        return await client.ping()
    except Exception as e:
        logger.error("redis_ping_failed", error=str(e))
        return False
