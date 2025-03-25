"""Configuration settings for Skyflo.ai MCP Server."""

from dataclasses import dataclass
from decouple import config


@dataclass
class EngineConfig:
    """MCP Server configuration settings."""

    # Retry Configuration
    max_retry_attempts: int = 3
    retry_base_delay: float = 60  # Base delay in seconds
    retry_max_delay: float = 60 * 5  # Maximum delay in seconds
    retry_exponential_base: float = 2.0  # Base for exponential backoff


def get_config() -> EngineConfig:
    """Get engine configuration from environment variables."""
    return EngineConfig(
        max_retry_attempts=config("MAX_RETRY_ATTEMPTS", default=3, cast=int),
        retry_base_delay=config("RETRY_BASE_DELAY", default=1.0, cast=float),
        retry_max_delay=config("RETRY_MAX_DELAY", default=10.0, cast=float),
        retry_exponential_base=config(
            "RETRY_EXPONENTIAL_BASE", default=2.0, cast=float
        ),
    )
