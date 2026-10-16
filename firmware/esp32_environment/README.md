# ESP32 Environmental Monitoring Edge Firmware

Edge firmware for the **AI-Powered Multi-Sensor Environmental Monitoring and Prediction System**, implemented in Arduino C++ for the ESP32 DevKit V1 microcontroller platform.

---

## 1. Overview & Architecture

The environmental firmware performs non-blocking acquisition across four physical sensors, formats telemetry packets according to the backend's strict Pydantic schema, and streams data over HTTP POST to the FastAPI backend:

```
[DHT22]       (Temp & Humidity)        ---> GPIO 4 (3.3V, 10k pull-up)
[MQ135]       (Gas Analog Voltage)     ---> GPIO 34 (ADC1, via 10k/20k divider)
[IR Sensor]   (Traffic/Pedestrians)    ---> GPIO 27 (Interrupt with 50ms debounce)
[HC-SR04]     (Waste Bin Ultrasonic)   ---> TRIG: GPIO 5 / ECHO: GPIO 18 (via 1k/2k divider)
      |
      v
  ESP32 Edge Microcontroller Node
      |
  [Wi-Fi Client with Non-blocking Auto-Reconnect]
      |
      v
  HTTP POST /api/v1/environment/telemetry
```

---

## 2. Directory Layout

```
firmware/esp32_environment/
├── platformio.ini               # PlatformIO board, framework & library definitions
├── README.md                    # This document
├── include/
│   ├── config.h                 # Master GPIO pins, timing intervals, and calibration
│   ├── secrets.h                # Local Wi-Fi credentials and server endpoint (untracked)
│   └── secrets.h.example        # Version-controlled secrets template
└── src/
    ├── main.cpp                 # Boot self-test, serial CLI, and non-blocking scheduling
    ├── sensors/
    │   ├── dht_sensor.h/.cpp    # DHT22 temperature & humidity driver
    │   ├── mq135_sensor.h/.cpp  # MQ135 analog voltage driver
    │   ├── ir_counter.h/.cpp    # IR pulse counter with interrupt-safe spinlock
    │   └── ultrasonic_sensor.h/.cpp # HC-SR04 distance & bin fill driver
    ├── wifi/
    │   └── wifi_manager.h/.cpp  # Non-blocking Wi-Fi lifecycle & reconnection
    └── telemetry/
        ├── env_telemetry.h      # EnvironmentalTelemetryData container
        └── env_telemetry_sender.h/.cpp # JSON serialization & HTTP client
```

---

## 3. Libraries & Dependencies

Managed automatically via PlatformIO (`platformio.ini`):
- `adafruit/DHT sensor library @ ^1.4.6` (v1.4.7 installed)
- `adafruit/Adafruit Unified Sensor @ ^1.1.14` (v1.1.15 installed)
- `bblanchon/ArduinoJson @ ^7.0.4` (v7.4.3 installed)

---

## 4. Electrical Safety & Voltage Dividers

> [!WARNING]
> **ESP32 GPIO Pins are 3.3V Max. Never apply 5V directly to GPIO 34 or GPIO 18.**
> - **MQ135 AOUT**: Wire a $10\text{k}\Omega$ series resistor to GPIO 34, with a $20\text{k}\Omega$ resistor from GPIO 34 to GND ($5\text{V} \to 3.33\text{V}$).
> - **HC-SR04 ECHO**: Wire a $1\text{k}\Omega$ series resistor to GPIO 18, with a $2\text{k}\Omega$ resistor from GPIO 18 to GND ($5\text{V} \to 3.33\text{V}$).

---

## 5. Build, Flash, and Monitor Instructions

```bash
# 1. Compile firmware
~/.local/bin/pio run -d firmware/esp32_environment

# 2. Flash to ESP32 (connect board via USB)
~/.local/bin/pio run -d firmware/esp32_environment --target upload

# 3. Open Serial Monitor (115200 baud)
~/.local/bin/pio devicemonitor -b 115200
```

### Interactive Serial Commands
While connected via Serial Monitor:
- `m` or `M`: Toggle dynamically between **Real Hardware Mode** (`is_mock: false`) and **Demonstration Mode** (`is_mock: true`).
- `s` or `S`: Print a diagnostic status summary (Wi-Fi IP, signal RSSI, device ID, sensor states).
