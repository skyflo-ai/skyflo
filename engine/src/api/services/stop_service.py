import logging
from typing import Optional

import redis.asyncio as redis

from ..config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


async def _get_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    return _redis_client


def _stop_key(run_id: str) -> str:
    return f"agent:stop:{run_id}"


async def request_stop(run_id: str, ttl_seconds: int = 600) -> None:
    try:
        client = await _get_client()
        await client.set(_stop_key(run_id), "1", ex=ttl_seconds)
    except Exception as e:
        logger.error(f"Failed to set stop flag for {run_id}: {e}")


async def clear_stop(run_id: str) -> None:
    try:
        client = await _get_client()
        await client.delete(_stop_key(run_id))
    except Exception as e:
        logger.error(f"Failed to clear stop flag for {run_id}: {e}")


async def should_stop(run_id: Optional[str]) -> bool:
    if not run_id:
        return False
    try:
        client = await _get_client()
        value = await client.get(_stop_key(run_id))
        return value == "1"
    except Exception as e:
        logger.error(f"Failed to read stop flag for {run_id}: {e}")
        return False
