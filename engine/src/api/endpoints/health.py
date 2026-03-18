import asyncio
import logging
from typing import Any, Dict
from fastapi import Response
from fastapi import APIRouter
from fastapi import HTTPException
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
async def mcp_health_check() -> Response:
    try:
        async def _check():
            async with MCPClient() as client:
                 return await client.list_tools_raw()
        
        tools = await asyncio.wait_for(_check(), timeout=5)

        return {
            "status":"ok",
            "mcp":"connected",
            "tool_count": len(tools),
        }
    
    except Exception as e:
        logger.exception("MCP health check failed")
        raise HTTPException(
            status_code=503,
            detail={
                "status":"degraded",
                "mcp":"disconnected",
                "error": str(e),
            },
        )