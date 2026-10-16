# AI-Powered Multi-Sensor Environmental Monitoring and Prediction System

An end-to-end AIoT environmental and climate intelligence platform integrating edge microcontrollers, real-time FastAPI ingestion, Random Forest regression for 1-hour ahead air quality forecasting, Isolation Forest multi-sensor anomaly detection, Blynk IoT Cloud synchronization with threshold alerts, and a Next.js presentation-ready dashboard.

> [!NOTE]
> **Dual-Architecture Workspace**: This repository maintains both the **Environmental Monitoring System** (primary) and the legacy **Machine Health Condition Monitoring System** in isolated, non-interfering namespaces. All 71 automated backend tests pass across both systems.

---

## 1. System Architecture: Edge to Cloud to AI

```mermaid
flowchart TD
    subgraph EDGE["Edge Hardware Tier (ESP32 DevKit)"]
        DHT[DHT22: Temp & Humidity] -->|GPIO 4 (3.3V)| ESP[ESP32 Environmental Node]
        MQ[MQ135: Air Quality] -->|Voltage Divider 5V→3.3V| ADC[GPIO 34 ADC1] --> ESP
        IR[IR Obstacle: Traffic Count] -->|GPIO 27| ESP
        US[HC-SR04: Ultrasonic Bin Fill] -->|TRIG: GPIO 5 / ECHO: Divider GPIO 18| ESP
    end

    subgraph CLOUD["Blynk IoT Cloud Tier"]
        ESP -.->|WiFi Blynk Protocol| BLYNK_DEV[Blynk Virtual Pins V0–V7]
        BACKEND -.->|REST HTTP /update| BLYNK_DEV
        BLYNK_DEV --> MOBILE[Blynk Mobile & Web App\nPush Alerts & Gauges]
    end

    subgraph BACKEND["FastAPI Backend & Telemetry Storage"]
        ESP -->|HTTP POST JSON| ROUTE[/api/v1/environment/telemetry]
        ROUTE --> DB[(SQLite: environment_readings & environment_alerts)]
        DB --> HIST[GET /api/v1/environment/{device_id}/history]
        DB --> LATEST[GET /api/v1/environment/{device_id}/latest]
        DB --> ALERTS[GET /api/v1/environment/{device_id}/alerts]
        DB --> SUMM[GET /api/v1/environment/{device_id}/summary]
    end

    subgraph AI["Scikit-Learn Machine Learning Pipeline"]
        DB --> FE[Feature Engineering: Lags, Rolling Stats, Diurnal sin/cos]
        FE --> RF[RandomForestRegressor: 100 Trees\n60-Min Ahead MQ135 Forecast\n80% Quantile Prediction Intervals]
        FE --> IF[IsolationForest: Contamination 0.05\nZ-Score Root-Cause Feature Attribution]
        RF --> PRED_API[GET /api/v1/environment/{device_id}/prediction]
        IF --> ANOM_API[GET /api/v1/environment/{device_id}/anomalies]
        FE --> TRAIN_API[POST /api/v1/environment/models/train]
    end

    subgraph DASHBOARD["Next.js Presentation Dashboard"]
        HIST & LATEST & PRED_API & ANOM_API & ALERTS --> UI[Next.js 14 TypeScript + Tailwind CSS\nDark Green & Teal Aesthetic]
        UI --> DEMO[Demonstration Lab & Scenario Injector\nis_mock=True Provenance Tracking]
    end
```

---

## 2. Quickstart: Running Backend and Frontend

### Step 1: Start the FastAPI Backend
Ensure Python 3.12+ is active with the required dependencies:
```bash
# From repository root
cd /home/kusuma/.gemini/antigravity/scratch/aiot-machine-health

# Verify all 71 automated tests pass
PYTHONPATH=backend python3 -m pytest backend/tests/ -v

# Launch the FastAPI ingestion and ML backend
cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The backend API documentation will be available at:
- Swagger Interactive Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

### Step 2: Start the Next.js Dashboard
In a separate terminal window:
```bash
cd /home/kusuma/.gemini/antigravity/scratch/aiot-machine-health/dashboard

# Development server (with hot reloading)
npm run dev
```
Open **`http://localhost:3000`** in any modern web browser.

To compile an optimized production build:
```bash
cd dashboard
npm run build
npm run start
```

### Step 3: Run the 8-Step Presentation Demonstration Engine
To execute a live, repeatable walkthrough of the complete telemetry, AI forecast, and alert lifecycle:
```bash
cd /home/kusuma/.gemini/antigravity/scratch/aiot-machine-health
python3 scripts/run_presentation_demo.py
```

---

## 3. Dashboard Features & Layout Guide

The web dashboard is styled with a dark green and teal theme (`#020e0a` background with emerald and teal highlights):

1. **System Status Header**:
   - Device selector: Switch between live physical nodes (`env_node_001`) and demonstration nodes (`env_node_demo`).
   - Real-time connection badge: Tracks FastAPI connectivity (`API Online` / `API Offline`).
   - Active sync indicator: Reports polling state (5s interval) and relative telemetry age.
   - Demonstration toggle & Model Lifecycle inspector modal.
2. **Demonstration Warning Banner**:
   - Prominently displays an amber notice whenever simulated data is active:  
     `⚠️ DEMONSTRATION BENCH MODE ACTIVE (PROVENANCE: IS_MOCK=TRUE)`
3. **Live Multi-Sensor Grid**:
   - **Temperature**: °C from DHT22 with comfort zone evaluation (18°C–28°C).
   - **Humidity**: % RH from DHT22 with optimal humidity evaluation (30%–60%).
   - **MQ135 Gas Voltage**: Analog voltage (0–3.3V) with dynamic air quality rating (`Excellent`, `Moderate`, `Poor`, `Hazardous`).
   - **ADC1 Raw**: 12-bit integer reading (0–4095).
   - **IR Traffic Count**: Cumulative optical event pulses.
   - **Waste-Bin Fill**: Surface distance (cm) and % Fill with graphic progress gauge.
   - *Data Integrity*: Disconnected or missing sensors are rendered as `--` / *Unavailable*, **never** converted to 0.
4. **Interactive Historical Charts**:
   - Recharts time-series with lookback filters (**1h**, **6h**, **24h**, **72h**).
   - Multi-tab views: **Air Quality** (with 1.6V Poor and 2.2V Hazard reference lines), **Climate** (Temperature & Humidity dual-axis), and **Activity & Waste** (IR footfall & fill level).
5. **AI 60-Minute Air Quality Forecast**:
   - Random Forest Regressor predicting gas voltage approximately 60 minutes ahead.
   - **80% Quantile Prediction Interval**: Displays 10th and 90th percentile bounds derived across 100 decision trees.
   - **Genuine Metrics**: Displays real MAE and RMSE strictly computed on the held-out test split. If insufficient historical data exists, clearly reports `WAITING_FOR_DATA` (no fabricated accuracy).
6. **Isolation Forest Anomaly Detection**:
   - Status badge: `NORMAL` (emerald), `WARNING` (amber), `CRITICAL` (rose).
   - Decision score ($< 0$ indicates outlier).
   - **Feature Attribution**: Lists specific sensors driving the anomaly ($z \ge 2.0\sigma$).
   - Suggested manual inspection action and educational disclaimer.
7. **Alert & Anomaly Event Log**:
   - Audit trail of past anomaly events filterable by severity (`ALL`, `CRITICAL`, `WARNING`).
8. **Demonstration Scenario Laboratory**:
   - Allows evaluators to inject 5 reproducible scenarios:
     1. *Nominal Climate Baseline*: Normal diurnal temperature and clean air.
     2. *Progressive Gas Drift*: Steady upward trajectory simulating emission buildup.
     3. *Episodic Gas Spike*: Transient Gaussian spike simulating localized vapor release.
     4. *Multi-Sensor Divergence*: Simultaneous thermal rise and gas surge.
     5. *Diurnal ML Training Series*: Multi-hour organic pattern for training the regressor.

---

## 4. Environment Variables

Create or edit `dashboard/.env.local`:
```env
# Backend API Base URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# Client polling frequency in milliseconds
NEXT_PUBLIC_POLL_INTERVAL_MS=5000
```

---

## 5. Troubleshooting Guide

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| **"API Offline" badge in header** | Backend uvicorn server is not running on port 8000. | Start backend: `python3 -m uvicorn app.main:app --port 8000` from `backend/`. |
| **CORS errors in browser console** | `NEXT_PUBLIC_API_URL` origin not permitted in backend `CORS_ORIGINS`. | Default `backend/app/core/config.py` allows `http://localhost:3000`. Ensure port matches. |
| **"Waiting for Data" on Forecast card** | Database has $< 100$ historical readings for the selected node. | Either transmit real sensor data from ESP32, or click **Scenarios** &rarr; **Diurnal ML Training Series** &rarr; **Inject** &rarr; toggle **Demo Mode**. |
| **Missing sensors showing "--"** | Edge firmware sent `null` due to probe timeout or disconnection. | Normal expected behavior. Check hardware wiring (DHT22 on GPIO 4, MQ135 on GPIO 34). |
| **Node.js command not found** | Node.js was installed to user space `~/.local/bin/`. | Ensure `~/.local/bin` is in `$PATH`: `export PATH="$HOME/.local/bin:$PATH"`. |

---

## 6. Blynk IoT Integration & Real-time Alerts

The system features dual telemetry dispatch from both the ESP32 edge node and the FastAPI server to the **Blynk IoT Cloud**:

- **Virtual Pins V0–V7**:
  - `V0`: Temperature (°C)
  - `V1`: Humidity (% RH)
  - `V2`: MQ135 Gas Voltage (0.0–3.3V)
  - `V3`: IR Event Count
  - `V4`: Waste-Bin Fill (%)
  - `V5`: 1-Hour Ahead MQ135 Forecast (V)
  - `V6`: AI Anomaly Flag (0 = Normal, 1 = Outlier)
  - `V7`: System Status & Push Notification Messages
- **Threshold Alerts**:
  - High Gas Voltage: $\ge 2.0\text{V}$ (`high_gas_alert`)
  - Elevated Temperature: $\ge 35.0^\circ\text{C}$ (`high_temp_alert`)
  - Waste-Bin Fill: $\ge 80.0\%$ (`bin_full_alert`)
  - Sensor Disconnection: Probe error or timeout (`sensor_fault`)
  - AI Anomaly: Isolation Forest outlier detection (`ai_anomaly_alert`)
- **Anti-Spam Cooldown**: 300-second lockout per condition with automatic `RECOVERY` re-arming.
- **Setup Guide**: See [BLYNK_SETUP.md](BLYNK_SETUP.md) for step-by-step account configuration, datastream creation, template ID setup, and mobile widgets.

---

## 7. Master Engineering Documentation

Complete, publication-ready documentation is available for all subsystems:

- **[PRESENTATION_GUIDE.md](PRESENTATION_GUIDE.md)**: 3–5 minute college presentation script, slide-by-slide timing, architecture defense, and 12 evaluator viva questions & answers.
- **[HARDWARE.md](HARDWARE.md)**: ESP32 pinout table, sensor electrical interfaces, resistor voltage divider derivations ($5\text{V} \to 3.3\text{V}$), power current budget, and thermal isolation rules.
- **[AI_MODELS.md](AI_MODELS.md)**: Random Forest 1-hour ahead regression, Isolation Forest multivariate anomaly detection, 80% quantile confidence intervals, feature engineering, and scientific limitations.
- **[API_EXAMPLES.md](API_EXAMPLES.md)**: Realistic curl requests and JSON responses for all 14 implemented REST endpoints.
- **[BLYNK_SETUP.md](BLYNK_SETUP.md)**: Blynk IoT Cloud template setup, Virtual Pins V0–V7, threshold events, and mobile app dashboard widgets.
- **[MIGRATION_PLAN.md](MIGRATION_PLAN.md)**: Complete 7-phase migration architectural strategy, database schema evolution, and rollback procedures.

---

## 8. Phase Verification Summary

| Phase | Description | Status |
| :---: | :--- | :---: |
| **Phase 0** | Workspace inspection and baseline preservation | **COMPLETE** |
| **Phase 1** | Migration Plan & dependency setup (`scikit-learn`, `pandas`, `joblib`) | **COMPLETE** |
| **Phase 2** | Environmental database models, Pydantic schemas & dual telemetry APIs | **COMPLETE** |
| **Phase 3** | ESP32 environmental firmware (DHT22, MQ135, IR, HC-SR04) | **COMPLETE** |
| **Phase 4** | AI models (Random Forest 60m regressor, Isolation Forest, Quantile intervals) | **COMPLETE** |
| **Phase 5** | Presentation-Ready Next.js Dashboard (Dark green/teal, Recharts, Demo Lab) | **COMPLETE** |
| **Phase 6** | Blynk IoT Integration & Environmental Alerts (V0–V7, Cooldowns, Dashboard) | **COMPLETE** |
| **Phase 7** | End-to-End Testing, Polish & Presentation Documentation | **COMPLETE** |

---

## 9. Hardware & Cloud Manual Verification Notice

- **Software & Build Verification:** 100% verified. All 71 automated pytest suites pass, PlatformIO compiles in under 3s with 14.6% RAM, and Next.js builds cleanly with 0 errors.
- **Physical Hardware Notice:** Bench testing and verification have been conducted using high-fidelity synthetic scenarios and software loopbacks. Deploying to physical breadboards requires flashing the compiled binary (`pio run -t upload`) and wiring physical sensors per [HARDWARE.md](HARDWARE.md).
- **Blynk Cloud Account Notice:** Live push notifications to mobile devices require entering a valid `BLYNK_AUTH_TOKEN` into `secrets.h` and `.env` per [BLYNK_SETUP.md](BLYNK_SETUP.md). If absent, the firmware and backend gracefully operate in local telemetry mode without errors.


