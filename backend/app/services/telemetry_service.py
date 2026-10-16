"""
Telemetry Data Ingestion and Query Service.

Handles persistence, latest machine state lookups, and indexed historical
time-window queries with cursor-based pagination.
"""

import base64
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, and_, or_
from app.models.telemetry import SensorReading
from app.schemas.telemetry import (
    TelemetryPayload,
    TelemetryResponse,
    TelemetryRecordResponse,
    HistoricalTelemetryResponse,
)
from app.core.exceptions import (
    ResourceNotFoundException,
    TelemetryValidationException,
)
import logging

logger = logging.getLogger("aiot.telemetry_service")


def encode_cursor(dt: datetime, record_id: int) -> str:
    """Encode timestamp and record ID into an opaque URL-safe base64 string."""
    raw = f"{dt.isoformat()}|{record_id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")


def decode_cursor(cursor_str: str) -> Tuple[datetime, int]:
    """Decode an opaque URL-safe cursor string into (datetime, record_id)."""
    try:
        raw = base64.urlsafe_b64decode(cursor_str.encode("utf-8")).decode("utf-8")
        parts = raw.split("|")
        if len(parts) != 2:
            raise ValueError("Malformed cursor parts")
        dt = datetime.fromisoformat(parts[0])
        rec_id = int(parts[1])
        return dt, rec_id
    except Exception as exc:
        raise TelemetryValidationException(
            message=f"Invalid pagination cursor: '{cursor_str}'. Cursor must be a valid token from a prior response.",
            code="INVALID_CURSOR",
        ) from exc


class TelemetryService:
    """Service layer managing sensor reading persistence and queries."""

    @staticmethod
    async def save_telemetry(session: AsyncSession, payload: TelemetryPayload) -> TelemetryResponse:
        """
        Persist a validated telemetry payload into the sensor_readings table.
        """
        try:
            db_record = SensorReading(
                device_id=payload.device_id,
                timestamp=payload.timestamp,
                is_mock=bool(payload.is_mock),
                temperature=payload.temperature,
                accel_x=payload.accel_x,
                accel_y=payload.accel_y,
                accel_z=payload.accel_z,
                gyro_x=payload.gyro_x,
                gyro_y=payload.gyro_y,
                gyro_z=payload.gyro_z,
                current=payload.current,
                voltage=payload.voltage,
                power=payload.power,
                rpm=payload.rpm,
            )

            session.add(db_record)
            await session.commit()
            await session.refresh(db_record)

            received_iso = datetime.now(timezone.utc).isoformat()
            return TelemetryResponse(
                status="accepted",
                device_id=db_record.device_id,
                received_at=received_iso,
                telemetry_id=db_record.id,
            )

        except SQLAlchemyError as exc:
            await session.rollback()
            logger.error(f"Database error while saving telemetry for device '{payload.device_id}': {exc}", exc_info=True)
            raise RuntimeError("Database storage operation failed.") from exc

    @staticmethod
    async def get_latest_telemetry(session: AsyncSession, device_id: str) -> TelemetryRecordResponse:
        """
        Fetch the most recent valid telemetry record for the requested machine.

        Raises:
            ResourceNotFoundException: If no telemetry records exist for this device.
        """
        stmt = (
            select(SensorReading)
            .where(SensorReading.device_id == device_id)
            .order_by(SensorReading.timestamp.desc(), SensorReading.id.desc())
            .limit(1)
        )

        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            raise ResourceNotFoundException(
                message=f"No telemetry records found for device '{device_id}'.",
                code="DEVICE_TELEMETRY_NOT_FOUND",
            )

        return TelemetryRecordResponse.model_validate(record)

    @staticmethod
    async def get_historical_telemetry(
        session: AsyncSession,
        device_id: str,
        hours: float,
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> HistoricalTelemetryResponse:
        """
        Query historical telemetry for a machine within the requested time window
        using chronological ordering and cursor-based pagination.
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)

        conditions = [
            SensorReading.device_id == device_id,
            SensorReading.timestamp >= start_time,
            SensorReading.timestamp <= end_time,
        ]

        if cursor:
            cursor_dt, cursor_id = decode_cursor(cursor)
            conditions.append(
                or_(
                    SensorReading.timestamp > cursor_dt,
                    and_(
                        SensorReading.timestamp == cursor_dt,
                        SensorReading.id > cursor_id,
                    ),
                )
            )

        # Utilize composite index (device_id, timestamp) with deterministic sort
        stmt = (
            select(SensorReading)
            .where(and_(*conditions))
            .order_by(SensorReading.timestamp.asc(), SensorReading.id.asc())
            .limit(limit + 1)
        )

        result = await session.execute(stmt)
        records = result.scalars().all()

        has_more = len(records) > limit
        page_items = records[:limit]

        next_cursor = None
        if has_more and page_items:
            last_item = page_items[-1]
            next_cursor = encode_cursor(last_item.timestamp, last_item.id)

        items_dto = [TelemetryRecordResponse.model_validate(r) for r in page_items]

        return HistoricalTelemetryResponse(
            device_id=device_id,
            hours_queried=hours,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            count=len(items_dto),
            has_more=has_more,
            next_cursor=next_cursor,
            items=items_dto,
        )
