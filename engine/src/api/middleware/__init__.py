"""API middleware package."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .logging_middleware import LoggingMiddleware


def setup_middleware(app: FastAPI) -> None:
    """Set up all middleware for the application."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
    )

    app.add_middleware(LoggingMiddleware)


__all__ = ["setup_middleware"]
