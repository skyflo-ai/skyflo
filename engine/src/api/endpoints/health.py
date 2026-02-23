import logging
from typing import Any, Dict

from fastapi import APIRouter
from tortoise import Tortoise

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", tags=["health"])
async def health_check() -> Dict[str, Any]:
    return {
        "status": "ok",
    }


@router.get("/database", tags=["health"])
async def database_health_check() -> Dict[str, Any]:
    try:
        conn = Tortoise.get_connection("default")

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
