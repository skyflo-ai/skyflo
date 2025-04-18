"""Retry utility with exponential backoff for handling request timeouts."""

import asyncio
import logging
from functools import wraps
from typing import Callable, TypeVar, Any
from ..config.settings import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retry(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator that implements retry logic with exponential backoff.

    Args:
        func: The function to be retried

    Returns:
        A wrapped function that implements retry logic
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        last_exception = None

        for attempt in range(settings.MAX_RETRY_ATTEMPTS):
            try:
                return await func(*args, **kwargs)
            except asyncio.TimeoutError as e:
                last_exception = e
                if attempt < settings.MAX_RETRY_ATTEMPTS - 1:
                    delay = min(
                        settings.RETRY_BASE_DELAY
                        * (settings.RETRY_EXPONENTIAL_BASE**attempt),
                        settings.RETRY_MAX_DELAY,
                    )
                    logger.warning(
                        f"Request timed out (attempt {attempt + 1}/{settings.MAX_RETRY_ATTEMPTS}). "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Request failed after {settings.MAX_RETRY_ATTEMPTS} attempts. "
                        f"Last error: {str(e)}"
                    )

        raise last_exception

    return wrapper
