import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import close_db_connection, init_db, settings
from .endpoints import api_router
from .middleware import setup_middleware
from .services.checkpointer import close_graph_checkpointer, init_graph_checkpointer
from .services.limiter import close_limiter, init_limiter
from .services.mcp_client import MCPClient

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

MCP_RETRY_ATTEMPTS = 5
MCP_RETRY_DELAY = 3


async def verify_mcp_connection() -> None:
    last_error: Exception | None = None

    for attempt in range(1, MCP_RETRY_ATTEMPTS + 1):
        try:
            client = MCPClient()
            tools = await client.list_tools_raw()
            logger.info(
                "MCP server %s connected successfully. Available tools: %d",
                client.mcp_url,
                len(tools),
            )
            return
        except Exception as e:
            last_error = e
            logger.warning(
                "MCP connection attempt %d/%d failed: %s",
                attempt,
                MCP_RETRY_ATTEMPTS,
                str(e),
            )
            if attempt < MCP_RETRY_ATTEMPTS:
                await asyncio.sleep(MCP_RETRY_DELAY)
    raise RuntimeError(
        f"MCP server unreachable after {MCP_RETRY_ATTEMPTS} attempts. Last error: {last_error}"
    ) from last_error


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} version {settings.APP_VERSION}")
    await verify_mcp_connection()
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
