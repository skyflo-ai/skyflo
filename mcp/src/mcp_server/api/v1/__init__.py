"""V1 API router for Skyflo.ai MCP Server."""

from fastapi import APIRouter
from .tools import router as tools_router
from .health import router as health_router

router = APIRouter()
router.include_router(tools_router, prefix="/tools", tags=["tools"])
router.include_router(health_router, prefix="/health", tags=["health"])
