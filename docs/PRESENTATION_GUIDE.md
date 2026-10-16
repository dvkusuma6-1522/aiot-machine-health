# AI-Powered Multi-Sensor Environmental Monitoring and Prediction System
## Academic Presentation Guide & Technical Defense Manual

**Project Title:** AI-Powered Multi-Sensor Environmental Monitoring and Prediction System  
**Target Duration:** 3–5 Minutes (College Viva, Capstone Defense, or Industry Evaluation)  
**Workspace:** `/home/kusuma/.gemini/antigravity/scratch/aiot-machine-health`  
**Dual Architecture:** Independent Environmental Monitoring alongside Preserved Machine Health  

---

## 1. 3–5 Minute Presentation Script

### Minute 0:00 – 1:00: Problem Statement & Value Proposition
> "Good morning, respected evaluators and panel members. Today, I am presenting our **AI-Powered Multi-Sensor Environmental Monitoring and Prediction System**.
>
> Traditional IoT environmental nodes suffer from three critical flaws:
> 1. **Reactive Thresholds**: They only beep or notify after air quality has already degraded or a waste bin has overflowed.
> 2. **Notification Fatigue**: Fluctuating readings cause continuous alert spamming that operators quickly ignore.
> 3. **Black-Box Unreliability**: Off-the-shelf air quality monitors frequently report fictitious 'Air Quality Index' numbers from cheap metal-oxide sensors without certified calibration.
>
> Our project resolves this by pairing an **ESP32 edge node** with an **asynchronous FastAPI backend**, a **Scikit-Learn Machine Learning pipeline**, a **Blynk IoT mobile bridge**, and a **Next.js 14 presentation dashboard**. Crucially, we deliver **1-hour ahead predictive forecasting** with prediction confidence intervals, **multivariate anomaly detection with root-cause feature attribution**, and an **anti-spam cooldown architecture**."

---

### Minute 1:00 – 2:15: Hardware & Edge-to-Cloud Architecture
> "Let us look at our edge hardware tier. We use an **ESP32 DevKit** reading four physical sensors:
> - **DHT22** on GPIO 4 for ambient temperature (-40°C to 80°C) and relative humidity (0% to 100%).
> - **MQ135** on GPIO 34 (ADC1) reading analog gas sensor response voltage. We read the raw ADC voltage ($0.0\text{V} - 3.3\text{V}$) with a 10-sample moving average filter, maintaining scientific integrity by not claiming uncalibrated ppm.
> - **IR Optical Sensor** on GPIO 27 with interrupt-safe edge counting and software debouncing for human footfall activity.
> - **HC-SR04 Ultrasonic Sensor** on GPIO 5 (TRIG) and GPIO 18 (ECHO). Because HC-SR04 outputs a 5V echo pulse, we designed a **1kΩ / 2kΩ resistor voltage divider** to step the signal down to a safe **3.33V**, protecting the ESP32 GPIO from silicon breakdown.
>
> Telemetry flows via Wi-Fi through a dual-dispatch architecture:
> 1. Directly to our **FastAPI backend** over HTTP REST (`POST /api/v1/environment/telemetry`), persisting to SQLite with composite `(device_id, timestamp)` indexing.
> 2. Simultaneously to the **Blynk IoT Cloud** across Virtual Pins V0 through V7 using non-blocking, rate-limited publishing."

---

### Minute 2:15 – 3:30: Machine Learning Pipelines & Live Demonstration
> "Now let us turn to our machine learning tier, running Scikit-Learn in our backend:
>
> 1. **Model 1: Random Forest Regression (1-Hour Ahead MQ135 Forecast)**:
>    - Uses historical time-series features: 5m, 10m, 15m, and 30m lagged voltages, rolling means, rate of change ($\Delta V / \Delta t$), ambient temperature, humidity, IR activity, bin fill %, and diurnal cyclical factors ($\sin/\cos$ of hour).
>    - Trained using strict **chronological train/test splitting** (first 80% train, final 20% test). We use backward tolerance matching (`merge_asof`) to ensure zero future data leakage.
>    - Rather than giving a naive single point, it predicts an **80% Quantile Prediction Interval** derived from across all 100 decision trees.
>    - If the node has insufficient data, the model returns an honest `WAITING_FOR_DATA` status rather than a fabricated accuracy number.
>
> 2. **Model 2: Isolation Forest (Multi-Sensor Anomaly Detection)**:
>    - Flags multidimensional outliers with $\nu=0.05$ contamination.
>    - Crucially, it provides **Z-score root-cause feature attribution**, explicitly telling the operator *why* an observation is anomalous (e.g. 'MQ135 voltage elevated by +3.4σ while IR traffic remained baseline zero').
>
> Let us view the live dashboard and run our demonstration engine." *(Switch to terminal and browser).*

---

### Minute 3:30 – 4:30: Live Demonstration & Alert Anti-Spam Protection
> *(Run `python3 scripts/run_presentation_demo.py`)*
>
> "As you see on the dashboard at `http://localhost:3000`:
> - In **Step 1**, nominal baseline conditions are displayed with dark-green and teal styling. Missing sensors are rendered honestly as `--` and are never coerced to zero.
> - In **Step 3**, as simulated gas emissions climb from 0.8V to 2.1V, the Random Forest model forecasts that gas voltage will exceed our 2.0V threshold within the next hour.
> - In **Step 5**, the Isolation Forest detects the divergence, displaying the anomaly badge and root-cause card.
> - In **Step 6**, the threshold alert triggers. Notice the **300-second cooldown timer**: subsequent readings do not spam notifications. When conditions return to normal in Step 8, an automated `RECOVERY` event is logged and the cooldown resets.
> - All bench test data carries `is_mock=True` provenance, clearly highlighted by the amber banner."

---

### Minute 4:30 – 5:00: Engineering Rigor & Conclusion
> "In summary:
> - The entire system is backed by **71 automated unit and integration tests** with a 100% pass rate.
> - The legacy machine-health monitoring database and its 24 original tests remain completely untouched in a dual-architecture configuration.
> - The ESP32 firmware compiles in under 3 seconds using only 14.6% RAM.
> - The Next.js dashboard compiles to static production pages with zero TypeScript errors.
>
> Thank you, and I am now ready for your questions."

---

## 2. Step-by-Step Live Demonstration Guide

Follow these exact steps during an evaluation or presentation:

### Preparation (Before Evaluators Arrive)
1. **Start the FastAPI Backend** (Terminal 1):
   ```bash
   cd /home/kusuma/.gemini/antigravity/scratch/aiot-machine-health
   python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
   ```
   *Verify:* Navigate to `http://localhost:8000/health` (returns `{"status":"HEALTHY","database":"CONNECTED"}`).

2. **Start the Next.js Dashboard** (Terminal 2):
   ```bash
   cd /home/kusuma/.gemini/antigravity/scratch/aiot-machine-health/dashboard
   npm run dev
   ```
   *Verify:* Open `http://localhost:3000` in Google Chrome or Firefox.

3. **Verify Clean Test Baseline** (Terminal 3):
   ```bash
   cd /home/kusuma/.gemini/antigravity/scratch/aiot-machine-health
   PYTHONPATH=backend python3 -m pytest backend/tests/ -q
   ```
   *Output:* `71 passed, 1 warning in ~6.5s`.

---

### Live Demonstration Execution (During Presentation)

Run the automated 8-step presentation demo script in Terminal 3:
```bash
python3 scripts/run_presentation_demo.py
```

| Step | Action Displayed on CLI | Visual Effect on Dashboard (`http://localhost:3000`) |
| :---: | :--- | :--- |
| **1** | Injects clean baseline data (`env_node_demo`). | Live cards update: Temp 24.5°C, Hum 52%, Gas 0.82V, Bin 22%. Green status. |
| **2** | Historical time-series verification. | Recharts graph populates smooth 60-minute historical trendlines. |
| **3** | Progressive gas drift scenario injection. | MQ135 voltage climbs (0.82V &rarr; 1.45V &rarr; 2.15V). Air quality badge turns amber. |
| **4** | Random Forest 1h-ahead regression inference. | "AI 60-Min Forecast" card displays projected 2.48V with 80% interval `[2.15V, 2.78V]`. |
| **5** | Isolation Forest multivariate anomaly scoring. | Anomaly card turns amber/rose; feature attribution displays `+3.2σ MQ135 deviation`. |
| **6** | Alert dispatch and cooldown verification. | Alert appears in `Alert & Incident Log` with `Blynk Dispatched` badge. Cooldown timer locks for 300s. |
| **7** | Anti-spam suppression test. | Script sends 3 duplicate violating packets; console proves packets are suppressed from duplicate alerts. |
| **8** | Scenario reset & recovery re-arm. | Baseline restored; `RECOVERY` log event inserted; dashboard returns to nominal green. |

---

## 3. Likely Evaluator / Professor Questions & Answers

### Q1: "Why do you report MQ135 voltage instead of converting to PPM or AQI?"
> **Answer:**  
> "Metal-oxide semiconductor (MOS) sensors like the MQ135 measure surface electrical conductivity changes caused by reducing or oxidizing gases. A valid conversion from analog voltage to parts-per-million (PPM) requires determining $R_s/R_0$ where $R_0$ is the clean-air resistance calibrated in a sealed, laboratory-certified chamber at exactly 20°C and 65% RH. Furthermore, MQ135 is cross-sensitive to ethanol, ammonia, CO, and smoke without gas selectivity. Claiming certified PPM or official EPA AQI without multi-point chamber calibration and individual sensor pre-heating curves is scientifically invalid. We report the exact analog voltage ($0.0\text{V} - 3.3\text{V}$) with temperature and humidity context, and use machine learning to forecast relative atmospheric drift."

### Q2: "Why choose Random Forest instead of an LSTM or GRU recurrent neural network for forecasting?"
> **Answer:**  
> "We selected Random Forest for three key engineering reasons:
> 1. **Data Efficiency**: LSTMs require tens of thousands of continuous sequences to avoid severe overfitting; our tabular environmental data operates on 5-second to 1-minute intervals where Random Forest achieves lower MAE on limited datasets.
> 2. **Quantile Interval Generation**: We extract the 10th and 90th percentiles across the 100 individual tree estimators, providing a genuine 80% confidence interval without computationally expensive Monte Carlo dropout.
> 3. **Latency & Robustness**: Inference takes under 2 milliseconds on CPU with zero GPU requirement, making it ideal for edge-gateway deployment, and decision trees are completely immune to vanishing gradients and unscaled feature distortions."

### Q3: "How do you guarantee that your 1-hour ahead model has no data leakage?"
> **Answer:**  
> "Data leakage is prevented in our `EnvironmentalFeatureEngineer` through two mechanisms:
> 1. **Strict Chronological Splitting**: We never randomly shuffle time-series data. The earliest 80% of timestamped records form the training set, and the final 20% form the held-out evaluation set.
> 2. **Backward Target Alignment (`merge_asof`)**: When pairing input feature vector $X_t$ with future target $y_{t+60\text{m}}$, we search for the closest observation at or after $t + 60\text{m}$ within a narrow 5-minute tolerance window. Feature rolling means and standard deviations strictly look *backward* ($t-15\text{m}$, $t-60\text{m}$) and never include future samples."

### Q4: "Why is a resistor voltage divider required for the HC-SR04 ultrasonic sensor?"
> **Answer:**  
> "The HC-SR04 ultrasonic sensor operates on a 5V $V_{CC}$ rail, and its ECHO output pulse transitions between 0V and 5V. However, the ESP32 GPIO pins operate at 3.3V CMOS logic and have an absolute maximum rating of 3.6V. Supplying 5V directly to GPIO 18 would forward-bias the ESP32 internal ESD clamping diodes, causing excessive current injection and permanent silicon latch-up.
> We implemented a voltage divider using $R_1 = 1.0\,\text{k}\Omega$ and $R_2 = 2.0\,\text{k}\Omega$:
> $$V_{\text{ECHO\_ESP32}} = 5.0\,\text{V} \times \frac{2.0\,\text{k}\Omega}{1.0\,\text{k}\Omega + 2.0\,\text{k}\Omega} = 3.33\,\text{V}$$
> This is perfectly within the ESP32 input high threshold ($V_{IH} \ge 2.47\,\text{V}$) and safely below the 3.6V damage limit."

### Q5: "How does Isolation Forest detect anomalies, and how do you calculate feature attribution?"
> **Answer:**  
> "Isolation Forest works on the principle that anomalies are 'few and different'. It randomly selects a feature and randomly selects a split value between that feature's minimum and maximum. Because outliers occupy sparse regions of the multidimensional feature space, they are isolated in fewer tree splits (shorter path lengths) than nominal clusters.
> For feature attribution, whenever an observation is flagged as an anomaly, our pipeline computes the standardized Z-score of each sensor relative to the baseline training distribution:
> $$z_i = \frac{x_i - \mu_i}{\sigma_i}$$
> Any sensor where $|z_i| \ge 2.0$ is flagged as an active contributor, allowing the system to output human-readable explanations like 'Temperature elevated by +3.1σ'."

### Q6: "What happens if a physical sensor probe disconnects while the system is running?"
> **Answer:**  
> "The system employs safe null-preservation at all tiers:
> 1. **Firmware Tier**: If the DHT22 returns `NaN` or the HC-SR04 times out after 30ms, the driver marks `is_valid = false` and serializes `null` in the JSON payload.
> 2. **Backend & Database Tier**: The Pydantic schema accepts `None`, and the SQLite column stores SQL `NULL`. Crucially, we **never** convert missing sensor data to 0.0, because a 0°C reading or 0V gas reading has a valid physical meaning.
> 3. **Machine Learning Tier**: The feature pipeline imputes missing values using historical median values, preventing pipeline crashes.
> 4. **Dashboard Tier**: Disconnected sensors render as `--` with a 'Check Probe' badge."

### Q7: "How does the system prevent notification spamming when gas oscillates around 2.0V?"
> **Answer:**  
> "We implement a stateful 300-second (5-minute) cooldown lockout in both edge firmware (`BlynkManager`) and backend (`BlynkService`). When MQ135 voltage first crosses 2.0V, an alert event is dispatched and logged. Subsequent samples that remain above 2.0V update telemetry and live charts, but push notifications are suppressed until 300 seconds elapse. Once readings drop back below 2.0V, an automated `RECOVERY` event is logged, which re-arms the trigger."

### Q8: "How does your dual-architecture ensure the original machine-health system was not broken?"
> **Answer:**  
> "We applied strict namespace isolation:
> - **Firmware**: Legacy firmware remains in `firmware/esp32/`; new firmware lives in `firmware/esp32_environment/`.
> - **Database**: The original `sensor_readings` table and its data remain completely untouched; environmental records write to `environment_readings` and `environment_alerts`.
> - **API Routing**: Original `/api/v1/telemetry` and `/api/v1/machine/*` endpoints remain active; new endpoints are mounted under `/api/v1/environment/*`.
> - **Verification**: All 24 original machine-health tests run in CI/pytest alongside our 47 new environmental tests, maintaining a 100% pass rate (71/71)."

### Q9: "Can this system directly trigger physical actuators like exhaust fans or bin compactors?"
> **Answer:**  
> "No, and this is by deliberate safety design. In industrial and commercial IoT, raw sensor readings and unsupervised anomaly detections should never trigger unverified physical actuation due to the risk of false positives causing motor burnout or equipment damage. Our system provides diagnostic decision support and real-time alerts. Physical actuation must be mediated through an interlocked PLC or verified human operator."

### Q10: "How do you distinguish bench demonstration data from live physical hardware data?"
> **Answer:**  
> "Every database row, API schema, and JSON packet includes the boolean flag `is_mock`. When the ESP32 hardware transmits, `is_mock=false`. When synthetic bench scenarios or tests run, `is_mock=true`. The Next.js dashboard detects this flag and automatically renders an amber warning banner:
> `⚠️ DEMONSTRATION MODE — SYNTHETIC BENCH SCENARIO (NOT LIVE SENSOR DATA)`
> This guarantees total data provenance and academic honesty."
