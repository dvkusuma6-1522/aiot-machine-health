"""
Automated Test Suite for Machine Query & Historical Services (Phase 4).

Verifies latest machine telemetry, 404 handling, historical time-window filtering,
chronological ordering, cursor pagination, multiple device isolation, provenance,
and database index usage.
"""

from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.models.telemetry import SensorReading


async def seed_machine_telemetry(session: AsyncSession, device_id: str, count: int, start_offset_minutes: int = 60):
    """Helper to insert a sequence of evenly spaced telemetry records."""
    base_time = datetime.now(timezone.utc) - timedelta(minutes=start_offset_minutes)
    records = []
    for i in range(count):
        t = base_time + timedelta(seconds=i * 10)  # 1 record every 10 seconds
        reading = SensorReading(
            device_id=device_id,
            timestamp=t,
            is_mock=(i % 2 == 0),
            temperature=40.0 + (i * 0.1),
            accel_x=0.01 * i,
            accel_y=0.02 * i,
            accel_z=1.00 + (0.01 * i),
            gyro_x=0.1,
            gyro_y=0.2,
            gyro_z=0.3,
            current=1.0 + (0.01 * i),
            voltage=12.0,
            power=12.0 * (1.0 + 0.01 * i),
            rpm=1500.0 + i,
        )
        records.append(reading)
        session.add(reading)
    await session.commit()
    return records


# ------------------------------------------------------------------------------
# 1. LATEST TELEMETRY TESTS
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_latest_telemetry_success(client: AsyncClient, db_session: AsyncSession):
    """Test 1: Returns the latest recorded telemetry entry for a given machine."""
    await seed_machine_telemetry(db_session, "motor_001", count=10, start_offset_minutes=30)

    response = await client.get("/api/v1/machine/motor_001/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == "motor_001"
    assert data["rpm"] == 1509.0  # 1500 + 9 (last of 10)
    assert data["temperature"] == pytest.approx(40.9, rel=1e-2)
    assert "timestamp" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_latest_telemetry_not_found(client: AsyncClient, db_session: AsyncSession):
    """Test 2: Requesting latest telemetry for a non-existent machine returns 404."""
    response = await client.get("/api/v1/machine/non_existent_motor/latest")
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["code"] == "DEVICE_TELEMETRY_NOT_FOUND"


# ------------------------------------------------------------------------------
# 2. HISTORICAL WINDOW & CHRONOLOGICAL TESTS
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_historical_window_and_chronological_ordering(client: AsyncClient, db_session: AsyncSession):
    """Test 3 & 6: Historical query filters time window correctly and preserves chronological order."""
    # Seed 20 records starting 20 minutes ago
    await seed_machine_telemetry(db_session, "motor_001", count=20, start_offset_minutes=20)

    # Query last 1 hour
    response = await client.get("/api/v1/machine/motor_001/history?hours=1.0&limit=50")
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == "motor_001"
    assert data["count"] == 20
    assert len(data["items"]) == 20
    assert data["has_more"] is False

    # Verify chronological ascending order
    timestamps = [datetime.fromisoformat(item["timestamp"]) for item in data["items"]]
    for i in range(len(timestamps) - 1):
        assert timestamps[i] <= timestamps[i + 1]


@pytest.mark.asyncio
async def test_historical_time_window_filtering(client: AsyncClient, db_session: AsyncSession):
    """Test 5: Time window boundaries filter out older records outside the window."""
    # Insert records from 10 hours ago
    await seed_machine_telemetry(db_session, "motor_001", count=10, start_offset_minutes=600)
    # Insert records from 10 minutes ago
    await seed_machine_telemetry(db_session, "motor_001", count=5, start_offset_minutes=10)

    # Query 1-hour window: should only get the 5 recent records
    response = await client.get("/api/v1/machine/motor_001/history?hours=1.0")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 5


@pytest.mark.asyncio
async def test_multiple_machines_isolation(client: AsyncClient, db_session: AsyncSession):
    """Test 4: Multiple machines do not leak data across device queries."""
    await seed_machine_telemetry(db_session, "motor_001", count=10, start_offset_minutes=15)
    await seed_machine_telemetry(db_session, "pump_999", count=5, start_offset_minutes=15)

    res1 = await client.get("/api/v1/machine/motor_001/history?hours=1.0")
    assert res1.json()["count"] == 10
    assert all(item["device_id"] == "motor_001" for item in res1.json()["items"])

    res2 = await client.get("/api/v1/machine/pump_999/history?hours=1.0")
    assert res2.json()["count"] == 5
    assert all(item["device_id"] == "pump_999" for item in res2.json()["items"])


# ------------------------------------------------------------------------------
# 3. PAGINATION & CURSOR TESTS
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cursor_based_pagination(client: AsyncClient, db_session: AsyncSession):
    """Test 7: Cursor-based pagination traverses multi-page sequences without duplicates or gaps."""
    # Seed 25 records
    await seed_machine_telemetry(db_session, "motor_001", count=25, start_offset_minutes=30)

    # Page 1: limit=10
    res_p1 = await client.get("/api/v1/machine/motor_001/history?hours=2.0&limit=10")
    assert res_p1.status_code == 200
    d1 = res_p1.json()
    assert d1["count"] == 10
    assert d1["has_more"] is True
    cursor_1 = d1["next_cursor"]
    assert cursor_1 is not None

    # Page 2: limit=10 with cursor_1
    res_p2 = await client.get(f"/api/v1/machine/motor_001/history?hours=2.0&limit=10&cursor={cursor_1}")
    assert res_p2.status_code == 200
    d2 = res_p2.json()
    assert d2["count"] == 10
    assert d2["has_more"] is True
    cursor_2 = d2["next_cursor"]
    assert cursor_2 is not None

    # Page 3: limit=10 with cursor_2 (remaining 5)
    res_p3 = await client.get(f"/api/v1/machine/motor_001/history?hours=2.0&limit=10&cursor={cursor_2}")
    assert res_p3.status_code == 200
    d3 = res_p3.json()
    assert d3["count"] == 5
    assert d3["has_more"] is False
    assert d3["next_cursor"] is None

    # Verify no overlapping IDs across pages
    ids_p1 = {item["id"] for item in d1["items"]}
    ids_p2 = {item["id"] for item in d2["items"]}
    ids_p3 = {item["id"] for item in d3["items"]}
    assert ids_p1.isdisjoint(ids_p2)
    assert ids_p2.isdisjoint(ids_p3)
    assert len(ids_p1 | ids_p2 | ids_p3) == 25


@pytest.mark.asyncio
async def test_invalid_hours_and_cursor_rejected(client: AsyncClient):
    """Test 8: Invalid hours boundary and corrupt cursor tokens return 422 validation errors."""
    # Negative hours
    resp1 = await client.get("/api/v1/machine/motor_001/history?hours=-5.0")
    assert resp1.status_code == 422

    # Zero hours
    resp2 = await client.get("/api/v1/machine/motor_001/history?hours=0.0")
    assert resp2.status_code == 422

    # Exceeding max limit (720 hours / 30 days)
    resp3 = await client.get("/api/v1/machine/motor_001/history?hours=1000.0")
    assert resp3.status_code == 422

    # Corrupted cursor string
    resp4 = await client.get("/api/v1/machine/motor_001/history?hours=1.0&cursor=GARBAGE_TOKEN_XYZ")
    assert resp4.status_code == 422
    assert resp4.json()["code"] == "INVALID_CURSOR"


@pytest.mark.asyncio
async def test_empty_history_returns_200_empty_list(client: AsyncClient, db_session: AsyncSession):
    """Test 9: Querying an empty window returns 200 OK with empty items list."""
    # Machine exists with old data, but 0.05h (3 min) window is empty
    await seed_machine_telemetry(db_session, "motor_001", count=5, start_offset_minutes=120)

    response = await client.get("/api/v1/machine/motor_001/history?hours=0.1")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["items"] == []
    assert data["has_more"] is False


@pytest.mark.asyncio
async def test_provenance_preservation(client: AsyncClient, db_session: AsyncSession):
    """Test 10: Real vs Mock provenance flag is strictly preserved."""
    await seed_machine_telemetry(db_session, "motor_001", count=4, start_offset_minutes=10)
    response = await client.get("/api/v1/machine/motor_001/history?hours=1.0")
    assert response.status_code == 200
    items = response.json()["items"]
    # Verify alternating mock flags from seed
    assert items[0]["is_mock"] is True
    assert items[1]["is_mock"] is False
    assert items[2]["is_mock"] is True
    assert items[3]["is_mock"] is False


# ------------------------------------------------------------------------------
# 4. QUERY OPTIMIZATION & INDEX USAGE TEST
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_query_plan_uses_composite_index(db_session: AsyncSession):
    """Test 11: Verify SQLite / DB engine utilizes ix_sensor_device_timestamp index."""
    explain_query = text(
        "EXPLAIN QUERY PLAN "
        "SELECT * FROM sensor_readings "
        "WHERE device_id = :dev AND timestamp >= :t "
        "ORDER BY timestamp ASC, id ASC LIMIT 10"
    )
    result = await db_session.execute(
        explain_query,
        {"dev": "motor_001", "t": datetime.now(timezone.utc)},
    )
    plan_rows = result.fetchall()
    plan_text = " ".join(str(row) for row in plan_rows)
    # In SQLite, the query plan explicitly mentions using index
    assert "USING INDEX" in plan_text or "COVERING INDEX" in plan_text
    assert "ix_sensor_device_timestamp" in plan_text
