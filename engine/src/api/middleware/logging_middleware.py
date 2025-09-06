import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", "unknown")
        start_time = time.time()

        logger.debug(f"Request started [id={request_id}] {request.method} {request.url.path}")

        try:
            response = await call_next(request)

            process_time = time.time() - start_time

            logger.debug(
                f"Request completed [id={request_id}] {request.method} {request.url.path} "
                f"status={response.status_code} duration={process_time:.4f}s"
            )

            response.headers["X-Process-Time"] = str(process_time)
            return response

        except Exception as e:
            logger.exception(
                f"Request failed [id={request_id}] {request.method} {request.url.path}: {str(e)}"
            )
            raise
