"""
Custom Exception Classes and Error Handlers.

Ensures consistent machine-readable JSON error responses without exposing
internal stack traces or raw database error strings to clients.
"""

from typing import Any, List, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging

logger = logging.getLogger("aiot.exceptions")


class TelemetryValidationException(Exception):
    """Raised when telemetry payload violates physical range sanity boundaries."""

    def __init__(self, message: str, code: str = "PHYSICAL_LIMIT_EXCEEDED", details: Optional[List[Any]] = None):
        self.message = message
        self.code = code
        self.details = details or []
        super().__init__(message)


class ResourceNotFoundException(Exception):
    """Raised when a requested resource (e.g. machine telemetry) is not found."""

    def __init__(self, message: str, code: str = "RESOURCE_NOT_FOUND"):
        self.message = message
        self.code = code
        super().__init__(message)


async def resource_not_found_exception_handler(
    request: Request, exc: ResourceNotFoundException
) -> JSONResponse:
    request.state.validation_status = f"NOT_FOUND:{exc.code}"
    return JSONResponse(
        status_code=404,
        content={
            "status": "error",
            "code": exc.code,
            "message": exc.message,
            "details": [],
        },
    )


async def telemetry_validation_exception_handler(
    request: Request, exc: TelemetryValidationException
) -> JSONResponse:
    request.state.validation_status = f"FAILED:{exc.code}"
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Format Pydantic v2 validation errors cleanly."""
    request.state.validation_status = "FAILED:SCHEMA_VALIDATION"
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(item) for item in err.get("loc", []))
        errors.append({
            "field": loc,
            "type": err.get("type"),
            "message": err.get("msg"),
        })

    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "code": "SCHEMA_VALIDATION_ERROR",
            "message": "Payload does not conform to telemetry schema or contains invalid values.",
            "details": errors,
        },
    )


async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all handler for unexpected server exceptions; hides raw stack traces."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    request.state.validation_status = "ERROR:SERVER_FAULT"
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred while processing the telemetry request.",
            "details": [],
        },
    )
