"""Logging middleware for request/response tracking."""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log request and response details."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request/response and log details."""
        request_id = request.headers.get("X-Request-ID", "unknown")
        start_time = time.time()

        # Log the incoming request
        logger.debug(f"Request started [id={request_id}] {request.method} {request.url.path}")

        # Process the request
        try:
            response = await call_next(request)

            # Calculate request processing time
            process_time = time.time() - start_time

            # Log the response
            logger.debug(
                f"Request completed [id={request_id}] {request.method} {request.url.path} "
                f"status={response.status_code} duration={process_time:.4f}s"
            )

            # Add processing time header
            response.headers["X-Process-Time"] = str(process_time)
            return response

        except Exception as e:
            # Log any exceptions
            logger.exception(
                f"Request failed [id={request_id}] {request.method} {request.url.path}: {str(e)}"
            )
            raise
