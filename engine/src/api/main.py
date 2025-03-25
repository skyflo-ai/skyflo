"""Main entry point for Skyflo.ai API service."""

import logging
import typer
import uvicorn
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .repositories import init_db, close_db_connection, generate_schemas
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

app = typer.Typer()


def create_application() -> FastAPI:
    """Create the FastAPI application."""
    application = FastAPI(
        title=settings.APP_NAME,
        description="Skyflo.ai API Service - Middleware for Cloud Native AI Agent",
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
    )

    # Configure CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware
    setup_middleware(application)

    # Include API routes
    application.include_router(api_router, prefix=settings.API_V1_STR)

    # Mount the Socket.IO app at the root to handle Socket.IO connections
    application.mount("/socket.io", socketio_app)

    # Event handlers
    @application.on_event("startup")
    async def startup_event():
        """Run on application startup."""
        logger.info(f"Starting {settings.APP_NAME} version {settings.APP_VERSION}")
        await init_db()
        await init_enforcer()
        await init_limiter()

    @application.on_event("shutdown")
    async def shutdown_event():
        """Run on application shutdown."""
        logger.info(f"Shutting down {settings.APP_NAME}")
        await close_db_connection()
        await close_limiter()

    return application


# Create the FastAPI application
fastapi_app = create_application()


@app.command()
def serve(
    host: str = settings.HOST,
    port: int = settings.PORT,
    reload: bool = False,
):
    """Serve the API application with Uvicorn."""
    logger.info(f"Starting Skyflo.ai API on {host}:{port}")

    # Check if the current event loop is running
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            logger.warning("Event loop is already running, creating a new one")
            asyncio.set_event_loop(asyncio.new_event_loop())
    except RuntimeError:
        logger.info("No running event loop, creating a new one")
        asyncio.set_event_loop(asyncio.new_event_loop())

    # Start Uvicorn server
    uvicorn.run(
        "api.main:fastapi_app",
        host=host,
        port=port,
        reload=reload,
        log_level=settings.LOG_LEVEL.lower(),
    )


@app.command()
def init_database():
    """Initialize the database and create tables."""

    async def _init_db():
        await init_db()
        await generate_schemas()
        logger.info("Database initialized successfully")

    asyncio.run(_init_db())


def run():
    """CLI entry point."""
    app()


if __name__ == "__main__":
    run()
