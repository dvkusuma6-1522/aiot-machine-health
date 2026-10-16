"""
Application Configuration and Physical Validation Limits.

Defines environment-driven settings via Pydantic Settings and centralizes
physical validation boundaries for sensor telemetry ingestion.
"""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PhysicalValidationLimits:
    """
    Centralized Physical Validation Boundaries for Ingested Sensor Data.

    IMPORTANT ARCHITECTURAL DISTINCTION:
    These limits are purely data-integrity sanity boundaries designed to catch
    sensor disconnections, ADC hardware bit-rot, bus noise, or malformed packets.
    They are STRICTLY NOT machine-fault thresholds or AI anomaly alarms.
    Machine health analysis and condition monitoring thresholds belong exclusively
    to downstream analytics and ML layers.
    """

    # DS18B20 Temperature Sensor: Physical limit is -55C to +125C.
    # Safe validation envelope for industrial laboratory testing: -20C to +130C.
    TEMP_MIN_C: float = -20.0
    TEMP_MAX_C: float = 130.0

    # INA219 / ACS712 Current Sensor: Operating current must be non-negative.
    # Laboratory DC motor bench limit is 10.0A.
    CURRENT_MIN_A: float = 0.0
    CURRENT_MAX_A: float = 10.0

    # Bus Voltage: Motor DC power rail must be non-negative.
    # INA219 max bus rating is 26V (or 32V calibration).
    VOLTAGE_MIN_V: float = 0.0
    VOLTAGE_MAX_V: float = 35.0

    # A3144 Hall Effect Sensor: Rotational speed must be non-negative.
    # Benchmark ceiling for small high-speed DC test motors.
    RPM_MIN: float = 0.0
    RPM_MAX: float = 10000.0

    # MPU-6050 Accelerometer: Hardware full-scale dynamic range (+/- 16g).
    ACCEL_MIN_G: float = -16.0
    ACCEL_MAX_G: float = 16.0

    # MPU-6050 Gyroscope: Hardware full-scale range (+/- 2000 deg/s).
    GYRO_MIN_DEG_S: float = -2000.0
    GYRO_MAX_DEG_S: float = 2000.0

    # Power: DC electrical power P = V * I must be non-negative.
    POWER_MIN_W: float = 0.0
    POWER_MAX_W: float = 350.0

    # Permitted physical divergence between P and V * I (watts)
    # Allows for power factor and ADC sampling synchronization delta.
    POWER_CONSISTENCY_TOLERANCE_W: float = 10.0


class EnvironmentalValidationLimits:
    """
    Physical Validation Boundaries for Ingested Environmental Sensor Data.

    Sanity boundaries to detect disconnected probes, 12-bit ADC overflow,
    bus faults, and malformed network packets.
    """

    # DHT22 Temperature Sensor: -40°C to +80°C operating envelope.
    TEMP_MIN_C: float = -40.0
    TEMP_MAX_C: float = 85.0

    # DHT22 Relative Humidity: 0.0% to 100.0%.
    HUMIDITY_MIN_PCT: float = 0.0
    HUMIDITY_MAX_PCT: float = 100.0

    # MQ135 Air Quality Sensor 12-bit ADC raw count (ESP32 ADC1).
    MQ135_RAW_MIN: float = 0.0
    MQ135_RAW_MAX: float = 4095.0

    # MQ135 Analog Voltage: 0.0V to 5.0V (attenuated to 3.33V maximum on ESP32 pin).
    MQ135_VOLTAGE_MIN_V: float = 0.0
    MQ135_VOLTAGE_MAX_V: float = 5.0

    # IR Object / People Counter: Non-negative integer count.
    IR_COUNT_MIN: int = 0
    IR_COUNT_MAX: int = 1_000_000_000

    # HC-SR04 Ultrasonic Distance: 0.0 cm to 500.0 cm range envelope.
    DISTANCE_MIN_CM: float = 0.0
    DISTANCE_MAX_CM: float = 500.0

    # Ultrasonic Waste Bin Fill Percentage: 0.0% to 100.0%.
    BIN_FILL_MIN_PCT: float = 0.0
    BIN_FILL_MAX_PCT: float = 100.0


class Settings(BaseSettings):
    """Application Settings loaded from environment or .env file."""

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "AIoT Machine Health & Environmental Monitoring System"
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "aiot-secret-key-change-in-production"

    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database: Default to SQLite for local development, asyncpg for PostgreSQL
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/machine_health.db"
    DB_ECHO: bool = False

    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    # Sensor validation limits
    limits: PhysicalValidationLimits = Field(default_factory=PhysicalValidationLimits)
    env_limits: EnvironmentalValidationLimits = Field(default_factory=EnvironmentalValidationLimits)

    # Blynk IoT Cloud Configuration
    BLYNK_AUTH_TOKEN: Optional[str] = None
    BLYNK_SERVER_URL: str = "https://blynk.cloud/external/api"
    BLYNK_ENABLED: bool = False

    # Environmental Alert Thresholds & Cooldowns
    ALERT_MQ135_THRESHOLD_VOLTS: float = 2.0
    ALERT_TEMP_HIGH_C: float = 35.0
    ALERT_BIN_FULL_PERCENT: float = 80.0
    ALERT_COOLDOWN_SECONDS: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
