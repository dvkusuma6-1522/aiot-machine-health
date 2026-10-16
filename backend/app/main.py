"""
FastAPI Ingestion Backend Application Entrypoint.

AIoT-Based Machine Health Monitoring and Predictive Maintenance System.
Provides high-throughput non-blocking ingestion of sensor telemetry from edge nodes.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import StructuredLoggingMiddleware
from app.core.exceptions import (
    TelemetryValidationException,
    ResourceNotFoundException,
    telemetry_validation_exception_handler,
    resource_not_found_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from app.database.init_db import init_db
from app.database.session import get_db
from app.api.router import api_router
from app.schemas.health import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context: initialize database on startup."""
    await init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Production-grade Ingestion API for continuous condition monitoring "
        "and predictive maintenance of rotating machinery. Ingests high-frequency "
        "accelerometer vibration, thermal, current, voltage, and RPM telemetry."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ------------------------------------------------------------------------------
# MIDDLEWARE SETUP
# ------------------------------------------------------------------------------
# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Structured Request Logging Middleware
app.add_middleware(StructuredLoggingMiddleware)

# ------------------------------------------------------------------------------
# EXCEPTION HANDLERS
# ------------------------------------------------------------------------------
app.add_exception_handler(TelemetryValidationException, telemetry_validation_exception_handler)
app.add_exception_handler(ResourceNotFoundException, resource_not_found_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# ------------------------------------------------------------------------------
# ROUTER REGISTRATION
# ------------------------------------------------------------------------------
# Mount versioned API routes under /api/v1
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Root-level health check endpoint (as specified in GET /health)
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Root Service Health Status",
)
async def root_health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        database=db_status,
        environment=settings.ENVIRONMENT,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
