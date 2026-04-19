"""Authentication, logging, and CORS middleware"""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.services.datadog_service import get_datadog_tags, send_datadog_metric

logger = logging.getLogger(__name__)


class DatadogAPMMiddleware(BaseHTTPMiddleware):
    """Track HTTP request metrics with Datadog"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start_time

            send_datadog_metric(
                "http.request.duration",
                duration,
                "gauge",
                {
                    "method": request.method,
                    "path": request.url.path,
                    "status": str(response.status_code),
                },
            )
            logger.info(
                f"{request.method} {request.url.path} {response.status_code}",
                extra={
                    "status_code": response.status_code,
                    "duration_ms": duration * 1000,
                    "tags": get_datadog_tags({"method": request.method, "path": request.url.path}),
                },
            )
            return response

        except Exception as exc:
            logger.error(f"Request failed: {str(exc)}", exc_info=True)
            send_datadog_metric("http.request.error", 1, "increment")
            raise


def add_cors_middleware(app) -> None:
    """Attach CORS middleware to the FastAPI application"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
