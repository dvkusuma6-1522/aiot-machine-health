# Blynk IoT Setup and Environmental Alert Configuration Guide

## Project Overview
**System:** AI-Powered Multi-Sensor Environmental Monitoring and Prediction System  
**Hardware Node:** ESP32 DevKit (DHT22, MQ135, IR Sensor, HC-SR04)  
**Cloud & Edge Telemetry:** Dual-dispatch to FastAPI REST backend and Blynk IoT Cloud  
**Phase:** Phase 6 — Blynk IoT Integration & Environmental Alerts  

---

## 1. Blynk IoT Cloud Account & Template Setup

### Step 1: Create an Account
1. Navigate to [blynk.cloud](https://blynk.cloud/) and create a free or developer account.
2. Log into the Blynk Cloud Console.

### Step 2: Create a Device Template
1. In the left navigation bar, go to **Templates** &rarr; **+ New Template**.
2. Fill in the Template attributes:
   - **Name:** `AI Environmental Monitoring Node`
   - **Hardware:** `ESP32`
   - **Connection Type:** `WiFi`
   - **Description:** `Dual-telemetry environmental sensing with ML-driven gas forecasting and isolation forest anomaly alerts.`
3. Click **Done**.
4. Take note of the automatically generated Template Header information:
   ```cpp
   #define BLYNK_TEMPLATE_ID "TMPLxxxxxx"
   #define BLYNK_TEMPLATE_NAME "AI Environmental Monitoring Node"
   ```

---

## 2. Datastream Configuration (V0 – V7)

In your Template, select the **Datastreams** tab and configure each Virtual Pin exactly as specified in the system architecture:

| Virtual Pin | Datastream Name | Data Type | Min | Max | Units | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **V0** | `Temperature` | Double | `-40.0` | `80.0` | `°C` | Ambient air temperature from DHT22 |
| **V1** | `Humidity` | Double | `0.0` | `100.0` | `%` | Relative humidity from DHT22 |
| **V2** | `MQ135 Voltage` | Double | `0.0` | `3.3` | `V` | Analog sensor voltage response (*Note: not uncalibrated AQI*) |
| **V3** | `IR Event Count` | Integer | `0` | `2147483647` | `count` | Accumulated pulse transitions from IR sensor |
| **V4** | `Waste-Bin Fill` | Double | `0.0` | `100.0` | `%` | Calculated bin fill percentage from HC-SR04 |
| **V5** | `1h MQ135 Forecast` | Double | `0.0` | `3.3` | `V` | Random Forest regression forecast (~60 min ahead) |
| **V6** | `AI Anomaly Status` | Integer | `0` | `1` | `status` | Isolation Forest flag: `0` = Normal, `1` = Outlier |
| **V7** | `System Status` | String | — | — | — | Node connection status, cooldown state, or alert text |

> **Scientific Disclosure Regarding MQ135:**  
> The system reads and displays the analog pin voltage ($0.0\,\text{V} - 3.3\,\text{V}$). Raw resistance ratio ($R_s/R_0$) varies significantly with temperature, humidity, and individual sensor pre-heating characteristics. The system explicitly avoids claiming certified gas concentrations (ppm) or regulatory AQI without certified laboratory multi-point calibration.

---

## 3. Blynk Events and Threshold Notifications

Navigate to the **Events** tab in your Template to create real-time alert rules:

### Event 1: `high_gas_alert`
- **Event Code:** `high_gas_alert`
- **Type:** Warning
- **Condition:** MQ135 sensor voltage $\ge 2.0\,\text{V}$
- **Notification Message:** `ALERT: Elevated gas sensor voltage observed ({V2}V >= 2.0V threshold). Inspect area ventilation.`

### Event 2: `high_temp_alert`
- **Event Code:** `high_temp_alert`
- **Type:** Warning
- **Condition:** DHT22 temperature $\ge 35.0^\circ\text{C}$
- **Notification Message:** `ALERT: Ambient temperature ({V0}°C) exceeds safety limit (35.0°C).`

### Event 3: `bin_full_alert`
- **Event Code:** `bin_full_alert`
- **Type:** Warning
- **Condition:** HC-SR04 waste-bin fill $\ge 80.0\%$
- **Notification Message:** `ALERT: Waste receptacle fill level reached {V4}% (>= 80% threshold). Dispatch collection.`

### Event 4: `sensor_fault`
- **Event Code:** `sensor_fault`
- **Type:** Critical
- **Condition:** Sensor disconnection or probe timeout (`FAIL` status)
- **Notification Message:** `CRITICAL: Environmental sensor probe failure detected. Check physical wiring.`

### Event 5: `ai_anomaly_alert`
- **Event Code:** `ai_anomaly_alert`
- **Type:** Warning / Critical
- **Condition:** Isolation Forest flags multidimensional outlier ($V_6 = 1$)
- **Notification Message:** `AI OUTLIER: Sensor correlation anomaly detected by Isolation Forest. Inspect node.`

---

## 4. Alert Cooldown & Anti-Spam Architecture

To prevent notification storms when sensor readings oscillate around threshold boundaries:
1. **Cooldown Window:** Configured to **300 seconds (5 minutes)** per alert type.
2. **Lockout Logic:** Once an alert triggers, subsequent events for that specific condition are suppressed until 300 seconds elapse.
3. **Recovery Notification:** When an abnormal condition resolves back to the normal baseline, an automated `RECOVERY` event is logged and the cooldown timer resets.
4. **Independent Threshold Tracking:** Each alert type (`HIGH_MQ135`, `HIGH_TEMP`, `BIN_FULL`, `SENSOR_FAULT`, `AI_ANOMALY`) maintains its own independent lockout timestamp.

---

## 5. ESP32 Environmental Firmware Configuration

### Step 1: Populate Secrets
Edit `firmware/esp32_environment/include/secrets.h` (or copy from `secrets.h.example`):
```cpp
#pragma once

// Wi-Fi Configuration
#define WIFI_SSID           "Your_WiFi_SSID"
#define WIFI_PASSWORD       "Your_WiFi_Password"

// FastAPI Telemetry Ingestion Endpoint
#define BACKEND_INGEST_URL  "http://192.168.1.100:8000/api/v1/environment/telemetry"
#define BACKEND_API_KEY     "test-backend-key-change-in-prod"

// Blynk IoT Cloud Credentials
#define BLYNK_TEMPLATE_ID   "TMPLxxxxxx"
#define BLYNK_TEMPLATE_NAME "AI Environmental Monitoring Node"
#define BLYNK_AUTH_TOKEN    "Your_Blynk_Auth_Token"
```

### Step 2: Graceful Offline Fallback
The firmware includes built-in protection against crashes or hangs when Blynk credentials are not provided:
- If `BLYNK_AUTH_TOKEN` is blank (`""`) or starts with `"YOUR_"`, the firmware logs:
  `[BlynkManager] Blynk auth token not configured; operating in local telemetry mode.`
- In local mode, the ESP32 continues uninterrupted: reading all four physical sensors and posting telemetry to the FastAPI backend over Wi-Fi.

### Step 3: Compiling and Flashing
From the project root:
```bash
cd firmware/esp32_environment
pio run -t upload
pio device_monitor -b 115200
```

---

## 6. FastAPI Backend Configuration & Synchronization

The FastAPI backend also integrates directly with the Blynk Cloud REST API (`https://blynk.cloud/external/api`), enabling synchronization from both edge hardware and server-side ML pipelines.

### Environment Variables
Configure `.env` in the project root or backend directory:
```bash
# Blynk Cloud Integration
BLYNK_AUTH_TOKEN=Your_Blynk_Auth_Token_Here
BLYNK_SERVER_URL=https://blynk.cloud/external/api
BLYNK_ENABLED=true

# Environmental Alert Thresholds
ALERT_MQ135_THRESHOLD_VOLTS=2.0
ALERT_TEMP_HIGH_C=35.0
ALERT_BIN_FULL_PERCENT=80.0
ALERT_COOLDOWN_SECONDS=300
```

### REST Endpoints
- `GET /api/v1/environment/blynk/status`: Returns current Blynk connection state, active cooldowns, configured thresholds, and virtual pin mappings.
- `POST /api/v1/environment/alerts/test`: Dispatches a synthetic demonstration alert to verify the local database audit log and Blynk cloud notification pipelines.
- `GET /api/v1/environment/{device_id}/alerts`: Retrieves historical alert records with filtering and pagination.

---

## 7. Web Dashboard Integration

The Next.js dashboard (`dashboard/`) features:
1. **Blynk Cloud Status Badge:** Displays `Blynk: Ready` when configured and enabled, or `Blynk: Local Mode` when running locally.
2. **Threshold & Alerts Tab:** Displays historical alerts with severity badges, observed vs. threshold values, and a `Blynk Dispatched` delivery indicator.
3. **Interactive Test Alert Trigger:** Allows operators to trigger a test alert directly from the UI to demonstrate push notifications during live presentations.

---

## 8. Mobile App Dashboard Layout Guide

In the Blynk mobile app (iOS / Android):
1. Open the **AI Environmental Monitoring Node** device dashboard.
2. Add the following widgets:
   - **Value Display (V0):** Label "Temperature", Color Orange, `°C`
   - **Value Display (V1):** Label "Humidity", Color Blue, `%`
   - **Radial Gauge (V2):** Label "MQ135 Voltage", Min 0.0, Max 3.3, Color Teal, `V`
   - **Labeled Display (V3):** Label "IR Events", Color Purple
   - **Vertical Level / Progress Bar (V4):** Label "Bin Fill", Min 0, Max 100, Color Yellow/Red, `%`
   - **Value Display (V5):** Label "1h Forecast", Color Cyan, `V`
   - **LED Widget (V6):** Label "AI Anomaly", Color Red (ON when V6 = 1)
   - **Terminal or Text Display (V7):** Label "Device Notification"
3. Configure the **Notification** widget to enable push alerts on `high_gas_alert`, `high_temp_alert`, and `bin_full_alert`.
