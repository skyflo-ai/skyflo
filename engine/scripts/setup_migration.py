#!/usr/bin/env python
"""Script to set up initial database migration."""

import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api.repositories.database import init_db, generate_schemas


async def main():
    """Initialize database and generate schemas."""
    # Initialize database connection
    await init_db()

    # Generate schemas
    await generate_schemas()

    print("Database migration setup completed.")


if __name__ == "__main__":
    asyncio.run(main())
