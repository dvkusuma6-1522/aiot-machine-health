"""
Automated Test Suite for Telemetry Ingestion API (Phase 3).

Verifies validation, physical bounds, persistence, error handling,
health checks, and ESP32 firmware compatibility.
"""

import json
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import patch
from app.models.telemetry import SensorReading


@pytest.fixture
def valid_telemetry_dict():
    """Returns a dictionary representing valid standard ISO telemetry."""
    return {
        "device_id": "motor_001",
        "timestamp": "2026-10-08T18:00:00Z",
        "is_mock": False,
        "temperature": 43.2,
        "accel_x": 0.12,
        "accel_y": 0.08,
        "accel_z": 1.04,
        "gyro_x": 0.1,
        "gyro_y": 0.2,
        "gyro_z": 0.3,
        "current": 1.12,
        "voltage": 11.8,
        "power": 13.216,  # 11.8V * 1.12A = 13.216W
        "rpm": 1498.0,
    }


# ------------------------------------------------------------------------------
# 1. POSITIVE INGESTION & PERSISTENCE TESTS
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valid_telemetry_accepted(client: AsyncClient, valid_telemetry_dict):
    """Test 1: Valid telemetry payload is accepted with 201 Created."""
    response = await client.post("/api/v1/telemetry", json=valid_telemetry_dict)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "accepted"
    assert data["device_id"] == "motor_001"
    assert "telemetry_id" in data
    assert "received_at" in data


@pytest.mark.asyncio
async def test_valid_telemetry_persisted(client: AsyncClient, db_session: AsyncSession, valid_telemetry_dict):
    """Test 10: Valid telemetry payload is accurately persisted into the database."""
    response = await client.post("/api/v1/telemetry", json=valid_telemetry_dict)
    assert response.status_code == 201
    telemetry_id = response.json()["telemetry_id"]

    # Verify directly from database
    result = await db_session.execute(select(SensorReading).where(SensorReading.id == telemetry_id))
    reading = result.scalar_one_or_none()
    assert reading is not None
    assert reading.device_id == "motor_001"
    assert reading.temperature == 43.2
    assert reading.accel_z == 1.04
    assert reading.current == 1.12
    assert reading.rpm == 1498.0
    assert reading.is_mock is False


@pytest.mark.asyncio
async def test_multiple_devices_submission(client: AsyncClient, db_session: AsyncSession, valid_telemetry_dict):
    """Test 11: Telemetry from multiple distinct edge machines is accepted and distinguished."""
    devices = ["motor_001", "motor_002", "chiller_pump_01"]
    for dev in devices:
        payload = dict(valid_telemetry_dict)
        payload["device_id"] = dev
        resp = await client.post("/api/v1/telemetry", json=payload)
        assert resp.status_code == 201
        assert resp.json()["device_id"] == dev

    result = await db_session.execute(select(SensorReading))
    readings = result.scalars().all()
    assert len(readings) == 3
    recorded_devices = {r.device_id for r in readings}
    assert recorded_devices == set(devices)


@pytest.mark.asyncio
async def test_esp32_phase2_payload_compatibility(client: AsyncClient, db_session: AsyncSession):
    """Test 13: Full compatibility with Phase 2 ESP32 firmware JSON payload."""
    esp32_payload = {
        "device_id": "motor_001",
        "timestamp": 1728410400000,  # Milliseconds epoch from MCU
        "is_mock": True,
        "sensor_status": {
            "mpu6050": True,
            "ds18b20": True,
            "ina219": True,
            "hall": True,
        },
        "temperature": 43.2,
        "accel_x": 0.12,
        "accel_y": 0.08,
        "accel_z": 1.04,
        "gyro_x": 0.1,
        "gyro_y": 0.2,
        "gyro_z": 0.3,
        "current": 1.12,
        "voltage": 11.8,
        "power": 13.2,
        "rpm": 1498.0,
    }
    response = await client.post("/api/v1/telemetry", json=esp32_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "accepted"
    assert data["device_id"] == "motor_001"

    # Verify is_mock flag was saved
    result = await db_session.execute(select(SensorReading).where(SensorReading.id == data["telemetry_id"]))
    reading = result.scalar_one()
    assert reading.is_mock is True


# ------------------------------------------------------------------------------
# 2. SCHEMA & VALIDATION REJECTION TESTS
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_device_id_rejected(client: AsyncClient, valid_telemetry_dict):
    """Test 2: Payload without device_id must be rejected (422)."""
    payload = dict(valid_telemetry_dict)
    del payload["device_id"]
    response = await client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == "error"
    assert data["code"] == "SCHEMA_VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_missing_sensor_field_rejected(client: AsyncClient, valid_telemetry_dict):
    """Test 3: Missing required sensor field (e.g., temperature) must be rejected (422)."""
    payload = dict(valid_telemetry_dict)
    del payload["temperature"]
    response = await client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 422
    assert response.json()["status"] == "error"


@pytest.mark.asyncio
async def test_invalid_temperature_type_rejected(client: AsyncClient, valid_telemetry_dict):
    """Test 4: Non-numeric temperature type must be rejected (422)."""
    payload = dict(valid_telemetry_dict)
    payload["temperature"] = "OVERHEATED_VERY_HOT"
    response = await client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 422
    assert response.json()["status"] == "error"


@pytest.mark.asyncio
async def test_negative_rpm_rejected(client: AsyncClient, valid_telemetry_dict):
    """Test 5: Physically impossible negative RPM must be rejected (422)."""
    payload = dict(valid_telemetry_dict)
    payload["rpm"] = -250.0
    response = await client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 422
    assert "violates non-negative rotational bounds" in str(response.json())


@pytest.mark.asyncio
async def test_negative_current_rejected(client: AsyncClient, valid_telemetry_dict):
    """Test 6: Physically impossible negative operating current must be rejected (422)."""
    payload = dict(valid_telemetry_dict)
    payload["current"] = -0.5
    response = await client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 422
    assert "violates non-negative physical boundary" in str(response.json())


@pytest.mark.asyncio
async def test_nan_rejected(client: AsyncClient, valid_telemetry_dict):
    """Test 7: Illegal NaN float value must be rejected (422)."""
    # Raw JSON string containing NaN
    payload = dict(valid_telemetry_dict)
    payload["temperature"] = float("nan")
    # Using json.dumps with allow_nan=True to format the raw payload
    raw_body = json.dumps(payload, allow_nan=True)
    response = await client.post(
        "/api/v1/telemetry",
        content=raw_body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["status"] == "error"


@pytest.mark.asyncio
async def test_infinity_rejected(client: AsyncClient, valid_telemetry_dict):
    """Test 8: Illegal Infinite float value must be rejected (422)."""
    payload = dict(valid_telemetry_dict)
    payload["accel_z"] = float("inf")
    raw_body = json.dumps(payload, allow_nan=True)
    response = await client.post(
        "/api/v1/telemetry",
        content=raw_body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["status"] == "error"


@pytest.mark.asyncio
async def test_invalid_timestamp_rejected(client: AsyncClient, valid_telemetry_dict):
    """Test 9: Malformed or unparseable timestamp string must be rejected (422)."""
    payload = dict(valid_telemetry_dict)
    payload["timestamp"] = "INVALID_TIMESTAMP_2026-99-99"
    response = await client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 422
    assert response.json()["status"] == "error"


# ------------------------------------------------------------------------------
# 3. FAULT INJECTION & HEALTH ENDPOINT TESTS
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_database_failure_handled_cleanly(client: AsyncClient, valid_telemetry_dict):
    """Test 12: Unexpected database exceptions return clean 500 error without leaking stack traces."""
    with patch(
        "app.services.telemetry_service.TelemetryService.save_telemetry",
        side_effect=RuntimeError("Simulated DB connection reset"),
    ):
        response = await client.post("/api/v1/telemetry", json=valid_telemetry_dict)
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert data["code"] == "INTERNAL_SERVER_ERROR"
        # Ensure raw DB connection error string or internal trace is not exposed
        assert "Simulated DB connection reset" not in data["message"]


@pytest.mark.asyncio
async def test_health_endpoints(client: AsyncClient):
    """Test 14: System health endpoint returns 200 OK and connected database."""
    # Test root /health
    resp1 = await client.get("/health")
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "ok"
    assert resp1.json()["database"] == "connected"

    # Test versioned /api/v1/health
    resp2 = await client.get("/api/v1/health")
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "ok"
    assert resp2.json()["database"] == "connected"
