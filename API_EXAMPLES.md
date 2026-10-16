# Environmental REST API: Examples & Interaction Manual

**Base URL:** `http://localhost:8000`  
**Interactive Docs (Swagger UI):** `http://localhost:8000/docs`  
**Alternative Docs (ReDoc):** `http://localhost:8000/redoc`  
**OpenAPI Specification:** `http://localhost:8000/openapi.json`  

---

## 1. Health & Status

### 1.1 Service Health Check
- **Endpoint:** `GET /health`
- **Description:** Verifies FastAPI application state and SQLite database connection.

```bash
curl -X GET "http://localhost:8000/health" -H "Accept: application/json"
```

**Response (`200 OK`):**
```json
{
  "status": "HEALTHY",
  "database": "CONNECTED"
}
```

---

## 2. Telemetry Ingestion

### 2.1 Ingest Environmental Telemetry (Dedicated Endpoint)
- **Endpoint:** `POST /api/v1/environment/telemetry`
- **Description:** Receives physical or simulated sensor packets from ESP32 edge nodes.

```bash
curl -X POST "http://localhost:8000/api/v1/environment/telemetry" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "env_node_001",
    "timestamp": "2026-10-16T14:00:00Z",
    "is_mock": false,
    "temperature_c": 24.8,
    "humidity_percent": 53.2,
    "mq135_raw": 1042.0,
    "mq135_voltage": 0.84,
    "ir_count": 14,
    "ultrasonic_distance_cm": 38.5,
    "bin_fill_percent": 23.0,
    "sensor_status": {
      "dht22": true,
      "mq135": true,
      "ir": true,
      "ultrasonic": true
    }
  }'
```

**Response (`201 Created`):**
```json
{
  "status": "SUCCESS",
  "id": 142,
  "device_id": "env_node_001",
  "timestamp": "2026-10-16T14:00:00Z",
  "message": "Telemetry accepted and persisted successfully"
}
```

---

## 3. Telemetry Query Endpoints

### 3.1 Get Latest Telemetry
- **Endpoint:** `GET /api/v1/environment/{device_id}/latest`
- **Description:** Fetches the most recent observation for a specific node.

```bash
curl -X GET "http://localhost:8000/api/v1/environment/env_node_001/latest"
```

**Response (`200 OK`):**
```json
{
  "id": 142,
  "device_id": "env_node_001",
  "timestamp": "2026-10-16T14:00:00Z",
  "is_mock": false,
  "temperature_c": 24.8,
  "humidity_percent": 53.2,
  "mq135_raw": 1042.0,
  "mq135_voltage": 0.84,
  "ir_count": 14,
  "ultrasonic_distance_cm": 38.5,
  "bin_fill_percent": 23.0,
  "sensor_status": {
    "dht22": true,
    "mq135": true,
    "ir": true,
    "ultrasonic": true
  },
  "created_at": "2026-10-16T14:00:01.124Z"
}
```

### 3.2 Query Historical Telemetry (With Cursor Pagination)
- **Endpoint:** `GET /api/v1/environment/{device_id}/history?hours=1.0&limit=2`
- **Description:** Returns chronological time-series observations with cursor pagination.

```bash
curl -X GET "http://localhost:8000/api/v1/environment/env_node_001/history?hours=1.0&limit=2"
```

**Response (`200 OK`):**
```json
{
  "device_id": "env_node_001",
  "total_records": 120,
  "limit": 2,
  "next_cursor": "eyJpZCI6MTQxfQ==",
  "items": [
    {
      "id": 142,
      "device_id": "env_node_001",
      "timestamp": "2026-10-16T14:00:00Z",
      "is_mock": false,
      "temperature_c": 24.8,
      "humidity_percent": 53.2,
      "mq135_voltage": 0.84,
      "ir_count": 14,
      "bin_fill_percent": 23.0
    },
    {
      "id": 141,
      "device_id": "env_node_001",
      "timestamp": "2026-10-16T13:59:55Z",
      "is_mock": false,
      "temperature_c": 24.7,
      "humidity_percent": 53.4,
      "mq135_voltage": 0.83,
      "ir_count": 14,
      "bin_fill_percent": 23.0
    }
  ]
}
```

### 3.3 Query Statistical Summary
- **Endpoint:** `GET /api/v1/environment/{device_id}/summary?hours=24.0`
- **Description:** Computes min, max, and average metrics over the specified time window.

```bash
curl -X GET "http://localhost:8000/api/v1/environment/env_node_001/summary?hours=24.0"
```

**Response (`200 OK`):**
```json
{
  "device_id": "env_node_001",
  "hours": 24.0,
  "sample_count": 288,
  "temperature": { "min": 21.2, "max": 28.4, "avg": 24.6 },
  "humidity": { "min": 45.0, "max": 68.2, "avg": 54.1 },
  "mq135_voltage": { "min": 0.65, "max": 1.45, "avg": 0.88 },
  "bin_fill_percent": { "min": 10.0, "max": 78.5, "avg": 34.2 }
}
```

---

## 4. Machine Learning Endpoints

### 4.1 1-Hour Ahead Random Forest Prediction
- **Endpoint:** `GET /api/v1/environment/{device_id}/prediction?demo=false`
- **Description:** Generates forecast of MQ135 voltage 60 minutes ahead with 80% quantile confidence interval.

```bash
curl -X GET "http://localhost:8000/api/v1/environment/env_node_001/prediction"
```

**Response (`200 OK`):**
```json
{
  "device_id": "env_node_001",
  "model_status": "MODEL_EVALUATED",
  "target_variable": "mq135_voltage",
  "horizon_minutes": 60,
  "target_timestamp": "2026-10-16T15:00:00Z",
  "predicted_value": 1.84,
  "confidence_lower": 1.62,
  "confidence_upper": 2.08,
  "model_name": "RandomForestRegressor",
  "model_version": "1.0.0",
  "is_demonstration": false,
  "message": "Model evaluated on historical dataset. 60-minute ahead forecast generated.",
  "mae": 0.084,
  "rmse": 0.112
}
```

### 4.2 Isolation Forest Anomaly Detection
- **Endpoint:** `GET /api/v1/environment/{device_id}/anomalies?hours=24.0&limit=10`
- **Description:** Retrieves multi-sensor outliers with z-score feature attribution.

```bash
curl -X GET "http://localhost:8000/api/v1/environment/env_node_001/anomalies?hours=24.0&limit=10"
```

**Response (`200 OK`):**
```json
{
  "device_id": "env_node_001",
  "count": 1,
  "items": [
    {
      "id": 12,
      "timestamp": "2026-10-16T13:45:00Z",
      "severity": "WARNING",
      "anomaly_score": -0.168,
      "explanation": "Elevated MQ135 gas voltage (+3.4σ above baseline) without proportional footfall.",
      "suggested_action": "Inspect local area ventilation; verify whether cleaning solvents were used.",
      "driving_features": ["mq135_voltage", "mq135_rate_of_change"],
      "is_demo": false
    }
  ]
}
```

### 4.3 Trigger Model Training
- **Endpoint:** `POST /api/v1/environment/models/train`
- **Description:** Triggers chronological retraining of Random Forest and Isolation Forest pipelines.

```bash
curl -X POST "http://localhost:8000/api/v1/environment/models/train" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "env_node_001",
    "allow_mock_data": true,
    "min_samples": 50,
    "test_size": 0.2
  }'
```

**Response (`200 OK`):**
```json
{
  "status": "TRAINED",
  "device_id": "env_node_001",
  "samples_used": 180,
  "rf_metrics": {
    "mae": 0.076,
    "rmse": 0.098,
    "r2": 0.914
  },
  "if_anomalies_detected": 9,
  "model_persisted": true
}
```

### 4.4 Model System Status
- **Endpoint:** `GET /api/v1/environment/models/status`
- **Description:** Reports serialized model inventory and in-memory lifecycle state.

```bash
curl -X GET "http://localhost:8000/api/v1/environment/models/status"
```

**Response (`200 OK`):**
```json
{
  "models_available": ["RandomForestRegressor", "IsolationForest"],
  "rf_model_loaded": true,
  "if_model_loaded": true,
  "model_storage_path": "/home/kusuma/.../backend/app/ml/models",
  "active_devices": ["env_node_001", "env_node_demo"]
}
```

---

## 5. Demonstration & Scenario Engine

### 5.1 Inject Calibrated Demo Scenario
- **Endpoint:** `POST /api/v1/environment/demo/scenario`
- **Description:** Injects reproducible benchmark time-series marked with `is_mock=true`.

```bash
curl -X POST "http://localhost:8000/api/v1/environment/demo/scenario" \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": "spike_mq135",
    "device_id": "env_node_demo",
    "n_samples": 30,
    "sample_interval_sec": 60,
    "clear_previous_demo": true
  }'
```

**Response (`200 OK`):**
```json
{
  "status": "SUCCESS",
  "scenario": "spike_mq135",
  "device_id": "env_node_demo",
  "records_inserted": 30,
  "start_time": "2026-10-16T13:30:00Z",
  "end_time": "2026-10-16T14:00:00Z",
  "message": "Scenario spike_mq135 successfully populated with 30 synthetic data points."
}
```

---

## 6. Blynk IoT Cloud & Alert Endpoints

### 6.1 Get Blynk Integration Status
- **Endpoint:** `GET /api/v1/environment/blynk/status`
- **Description:** Returns cloud connectivity state, configured virtual pins, active cooldown lockouts, and thresholds.

```bash
curl -X GET "http://localhost:8000/api/v1/environment/blynk/status"
```

**Response (`200 OK`):**
```json
{
  "blynk_configured": false,
  "blynk_enabled": true,
  "server_url": "https://blynk.cloud/external/api",
  "active_cooldowns": {},
  "thresholds": {
    "mq135_voltage_limit": 2.0,
    "temperature_high_c": 35.0,
    "bin_full_percent": 80.0,
    "cooldown_seconds": 300.0
  },
  "virtual_pins": {
    "V0": "Temperature (°C)",
    "V1": "Humidity (%)",
    "V2": "MQ135 Voltage (V)",
    "V3": "IR Event Count",
    "V4": "Waste-Bin Fill (%)",
    "V5": "1-Hour Ahead MQ135 Forecast (V)",
    "V6": "AI Anomaly Status (0=Normal, 1=Outlier)",
    "V7": "System Notification / Alert Text"
  }
}
```

### 6.2 Trigger Demonstration Test Alert
- **Endpoint:** `POST /api/v1/environment/alerts/test`
- **Description:** Dispatches a test alert to verify the local audit table and Blynk notification pipelines.

```bash
curl -X POST "http://localhost:8000/api/v1/environment/alerts/test" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "env_node_001",
    "alert_type": "HIGH_MQ135",
    "metric_value": 2.45,
    "severity": "WARNING",
    "message": "Manual test alert: Simulated MQ135 voltage 2.45V exceeding 2.0V limit."
  }'
```

**Response (`200 OK`):**
```json
{
  "id": 1,
  "device_id": "env_node_001",
  "timestamp": "2026-10-16T14:02:15.821Z",
  "alert_type": "HIGH_MQ135",
  "severity": "WARNING",
  "message": "Manual test alert: Simulated MQ135 voltage 2.45V exceeding 2.0V limit.",
  "metric_value": 2.45,
  "threshold_value": 2.0,
  "is_mock": false,
  "blynk_delivered": false,
  "created_at": "2026-10-16T14:02:15.825Z"
}
```

### 6.3 Query Historical Alerts
- **Endpoint:** `GET /api/v1/environment/{device_id}/alerts?hours=24.0&limit=50`
- **Description:** Returns historical alerts logged for the node.

```bash
curl -X GET "http://localhost:8000/api/v1/environment/env_node_001/alerts?hours=24.0&limit=50"
```

**Response (`200 OK`):**
```json
{
  "device_id": "env_node_001",
  "hours_analyzed": 24.0,
  "count": 1,
  "items": [
    {
      "id": 1,
      "device_id": "env_node_001",
      "timestamp": "2026-10-16T14:02:15.821Z",
      "alert_type": "HIGH_MQ135",
      "severity": "WARNING",
      "message": "Manual test alert: Simulated MQ135 voltage 2.45V exceeding 2.0V limit.",
      "metric_value": 2.45,
      "threshold_value": 2.0,
      "is_mock": false,
      "blynk_delivered": false,
      "created_at": "2026-10-16T14:02:15.825Z"
    }
  ]
}
```
