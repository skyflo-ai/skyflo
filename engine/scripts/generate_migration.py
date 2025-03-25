#!/usr/bin/env python
"""Script to generate migration files using aerich after database initialization."""

import asyncio
import os
import sys
import logging
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_aerich_command(command, *args):
    """Run aerich command with arguments."""
    cmd = ["aerich", command]
    cmd.extend(args)

    try:
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return False


def main():
    """Generate migrations using aerich."""
    # Initialize aerich if not already initialized
    if not os.path.exists("migrations"):
        logger.info("Initializing aerich")
        if not run_aerich_command(
            "init", "-t", "src.api.repositories.database.TORTOISE_ORM_CONFIG"
        ):
            logger.error("Failed to initialize aerich")
            sys.exit(1)

    # Create initial migration if none exists
    migration_files = os.listdir("migrations/models") if os.path.exists("migrations/models") else []
    if not migration_files:
        logger.info("Creating initial migration")
        if not run_aerich_command("init-db"):
            logger.error("Failed to create initial migration")
            sys.exit(1)
        logger.info("Initial migration created successfully")
    else:
        # Generate migration for schema changes
        logger.info("Generating migration for schema changes")
        migration_name = input("Enter migration name (default: update): ").strip() or "update"
        if not run_aerich_command("migrate", "--name", migration_name):
            logger.error("Failed to generate migration")
            sys.exit(1)

        # Apply the migration
        logger.info("Applying migration")
        if not run_aerich_command("upgrade"):
            logger.error("Failed to apply migration")
            sys.exit(1)

        logger.info("Migration applied successfully")


if __name__ == "__main__":
    main()
