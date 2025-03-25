"""Rate limiting service using Redis."""

import logging
from typing import Optional

import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter

from ..config import settings

logger = logging.getLogger(__name__)

# Redis client instance
_redis_client: Optional[redis.Redis] = None


async def init_limiter() -> None:
    """Initialize the rate limiter with Redis."""
    global _redis_client

    if not settings.RATE_LIMITING_ENABLED:
        logger.info("Rate limiting is disabled")
        return

    try:
        # Create Redis client
        _redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

        # Test connection
        await _redis_client.ping()

        # Initialize FastAPI limiter
        await FastAPILimiter.init(_redis_client)

        logger.info(f"Rate limiter initialized with Redis at {settings.REDIS_URL}")
    except Exception as e:
        logger.error(f"Failed to initialize rate limiter: {str(e)}")
        logger.warning("Rate limiting will be disabled")


async def close_limiter() -> None:
    """Close the Redis connection for the rate limiter."""
    global _redis_client

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("Rate limiter connection closed")


async def get_redis_client() -> Optional[redis.Redis]:
    """Get the Redis client instance."""
    global _redis_client

    if _redis_client is None and settings.RATE_LIMITING_ENABLED:
        await init_limiter()

    return _redis_client
