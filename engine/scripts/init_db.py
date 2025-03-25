#!/usr/bin/env python
"""Script to initialize the database and create tables for the first time."""

import asyncio
import os
import sys
import logging

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api.repositories.database import init_db, generate_schemas
from src.api.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Initialize database and generate schemas."""
    try:
        logger.info("Initializing database connection")
        await init_db()

        logger.info("Generating database schemas")
        await generate_schemas()

        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
