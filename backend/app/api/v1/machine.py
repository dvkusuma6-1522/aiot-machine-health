"""
Machine Historical & Latest Telemetry Query API Endpoints.

Provides GET /api/v1/machine/{device_id}/latest and
         GET /api/v1/machine/{device_id}/history
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.schemas.telemetry import (
    TelemetryRecordResponse,
    HistoricalTelemetryResponse,
)
from app.schemas.common import StandardErrorResponse
from app.services.telemetry_service import TelemetryService

router = APIRouter(prefix="/machine", tags=["Machine Telemetry Queries"])


@router.get(
    "/{device_id}/latest",
    response_model=TelemetryRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Machine Telemetry Record",
    description="Fetches the most recently recorded telemetry sample for the specified machine.",
    responses={
        200: {"model": TelemetryRecordResponse, "description": "Latest telemetry record."},
        404: {"model": StandardErrorResponse, "description": "No telemetry found for this machine."},
    },
)
async def get_latest_machine_telemetry(
    device_id: str,
    db: AsyncSession = Depends(get_db),
) -> TelemetryRecordResponse:
    return await TelemetryService.get_latest_telemetry(db, device_id)


@router.get(
    "/{device_id}/history",
    response_model=HistoricalTelemetryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Historical Telemetry Window",
    description=(
        "Retrieves a chronologically ordered sequence of telemetry readings within a specified "
        "lookback window (hours). Supports scalable cursor-based pagination for time-series extraction."
    ),
    responses={
        200: {"model": HistoricalTelemetryResponse, "description": "Historical telemetry sequence."},
        422: {"model": StandardErrorResponse, "description": "Invalid query parameters or cursor."},
    },
)
async def get_historical_machine_telemetry(
    device_id: str,
    hours: float = Query(
        default=1.0,
        gt=0.0,
        le=720.0,
        description="Time window in hours to look back (minimum > 0, maximum 720.0 hours / 30 days).",
        examples=[1.0, 24.0],
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum records to return per page (1 to 1000).",
        examples=[50, 100],
    ),
    cursor: Optional[str] = Query(
        default=None,
        description="Opaque base64 cursor token returned in 'next_cursor' of previous page.",
    ),
    db: AsyncSession = Depends(get_db),
) -> HistoricalTelemetryResponse:
    return await TelemetryService.get_historical_telemetry(
        session=db,
        device_id=device_id,
        hours=hours,
        limit=limit,
        cursor=cursor,
    )
