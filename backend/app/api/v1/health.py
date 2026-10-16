"""
Health Check API Endpoint.

Implements GET /health checking API liveness and database connectivity.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database.session import get_db
from app.schemas.health import HealthResponse
from app.core.config import settings
import logging

logger = logging.getLogger("aiot.health")

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Health & Database Connectivity Check",
    description="Returns service liveness and checks connection to the persistence database.",
)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning(f"Database health check query failed: {exc}")
        db_status = "disconnected"

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        database=db_status,
        environment=settings.ENVIRONMENT,
    )
