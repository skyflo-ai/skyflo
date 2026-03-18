import asyncio
import logging
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from tortoise import Tortoise

from ..services.mcp_client import MCPClient

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


@router.get("/mcp", tags=["health"])
async def mcp_health_check() -> Dict[str, Any]:
    try:
        async with MCPClient() as client:
            tools = await asyncio.wait_for(client.list_tools_raw(), timeout=5)

        return {
            "status":"ok",
            "mcp":"connected",
            "tool_count": len(tools),
        }
    
    except Exception as e:
        logger.exception("MCP health check failed")
        return JSONResponse(
            status_code=503,
            content={
                "status":"degraded",
                "mcp":"disconnected",
                "error": str(e),
            },
        )