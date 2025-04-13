"""Rate limiting dependencies for API endpoints."""

from fastapi import Depends, Request
from fastapi_limiter.depends import RateLimiter

from ...config import settings


def get_client_ip(request: Request) -> str:
    """Get the client IP address from a request."""
    # Check X-Forwarded-For header (for proxy environments)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Get the first IP in the chain (client IP)
        return forwarded.split(",")[0].strip()

    # Fall back to direct client IP
    return request.client.host if request.client else "unknown"


# Default rate limit dependency for API endpoints
rate_limit_dependency = (
    Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))
    if settings.RATE_LIMITING_ENABLED
    else None
)
