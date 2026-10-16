"""
SQLAlchemy ORM Models for Ingested Environmental Telemetry and ML Outputs.

Stores raw environmental physical observations (DHT22, MQ135, IR, HC-SR04)
in environment_readings, with reserved future analytical schemas in
environment_predictions and environment_anomalies.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Index,
    JSON,
)
from app.database.session import Base


class EnvironmentReading(Base):
    """
    Physical environmental telemetry captured from an ESP32 edge node.
    """

    __tablename__ = "environment_readings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    is_mock = Column(Boolean, default=False, nullable=False)

    # Ambient Climate Metrics (DHT22)
    temperature_c = Column(Float, nullable=True)
    humidity_percent = Column(Float, nullable=True)

    # Air Quality Metrics (MQ135 Gas Sensor)
    mq135_raw = Column(Float, nullable=True)
    mq135_voltage = Column(Float, nullable=True)

    # Traffic / Object Counter (IR Obstacle Sensor)
    ir_count = Column(Integer, nullable=True)

    # Smart Waste Monitoring (HC-SR04 Ultrasonic Sensor)
    ultrasonic_distance_cm = Column(Float, nullable=True)
    bin_fill_percent = Column(Float, nullable=True)

    # Sensor Diagnostics & Edge Health
    sensor_status = Column(JSON, nullable=True)

    # Ingestion Metadata
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_env_device_timestamp", "device_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<EnvironmentReading(id={self.id}, device={self.device_id}, "
            f"temp={self.temperature_c}C, hum={self.humidity_percent}%, "
            f"gas_v={self.mq135_voltage}V, fill={self.bin_fill_percent}%)>"
        )


class EnvironmentPrediction(Base):
    """
    Model forecast record for environmental time-series (e.g. 1-hour ahead MQ135).
    Reserved schema for future AI inference pipeline (Phase 4).
    """

    __tablename__ = "environment_predictions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Target & Forecast Horizon
    target_variable = Column(String(64), nullable=False)  # e.g., "mq135_voltage"
    horizon_minutes = Column(Integer, nullable=False, default=60)
    predicted_value = Column(Float, nullable=False)
    confidence_lower = Column(Float, nullable=True)
    confidence_upper = Column(Float, nullable=True)

    # Model Lineage
    model_name = Column(String(64), nullable=False, default="random_forest_regressor")
    model_version = Column(String(32), nullable=False, default="1.0.0")

    # Record Metadata
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_env_pred_device_timestamp", "device_id", "timestamp"),
        Index("ix_env_pred_lookup", "device_id", "target_variable", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<EnvironmentPrediction(id={self.id}, device={self.device_id}, "
            f"target={self.target_variable}, pred={self.predicted_value}, h={self.horizon_minutes}m)>"
        )


class EnvironmentAnomaly(Base):
    """
    Multivariate anomaly event record detected by Isolation Forest.
    Reserved schema for future AI inference pipeline (Phase 4).
    """

    __tablename__ = "environment_anomalies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Anomaly Detection Output
    anomaly_score = Column(Float, nullable=False)  # Raw isolation forest decision score
    is_anomaly = Column(Boolean, nullable=False, default=False)
    severity = Column(String(32), nullable=False, default="NORMAL")  # NORMAL, WARNING, CRITICAL
    affected_sensors = Column(JSON, nullable=True)  # e.g. ["mq135_voltage", "temperature_c"]
    explanation = Column(String(512), nullable=True)

    # Model Lineage
    model_name = Column(String(64), nullable=False, default="isolation_forest")
    model_version = Column(String(32), nullable=False, default="1.0.0")

    # Record Metadata
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_env_anom_device_timestamp", "device_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<EnvironmentAnomaly(id={self.id}, device={self.device_id}, "
            f"score={self.anomaly_score}, is_anom={self.is_anomaly}, sev={self.severity})>"
        )


class EnvironmentAlert(Base):
    """
    Environmental threshold and AI anomaly alert records dispatched to Blynk / local dashboard.
    """

    __tablename__ = "environment_alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    alert_type = Column(String(64), nullable=False)  # HIGH_MQ135, HIGH_TEMP, BIN_FULL, SENSOR_DISCONNECT, AI_ANOMALY
    severity = Column(String(16), nullable=False, default="WARNING")  # WARNING, CRITICAL
    message = Column(String(512), nullable=False)
    metric_value = Column(Float, nullable=True)
    threshold_value = Column(Float, nullable=True)

    is_mock = Column(Boolean, nullable=False, default=False)
    blynk_delivered = Column(Boolean, nullable=False, default=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_env_alert_device_timestamp", "device_id", "timestamp"),
        Index("ix_env_alert_type", "device_id", "alert_type", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<EnvironmentAlert(id={self.id}, device={self.device_id}, "
            f"type={self.alert_type}, sev={self.severity}, blynk={self.blynk_delivered})>"
        )

