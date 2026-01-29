import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import close_db_connection, init_db, settings
from .endpoints import api_router
from .middleware import setup_middleware
from .services.checkpointer import close_graph_checkpointer, init_graph_checkpointer
from .services.limiter import close_limiter, init_limiter

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} version {settings.APP_VERSION}")
    await init_db()
    await init_limiter()
    await init_graph_checkpointer()

    yield

    logger.info(f"Shutting down {settings.APP_NAME}")
    await close_db_connection()
    await close_limiter()
    await close_graph_checkpointer()


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    setup_middleware(application)

    application.include_router(api_router, prefix=settings.API_V1_STR)

    return application


app = create_application()
