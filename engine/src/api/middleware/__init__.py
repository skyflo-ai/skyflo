"""API middleware package."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..config.settings import get_settings
from .logging_middleware import LoggingMiddleware


def setup_middleware(app: FastAPI) -> None:
    """Set up all middleware for the application."""
    settings = get_settings()

    cors_origins = [
        stripped
        for origin in settings.CORS_ORIGINS.split(",")
        if (stripped := origin.strip())
    ]

    if not cors_origins:
        raise ValueError(
            "CORS_ORIGINS resolved to an empty list. "
            "Set at least one allowed origin."
        )

    if "*" in cors_origins:
        raise ValueError(
            "CORS_ORIGINS cannot be set to '*' when allow_credentials=True. "
            "Please specify explicit origins instead."
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "User-Agent",
            "X-Requested-With",
            "Access-Control-Request-Method",
            "Access-Control-Request-Headers",
        ],
    )

    app.add_middleware(LoggingMiddleware)


__all__ = ["setup_middleware"]