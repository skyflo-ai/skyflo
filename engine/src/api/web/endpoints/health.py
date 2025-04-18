"""Health check endpoints."""

import logging
from typing import Dict, Any

from fastapi import APIRouter
from tortoise import Tortoise

from api.__about__ import __version__

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", tags=["health"])
async def health_check() -> Dict[str, Any]:
    """Check if the API service is healthy."""
    logger.debug("Health check endpoint called")
    return {
        "status": "ok",
        "version": __version__,
    }


@router.get("/database", tags=["health"])
async def database_health_check() -> Dict[str, Any]:
    """Check if the database connection is healthy."""
    try:
        # Check if Tortoise ORM is initialized
        conn = Tortoise.get_connection("default")

        # Execute a simple query to check database connection
        await conn.execute_query("SELECT 1")

        return {
            "status": "ok",
            "database": "connected",
        }
    except Exception as e:
        logger.exception("Database health check failed")
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e),
        }
