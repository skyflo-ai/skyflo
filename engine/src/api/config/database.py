import logging
from typing import Dict, Any

from tortoise import Tortoise

from . import settings

logger = logging.getLogger(__name__)

TORTOISE_ORM_CONFIG = {
    "connections": {"default": str(settings.POSTGRES_DATABASE_URL)},
    "apps": {
        "models": {
            "models": [
                "src.api.models.user",
                "src.api.models.conversation",
                "src.api.models.integration",
                "aerich.models",
            ],
            "default_connection": "default",
        }
    },
    "use_tz": False,
    "timezone": "UTC",
}


async def init_db() -> None:
    try:
        logger.info("Initializing database connection")
        await Tortoise.init(config=TORTOISE_ORM_CONFIG)

        logger.info("Database connection established")
    except Exception as e:
        logger.exception(f"Failed to initialize database: {str(e)}")
        raise


async def generate_schemas() -> None:
    try:
        logger.info("Generating database schemas")
        await Tortoise.generate_schemas()
        logger.info("Database schemas generated")
    except Exception as e:
        logger.exception(f"Failed to generate schemas: {str(e)}")
        raise


async def close_db_connection() -> None:
    try:
        logger.info("Closing database connection")
        await Tortoise.close_connections()
        logger.info("Database connection closed")
    except Exception as e:
        logger.exception(f"Error closing database connection: {str(e)}")
        raise


def get_tortoise_config() -> Dict[str, Any]:
    return TORTOISE_ORM_CONFIG
