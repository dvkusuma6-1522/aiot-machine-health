"""
Structured Logging Configuration.

Provides JSON-formatted and human-readable structured logs for telemetry ingestion,
recording processing duration, device identifiers, and validation status without
leaking sensitive system secrets or credentials.
"""

import sys
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("aiot.telemetry")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that captures request duration and structured metadata.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        endpoint = request.url.path
        method = request.method

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            device_id = getattr(request.state, "device_id", "N/A")
            logger.error(
                f"{method} {endpoint} -> status=500 device={device_id} "
                f"validation=ERROR:SERVER_FAULT latency={duration_ms:.2f}ms: {exc}"
            )
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred while processing the telemetry request.",
                    "details": [],
                },
            )

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Extract device_id if attached to request state by endpoints
        device_id = getattr(request.state, "device_id", "N/A")
        validation_status = getattr(request.state, "validation_status", "N/A")

        log_level = logging.INFO if response.status_code < 400 else logging.WARNING
        logger.log(
            log_level,
            f"{method} {endpoint} -> status={response.status_code} "
            f"device={device_id} validation={validation_status} "
            f"latency={duration_ms:.2f}ms",
        )
        return response
