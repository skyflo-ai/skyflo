from fastapi import APIRouter

from .health import router as health_router
from .agent import router as agent_router
from .conversation import router as conversation_router
from .auth import router as auth_router
from .team import router as team_router
from .integrations import router as integrations_router
from .analytics import router as analytics_router

api_router = APIRouter()

api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(agent_router, prefix="/agent", tags=["agent"])
api_router.include_router(conversation_router, prefix="/conversations", tags=["conversations"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(team_router, prefix="/team", tags=["team"])
api_router.include_router(integrations_router, prefix="/integrations", tags=["integrations"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])


__all__ = ["api_router"]
