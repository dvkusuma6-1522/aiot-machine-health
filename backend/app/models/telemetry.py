"""
SQLAlchemy ORM Model for Ingested Sensor Telemetry.

Stores raw physical sensor readings without storing AI predictions (which belong
to subsequent analytical phases).
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
)
from app.database.session import Base


class SensorReading(Base):
    """
    Physical sensor telemetry record captured from an edge machine.
    """

    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    is_mock = Column(Boolean, default=False, nullable=False)

    # Thermal Metric (DS18B20)
    temperature = Column(Float, nullable=False)

    # 3-Axis Acceleration (MPU-6050 in g)
    accel_x = Column(Float, nullable=False)
    accel_y = Column(Float, nullable=False)
    accel_z = Column(Float, nullable=False)

    # 3-Axis Angular Velocity (MPU-6050 in deg/s)
    gyro_x = Column(Float, nullable=False)
    gyro_y = Column(Float, nullable=False)
    gyro_z = Column(Float, nullable=False)

    # Electrical Power Metrics (INA219: Amperes, Volts, Watts)
    current = Column(Float, nullable=False)
    voltage = Column(Float, nullable=False)
    power = Column(Float, nullable=False)

    # Rotational Speed (A3144 Hall Effect: RPM)
    rpm = Column(Float, nullable=False)

    # Record Metadata
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_sensor_device_timestamp", "device_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<SensorReading(id={self.id}, device={self.device_id}, temp={self.temperature}C, rpm={self.rpm})>"
