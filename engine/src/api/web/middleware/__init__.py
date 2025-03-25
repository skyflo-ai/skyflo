"""API middleware package."""

from fastapi import FastAPI
from .logging_middleware import LoggingMiddleware


def setup_middleware(app: FastAPI) -> None:
    """Set up all middleware for the application."""
    # Add logging middleware
    app.add_middleware(LoggingMiddleware)

    # Note: Rate limiting is now handled directly by FastAPI-Limiter
    # via dependency injection rather than middleware
    # See services/limiter.py for configuration


__all__ = ["setup_middleware"]
