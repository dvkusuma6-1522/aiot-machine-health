"""
Environmental Telemetry Service.

Handles persistence, latest state retrieval, indexed cursor-paginated history,
and aggregation summaries for environmental monitoring nodes.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
from sqlalchemy import select, and_, or_, func, delete
from app.models.environment import EnvironmentReading
from app.schemas.environment import (
    EnvironmentTelemetryPayload,
    EnvironmentTelemetryResponse,
    EnvironmentRecordResponse,
    HistoricalEnvironmentResponse,
    EnvironmentSummaryResponse,
    MetricStats,
    DemoScenarioRequest,
    DemoScenarioResponse,
)
from ml.environment.synthetic_generator import SyntheticDataGenerator
from app.services.telemetry_service import encode_cursor, decode_cursor
from app.core.exceptions import ResourceNotFoundException
import logging

logger = logging.getLogger("aiot.environment_service")


class EnvironmentService:
    """Service layer managing environmental sensor reading persistence and queries."""

    @staticmethod
    async def save_telemetry(
        session: AsyncSession,
        payload: EnvironmentTelemetryPayload,
    ) -> EnvironmentTelemetryResponse:
        """
        Persist a validated environmental payload into the environment_readings table.
        """
        try:
            db_record = EnvironmentReading(
                device_id=payload.device_id,
                timestamp=payload.timestamp,
                is_mock=bool(payload.is_mock),
                temperature_c=payload.temperature_c,
                humidity_percent=payload.humidity_percent,
                mq135_raw=payload.mq135_raw,
                mq135_voltage=payload.mq135_voltage,
                ir_count=payload.ir_count,
                ultrasonic_distance_cm=payload.ultrasonic_distance_cm,
                bin_fill_percent=payload.bin_fill_percent,
                sensor_status=payload.sensor_status,
            )

            session.add(db_record)
            await session.commit()
            await session.refresh(db_record)

            # Evaluate threshold and AI alerts (non-blocking / safe)
            try:
                from app.services.blynk_service import BlynkService
                await BlynkService.evaluate_and_dispatch_alerts(session, db_record)
            except Exception as alert_err:
                logger.warning(f"Alert evaluation error (non-fatal): {alert_err}")

            received_iso = datetime.now(timezone.utc).isoformat()
            return EnvironmentTelemetryResponse(
                status="accepted",
                device_id=db_record.device_id,
                received_at=received_iso,
                telemetry_id=db_record.id,
            )

        except SQLAlchemyError as exc:
            await session.rollback()
            logger.error(
                f"Database error while saving environmental telemetry for device '{payload.device_id}': {exc}",
                exc_info=True,
            )
            raise RuntimeError("Database storage operation failed.") from exc

    @staticmethod
    async def get_latest_telemetry(
        session: AsyncSession,
        device_id: str,
    ) -> EnvironmentRecordResponse:
        """
        Fetch the most recent valid environmental telemetry record for the requested device.

        Raises:
            ResourceNotFoundException: If no records exist for this device.
        """
        stmt = (
            select(EnvironmentReading)
            .where(EnvironmentReading.device_id == device_id)
            .order_by(EnvironmentReading.timestamp.desc(), EnvironmentReading.id.desc())
            .limit(1)
        )

        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            raise ResourceNotFoundException(
                message=f"No environmental telemetry records found for device '{device_id}'.",
                code="DEVICE_TELEMETRY_NOT_FOUND",
            )

        return EnvironmentRecordResponse.model_validate(record)

    @staticmethod
    async def get_historical_telemetry(
        session: AsyncSession,
        device_id: str,
        hours: float,
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> HistoricalEnvironmentResponse:
        """
        Query historical environmental telemetry for a device within the requested time window
        using chronological ordering and cursor-based pagination.
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)

        conditions = [
            EnvironmentReading.device_id == device_id,
            EnvironmentReading.timestamp >= start_time,
            EnvironmentReading.timestamp <= end_time,
        ]

        if cursor:
            cursor_dt, cursor_id = decode_cursor(cursor)
            conditions.append(
                or_(
                    EnvironmentReading.timestamp > cursor_dt,
                    and_(
                        EnvironmentReading.timestamp == cursor_dt,
                        EnvironmentReading.id > cursor_id,
                    ),
                )
            )

        # Utilize composite index (device_id, timestamp) with deterministic sort
        stmt = (
            select(EnvironmentReading)
            .where(and_(*conditions))
            .order_by(EnvironmentReading.timestamp.asc(), EnvironmentReading.id.asc())
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

        items_dto = [EnvironmentRecordResponse.model_validate(r) for r in page_items]

        return HistoricalEnvironmentResponse(
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

    @staticmethod
    async def get_environment_summary(
        session: AsyncSession,
        device_id: str,
        hours: float = 24.0,
    ) -> EnvironmentSummaryResponse:
        """
        Compute descriptive summary statistics (min, max, avg, latest, count)
        for all sensor measurements over the requested time window.
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)

        # 1. Total record count in window
        count_stmt = (
            select(func.count(EnvironmentReading.id))
            .where(
                and_(
                    EnvironmentReading.device_id == device_id,
                    EnvironmentReading.timestamp >= start_time,
                    EnvironmentReading.timestamp <= end_time,
                )
            )
        )
        total_records_result = await session.execute(count_stmt)
        total_records = total_records_result.scalar_one() or 0

        metric_names = [
            "temperature_c",
            "humidity_percent",
            "mq135_raw",
            "mq135_voltage",
            "ir_count",
            "ultrasonic_distance_cm",
            "bin_fill_percent",
        ]

        metrics_dict: Dict[str, MetricStats] = {}

        if total_records == 0:
            for m in metric_names:
                metrics_dict[m] = MetricStats(count=0, min=None, max=None, avg=None, latest=None)
            return EnvironmentSummaryResponse(
                device_id=device_id,
                hours_queried=hours,
                start_time=start_time,
                end_time=end_time,
                total_records=0,
                metrics=metrics_dict,
            )

        # 2. Latest reading for current snapshot
        latest_stmt = (
            select(EnvironmentReading)
            .where(
                and_(
                    EnvironmentReading.device_id == device_id,
                    EnvironmentReading.timestamp >= start_time,
                    EnvironmentReading.timestamp <= end_time,
                )
            )
            .order_by(EnvironmentReading.timestamp.desc(), EnvironmentReading.id.desc())
            .limit(1)
        )
        latest_result = await session.execute(latest_stmt)
        latest_record = latest_result.scalar_one_or_none()

        # 3. Aggregate statistics query
        agg_stmt = (
            select(
                func.count(EnvironmentReading.temperature_c),
                func.min(EnvironmentReading.temperature_c),
                func.max(EnvironmentReading.temperature_c),
                func.avg(EnvironmentReading.temperature_c),
                func.count(EnvironmentReading.humidity_percent),
                func.min(EnvironmentReading.humidity_percent),
                func.max(EnvironmentReading.humidity_percent),
                func.avg(EnvironmentReading.humidity_percent),
                func.count(EnvironmentReading.mq135_raw),
                func.min(EnvironmentReading.mq135_raw),
                func.max(EnvironmentReading.mq135_raw),
                func.avg(EnvironmentReading.mq135_raw),
                func.count(EnvironmentReading.mq135_voltage),
                func.min(EnvironmentReading.mq135_voltage),
                func.max(EnvironmentReading.mq135_voltage),
                func.avg(EnvironmentReading.mq135_voltage),
                func.count(EnvironmentReading.ir_count),
                func.min(EnvironmentReading.ir_count),
                func.max(EnvironmentReading.ir_count),
                func.avg(EnvironmentReading.ir_count),
                func.count(EnvironmentReading.ultrasonic_distance_cm),
                func.min(EnvironmentReading.ultrasonic_distance_cm),
                func.max(EnvironmentReading.ultrasonic_distance_cm),
                func.avg(EnvironmentReading.ultrasonic_distance_cm),
                func.count(EnvironmentReading.bin_fill_percent),
                func.min(EnvironmentReading.bin_fill_percent),
                func.max(EnvironmentReading.bin_fill_percent),
                func.avg(EnvironmentReading.bin_fill_percent),
            )
            .where(
                and_(
                    EnvironmentReading.device_id == device_id,
                    EnvironmentReading.timestamp >= start_time,
                    EnvironmentReading.timestamp <= end_time,
                )
            )
        )
        agg_result = await session.execute(agg_stmt)
        row = agg_result.one()

        for idx, m in enumerate(metric_names):
            cnt_val = row[idx * 4]
            min_val = row[idx * 4 + 1]
            max_val = row[idx * 4 + 2]
            avg_val = row[idx * 4 + 3]
            latest_val = getattr(latest_record, m, None) if latest_record else None

            metrics_dict[m] = MetricStats(
                count=cnt_val or 0,
                min=float(min_val) if min_val is not None else None,
                max=float(max_val) if max_val is not None else None,
                avg=round(float(avg_val), 2) if avg_val is not None else None,
                latest=float(latest_val) if latest_val is not None else None,
            )

        return EnvironmentSummaryResponse(
            device_id=device_id,
            hours_queried=hours,
            start_time=start_time,
            end_time=end_time,
            total_records=total_records,
            metrics=metrics_dict,
        )

    @staticmethod
    async def inject_demo_scenario(
        session: AsyncSession,
        request: DemoScenarioRequest,
    ) -> DemoScenarioResponse:
        """
        Inject a reproducible synthetic multi-sensor scenario dataset into environment_readings.
        All records are strictly marked with is_mock=True.
        """
        try:
            if request.clear_previous_demo:
                del_stmt = delete(EnvironmentReading).where(
                    and_(
                        EnvironmentReading.device_id == request.device_id,
                        EnvironmentReading.is_mock == True,
                    )
                )
                await session.execute(del_stmt)

                from app.models.environment import EnvironmentAlert
                del_alerts = delete(EnvironmentAlert).where(
                    and_(
                        EnvironmentAlert.device_id == request.device_id,
                        EnvironmentAlert.is_mock == True,
                    )
                )
                await session.execute(del_alerts)

            df = SyntheticDataGenerator.generate_scenario_dataset(
                scenario=request.scenario,
                n_samples=request.n_samples,
                device_id=request.device_id,
                sample_interval_sec=request.sample_interval_sec,
            )

            records = []
            for _, row in df.iterrows():
                ts = row["timestamp"]
                if hasattr(ts, "to_pydatetime"):
                    ts = ts.to_pydatetime()
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)

                rec = EnvironmentReading(
                    device_id=str(row["device_id"]),
                    timestamp=ts,
                    is_mock=True,
                    temperature_c=float(row["temperature_c"]) if pd.notna(row["temperature_c"]) else None,
                    humidity_percent=float(row["humidity_percent"]) if pd.notna(row["humidity_percent"]) else None,
                    mq135_raw=float(row["mq135_raw"]) if pd.notna(row["mq135_raw"]) else None,
                    mq135_voltage=float(row["mq135_voltage"]) if pd.notna(row["mq135_voltage"]) else None,
                    ir_count=int(row["ir_count"]) if pd.notna(row["ir_count"]) else None,
                    ultrasonic_distance_cm=float(row["ultrasonic_distance_cm"]) if pd.notna(row["ultrasonic_distance_cm"]) else None,
                    bin_fill_percent=float(row["bin_fill_percent"]) if pd.notna(row["bin_fill_percent"]) else None,
                    sensor_status=row.get("sensor_status", {"dht22": "OK", "mq135": "OK", "ir": "OK", "ultrasonic": "OK"}),
                )
                records.append(rec)

            session.add_all(records)
            await session.commit()

            # Evaluate alerts on the injected scenario records (triggering demo alert pipeline)
            try:
                from app.services.blynk_service import BlynkService
                for rec in records:
                    await BlynkService.evaluate_and_dispatch_alerts(session, rec)
            except Exception as alert_err:
                logger.warning(f"Demo scenario alert dispatch warning: {alert_err}")

            start_t = records[0].timestamp if records else datetime.now(timezone.utc)
            end_t = records[-1].timestamp if records else datetime.now(timezone.utc)

            return DemoScenarioResponse(
                status="SUCCESS",
                scenario=request.scenario,
                device_id=request.device_id,
                records_inserted=len(records),
                start_time=start_t,
                end_time=end_t,
                message=f"Successfully injected {len(records)} mock telemetry records for scenario '{request.scenario}'.",
            )
        except Exception as exc:
            await session.rollback()
            logger.error(f"Failed to inject demo scenario: {exc}", exc_info=True)
            raise RuntimeError(f"Demo scenario generation failed: {exc}") from exc
