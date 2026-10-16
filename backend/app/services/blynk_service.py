"""
Blynk IoT Cloud Integration & Environmental Alert Service.

Manages:
1. Virtual Datastream synchronization (V0 to V7) via Blynk REST API.
2. Real-time threshold monitoring (High MQ135 response, High Temperature, Waste-Bin capacity, Sensor faults).
3. AI Anomaly alert bridging from Isolation Forest.
4. Configurable cooldown timers (default 300s) preventing notification spamming.
5. Persistent audit logging in environment_alerts table.
6. Graceful unconfigured fallback when Blynk credentials are not provided.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any
import logging
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.core.config import settings
from app.models.environment import EnvironmentReading, EnvironmentAlert
from app.schemas.environment import (
    AlertItemResponse,
    AlertListResponse,
    BlynkStatusResponse,
    TestAlertRequest,
)

logger = logging.getLogger("aiot.blynk_service")

# Virtual Datastream Documentation
VIRTUAL_PIN_MAP = {
    "V0": "Temperature (°C)",
    "V1": "Relative Humidity (%)",
    "V2": "MQ135 Gas Sensor Voltage (V)",
    "V3": "Cumulative IR Footfall Count",
    "V4": "Smart Waste-Bin Fill (%)",
    "V5": "1-Hour Ahead MQ135 Forecast (V)",
    "V6": "AI Anomaly Status (0=Normal, 1=Outlier)",
    "V7": "Device Status & Alert Notification String",
}


class BlynkService:
    """Service managing Blynk IoT Cloud synchronization and environmental threshold alerts."""

    # In-memory cooldown tracking: dict of (device_id, alert_type) -> last_triggered_epoch_seconds
    _last_alert_times: Dict[str, float] = {}

    @classmethod
    def _get_cooldown_key(cls, device_id: str, alert_type: str) -> str:
        return f"{device_id}:{alert_type}"

    @classmethod
    def get_remaining_cooldown(cls, device_id: str, alert_type: str) -> float:
        """Returns remaining cooldown lockout in seconds, or 0.0 if alert can trigger."""
        key = cls._get_cooldown_key(device_id, alert_type)
        last_time = cls._last_alert_times.get(key)
        if last_time is None:
            return 0.0

        elapsed = datetime.now(timezone.utc).timestamp() - last_time
        remaining = settings.ALERT_COOLDOWN_SECONDS - elapsed
        return max(0.0, round(remaining, 1))

    @classmethod
    def can_trigger_alert(cls, device_id: str, alert_type: str) -> bool:
        """Check whether alert can be dispatched without violating cooldown lockout."""
        return cls.get_remaining_cooldown(device_id, alert_type) <= 0.0

    @classmethod
    def record_alert_trigger(cls, device_id: str, alert_type: str) -> None:
        """Update cooldown timestamp upon dispatching alert."""
        key = cls._get_cooldown_key(device_id, alert_type)
        cls._last_alert_times[key] = datetime.now(timezone.utc).timestamp()

    @classmethod
    def reset_cooldown(cls, device_id: str, alert_type: str) -> None:
        """Reset cooldown when condition has recovered."""
        key = cls._get_cooldown_key(device_id, alert_type)
        if key in cls._last_alert_times:
            del cls._last_alert_times[key]

    @classmethod
    def get_all_active_cooldowns(cls) -> Dict[str, float]:
        """Returns map of active cooldown timers for monitoring."""
        now = datetime.now(timezone.utc).timestamp()
        active = {}
        for key, last_time in list(cls._last_alert_times.items()):
            remaining = settings.ALERT_COOLDOWN_SECONDS - (now - last_time)
            if remaining > 0:
                active[key] = round(remaining, 1)
            else:
                del cls._last_alert_times[key]
        return active

    @classmethod
    async def sync_virtual_pins(
        cls,
        device_id: str,
        temperature: Optional[float] = None,
        humidity: Optional[float] = None,
        mq135_voltage: Optional[float] = None,
        ir_count: Optional[int] = None,
        bin_fill: Optional[float] = None,
        forecast_60m: Optional[float] = None,
        is_anomaly: Optional[bool] = None,
        status_message: Optional[str] = None,
    ) -> bool:
        """
        Synchronize multi-sensor metrics and AI predictions to Blynk Cloud Virtual Pins V0-V7.
        Executes via Blynk Cloud REST API.
        """
        token = settings.BLYNK_AUTH_TOKEN
        if not token or not settings.BLYNK_ENABLED:
            logger.debug("[BLYNK] Cloud synchronization skipped (token unconfigured or disabled).")
            return False

        # Construct query parameters for Blynk /update endpoint
        params: Dict[str, Any] = {"token": token}
        if temperature is not None:
            params["v0"] = round(temperature, 1)
        if humidity is not None:
            params["v1"] = round(humidity, 1)
        if mq135_voltage is not None:
            params["v2"] = round(mq135_voltage, 3)
        if ir_count is not None:
            params["v3"] = ir_count
        if bin_fill is not None:
            params["v4"] = round(bin_fill, 1)
        if forecast_60m is not None:
            params["v5"] = round(forecast_60m, 3)
        if is_anomaly is not None:
            params["v6"] = 1 if is_anomaly else 0
        if status_message is not None:
            params["v7"] = status_message[:128]

        url = f"{settings.BLYNK_SERVER_URL.rstrip('/')}/update"

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    logger.debug(f"[BLYNK] Synced virtual pins for {device_id} successfully.")
                    return True
                else:
                    logger.warning(f"[BLYNK] Update returned HTTP {res.status_code}: {res.text}")
                    return False
        except Exception as exc:
            logger.warning(f"[BLYNK] Cloud connection failed: {exc}")
            return False

    @classmethod
    async def dispatch_blynk_event(cls, event_code: str, description: str) -> bool:
        """
        Dispatch a high-priority event notification to Blynk Cloud mobile app and timeline.
        Endpoint: /logEvent?token=...&code=...&description=...
        """
        token = settings.BLYNK_AUTH_TOKEN
        if not token or not settings.BLYNK_ENABLED:
            logger.debug(f"[BLYNK] Local alert logged (Blynk cloud event '{event_code}' skipped - unconfigured).")
            return False

        url = f"{settings.BLYNK_SERVER_URL.rstrip('/')}/logEvent"
        params = {
            "token": token,
            "code": event_code,
            "description": description[:255],
        }

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    logger.info(f"[BLYNK] Dispatched event notification '{event_code}' successfully.")
                    return True
                else:
                    logger.warning(f"[BLYNK] Event dispatch returned HTTP {res.status_code}: {res.text}")
                    return False
        except Exception as exc:
            logger.warning(f"[BLYNK] Event notification network error: {exc}")
            return False

    @classmethod
    async def evaluate_and_dispatch_alerts(
        cls,
        session: AsyncSession,
        reading: EnvironmentReading,
        prediction_val: Optional[float] = None,
        is_anomaly: Optional[bool] = None,
        anomaly_explanation: Optional[str] = None,
    ) -> List[EnvironmentAlert]:
        """
        Evaluates an environmental telemetry reading against physical thresholds and AI outcomes.
        Applies cooldowns, dispatches to Blynk Cloud if enabled, and persists to environment_alerts.
        """
        dispatched_alerts: List[EnvironmentAlert] = []
        device_id = reading.device_id
        timestamp = reading.timestamp or datetime.now(timezone.utc)
        is_mock = reading.is_mock

        # ----------------------------------------------------------------------
        # 1. High Gas Response Threshold Alert (MQ135 Voltage)
        # Note: Do NOT interpret voltage as official calibrated AQI or toxic concentration.
        # ----------------------------------------------------------------------
        if reading.mq135_voltage is not None:
            threshold = settings.ALERT_MQ135_THRESHOLD_VOLTS
            if reading.mq135_voltage >= threshold:
                if cls.can_trigger_alert(device_id, "HIGH_MQ135"):
                    msg = (
                        f"Elevated MQ135 gas sensor response: {reading.mq135_voltage:.2f}V "
                        f"(Threshold: {threshold:.2f}V). Verify local area ventilation."
                    )
                    blynk_ok = await cls.dispatch_blynk_event("high_gas_alert", msg)
                    alert_rec = EnvironmentAlert(
                        device_id=device_id,
                        timestamp=timestamp,
                        alert_type="HIGH_MQ135",
                        severity="WARNING" if reading.mq135_voltage < 3.0 else "CRITICAL",
                        message=msg,
                        metric_value=float(reading.mq135_voltage),
                        threshold_value=float(threshold),
                        is_mock=is_mock,
                        blynk_delivered=blynk_ok,
                    )
                    session.add(alert_rec)
                    dispatched_alerts.append(alert_rec)
                    cls.record_alert_trigger(device_id, "HIGH_MQ135")
            else:
                # Reset cooldown if value drops significantly below threshold
                if reading.mq135_voltage < (threshold - 0.2):
                    cls.reset_cooldown(device_id, "HIGH_MQ135")

        # ----------------------------------------------------------------------
        # 2. High Ambient Thermal Threshold Alert (DHT22)
        # ----------------------------------------------------------------------
        if reading.temperature_c is not None:
            threshold = settings.ALERT_TEMP_HIGH_C
            if reading.temperature_c >= threshold:
                if cls.can_trigger_alert(device_id, "HIGH_TEMP"):
                    msg = (
                        f"Elevated ambient temperature: {reading.temperature_c:.1f}°C "
                        f"(Threshold: {threshold:.1f}°C). Check cooling / HVAC or thermal source."
                    )
                    blynk_ok = await cls.dispatch_blynk_event("high_temp_alert", msg)
                    alert_rec = EnvironmentAlert(
                        device_id=device_id,
                        timestamp=timestamp,
                        alert_type="HIGH_TEMP",
                        severity="WARNING" if reading.temperature_c < 45.0 else "CRITICAL",
                        message=msg,
                        metric_value=float(reading.temperature_c),
                        threshold_value=float(threshold),
                        is_mock=is_mock,
                        blynk_delivered=blynk_ok,
                    )
                    session.add(alert_rec)
                    dispatched_alerts.append(alert_rec)
                    cls.record_alert_trigger(device_id, "HIGH_TEMP")
            else:
                if reading.temperature_c < (threshold - 2.0):
                    cls.reset_cooldown(device_id, "HIGH_TEMP")

        # ----------------------------------------------------------------------
        # 3. Waste-Bin Capacity Threshold Alert (HC-SR04)
        # ----------------------------------------------------------------------
        if reading.bin_fill_percent is not None:
            threshold = settings.ALERT_BIN_FULL_PERCENT
            if reading.bin_fill_percent >= threshold:
                if cls.can_trigger_alert(device_id, "BIN_FULL"):
                    msg = (
                        f"Smart waste bin capacity reached: {reading.bin_fill_percent:.1f}% "
                        f"(Threshold: {threshold:.1f}%). Waste collection recommended."
                    )
                    blynk_ok = await cls.dispatch_blynk_event("bin_full_alert", msg)
                    alert_rec = EnvironmentAlert(
                        device_id=device_id,
                        timestamp=timestamp,
                        alert_type="BIN_FULL",
                        severity="WARNING",
                        message=msg,
                        metric_value=float(reading.bin_fill_percent),
                        threshold_value=float(threshold),
                        is_mock=is_mock,
                        blynk_delivered=blynk_ok,
                    )
                    session.add(alert_rec)
                    dispatched_alerts.append(alert_rec)
                    cls.record_alert_trigger(device_id, "BIN_FULL")
            else:
                if reading.bin_fill_percent < (threshold - 10.0):
                    cls.reset_cooldown(device_id, "BIN_FULL")

        # ----------------------------------------------------------------------
        # 4. Hardware Sensor Probe Disconnection Alert
        # ----------------------------------------------------------------------
        status_map = reading.sensor_status or {}
        failed_probes = [k for k, v in status_map.items() if str(v).upper() == "FAIL"]
        if failed_probes and not is_mock:
            if cls.can_trigger_alert(device_id, "SENSOR_DISCONNECT"):
                msg = f"Hardware sensor probe fault detected: {', '.join(failed_probes)}. Check wiring."
                blynk_ok = await cls.dispatch_blynk_event("sensor_fault", msg)
                alert_rec = EnvironmentAlert(
                    device_id=device_id,
                    timestamp=timestamp,
                    alert_type="SENSOR_DISCONNECT",
                    severity="WARNING",
                    message=msg,
                    is_mock=False,
                    blynk_delivered=blynk_ok,
                )
                session.add(alert_rec)
                dispatched_alerts.append(alert_rec)
                cls.record_alert_trigger(device_id, "SENSOR_DISCONNECT")
        elif not failed_probes:
            cls.reset_cooldown(device_id, "SENSOR_DISCONNECT")

        # ----------------------------------------------------------------------
        # 5. AI Anomaly Alert (Isolation Forest)
        # ----------------------------------------------------------------------
        if is_anomaly:
            if cls.can_trigger_alert(device_id, "AI_ANOMALY"):
                msg = anomaly_explanation or "Multivariate environmental outlier detected by Isolation Forest."
                blynk_ok = await cls.dispatch_blynk_event("ai_anomaly_alert", msg)
                alert_rec = EnvironmentAlert(
                    device_id=device_id,
                    timestamp=timestamp,
                    alert_type="AI_ANOMALY",
                    severity="CRITICAL",
                    message=msg,
                    is_mock=is_mock,
                    blynk_delivered=blynk_ok,
                )
                session.add(alert_rec)
                dispatched_alerts.append(alert_rec)
                cls.record_alert_trigger(device_id, "AI_ANOMALY")

        # Commit dispatched alerts if any
        if dispatched_alerts:
            await session.commit()
            for a in dispatched_alerts:
                await session.refresh(a)

        # ----------------------------------------------------------------------
        # 6. Synchronize Virtual Pins to Blynk Cloud (if enabled)
        # ----------------------------------------------------------------------
        status_msg = f"Alerts: {len(dispatched_alerts)}" if dispatched_alerts else "Nominal"
        await cls.sync_virtual_pins(
            device_id=device_id,
            temperature=reading.temperature_c,
            humidity=reading.humidity_percent,
            mq135_voltage=reading.mq135_voltage,
            ir_count=reading.ir_count,
            bin_fill=reading.bin_fill_percent,
            forecast_60m=prediction_val,
            is_anomaly=is_anomaly,
            status_message=status_msg,
        )

        return dispatched_alerts

    @classmethod
    async def get_alerts(
        cls,
        session: AsyncSession,
        device_id: str,
        hours: float = 24.0,
        limit: int = 50,
    ) -> AlertListResponse:
        """Retrieves historical environmental alerts for the specified device and lookback window."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        stmt = (
            select(EnvironmentAlert)
            .where(
                and_(
                    EnvironmentAlert.device_id == device_id,
                    EnvironmentAlert.timestamp >= start_time,
                )
            )
            .order_by(desc(EnvironmentAlert.timestamp), desc(EnvironmentAlert.id))
            .limit(limit)
        )

        result = await session.execute(stmt)
        records = result.scalars().all()

        items = [
            AlertItemResponse(
                id=r.id,
                device_id=r.device_id,
                timestamp=r.timestamp,
                alert_type=r.alert_type,
                severity=r.severity,
                message=r.message,
                metric_value=r.metric_value,
                threshold_value=r.threshold_value,
                is_mock=r.is_mock,
                blynk_delivered=r.blynk_delivered,
                created_at=r.created_at,
            )
            for r in records
        ]

        return AlertListResponse(
            device_id=device_id,
            hours_analyzed=hours,
            count=len(items),
            items=items,
        )

    @classmethod
    async def trigger_test_alert(
        cls,
        session: AsyncSession,
        request: TestAlertRequest,
    ) -> AlertItemResponse:
        """Manually trigger a demonstration or test alert to verify local and cloud notification pipeline."""
        now = datetime.now(timezone.utc)
        msg = request.message or f"Demonstration alert for {request.alert_type} (metric={request.metric_value})."

        blynk_ok = await cls.dispatch_blynk_event("test_alert", msg)

        alert_rec = EnvironmentAlert(
            device_id=request.device_id,
            timestamp=now,
            alert_type=request.alert_type,
            severity=request.severity,
            message=msg,
            metric_value=request.metric_value,
            threshold_value=settings.ALERT_MQ135_THRESHOLD_VOLTS,
            is_mock=True,
            blynk_delivered=blynk_ok,
        )
        session.add(alert_rec)
        await session.commit()
        await session.refresh(alert_rec)

        return AlertItemResponse(
            id=alert_rec.id,
            device_id=alert_rec.device_id,
            timestamp=alert_rec.timestamp,
            alert_type=alert_rec.alert_type,
            severity=alert_rec.severity,
            message=alert_rec.message,
            metric_value=alert_rec.metric_value,
            threshold_value=alert_rec.threshold_value,
            is_mock=alert_rec.is_mock,
            blynk_delivered=alert_rec.blynk_delivered,
            created_at=alert_rec.created_at,
        )

    @classmethod
    def get_status(cls) -> BlynkStatusResponse:
        """Returns the current operational and configuration state of the Blynk integration."""
        is_conf = bool(settings.BLYNK_AUTH_TOKEN and len(settings.BLYNK_AUTH_TOKEN.strip()) > 5)
        return BlynkStatusResponse(
            blynk_configured=is_conf,
            blynk_enabled=settings.BLYNK_ENABLED,
            server_url=settings.BLYNK_SERVER_URL,
            active_cooldowns=cls.get_all_active_cooldowns(),
            thresholds={
                "mq135_voltage_v": settings.ALERT_MQ135_THRESHOLD_VOLTS,
                "temperature_c": settings.ALERT_TEMP_HIGH_C,
                "bin_fill_percent": settings.ALERT_BIN_FULL_PERCENT,
                "cooldown_seconds": float(settings.ALERT_COOLDOWN_SECONDS),
            },
            virtual_pins=VIRTUAL_PIN_MAP,
        )
