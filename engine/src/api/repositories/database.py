"""Database connection and initialization using Tortoise ORM."""

import logging
from typing import List, Dict, Any

from tortoise import Tortoise

from ..config import settings

logger = logging.getLogger(__name__)

# Construct Tortoise ORM config with direct connection string
TORTOISE_ORM_CONFIG = {
    "connections": {"default": str(settings.POSTGRES_DATABASE_URL)},
    "apps": {
        "models": {
            "models": [
                "api.domain.models.user",
                "api.domain.models.conversation",
                "aerich.models",
            ],
            "default_connection": "default",
        }
    },
    "use_tz": False,
    "timezone": "UTC",
}


async def init_db() -> None:
    """Initialize database connection with Tortoise ORM."""
    try:
        logger.info("Initializing database connection")
        logger.info(f"Using database URL: {settings.POSTGRES_DATABASE_URL}")
        await Tortoise.init(config=TORTOISE_ORM_CONFIG)

        logger.info("Database connection established")
    except Exception as e:
        logger.exception(f"Failed to initialize database: {str(e)}")
        raise


async def generate_schemas() -> None:
    """Generate database schemas.

    This is mainly used for testing. In production, Aerich should handle migrations.
    """
    try:
        logger.info("Generating database schemas")
        await Tortoise.generate_schemas()
        logger.info("Database schemas generated")
    except Exception as e:
        logger.exception(f"Failed to generate schemas: {str(e)}")
        raise


async def close_db_connection() -> None:
    """Close database connection."""
    try:
        logger.info("Closing database connection")
        await Tortoise.close_connections()
        logger.info("Database connection closed")
    except Exception as e:
        logger.exception(f"Error closing database connection: {str(e)}")
        raise


def get_tortoise_config() -> Dict[str, Any]:
    """Get Tortoise ORM configuration."""
    return TORTOISE_ORM_CONFIG
