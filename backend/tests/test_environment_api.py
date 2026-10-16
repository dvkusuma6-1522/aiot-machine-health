"""
Automated Test Suite for Environmental Telemetry API, Storage, and Queries (Phase 2).

Verifies Pydantic v2 validation limits, rejection of NaN/Inf, null sensor preservation,
dual endpoint ingestion (/api/v1/environment/telemetry and /api/v1/telemetry),
database persistence in environment_readings, latest query, cursor-based pagination,
device isolation, and statistical summary aggregations.
"""

import json
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import patch
from app.models.environment import EnvironmentReading


@pytest.fixture
def valid_env_payload():
    """Returns a valid dictionary representing ESP32 environmental telemetry."""
    return {
        "device_id": "env_node_001",
        "timestamp": "2026-10-13T16:00:00Z",
        "is_mock": False,
        "temperature_c": 24.5,
        "humidity_percent": 58.2,
        "mq135_raw": 1420.0,
        "mq135_voltage": 1.14,
        "ir_count": 12,
        "ultrasonic_distance_cm": 45.0,
        "bin_fill_percent": 55.0,
        "sensor_status": {
            "dht22": "OK",
            "mq135": "OK",
            "ir": "OK",
            "ultrasonic": "OK",
        },
    }


# ------------------------------------------------------------------------------
# 1. INGESTION & PERSISTENCE TESTS
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valid_environmental_telemetry_dedicated_endpoint(client: AsyncClient, valid_env_payload):
    """Test 1: Valid environmental telemetry is accepted by POST /api/v1/environment/telemetry."""
    response = await client.post("/api/v1/environment/telemetry", json=valid_env_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "accepted"
    assert data["device_id"] == "env_node_001"
    assert "telemetry_id" in data
    assert "received_at" in data


@pytest.mark.asyncio
async def test_valid_environmental_telemetry_shared_endpoint(client: AsyncClient, valid_env_payload):
    """Test 2: Environmental telemetry sent to POST /api/v1/telemetry is correctly discriminated and accepted."""
    response = await client.post("/api/v1/telemetry", json=valid_env_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "accepted"
    assert data["device_id"] == "env_node_001"
    assert "telemetry_id" in data


@pytest.mark.asyncio
async def test_environmental_telemetry_persisted_correctly(
    client: AsyncClient, db_session: AsyncSession, valid_env_payload
):
    """Test 3: Environmental telemetry is accurately saved in environment_readings table."""
    response = await client.post("/api/v1/environment/telemetry", json=valid_env_payload)
    assert response.status_code == 201
    telemetry_id = response.json()["telemetry_id"]

    result = await db_session.execute(
        select(EnvironmentReading).where(EnvironmentReading.id == telemetry_id)
    )
    reading = result.scalar_one_or_none()
    assert reading is not None
    assert reading.device_id == "env_node_001"
    assert reading.temperature_c == 24.5
    assert reading.humidity_percent == 58.2
    assert reading.mq135_raw == 1420.0
    assert reading.mq135_voltage == 1.14
    assert reading.ir_count == 12
    assert reading.ultrasonic_distance_cm == 45.0
    assert reading.bin_fill_percent == 55.0
    assert reading.is_mock is False
    assert reading.sensor_status["dht22"] == "OK"


@pytest.mark.asyncio
async def test_null_sensor_measurements_preserved_without_zero_conversion(
    client: AsyncClient, db_session: AsyncSession, valid_env_payload
):
    """Test 4: Disconnected sensors report null, which MUST NOT be silently converted to 0.0."""
    payload = dict(valid_env_payload)
    payload["temperature_c"] = None
    payload["humidity_percent"] = None
    payload["mq135_voltage"] = None
    payload["ir_count"] = None
    payload["ultrasonic_distance_cm"] = None
    payload["bin_fill_percent"] = None
    payload["sensor_status"] = {"dht22": "DISCONNECTED", "mq135": "DISCONNECTED"}

    response = await client.post("/api/v1/environment/telemetry", json=payload)
    assert response.status_code == 201
    telemetry_id = response.json()["telemetry_id"]

    result = await db_session.execute(
        select(EnvironmentReading).where(EnvironmentReading.id == telemetry_id)
    )
    reading = result.scalar_one()
    assert reading.temperature_c is None
    assert reading.humidity_percent is None
    assert reading.mq135_voltage is None
    assert reading.ir_count is None
    assert reading.ultrasonic_distance_cm is None
    assert reading.bin_fill_percent is None


# ------------------------------------------------------------------------------
# 2. VALIDATION & ERROR HANDLING TESTS
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_device_id_rejected(client: AsyncClient, valid_env_payload):
    """Test 5: Payload without device_id must be rejected with 422."""
    payload = dict(valid_env_payload)
    del payload["device_id"]
    response = await client.post("/api/v1/environment/telemetry", json=payload)
    assert response.status_code == 422
    assert response.json()["status"] == "error"


@pytest.mark.asyncio
async def test_invalid_temperature_rejected(client: AsyncClient, valid_env_payload):
    """Test 6: Out-of-range temperature (> 85C or < -40C) must be rejected with 422."""
    payload = dict(valid_env_payload)
    payload["temperature_c"] = 125.0
    response = await client.post("/api/v1/environment/telemetry", json=payload)
    assert response.status_code == 422
    assert "exceeds sensor validation limits" in str(response.json())


@pytest.mark.asyncio
async def test_invalid_humidity_rejected(client: AsyncClient, valid_env_payload):
    """Test 7: Out-of-range humidity (> 100% or < 0%) must be rejected with 422."""
    payload = dict(valid_env_payload)
    payload["humidity_percent"] = 105.0
    response = await client.post("/api/v1/environment/telemetry", json=payload)
    assert response.status_code == 422
    assert "exceeds physical bounds" in str(response.json())


@pytest.mark.asyncio
async def test_negative_ir_count_rejected(client: AsyncClient, valid_env_payload):
    """Test 8: Negative IR pulse count must be rejected with 422."""
    payload = dict(valid_env_payload)
    payload["ir_count"] = -3
    response = await client.post("/api/v1/environment/telemetry", json=payload)
    assert response.status_code == 422
    assert "cannot be negative" in str(response.json())


@pytest.mark.asyncio
async def test_invalid_bin_fill_percentage_rejected(client: AsyncClient, valid_env_payload):
    """Test 9: Bin fill percentage outside 0-100% must be rejected with 422."""
    payload = dict(valid_env_payload)
    payload["bin_fill_percent"] = 150.0
    response = await client.post("/api/v1/environment/telemetry", json=payload)
    assert response.status_code == 422
    assert "exceeds valid range" in str(response.json())


@pytest.mark.asyncio
async def test_invalid_mq135_voltage_rejected(client: AsyncClient, valid_env_payload):
    """Test 10: MQ135 voltage outside 0.0V-5.0V must be rejected with 422."""
    payload = dict(valid_env_payload)
    payload["mq135_voltage"] = 7.5
    response = await client.post("/api/v1/environment/telemetry", json=payload)
    assert response.status_code == 422
    assert "exceeds physical bounds" in str(response.json())


@pytest.mark.asyncio
async def test_nan_rejected_in_environmental_telemetry(client: AsyncClient, valid_env_payload):
    """Test 11: Illegal NaN float value must be rejected with 422."""
    payload = dict(valid_env_payload)
    payload["temperature_c"] = float("nan")
    raw_body = json.dumps(payload, allow_nan=True)
    response = await client.post(
        "/api/v1/environment/telemetry",
        content=raw_body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["status"] == "error"


@pytest.mark.asyncio
async def test_infinity_rejected_in_environmental_telemetry(client: AsyncClient, valid_env_payload):
    """Test 12: Illegal Infinite float value must be rejected with 422."""
    payload = dict(valid_env_payload)
    payload["mq135_voltage"] = float("inf")
    raw_body = json.dumps(payload, allow_nan=True)
    response = await client.post(
        "/api/v1/environment/telemetry",
        content=raw_body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["status"] == "error"


@pytest.mark.asyncio
async def test_invalid_timestamp_rejected(client: AsyncClient, valid_env_payload):
    """Test 13: Unparseable timestamp string must be rejected with 422."""
    payload = dict(valid_env_payload)
    payload["timestamp"] = "NOT_A_TIMESTAMP"
    response = await client.post("/api/v1/environment/telemetry", json=payload)
    assert response.status_code == 422
    assert response.json()["status"] == "error"


@pytest.mark.asyncio
async def test_database_failure_handled_cleanly_environment(client: AsyncClient, valid_env_payload):
    """Test 14: Unexpected database errors return 500 without leaking stack traces."""
    with patch(
        "app.services.environment_service.EnvironmentService.save_telemetry",
        side_effect=RuntimeError("Simulated DB fault"),
    ):
        response = await client.post("/api/v1/environment/telemetry", json=valid_env_payload)
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert data["code"] == "INTERNAL_SERVER_ERROR"
        assert "Simulated DB fault" not in data["message"]


# ------------------------------------------------------------------------------
# 3. LATEST, HISTORY & SUMMARY QUERY TESTS
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_latest_environment_telemetry(client: AsyncClient):
    """Test 15: Latest environmental observation query returns newest record."""
    now = datetime.now(timezone.utc)
    # Insert older record
    await client.post(
        "/api/v1/environment/telemetry",
        json={
            "device_id": "env_node_latest",
            "timestamp": (now - timedelta(minutes=10)).isoformat(),
            "temperature_c": 21.0,
            "humidity_percent": 50.0,
            "mq135_voltage": 1.0,
        },
    )
    # Insert newer record
    await client.post(
        "/api/v1/environment/telemetry",
        json={
            "device_id": "env_node_latest",
            "timestamp": now.isoformat(),
            "temperature_c": 26.5,
            "humidity_percent": 62.0,
            "mq135_voltage": 1.45,
        },
    )

    response = await client.get("/api/v1/environment/env_node_latest/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == "env_node_latest"
    assert data["temperature_c"] == 26.5
    assert data["humidity_percent"] == 62.0
    assert data["mq135_voltage"] == 1.45


@pytest.mark.asyncio
async def test_get_latest_not_found(client: AsyncClient):
    """Test 16: Querying latest for a nonexistent device returns 404."""
    response = await client.get("/api/v1/environment/nonexistent_device/latest")
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["code"] == "DEVICE_TELEMETRY_NOT_FOUND"


@pytest.mark.asyncio
async def test_environmental_history_time_window_and_ordering(client: AsyncClient):
    """Test 17: History queries filter by time window and return records in chronological order."""
    now = datetime.now(timezone.utc)
    device = "env_node_hist"

    # Out of window (3 hours ago)
    await client.post(
        "/api/v1/environment/telemetry",
        json={
            "device_id": device,
            "timestamp": (now - timedelta(hours=3)).isoformat(),
            "temperature_c": 19.0,
        },
    )
    # Inside window (30 mins ago)
    await client.post(
        "/api/v1/environment/telemetry",
        json={
            "device_id": device,
            "timestamp": (now - timedelta(minutes=30)).isoformat(),
            "temperature_c": 22.0,
        },
    )
    # Inside window (10 mins ago)
    await client.post(
        "/api/v1/environment/telemetry",
        json={
            "device_id": device,
            "timestamp": (now - timedelta(minutes=10)).isoformat(),
            "temperature_c": 23.5,
        },
    )

    # Query with hours=1.0
    response = await client.get(f"/api/v1/environment/{device}/history?hours=1.0")
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == device
    assert data["count"] == 2
    # Ensure chronological order (oldest first in list)
    temps = [item["temperature_c"] for item in data["items"]]
    assert temps == [22.0, 23.5]


@pytest.mark.asyncio
async def test_environmental_history_cursor_pagination(client: AsyncClient):
    """Test 18: Scalable cursor-based pagination returns complete contiguous pages."""
    now = datetime.now(timezone.utc)
    device = "env_node_pages"

    # Ingest 5 records
    for i in range(5):
        await client.post(
            "/api/v1/environment/telemetry",
            json={
                "device_id": device,
                "timestamp": (now - timedelta(minutes=20 - i * 2)).isoformat(),
                "temperature_c": 20.0 + i,
            },
        )

    # Page 1: limit=2
    res1 = await client.get(f"/api/v1/environment/{device}/history?hours=1.0&limit=2")
    assert res1.status_code == 200
    page1 = res1.json()
    assert page1["count"] == 2
    assert page1["has_more"] is True
    assert page1["next_cursor"] is not None

    # Page 2: with cursor
    cursor = page1["next_cursor"]
    res2 = await client.get(f"/api/v1/environment/{device}/history?hours=1.0&limit=2&cursor={cursor}")
    assert res2.status_code == 200
    page2 = res2.json()
    assert page2["count"] == 2
    assert page2["has_more"] is True

    # Page 3: final record
    cursor2 = page2["next_cursor"]
    res3 = await client.get(f"/api/v1/environment/{device}/history?hours=1.0&limit=2&cursor={cursor2}")
    assert res3.status_code == 200
    page3 = res3.json()
    assert page3["count"] == 1
    assert page3["has_more"] is False
    assert page3["next_cursor"] is None

    # Verify contiguous sequence
    all_temps = (
        [i["temperature_c"] for i in page1["items"]]
        + [i["temperature_c"] for i in page2["items"]]
        + [i["temperature_c"] for i in page3["items"]]
    )
    assert all_temps == [20.0, 21.0, 22.0, 23.0, 24.0]


@pytest.mark.asyncio
async def test_environmental_device_isolation(client: AsyncClient):
    """Test 19: Strict multi-node isolation ensures readings from node A do not leak into node B."""
    now = datetime.now(timezone.utc)
    await client.post(
        "/api/v1/environment/telemetry",
        json={"device_id": "node_alpha", "timestamp": now.isoformat(), "temperature_c": 25.0},
    )
    await client.post(
        "/api/v1/environment/telemetry",
        json={"device_id": "node_beta", "timestamp": now.isoformat(), "temperature_c": 30.0},
    )

    res_alpha = await client.get("/api/v1/environment/node_alpha/history?hours=1.0")
    assert res_alpha.status_code == 200
    assert res_alpha.json()["count"] == 1
    assert res_alpha.json()["items"][0]["device_id"] == "node_alpha"

    res_beta = await client.get("/api/v1/environment/node_beta/history?hours=1.0")
    assert res_beta.status_code == 200
    assert res_beta.json()["count"] == 1
    assert res_beta.json()["items"][0]["device_id"] == "node_beta"


@pytest.mark.asyncio
async def test_environmental_summary_calculations(client: AsyncClient):
    """Test 20: Summary statistics endpoint calculates accurate min, max, avg, and latest."""
    now = datetime.now(timezone.utc)
    device = "env_node_stats"

    readings = [
        {"temp": 20.0, "hum": 40.0, "gas_v": 1.0, "ir": 5, "fill": 20.0},
        {"temp": 25.0, "hum": 50.0, "gas_v": 1.5, "ir": 10, "fill": 40.0},
        {"temp": 30.0, "hum": 60.0, "gas_v": 2.0, "ir": 15, "fill": 60.0},
    ]

    for idx, r in enumerate(readings):
        await client.post(
            "/api/v1/environment/telemetry",
            json={
                "device_id": device,
                "timestamp": (now - timedelta(minutes=15 - idx * 5)).isoformat(),
                "temperature_c": r["temp"],
                "humidity_percent": r["hum"],
                "mq135_voltage": r["gas_v"],
                "ir_count": r["ir"],
                "bin_fill_percent": r["fill"],
            },
        )

    res = await client.get(f"/api/v1/environment/{device}/summary?hours=1.0")
    assert res.status_code == 200
    data = res.json()
    assert data["device_id"] == device
    assert data["total_records"] == 3

    temp_stats = data["metrics"]["temperature_c"]
    assert temp_stats["count"] == 3
    assert temp_stats["min"] == 20.0
    assert temp_stats["max"] == 30.0
    assert temp_stats["avg"] == 25.0
    assert temp_stats["latest"] == 30.0

    gas_stats = data["metrics"]["mq135_voltage"]
    assert gas_stats["min"] == 1.0
    assert gas_stats["max"] == 2.0
    assert gas_stats["avg"] == 1.5
    assert gas_stats["latest"] == 2.0


@pytest.mark.asyncio
async def test_empty_environmental_history_and_summary(client: AsyncClient):
    """Test 21: Querying history and summary for a device with zero records handles gracefully."""
    # Empty history
    res_hist = await client.get("/api/v1/environment/empty_device/history?hours=1.0")
    assert res_hist.status_code == 200
    hist_data = res_hist.json()
    assert hist_data["count"] == 0
    assert hist_data["has_more"] is False
    assert hist_data["items"] == []

    # Empty summary
    res_sum = await client.get("/api/v1/environment/empty_device/summary?hours=1.0")
    assert res_sum.status_code == 200
    sum_data = res_sum.json()
    assert sum_data["total_records"] == 0
    assert sum_data["metrics"]["temperature_c"]["count"] == 0
    assert sum_data["metrics"]["temperature_c"]["min"] is None
    assert sum_data["metrics"]["temperature_c"]["max"] is None
    assert sum_data["metrics"]["temperature_c"]["avg"] is None


# ------------------------------------------------------------------------------
# 4. PHASE 3 FIRMWARE COMPATIBILITY TESTS
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_esp32_phase3_firmware_real_payload_compatibility(client: AsyncClient, db_session: AsyncSession):
    """Test 22: Exact JSON payload generated by Phase 3 ESP32 firmware in Real Mode."""
    firmware_payload = {
        "device_id": "env_node_001",
        "timestamp": 1728835200000,  # Milliseconds epoch from ESP32
        "is_mock": False,
        "temperature_c": 24.8,
        "humidity_percent": 56.4,
        "mq135_raw": 1512.0,
        "mq135_voltage": 1.22,
        "ir_count": 14,
        "ultrasonic_distance_cm": 42.5,
        "bin_fill_percent": 63.9,
        "sensor_status": {
            "dht22": "OK",
            "mq135": "OK",
            "ir": "OK",
            "ultrasonic": "OK",
        },
    }
    response = await client.post("/api/v1/environment/telemetry", json=firmware_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "accepted"
    assert data["device_id"] == "env_node_001"

    # Verify database persistence
    result = await db_session.execute(
        select(EnvironmentReading).where(EnvironmentReading.id == data["telemetry_id"])
    )
    rec = result.scalar_one()
    assert rec.is_mock is False
    assert rec.temperature_c == 24.8
    assert rec.humidity_percent == 56.4
    assert rec.mq135_voltage == 1.22
    assert rec.ir_count == 14
    assert rec.ultrasonic_distance_cm == 42.5
    assert rec.bin_fill_percent == 63.9
    assert rec.sensor_status["dht22"] == "OK"


@pytest.mark.asyncio
async def test_esp32_phase3_firmware_mock_payload_compatibility(client: AsyncClient, db_session: AsyncSession):
    """Test 23: Exact JSON payload generated by Phase 3 ESP32 firmware in Demonstration Mode."""
    mock_payload = {
        "device_id": "env_node_001",
        "timestamp": 1728835205000,
        "is_mock": True,
        "temperature_c": 25.1,
        "humidity_percent": 57.3,
        "mq135_raw": 1480.0,
        "mq135_voltage": 1.25,
        "ir_count": 3,
        "ultrasonic_distance_cm": 50.0,
        "bin_fill_percent": 55.5,
        "sensor_status": {
            "dht22": "OK",
            "mq135": "OK",
            "ir": "OK",
            "ultrasonic": "OK",
        },
    }
    response = await client.post("/api/v1/environment/telemetry", json=mock_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "accepted"

    # Verify is_mock flag is correctly stored in DB
    result = await db_session.execute(
        select(EnvironmentReading).where(EnvironmentReading.id == data["telemetry_id"])
    )
    rec = result.scalar_one()
    assert rec.is_mock is True


@pytest.mark.asyncio
async def test_esp32_phase3_firmware_null_diagnostics_payload_compatibility(
    client: AsyncClient, db_session: AsyncSession
):
    """Test 24: Exact JSON payload emitted by Phase 3 ESP32 firmware when hardware probes fail."""
    failed_probes_payload = {
        "device_id": "env_node_001",
        "timestamp": 1728835210000,
        "is_mock": False,
        "temperature_c": None,
        "humidity_percent": None,
        "mq135_raw": None,
        "mq135_voltage": None,
        "ir_count": None,
        "ultrasonic_distance_cm": None,
        "bin_fill_percent": None,
        "sensor_status": {
            "dht22": "FAIL",
            "mq135": "FAIL",
            "ir": "FAIL",
            "ultrasonic": "FAIL",
        },
    }
    response = await client.post("/api/v1/environment/telemetry", json=failed_probes_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "accepted"

    result = await db_session.execute(
        select(EnvironmentReading).where(EnvironmentReading.id == data["telemetry_id"])
    )
    rec = result.scalar_one()
    assert rec.temperature_c is None
    assert rec.humidity_percent is None
    assert rec.mq135_voltage is None
    assert rec.ir_count is None
    assert rec.sensor_status["dht22"] == "FAIL"


@pytest.mark.asyncio
async def test_inject_demo_scenario_endpoint(client: AsyncClient, db_session: AsyncSession):
    """Test 25: POST /demo/scenario injects synthetic scenario labeled is_mock=True."""
    payload = {
        "scenario": "spike_mq135",
        "device_id": "demo_test_node",
        "n_samples": 20,
        "sample_interval_sec": 60,
        "clear_previous_demo": True,
    }
    response = await client.post("/api/v1/environment/demo/scenario", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["scenario"] == "spike_mq135"
    assert data["records_inserted"] == 20

    # Query latest to verify data in DB
    latest_res = await client.get("/api/v1/environment/demo_test_node/latest")
    assert latest_res.status_code == 200
    latest_data = latest_res.json()
    assert latest_data["device_id"] == "demo_test_node"
    assert latest_data["is_mock"] is True


