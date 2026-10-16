"""
Pydantic v2 Schemas for Environmental Telemetry Ingestion, Queries, and Summaries.

Enforces strict type validation, physical range boundaries, rejection of NaN/Inf,
timestamp canonicalization, and non-zero preservation of null sensor measurements.
"""

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    ConfigDict,
)
from app.core.config import settings

env_limits = settings.env_limits


class EnvironmentTelemetryPayload(BaseModel):
    """
    Ingested Environmental Telemetry Payload conforming to ESP32 DevKit specifications.
    Captures DHT22, MQ135, IR obstacle, and HC-SR04 ultrasonic sensors.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    device_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique identifier for the environmental edge node.",
        examples=["env_node_001"],
    )

    timestamp: datetime = Field(
        ...,
        description="Timestamp as ISO-8601 string or numeric epoch seconds/milliseconds.",
        examples=["2026-10-13T16:00:00Z", 1728835200],
    )

    is_mock: Optional[bool] = Field(
        default=False,
        description="Denotes whether payload originates from simulated test bench data.",
    )

    # Ambient Climate (DHT22)
    temperature_c: Optional[float] = Field(
        default=None,
        description="Ambient temperature in degrees Celsius (-40.0C to 85.0C).",
        examples=[24.5],
    )

    humidity_percent: Optional[float] = Field(
        default=None,
        description="Relative ambient humidity percentage (0.0% to 100.0%).",
        examples=[58.2],
    )

    # Air Quality (MQ135)
    mq135_raw: Optional[float] = Field(
        default=None,
        description="Raw 12-bit ADC integer/float reading from ESP32 ADC1 (0.0 to 4095.0).",
        examples=[1420.0],
    )

    mq135_voltage: Optional[float] = Field(
        default=None,
        description="Sensor analog output voltage in Volts (0.0V to 5.0V).",
        examples=[1.14],
    )

    # Traffic / People Counting (IR Obstacle Sensor)
    ir_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Cumulative or window object pulse count (non-negative integer).",
        examples=[12],
    )

    # Smart Waste Monitoring (HC-SR04 Ultrasonic)
    ultrasonic_distance_cm: Optional[float] = Field(
        default=None,
        description="Measured echo distance to waste surface in cm (0.0 cm to 500.0 cm).",
        examples=[45.0],
    )

    bin_fill_percent: Optional[float] = Field(
        default=None,
        description="Calculated waste bin fill percentage (0.0% to 100.0%).",
        examples=[55.0],
    )

    # Edge Diagnostics
    sensor_status: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Hardware health status flags reported by edge sensors.",
        examples=[{"dht22": "OK", "mq135": "OK", "ir": "OK", "ultrasonic": "OK"}],
    )

    # --------------------------------------------------------------------------
    # FIELD VALIDATORS: NAN / INF REJECTION
    # --------------------------------------------------------------------------

    @field_validator(
        "temperature_c",
        "humidity_percent",
        "mq135_raw",
        "mq135_voltage",
        "ultrasonic_distance_cm",
        "bin_fill_percent",
        mode="before",
    )
    @classmethod
    def reject_nan_and_inf(cls, value: Any, info) -> Optional[float]:
        """Reject NaN and infinite float values before numerical evaluation."""
        if value is None:
            return None
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(
                f"Field '{info.field_name}' must be a numeric float or null, got {type(value).__name__}"
            )
        float_val = float(value)
        if math.isnan(float_val):
            raise ValueError(f"Field '{info.field_name}' contains illegal NaN value")
        if math.isinf(float_val):
            raise ValueError(f"Field '{info.field_name}' contains illegal infinite value")
        return float_val

    @field_validator("ir_count", mode="before")
    @classmethod
    def validate_ir_count_type(cls, value: Any) -> Optional[int]:
        """Validate non-negative integer for IR count and reject NaN / Inf / float."""
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError("Field 'ir_count' must be an integer, got bool")
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                raise ValueError("Field 'ir_count' cannot be NaN or infinite")
            if not value.is_integer():
                raise ValueError(f"Field 'ir_count' must be an integer, got non-integral float {value}")
            value = int(value)
        if not isinstance(value, int):
            raise ValueError(f"Field 'ir_count' must be an integer, got {type(value).__name__}")
        if value < env_limits.IR_COUNT_MIN:
            raise ValueError(f"Field 'ir_count' cannot be negative ({value} < {env_limits.IR_COUNT_MIN})")
        if value > env_limits.IR_COUNT_MAX:
            raise ValueError(f"Field 'ir_count' exceeds maximum threshold ({value} > {env_limits.IR_COUNT_MAX})")
        return value

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
            if value < 0:
                raise ValueError("Numeric timestamp cannot be negative")
            # If timestamp is in milliseconds (> 1e11), convert to seconds
            if value > 1e11:
                secs = value / 1000.0
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

    @field_validator("temperature_c")
    @classmethod
    def validate_temperature_bounds(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < env_limits.TEMP_MIN_C or v > env_limits.TEMP_MAX_C):
            raise ValueError(
                f"Temperature {v}C exceeds sensor validation limits "
                f"[{env_limits.TEMP_MIN_C}C, {env_limits.TEMP_MAX_C}C]"
            )
        return v

    @field_validator("humidity_percent")
    @classmethod
    def validate_humidity_bounds(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < env_limits.HUMIDITY_MIN_PCT or v > env_limits.HUMIDITY_MAX_PCT):
            raise ValueError(
                f"Humidity {v}% exceeds physical bounds "
                f"[{env_limits.HUMIDITY_MIN_PCT}%, {env_limits.HUMIDITY_MAX_PCT}%]"
            )
        return v

    @field_validator("mq135_raw")
    @classmethod
    def validate_mq135_raw_bounds(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < env_limits.MQ135_RAW_MIN or v > env_limits.MQ135_RAW_MAX):
            raise ValueError(
                f"MQ135 raw reading {v} exceeds 12-bit ADC limits "
                f"[{env_limits.MQ135_RAW_MIN}, {env_limits.MQ135_RAW_MAX}]"
            )
        return v

    @field_validator("mq135_voltage")
    @classmethod
    def validate_mq135_voltage_bounds(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < env_limits.MQ135_VOLTAGE_MIN_V or v > env_limits.MQ135_VOLTAGE_MAX_V):
            raise ValueError(
                f"MQ135 voltage {v}V exceeds physical bounds "
                f"[{env_limits.MQ135_VOLTAGE_MIN_V}V, {env_limits.MQ135_VOLTAGE_MAX_V}V]"
            )
        return v

    @field_validator("ultrasonic_distance_cm")
    @classmethod
    def validate_distance_bounds(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < env_limits.DISTANCE_MIN_CM or v > env_limits.DISTANCE_MAX_CM):
            raise ValueError(
                f"Ultrasonic distance {v} cm exceeds envelope "
                f"[{env_limits.DISTANCE_MIN_CM} cm, {env_limits.DISTANCE_MAX_CM} cm]"
            )
        return v

    @field_validator("bin_fill_percent")
    @classmethod
    def validate_bin_fill_bounds(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < env_limits.BIN_FILL_MIN_PCT or v > env_limits.BIN_FILL_MAX_PCT):
            raise ValueError(
                f"Bin fill percentage {v}% exceeds valid range "
                f"[{env_limits.BIN_FILL_MIN_PCT}%, {env_limits.BIN_FILL_MAX_PCT}%]"
            )
        return v


class EnvironmentTelemetryResponse(BaseModel):
    """Successful Environmental Telemetry Ingestion Response Schema."""

    status: str = Field(default="accepted", examples=["accepted"])
    device_id: str = Field(..., examples=["env_node_001"])
    received_at: str = Field(..., examples=["2026-10-13T16:00:00.123456Z"])
    telemetry_id: int = Field(..., examples=[1])


class EnvironmentRecordResponse(BaseModel):
    """Stored Environmental Telemetry Record Schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique record sequence ID.")
    device_id: str = Field(..., description="Unique environmental edge node identifier.")
    timestamp: datetime = Field(..., description="Sensor acquisition timestamp in UTC.")
    is_mock: bool = Field(..., description="Flag denoting whether reading originates from mock bench mode.")

    temperature_c: Optional[float] = Field(None, description="Ambient temperature in degrees Celsius.")
    humidity_percent: Optional[float] = Field(None, description="Relative humidity percentage.")
    mq135_raw: Optional[float] = Field(None, description="Raw 12-bit ADC count.")
    mq135_voltage: Optional[float] = Field(None, description="MQ135 air quality analog voltage in Volts.")
    ir_count: Optional[int] = Field(None, description="IR object/traffic count.")
    ultrasonic_distance_cm: Optional[float] = Field(None, description="Ultrasonic echo distance in cm.")
    bin_fill_percent: Optional[float] = Field(None, description="Waste bin fill percentage.")
    sensor_status: Optional[Dict[str, Any]] = Field(None, description="Sensor status flags.")
    created_at: datetime = Field(..., description="Record ingestion timestamp in UTC.")


class HistoricalEnvironmentResponse(BaseModel):
    """Paginated Historical Environmental Telemetry Response Schema."""

    device_id: str = Field(..., description="Queried environmental edge node identifier.")
    hours_queried: float = Field(..., description="Duration of requested historical window in hours.")
    start_time: datetime = Field(..., description="Beginning of query time window.")
    end_time: datetime = Field(..., description="End of query time window.")
    limit: int = Field(..., description="Maximum records requested per page.")
    count: int = Field(..., description="Number of environmental records returned in this page.")
    has_more: bool = Field(..., description="True if subsequent records exist in the time window.")
    next_cursor: Optional[str] = Field(None, description="Opaque pagination cursor to retrieve next page.")
    items: List[EnvironmentRecordResponse] = Field(..., description="Chronologically sorted environmental records.")


class MetricStats(BaseModel):
    """Summary statistics for an individual numerical sensor metric."""

    count: int = Field(0, description="Total non-null samples in query window.")
    min: Optional[float] = Field(None, description="Minimum observed value.")
    max: Optional[float] = Field(None, description="Maximum observed value.")
    avg: Optional[float] = Field(None, description="Arithmetic mean observed value.")
    latest: Optional[float] = Field(None, description="Most recent observed value in window.")


class EnvironmentSummaryResponse(BaseModel):
    """Aggregated Statistical Summary for an Environmental Node."""

    device_id: str = Field(..., description="Queried environmental edge node identifier.")
    hours_queried: float = Field(..., description="Lookback window duration in hours.")
    start_time: datetime = Field(..., description="Beginning of lookback window.")
    end_time: datetime = Field(..., description="End of lookback window.")
    total_records: int = Field(..., description="Total records found in window.")
    metrics: Dict[str, MetricStats] = Field(
        ...,
        description="Dictionary of sensor metrics containing min, max, avg, latest, and count.",
    )


class DemoScenarioRequest(BaseModel):
    """Request payload to inject a controlled synthetic demonstration scenario."""

    scenario: str = Field(
        default="normal",
        description="Scenario type: normal, increasing_mq135, spike_mq135, multivariate_anomaly, or longitudinal_forecasting",
    )
    device_id: str = Field(
        default="env_node_demo",
        min_length=1,
        max_length=64,
        description="Device ID to attach synthetic telemetry to.",
    )
    n_samples: int = Field(
        default=60,
        ge=5,
        le=500,
        description="Number of synthetic samples to generate.",
    )
    sample_interval_sec: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Time delta in seconds between adjacent synthetic points.",
    )
    clear_previous_demo: bool = Field(
        default=True,
        description="Whether to clear previous mock records for this device before inserting.",
    )


class DemoScenarioResponse(BaseModel):
    """Response returned upon injecting synthetic demo scenario."""

    status: str = Field("SUCCESS", description="Operation status.")
    scenario: str = Field(..., description="Injected scenario name.")
    device_id: str = Field(..., description="Device ID.")
    records_inserted: int = Field(..., description="Number of records inserted.")
    start_time: datetime = Field(..., description="Start timestamp of injected series.")
    end_time: datetime = Field(..., description="End timestamp of injected series.")
    message: str = Field(..., description="Human-readable outcome description.")


class AlertItemResponse(BaseModel):
    """Individual environmental threshold or AI anomaly alert record."""

    id: int = Field(..., description="Unique alert event ID.")
    device_id: str = Field(..., description="Originating edge node identifier.")
    timestamp: datetime = Field(..., description="Timestamp of alert generation.")
    alert_type: str = Field(..., description="Classification category of the alert condition.")
    severity: str = Field(..., description="Alert severity: WARNING or CRITICAL.")
    message: str = Field(..., description="Human-readable condition and guidance message.")
    metric_value: Optional[float] = Field(None, description="Observed numerical sensor reading.")
    threshold_value: Optional[float] = Field(None, description="Configured trigger threshold.")
    is_mock: bool = Field(False, description="True if alert originated from demonstration scenario.")
    blynk_delivered: bool = Field(False, description="True if successfully dispatched to Blynk IoT Cloud.")
    created_at: datetime = Field(..., description="Database persistence timestamp.")


class AlertListResponse(BaseModel):
    """Query response containing list of historical alerts."""

    device_id: str = Field(..., description="Target device identifier.")
    hours_analyzed: float = Field(..., description="Query lookback duration in hours.")
    count: int = Field(..., description="Total alert events returned.")
    items: List[AlertItemResponse] = Field(..., description="Chronological sequence of alert events.")


class BlynkStatusResponse(BaseModel):
    """Blynk Cloud integration and alert service operational status."""

    blynk_configured: bool = Field(..., description="True if valid BLYNK_AUTH_TOKEN is configured.")
    blynk_enabled: bool = Field(..., description="True if Blynk synchronization is active.")
    server_url: str = Field(..., description="Blynk Cloud REST endpoint.")
    active_cooldowns: Dict[str, float] = Field(..., description="Remaining cooldown lockouts in seconds by alert key.")
    thresholds: Dict[str, float] = Field(..., description="Configured alert threshold limits.")
    virtual_pins: Dict[str, str] = Field(..., description="Blynk virtual datastream mapping documentation.")


class TestAlertRequest(BaseModel):
    """Payload to trigger an explicit demonstration alert."""

    device_id: str = Field(default="env_node_001", description="Device ID.")
    alert_type: str = Field(default="HIGH_MQ135", description="Alert category.")
    metric_value: float = Field(default=2.45, description="Simulated sensor reading.")
    severity: str = Field(default="WARNING", description="Severity level.")
    message: Optional[str] = Field(default=None, description="Custom notification text.")

