"""API middleware package."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config.settings import settings
from .logging_middleware import LoggingMiddleware

logger = logging.getLogger(__name__)


def setup_middleware(app: FastAPI) -> None:
    """Set up all middleware for the application."""

    cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
    if not cors_origins:
        logger.warning(
            "CORS_ORIGINS is empty, all cross-origin requests will be blocked. "
            "Set CORS_ORIGINS to a comma-separated list of allowed origins."
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
    )

    app.add_middleware(LoggingMiddleware)


__all__ = ["setup_middleware"]
