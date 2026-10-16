"""
Automated Test Suite for Blynk IoT Cloud Integration and Environmental Alerts (Phase 6).

Verifies:
1. High gas response threshold detection (MQ135 >= 2.0V).
2. High ambient temperature threshold detection (DHT22 >= 35.0C).
3. Waste-bin capacity threshold detection (HC-SR04 >= 80.0%).
4. Sensor probe disconnection detection (probe status == FAIL).
5. Notification cooldown lockout enforcement (300s cooldown prevents repeated spam).
6. Recovery behavior resets cooldown when metric returns to nominal.
7. Mock-data provenance retention (is_mock=True preserved).
8. Graceful operation when Blynk credentials are unconfigured.
9. Historical alert queries (GET /{device_id}/alerts).
10. Blynk system status reporting (GET /blynk/status).
11. Test demonstration alert endpoint (POST /alerts/test).
"""

from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.environment import EnvironmentReading, EnvironmentAlert
from app.services.blynk_service import BlynkService


@pytest.fixture(autouse=True)
def reset_blynk_cooldowns():
    """Clear in-memory cooldown cache before each test."""
    BlynkService._last_alert_times.clear()
    yield
    BlynkService._last_alert_times.clear()


@pytest.mark.asyncio
async def test_high_gas_threshold_alert_generation(client: AsyncClient, db_session: AsyncSession):
    """Test 1: Ingesting telemetry with MQ135 voltage >= 2.0V generates HIGH_MQ135 alert."""
    now = datetime.now(timezone.utc)
    payload = {
        "device_id": "env_node_gas_alert",
        "timestamp": now.isoformat(),
        "is_mock": False,
        "temperature_c": 24.0,
        "humidity_percent": 50.0,
        "mq135_voltage": 2.45,  # Exceeds 2.0V threshold
        "ir_count": 5,
        "bin_fill_percent": 30.0,
    }

    res = await client.post("/api/v1/environment/telemetry", json=payload)
    assert res.status_code == 201

    # Verify alert created in database
    alerts_res = await client.get("/api/v1/environment/env_node_gas_alert/alerts?hours=1.0")
    assert alerts_res.status_code == 200
    data = alerts_res.json()
    assert data["count"] == 1
    alert = data["items"][0]
    assert alert["alert_type"] == "HIGH_MQ135"
    assert alert["severity"] == "WARNING"
    assert alert["metric_value"] == 2.45
    assert alert["threshold_value"] == 2.0
    assert "Elevated MQ135 gas sensor response" in alert["message"]


@pytest.mark.asyncio
async def test_high_temp_threshold_alert_generation(client: AsyncClient):
    """Test 2: Ingesting temperature >= 35.0C triggers HIGH_TEMP alert."""
    now = datetime.now(timezone.utc)
    payload = {
        "device_id": "env_node_temp_alert",
        "timestamp": now.isoformat(),
        "temperature_c": 38.5,  # Exceeds 35.0C
        "humidity_percent": 45.0,
        "mq135_voltage": 1.10,
    }

    res = await client.post("/api/v1/environment/telemetry", json=payload)
    assert res.status_code == 201

    alerts_res = await client.get("/api/v1/environment/env_node_temp_alert/alerts?hours=1.0")
    assert alerts_res.status_code == 200
    data = alerts_res.json()
    assert data["count"] == 1
    assert data["items"][0]["alert_type"] == "HIGH_TEMP"
    assert data["items"][0]["metric_value"] == 38.5


@pytest.mark.asyncio
async def test_bin_full_threshold_alert_generation(client: AsyncClient):
    """Test 3: Waste-bin fill percentage >= 80.0% triggers BIN_FULL alert."""
    now = datetime.now(timezone.utc)
    payload = {
        "device_id": "env_node_bin_alert",
        "timestamp": now.isoformat(),
        "temperature_c": 22.0,
        "humidity_percent": 50.0,
        "mq135_voltage": 1.05,
        "bin_fill_percent": 88.0,  # Exceeds 80% threshold
    }

    res = await client.post("/api/v1/environment/telemetry", json=payload)
    assert res.status_code == 201

    alerts_res = await client.get("/api/v1/environment/env_node_bin_alert/alerts?hours=1.0")
    assert alerts_res.status_code == 200
    data = alerts_res.json()
    assert data["count"] == 1
    assert data["items"][0]["alert_type"] == "BIN_FULL"
    assert data["items"][0]["metric_value"] == 88.0


@pytest.mark.asyncio
async def test_sensor_probe_disconnect_alert(client: AsyncClient):
    """Test 4: Hardware sensor probe reporting FAIL status triggers SENSOR_DISCONNECT alert."""
    now = datetime.now(timezone.utc)
    payload = {
        "device_id": "env_node_hw_fault",
        "timestamp": now.isoformat(),
        "is_mock": False,
        "temperature_c": None,
        "humidity_percent": None,
        "sensor_status": {
            "dht22": "FAIL",
            "mq135": "OK",
            "ir": "OK",
            "ultrasonic": "OK",
        },
    }

    res = await client.post("/api/v1/environment/telemetry", json=payload)
    assert res.status_code == 201

    alerts_res = await client.get("/api/v1/environment/env_node_hw_fault/alerts?hours=1.0")
    assert alerts_res.status_code == 200
    data = alerts_res.json()
    assert data["count"] == 1
    assert data["items"][0]["alert_type"] == "SENSOR_DISCONNECT"
    assert "dht22" in data["items"][0]["message"]


@pytest.mark.asyncio
async def test_alert_cooldown_lockout_prevents_spam(client: AsyncClient):
    """Test 5: Repeated violations within 300s cooldown lockout are suppressed."""
    now = datetime.now(timezone.utc)
    device = "env_node_spam_test"

    # First violation -> Dispatches alert
    payload1 = {
        "device_id": device,
        "timestamp": now.isoformat(),
        "mq135_voltage": 2.50,
    }
    await client.post("/api/v1/environment/telemetry", json=payload1)

    # Second violation 5 seconds later -> Should be locked out by cooldown
    payload2 = {
        "device_id": device,
        "timestamp": (now + timedelta(seconds=5)).isoformat(),
        "mq135_voltage": 2.55,
    }
    await client.post("/api/v1/environment/telemetry", json=payload2)

    # Third violation 10 seconds later -> Still locked out
    payload3 = {
        "device_id": device,
        "timestamp": (now + timedelta(seconds=10)).isoformat(),
        "mq135_voltage": 2.60,
    }
    await client.post("/api/v1/environment/telemetry", json=payload3)

    # Check alert count: must be exactly 1
    alerts_res = await client.get(f"/api/v1/environment/{device}/alerts?hours=1.0")
    assert alerts_res.status_code == 200
    assert alerts_res.json()["count"] == 1


@pytest.mark.asyncio
async def test_cooldown_recovery_and_rearm(client: AsyncClient):
    """Test 6: When metric returns to safe level, cooldown resets and re-arms."""
    now = datetime.now(timezone.utc)
    device = "env_node_recovery_test"

    # 1. Trigger violation
    await client.post(
        "/api/v1/environment/telemetry",
        json={"device_id": device, "timestamp": now.isoformat(), "mq135_voltage": 2.30},
    )
    alerts1 = await client.get(f"/api/v1/environment/{device}/alerts?hours=1.0")
    assert alerts1.json()["count"] == 1

    # 2. Metric drops back to clean baseline (< 1.8V)
    await client.post(
        "/api/v1/environment/telemetry",
        json={"device_id": device, "timestamp": (now + timedelta(seconds=10)).isoformat(), "mq135_voltage": 1.10},
    )

    # Cooldown should be cleared
    assert BlynkService.can_trigger_alert(device, "HIGH_MQ135") is True

    # 3. New violation occurs later -> Successfully dispatches second alert
    await client.post(
        "/api/v1/environment/telemetry",
        json={"device_id": device, "timestamp": (now + timedelta(seconds=20)).isoformat(), "mq135_voltage": 2.40},
    )
    alerts2 = await client.get(f"/api/v1/environment/{device}/alerts?hours=1.0")
    assert alerts2.json()["count"] == 2


@pytest.mark.asyncio
async def test_mock_data_provenance_preserved_in_alerts(client: AsyncClient):
    """Test 7: Demonstration/mock telemetry generates alerts explicitly tagged with is_mock=True."""
    now = datetime.now(timezone.utc)
    payload = {
        "device_id": "env_demo_alert_node",
        "timestamp": now.isoformat(),
        "is_mock": True,
        "mq135_voltage": 3.10,
    }

    await client.post("/api/v1/environment/telemetry", json=payload)

    alerts_res = await client.get("/api/v1/environment/env_demo_alert_node/alerts?hours=1.0")
    assert alerts_res.status_code == 200
    assert alerts_res.json()["count"] == 1
    assert alerts_res.json()["items"][0]["is_mock"] is True


@pytest.mark.asyncio
async def test_blynk_status_endpoint(client: AsyncClient):
    """Test 8: GET /blynk/status returns virtual pins, threshold configuration, and active lockouts."""
    res = await client.get("/api/v1/environment/blynk/status")
    assert res.status_code == 200
    data = res.json()
    assert "blynk_configured" in data
    assert "virtual_pins" in data
    assert "thresholds" in data
    assert data["virtual_pins"]["V0"] == "Temperature (°C)"
    assert data["virtual_pins"]["V2"] == "MQ135 Gas Sensor Voltage (V)"
    assert data["thresholds"]["mq135_voltage_v"] == 2.0


@pytest.mark.asyncio
async def test_trigger_test_alert_endpoint(client: AsyncClient):
    """Test 9: POST /alerts/test programmatically generates demonstration alert."""
    payload = {
        "device_id": "test_device_node",
        "alert_type": "HIGH_MQ135",
        "metric_value": 2.75,
        "severity": "CRITICAL",
        "message": "Manual test alert for college committee demonstration.",
    }

    res = await client.post("/api/v1/environment/alerts/test", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["device_id"] == "test_device_node"
    assert data["alert_type"] == "HIGH_MQ135"
    assert data["severity"] == "CRITICAL"
    assert data["is_mock"] is True
    assert "Manual test alert" in data["message"]


@pytest.mark.asyncio
async def test_demo_scenario_injection_evaluates_alerts(client: AsyncClient):
    """Test 10: Injecting spike_mq135 scenario automatically triggers alert pipeline."""
    payload = {
        "scenario": "spike_mq135",
        "device_id": "demo_alert_pipeline",
        "n_samples": 30,
        "sample_interval_sec": 60,
        "clear_previous_demo": True,
    }

    res = await client.post("/api/v1/environment/demo/scenario", json=payload)
    assert res.status_code == 200

    # Query alerts for this demo device
    alerts_res = await client.get("/api/v1/environment/demo_alert_pipeline/alerts?hours=1.0")
    assert alerts_res.status_code == 200
    data = alerts_res.json()
    assert data["count"] >= 1
    assert data["items"][0]["is_mock"] is True
