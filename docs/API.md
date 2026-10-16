# Telemetry Ingestion API Specification

This document details the REST Ingestion API implemented in Phase 3 of the **AIoT-Based Machine Health Monitoring and Predictive Maintenance System**.

---

## 1. Overview

The Telemetry Ingestion API exposes endpoints for edge devices (such as the ESP32 DevKit node) to stream high-frequency sensor readings into the persistent relational store.

- **Base URL**: `http://<host>:8000`
- **Interactive Documentation**:
  - Swagger UI: `http://<host>:8000/docs`
  - ReDoc: `http://<host>:8000/redoc`
- **OpenAPI Schema**: `http://<host>:8000/openapi.json`

---

## 2. Endpoints

### 2.1 Ingest Telemetry

- **Method**: `POST`
- **Path**: `/api/v1/telemetry`
- **Content-Type**: `application/json`

#### Request Body Schema (`TelemetryPayload`)

| Field | Type | Required | Physical Limits | Description |
| :--- | :--- | :--- | :--- | :--- |
| `device_id` | string | **Yes** | 1–64 characters | Unique machine edge node identifier |
| `timestamp` | string / int / float | **Yes** | Valid ISO-8601 or epoch | Acquisition timestamp |
| `is_mock` | boolean | No (default `false`) | `true` or `false` | Distinguishes bench mock vs real hardware |
| `sensor_status`| object | No | Boolean status map | Startup health flags reported by edge node |
| `temperature` | float | **Yes** | `[-20.0, 130.0]` °C | DS18B20 motor casing temperature |
| `accel_x` | float | **Yes** | `[-16.0, 16.0]` g | MPU-6050 X-axis acceleration |
| `accel_y` | float | **Yes** | `[-16.0, 16.0]` g | MPU-6050 Y-axis acceleration |
| `accel_z` | float | **Yes** | `[-16.0, 16.0]` g | MPU-6050 Z-axis acceleration |
| `gyro_x` | float | **Yes** | `[-2000.0, 2000.0]` deg/s | MPU-6050 X-axis angular velocity |
| `gyro_y` | float | **Yes** | `[-2000.0, 2000.0]` deg/s | MPU-6050 Y-axis angular velocity |
| `gyro_z` | float | **Yes** | `[-2000.0, 2000.0]` deg/s | MPU-6050 Z-axis angular velocity |
| `current` | float | **Yes** | `[0.0, 10.0]` A | INA219 DC motor operating current |
| `voltage` | float | **Yes** | `[0.0, 35.0]` V | INA219 DC bus rail voltage |
| `power` | float | **Yes** | `[0.0, 350.0]` W | Measured power ($|P - V \cdot I| \le 10\text{W}$) |
| `rpm` | float | **Yes** | `[0.0, 10000.0]` | A3144 Hall-effect rotational speed |

> [!NOTE]
> **Physical Validation Boundaries vs. AI Fault Thresholds**:
> The physical limits above are strictly data-integrity boundaries designed to detect unplugged probes or corrupt packets. They are **not** alarm thresholds. Downstream Machine Learning modules determine machine condition independently.

#### Example Request (ISO Timestamp)
```json
{
  "device_id": "motor_001",
  "timestamp": "2026-10-08T18:00:00Z",
  "is_mock": false,
  "temperature": 43.2,
  "accel_x": 0.12,
  "accel_y": 0.08,
  "accel_z": 1.04,
  "gyro_x": 0.1,
  "gyro_y": 0.2,
  "gyro_z": 0.3,
  "current": 1.12,
  "voltage": 11.8,
  "power": 13.216,
  "rpm": 1498.0
}
```

#### Example Request (ESP32 Firmware Format)
```json
{
  "device_id": "motor_001",
  "timestamp": 1728410400000,
  "is_mock": true,
  "sensor_status": {
    "mpu6050": true,
    "ds18b20": true,
    "ina219": true,
    "hall": true
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
  "rpm": 1498.0
}
```

#### Success Response (`201 Created`)
```json
{
  "status": "accepted",
  "device_id": "motor_001",
  "received_at": "2026-10-08T18:00:00.123456+00:00",
  "telemetry_id": 1
}
```

#### Validation Error Response (`422 Unprocessable Content`)
```json
{
  "status": "error",
  "code": "SCHEMA_VALIDATION_ERROR",
  "message": "Payload does not conform to telemetry schema or contains invalid values.",
  "details": [
    {
      "field": "body -> rpm",
      "type": "value_error",
      "message": "Value error, RPM -150.0 violates non-negative rotational bounds [0.0, 10000.0]"
    }
  ]
}
```

---

### 2.2 System Health Check

- **Method**: `GET`
- **Paths**: `/health` and `/api/v1/health`

#### Success Response (`200 OK`)
```json
{
  "status": "ok",
  "database": "connected",
  "environment": "development"
}
```

---

### 2.3 Get Latest Machine Telemetry

- **Method**: `GET`
- **Path**: `/api/v1/machine/{device_id}/latest`

#### Success Response (`200 OK`)
```json
{
  "id": 5,
  "device_id": "motor_001",
  "timestamp": "2026-10-08T12:31:18.563665Z",
  "is_mock": true,
  "temperature": 42.64,
  "accel_x": 0.0,
  "accel_y": -0.04,
  "accel_z": 1.0,
  "gyro_x": 0.1,
  "gyro_y": 0.15,
  "gyro_z": 0.2,
  "current": 1.142,
  "voltage": 11.82,
  "power": 13.497,
  "rpm": 1501.8,
  "created_at": "2026-10-08T12:31:18.569190Z"
}
```

#### Not Found Response (`404 Not Found`)
```json
{
  "status": "error",
  "code": "DEVICE_TELEMETRY_NOT_FOUND",
  "message": "No telemetry records found for device 'non_existent_motor'.",
  "details": []
}
```

---

### 2.4 Get Historical Telemetry Window (with Cursor Pagination)

- **Method**: `GET`
- **Path**: `/api/v1/machine/{device_id}/history`
- **Query Parameters**:
  - `hours` (float, optional, default: `1.0`): Lookback window in hours ($0.0 < \text{hours} \le 720.0$).
  - `limit` (integer, optional, default: `100`): Maximum items per page ($1 \le \text{limit} \le 1000$).
  - `cursor` (string, optional): Base64 pagination cursor obtained from `next_cursor` of previous page.

#### Success Response (`200 OK`)
```json
{
  "device_id": "motor_001",
  "hours_queried": 24.0,
  "start_time": "2026-10-07T12:40:21.758362Z",
  "end_time": "2026-10-08T12:40:21.758362Z",
  "limit": 3,
  "count": 3,
  "has_more": true,
  "next_cursor": "MjAyNi0xMC0wOFQxMjozMToxOC4xMjcyNjJ8Mw==",
  "items": [
    {
      "id": 1,
      "device_id": "motor_001",
      "timestamp": "2026-10-08T12:31:17.687853Z",
      "is_mock": true,
      "temperature": 42.53,
      "accel_x": 0.0,
      "accel_y": -0.04,
      "accel_z": 1.0,
      "gyro_x": 0.1,
      "gyro_y": 0.15,
      "gyro_z": 0.2,
      "current": 1.11,
      "voltage": 11.82,
      "power": 13.119,
      "rpm": 1496.5,
      "created_at": "2026-10-08T12:31:17.694378Z"
    }
  ]
}
```

---

## 3. Database Schema

Telemetry is persisted to the `sensor_readings` table:

```sql
CREATE TABLE sensor_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id VARCHAR(64) NOT NULL,
    timestamp DATETIME NOT NULL,
    is_mock BOOLEAN NOT NULL DEFAULT 0,
    temperature FLOAT NOT NULL,
    accel_x FLOAT NOT NULL,
    accel_y FLOAT NOT NULL,
    accel_z FLOAT NOT NULL,
    gyro_x FLOAT NOT NULL,
    gyro_y FLOAT NOT NULL,
    gyro_z FLOAT NOT NULL,
    current FLOAT NOT NULL,
    voltage FLOAT NOT NULL,
    power FLOAT NOT NULL,
    rpm FLOAT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_sensor_readings_device_id ON sensor_readings (device_id);
CREATE INDEX ix_sensor_readings_timestamp ON sensor_readings (timestamp);
CREATE INDEX ix_sensor_device_timestamp ON sensor_readings (device_id, timestamp);
```

---

## 4. Running and Testing

### 4.1 Starting the Backend
From the `backend/` directory:
```bash
PYTHONPATH=. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4.2 Executing Automated Pytest Suite
```bash
PYTHONPATH=. python3 -m pytest tests/ -v
```

### 4.3 Sending Live Test Telemetry via Script
From the repository root:
```bash
python3 scripts/send_test_telemetry.py --url http://127.0.0.1:8000/api/v1/telemetry --count 5 --delay 1.0
```

### 4.4 Example `curl` Commands

**Valid Request**:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "motor_001",
    "timestamp": "2026-10-08T18:00:00Z",
    "temperature": 43.2,
    "accel_x": 0.12,
    "accel_y": 0.08,
    "accel_z": 1.04,
    "gyro_x": 0.1,
    "gyro_y": 0.2,
    "gyro_z": 0.3,
    "current": 1.12,
    "voltage": 11.8,
    "power": 13.216,
    "rpm": 1498.0
  }'
```

**Testing Rejection (Negative RPM)**:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "motor_001",
    "timestamp": "2026-10-08T18:00:00Z",
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
    "rpm": -150.0
  }'
```
