"""ASGI entry point for Skyflo.ai API service."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .repositories import init_db, close_db_connection
from .web.endpoints import api_router, socketio_app
from .web.middleware import setup_middleware
from .services.rbac import init_enforcer
from .services.limiter import init_limiter, close_limiter

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} version {settings.APP_VERSION}")
    await init_db()
    await init_enforcer()
    await init_limiter()
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")
    await close_db_connection()
    await close_limiter()


def create_application() -> FastAPI:
    """Create the FastAPI application."""
    application = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # Add custom middleware
    setup_middleware(application)

    # Include API routes
    application.include_router(api_router, prefix=settings.API_V1_STR)

    # Mount the Socket.IO app at the root to handle Socket.IO connections
    application.mount("/socket.io", socketio_app)

    return application


# Create and export the FastAPI application
app = create_application()
