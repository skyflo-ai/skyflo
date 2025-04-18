"""API endpoints package."""

from fastapi import APIRouter

from .health import router as health_router
from .chat import router as chat_router
from .auth import router as auth_router
from .team import router as team_router
from .ws import router as ws_router, sio_app

# Create main API router
api_router = APIRouter()

# Include all routers
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(team_router, prefix="/team", tags=["team"])
api_router.include_router(ws_router, prefix="/ws", tags=["websocket"])

# Export socketio app
socketio_app = sio_app

__all__ = ["api_router", "socketio_app"]
