"""
Pydantic v2 Schemas for Telemetry Ingestion and Responses.

Implements strict type checking, physical validation limits, rejection of NaN/Inf,
timestamp standardisation, and response serialization.
"""

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
)
from app.core.config import settings

limits = settings.limits


class TelemetryPayload(BaseModel):
    """
    Ingested Telemetry Payload conforming to ESP32 DevKit packet specifications.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    device_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique identifier for the monitored machine edge node.",
        examples=["motor_001"],
    )

    timestamp: datetime = Field(
        ...,
        description="Timestamp as ISO-8601 string or numeric epoch seconds/milliseconds.",
        examples=["2026-10-08T18:00:00Z", 1728410400],
    )

    is_mock: Optional[bool] = Field(
        default=False,
        description="Flag denoting whether the payload originates from simulated test bench data.",
    )

    sensor_status: Optional[Dict[str, bool]] = Field(
        default=None,
        description="Optional startup health status flags reported by edge sensors.",
    )

    # Thermal Metric
    temperature: float = Field(
        ...,
        description="Motor stator/casing surface temperature in degrees Celsius.",
        examples=[43.2],
    )

    # Accelerometer (Vibration in g)
    accel_x: float = Field(..., description="X-axis acceleration in g.", examples=[0.12])
    accel_y: float = Field(..., description="Y-axis acceleration in g.", examples=[0.08])
    accel_z: float = Field(..., description="Z-axis acceleration in g.", examples=[1.04])

    # Gyroscope (deg/s)
    gyro_x: float = Field(..., description="X-axis angular velocity in deg/s.", examples=[0.1])
    gyro_y: float = Field(..., description="Y-axis angular velocity in deg/s.", examples=[0.2])
    gyro_z: float = Field(..., description="Z-axis angular velocity in deg/s.", examples=[0.3])

    # Electrical Power Metrics
    current: float = Field(..., description="Operating current in Amperes.", examples=[1.12])
    voltage: float = Field(..., description="Bus supply voltage in Volts.", examples=[11.8])
    power: float = Field(..., description="Electrical power in Watts.", examples=[13.2])

    # Rotational Speed
    rpm: float = Field(..., description="Rotor shaft speed in RPM.", examples=[1498.0])

    # --------------------------------------------------------------------------
    # FIELD VALIDATORS
    # --------------------------------------------------------------------------

    @field_validator(
        "temperature",
        "accel_x",
        "accel_y",
        "accel_z",
        "gyro_x",
        "gyro_y",
        "gyro_z",
        "current",
        "voltage",
        "power",
        "rpm",
        mode="before",
    )
    @classmethod
    def reject_nan_and_inf(cls, value: Any, info) -> float:
        """Reject NaN and infinite float values before numerical evaluation."""
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"Field '{info.field_name}' must be a numeric float, got {type(value).__name__}")
        float_val = float(value)
        if math.isnan(float_val):
            raise ValueError(f"Field '{info.field_name}' contains illegal NaN value")
        if math.isinf(float_val):
            raise ValueError(f"Field '{info.field_name}' contains illegal infinite value")
        return float_val

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_and_parse_timestamp(cls, value: Any) -> datetime:
        """Normalize numeric epoch or ISO timestamp strings into UTC datetime."""
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value

        if isinstance(value, (int, float)):
            if math.isnan(value) or math.isinf(value):
                raise ValueError("Timestamp cannot be NaN or infinite")
            # If timestamp is in milliseconds (> 1e11), convert to seconds
            if value > 1e11:
                secs = value / 1000.0
            elif value < 0:
                raise ValueError("Numeric timestamp cannot be negative")
            else:
                secs = float(value)
            try:
                return datetime.fromtimestamp(secs, tz=timezone.utc)
            except (OverflowError, OSError, ValueError) as exc:
                raise ValueError(f"Invalid numeric timestamp value: {value}") from exc

        if isinstance(value, str):
            clean_str = value.strip()
            if not clean_str:
                raise ValueError("Timestamp string cannot be empty")
            # Handle ISO 8601 formatting
            if clean_str.endswith("Z"):
                clean_str = clean_str[:-1] + "+00:00"
            try:
                parsed_dt = datetime.fromisoformat(clean_str)
                if parsed_dt.tzinfo is None:
                    parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                return parsed_dt
            except ValueError as exc:
                raise ValueError(f"Malformed ISO-8601 timestamp string: '{value}'") from exc

        raise ValueError(f"Unsupported timestamp format: {type(value).__name__}")

    # --------------------------------------------------------------------------
    # PHYSICAL RANGE SANITY VALIDATION
    # --------------------------------------------------------------------------

    @field_validator("temperature")
    @classmethod
    def validate_temperature_bounds(cls, v: float) -> float:
        if v < limits.TEMP_MIN_C or v > limits.TEMP_MAX_C:
            raise ValueError(
                f"Temperature {v}C exceeds sensor validation limits "
                f"[{limits.TEMP_MIN_C}C, {limits.TEMP_MAX_C}C]"
            )
        return v

    @field_validator("current")
    @classmethod
    def validate_current_bounds(cls, v: float) -> float:
        if v < limits.CURRENT_MIN_A or v > limits.CURRENT_MAX_A:
            raise ValueError(
                f"Current {v}A violates non-negative physical boundary "
                f"[{limits.CURRENT_MIN_A}A, {limits.CURRENT_MAX_A}A]"
            )
        return v

    @field_validator("voltage")
    @classmethod
    def validate_voltage_bounds(cls, v: float) -> float:
        if v < limits.VOLTAGE_MIN_V or v > limits.VOLTAGE_MAX_V:
            raise ValueError(
                f"Voltage {v}V violates non-negative physical boundary "
                f"[{limits.VOLTAGE_MIN_V}V, {limits.VOLTAGE_MAX_V}V]"
            )
        return v

    @field_validator("rpm")
    @classmethod
    def validate_rpm_bounds(cls, v: float) -> float:
        if v < limits.RPM_MIN or v > limits.RPM_MAX:
            raise ValueError(
                f"RPM {v} violates non-negative rotational bounds "
                f"[{limits.RPM_MIN}, {limits.RPM_MAX}]"
            )
        return v

    @field_validator("accel_x", "accel_y", "accel_z")
    @classmethod
    def validate_accel_bounds(cls, v: float, info) -> float:
        if v < limits.ACCEL_MIN_G or v > limits.ACCEL_MAX_G:
            raise ValueError(
                f"Acceleration component {info.field_name}={v}g exceeds hardware full-scale "
                f"[{limits.ACCEL_MIN_G}g, {limits.ACCEL_MAX_G}g]"
            )
        return v

    @field_validator("gyro_x", "gyro_y", "gyro_z")
    @classmethod
    def validate_gyro_bounds(cls, v: float, info) -> float:
        if v < limits.GYRO_MIN_DEG_S or v > limits.GYRO_MAX_DEG_S:
            raise ValueError(
                f"Gyroscope component {info.field_name}={v} deg/s exceeds hardware dynamic range "
                f"[{limits.GYRO_MIN_DEG_S}, {limits.GYRO_MAX_DEG_S}]"
            )
        return v

    @field_validator("power")
    @classmethod
    def validate_power_bounds(cls, v: float) -> float:
        if v < limits.POWER_MIN_W or v > limits.POWER_MAX_W:
            raise ValueError(
                f"Power {v}W violates non-negative boundary [{limits.POWER_MIN_W}W, {limits.POWER_MAX_W}W]"
            )
        return v

    @model_validator(mode="after")
    def validate_power_consistency(self) -> "TelemetryPayload":
        """Verify that power P is physically consistent with V * I within tolerance."""
        expected_power = self.voltage * self.current
        divergence = abs(self.power - expected_power)
        if divergence > limits.POWER_CONSISTENCY_TOLERANCE_W:
            raise ValueError(
                f"Power value ({self.power:.2f}W) is physically inconsistent with "
                f"V*I ({self.voltage:.2f}V * {self.current:.2f}A = {expected_power:.2f}W, "
                f"delta {divergence:.2f}W > tolerance {limits.POWER_CONSISTENCY_TOLERANCE_W}W)"
            )
        return self


class TelemetryResponse(BaseModel):
    """Successful Telemetry Ingestion Response Schema."""

    status: str = Field(default="accepted", examples=["accepted"])
    device_id: str = Field(..., examples=["motor_001"])
    received_at: str = Field(..., examples=["2026-10-08T18:00:00.123456Z"])
    telemetry_id: int = Field(..., examples=[1])


class TelemetryRecordResponse(BaseModel):
    """Stored Machine Telemetry Record Schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique record sequence ID.")
    device_id: str = Field(..., description="Unique machine edge node identifier.")
    timestamp: datetime = Field(..., description="Sensor acquisition timestamp in UTC.")
    is_mock: bool = Field(..., description="Flag denoting whether reading originates from mock bench mode.")

    temperature: float = Field(..., description="Stator/casing surface temperature in degrees Celsius.")
    accel_x: float = Field(..., description="X-axis acceleration in g.")
    accel_y: float = Field(..., description="Y-axis acceleration in g.")
    accel_z: float = Field(..., description="Z-axis acceleration in g.")
    gyro_x: float = Field(..., description="X-axis angular velocity in deg/s.")
    gyro_y: float = Field(..., description="Y-axis angular velocity in deg/s.")
    gyro_z: float = Field(..., description="Z-axis angular velocity in deg/s.")

    current: float = Field(..., description="Operating current in Amperes.")
    voltage: float = Field(..., description="Bus supply voltage in Volts.")
    power: float = Field(..., description="Electrical power in Watts.")
    rpm: float = Field(..., description="Rotor shaft speed in RPM.")
    created_at: datetime = Field(..., description="Record ingestion timestamp in UTC.")


class HistoricalTelemetryResponse(BaseModel):
    """Paginated Historical Telemetry Response Schema."""

    device_id: str = Field(..., description="Queried machine edge node identifier.")
    hours_queried: float = Field(..., description="Duration of requested historical window in hours.")
    start_time: datetime = Field(..., description="Beginning of query time window.")
    end_time: datetime = Field(..., description="End of query time window.")
    limit: int = Field(..., description="Maximum records requested per page.")
    count: int = Field(..., description="Number of telemetry records returned in this page.")
    has_more: bool = Field(..., description="True if subsequent records exist in the time window.")
    next_cursor: Optional[str] = Field(None, description="Opaque pagination cursor to retrieve next page.")
    items: List[TelemetryRecordResponse] = Field(..., description="Chronologically sorted telemetry records.")
