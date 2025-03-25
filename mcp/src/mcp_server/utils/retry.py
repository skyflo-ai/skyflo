"""Retry utility with exponential backoff for handling request timeouts."""

import asyncio
import logging
from functools import wraps
from typing import Callable, TypeVar, Any
from ..config.settings import get_config

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
    config = get_config()

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        last_exception = None

        for attempt in range(config.max_retry_attempts):
            try:
                return await func(*args, **kwargs)
            except asyncio.TimeoutError as e:
                last_exception = e
                if attempt < config.max_retry_attempts - 1:
                    delay = min(
                        config.retry_base_delay
                        * (config.retry_exponential_base**attempt),
                        config.retry_max_delay,
                    )
                    logger.warning(
                        f"Request timed out (attempt {attempt + 1}/{config.max_retry_attempts}). "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Request failed after {config.max_retry_attempts} attempts. "
                        f"Last error: {str(e)}"
                    )

        raise last_exception

    return wrapper
