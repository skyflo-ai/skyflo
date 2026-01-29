from fastapi import Depends
from fastapi_limiter.depends import RateLimiter

from .settings import settings


async def _noop_rate_limit() -> None:
    pass


rate_limit_dependency = (
    Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))
    if settings.RATE_LIMITING_ENABLED
    else Depends(_noop_rate_limit)
)
