import logging
from typing import Optional, Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

import psycopg
from psycopg.rows import dict_row

from ..config import settings


logger = logging.getLogger(__name__)

_checkpointer: Optional[Any] = None


async def init_graph_checkpointer() -> None:
    global _checkpointer

    if _checkpointer is not None:
        return

    if not settings.ENABLE_POSTGRES_CHECKPOINTER:
        _checkpointer = MemorySaver()
        return

    try:
        conn = await psycopg.AsyncConnection.connect(
            settings.CHECKPOINTER_DATABASE_URL,
            autocommit=True,
            row_factory=dict_row,
        )

        cp = AsyncPostgresSaver(conn)
        await cp.setup()
        _checkpointer = cp

    except Exception as e:
        logger.warning(
            f"Failed to initialize Postgres checkpointer: {e}. Falling back to in-memory."
        )
        _checkpointer = MemorySaver()


async def close_graph_checkpointer() -> None:
    global _checkpointer

    try:
        if _checkpointer is None:
            return

        if hasattr(_checkpointer, "aclose"):
            await _checkpointer.aclose()
        elif hasattr(_checkpointer, "conn") and hasattr(_checkpointer.conn, "aclose"):
            await _checkpointer.conn.aclose()
    finally:
        _checkpointer = None


def get_checkpointer():
    global _checkpointer
    return _checkpointer or MemorySaver()
