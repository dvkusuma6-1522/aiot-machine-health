# ESP32 Edge Firmware: AIoT Machine Health Monitoring

This folder contains the complete Arduino C++ firmware for the ESP32 DevKit edge node in the **AIoT-Based Machine Health Monitoring and Predictive Maintenance System**.

---

## 1. Subsystem Architecture

The firmware is designed with modularity, non-blocking execution, and hardware safety as core priorities:
- **Central Configuration** (`include/config.h`): Single source of truth for all GPIO assignments, sampling rates, validation boundaries, and operating modes.
- **Secrets Management** (`include/secrets.h`): Isolated Wi-Fi credentials and backend API URLs; ignored by git.
- **Sensor Drivers** (`src/sensors/`):
  - `vibration_sensor`: MPU-6050 3-axis accelerometer and gyro ($\pm 4g$ range, $44\text{ Hz}$ digital filter, 200 Hz sampling rate).
  - `temperature_sensor`: DS18B20 1-Wire temperature sensor with disconnection detection (-127°C sentinel) and range verification.
  - `current_sensor`: INA219 high-side DC monitor measuring bus voltage, shunt drop, current (mA), and power (mW).
  - `rpm_sensor`: Interrupt-driven Hall-effect pulse counter on GPIO 18 with microsecond debouncing and atomic fetch-and-reset.
- **Relay Controller** (`src/relay/`): Active-LOW relay driver with boot-glitch suppression, guaranteed default SAFE/OFF state.
- **Non-Blocking Wi-Fi** (`src/wifi/`): Asynchronous station mode connection and automatic background reconnection without pausing sensor loops.
- **Telemetry & Logging** (`src/telemetry/`): Standardized JSON formatting, HTTP REST client with configurable timeouts/retries, and human-readable serial logs.

---

## 2. Hardware Pinout Table

| Peripheral | Module Pin | ESP32 GPIO | Electrical Connection Notes |
| :--- | :--- | :--- | :--- |
| **MPU-6050** | VCC | 3V3 | Power (3.3V) |
| | GND | GND | Common System Ground |
| | SDA | **GPIO 21** | Shared I2C Data bus |
| | SCL | **GPIO 22** | Shared I2C Clock bus |
| | AD0 | GND | Sets I2C address to `0x68` |
| **DS18B20** | VDD | 3V3 | Power (3.3V) |
| | GND | GND | Common System Ground |
| | DATA | **GPIO 4** | 1-Wire bus with **$4.7\text{k}\Omega$ pull-up resistor** to 3.3V |
| **INA219** | VCC | 3V3 | Power (3.3V) |
| | GND | GND | Common System Ground |
| | SDA | **GPIO 21** | Shared I2C Data bus |
| | SCL | **GPIO 22** | Shared I2C Clock bus |
| | VIN+ | Motor Supply (+) | In series between DC supply (+) and Relay COM |
| | VIN- | Relay COM | Connected to Relay Common terminal |
| **A3144 Hall**| VCC | 3V3 | Power (3.3V) |
| | GND | GND | Common System Ground |
| | OUT | **GPIO 18** | Configured as `INPUT_PULLUP`, FALLING edge interrupt |
| **Relay Module**| VCC | VIN (5V) | Relay coil power (sourced from ESP32 5V VIN rail) |
| | GND | GND | Relay optocoupler Ground |
| | IN | **GPIO 5** | Active-LOW control (HIGH = SAFE/OFF, LOW = ON) |
| | COM | INA219 VIN- | High-side motor power feed |
| | NO | DC Motor (+) | Normally Open contact (closed only when relay energized) |

---

## 3. Required Libraries

The firmware relies on the following standard libraries (automatically resolved and installed by PlatformIO via `platformio.ini`):
- `adafruit/Adafruit MPU6050 @ ^2.2.6`
- `adafruit/Adafruit Unified Sensor @ ^1.1.14`
- `adafruit/Adafruit INA219 @ ^1.2.3`
- `paulstoffregen/OneWire @ ^2.3.8`
- `milesburton/DallasTemperature @ ^3.11.0`
- `bblanchon/ArduinoJson @ ^7.0.4`
- Built-in ESP32 core libraries: `Wire`, `WiFi`, `HTTPClient`

---

## 4. Configuration: Wi-Fi Credentials & MOCK_MODE

### 4.1 Configuring Wi-Fi and Backend API URL
1. Copy `include/secrets.h.example` to `include/secrets.h`:
   ```bash
   cp include/secrets.h.example include/secrets.h
   ```
2. Open `include/secrets.h` and edit your Wi-Fi credentials and backend IP:
   ```cpp
   #define WIFI_SSID       "Your_Home_Or_Lab_SSID"
   #define WIFI_PASSWORD   "Your_WiFi_Password"
   #define BACKEND_API_URL "http://192.168.1.150:8000/api/v1/telemetry"
   ```

### 4.2 Toggling Real vs. MOCK Mode
In `include/config.h`:
- **Real Hardware Mode** (Default):
  ```cpp
  #define MOCK_MODE 0
  ```
  The ESP32 reads physical sensors on I2C, 1-Wire, and GPIO interrupt.
- **Mock Bench Test Mode**:
  ```cpp
  #define MOCK_MODE 1
  ```
  Generates deterministic test telemetry with sinusoidal harmonics. Telemetry packets explicitly include `"is_mock": true` and are logged to Serial as `[MOCK]`.

---

## 5. How to Compile & Upload

### Using PlatformIO (Recommended)
1. Ensure PlatformIO Core is installed (`pio --version`).
2. Build the firmware:
   ```bash
   pio run
   ```
3. Connect the ESP32 DevKit to your computer via micro-USB.
4. Upload the firmware binary:
   ```bash
   pio run --target upload
   ```
5. Open the Serial Monitor (115200 baud):
   ```bash
   pio device monitor -b 115200
   ```

### Using Arduino IDE
1. Install ESP32 board support via Boards Manager (`esp32 by Espressif Systems`).
2. Select Board: **ESP32 Dev Module**.
3. Install the required libraries via the Library Manager.
4. Open `firmware/esp32/src/main.cpp` (or symlink into an `.ino` sketch directory).
5. Add `firmware/esp32/include` to include search paths.
6. Compile and upload.

---

## 6. Expected Serial Monitor Output

### On Startup (Sensor Health Self-Test)
```
==================================================================
    AIoT MACHINE HEALTH MONITORING SYSTEM - EDGE FIRMWARE         
    DEVICE ID : motor_001
    MODE      : REAL HARDWARE MODE
==================================================================
[SAFETY] Initializing Relay on GPIO 5 (Active-LOW, Default: SAFE / OFF)...
[SAFETY] Relay verified in SAFE / DE-ENERGIZED (OFF) state.

--- RUNNING SENSOR HEALTH SELF-TEST ---
[HARDWARE] Probing MPU-6050 on I2C Bus (SDA=21, SCL=22, Addr=0x68)...
[HARDWARE] MPU-6050 successfully initialized. Range: +/-4G, Filter: 44Hz.
[HARDWARE] Probing DS18B20 on 1-Wire Pin GPIO 4 (requires 4.7k pull-up)...
[HARDWARE] DS18B20 initialized successfully. Device count: 1
[HARDWARE] Probing INA219 on I2C address 0x40...
[HARDWARE] INA219 initialized successfully (32V, 2A calibration).
[HARDWARE] Configuring Hall-Effect Sensor on GPIO 18 (INPUT_PULLUP, FALLING edge interrupt)...
[HARDWARE] Hall RPM interrupt attached successfully.
---------------------------------------
  MPU6050 Accelerometer : [ OK ]
  DS18B20 Temperature   : [ OK ]
  INA219 Current/Volt   : [ OK ]
  A3144 Hall RPM Sensor : [ OK ]
---------------------------------------
[SUCCESS] All sensors passed startup health check!

--- INITIALIZING NETWORK ---
[WIFI] Initializing Wi-Fi in Station (STA) mode...
[WIFI] Connecting to SSID: AIoT_Lab_WiFi
[READY] Entering continuous sensing loop...
```

### During Operation (Every 1 Second)
```
[WIFI] Successfully connected!
[WIFI] IP Address: 192.168.1.142
[WIFI] Signal Strength (RSSI): -54 dBm

[REAL] TEMP=43.2C ACCEL=(0.12,0.08,1.04) CURRENT=1120mA RPM=1498 WIFI=CONNECTED
[REAL] TEMP=43.3C ACCEL=(0.11,0.09,1.03) CURRENT=1118mA RPM=1502 WIFI=CONNECTED
```

---

## 7. Troubleshooting Guide

| Symptom | Probable Cause | Corrective Action |
| :--- | :--- | :--- |
| `MPU6050 [ FAIL ]` | Missing I2C pull-ups, wrong pins, or AD0 disconnected | Check GPIO 21 (SDA) and GPIO 22 (SCL). Connect AD0 to GND. Verify module receives 3.3V. |
| `DS18B20 [ FAIL ]` or `TEMP=-127C` | Missing $4.7\text{k}\Omega$ pull-up resistor or faulty wire | Place a $4.7\text{k}\Omega$ resistor between GPIO 4 (DATA) and 3.3V VCC rail. Verify ground connection. |
| `INA219 [ FAIL ]` | Address conflict or loose I2C connection | Verify I2C address is `0x40` (A0 and A1 connected to GND). Check SDA/SCL continuity. |
| `RPM=0` while motor is spinning | Magnet misaligned or Hall sensor polarity inverted | Ensure magnet South pole faces the sensor face; ensure gap between magnet and sensor is $< 5\text{ mm}$. |
| Motor does not run | Relay remains in safe default OFF state | Relay defaults to OFF for safety. Relay control is commanded explicitly via software. |
| Wi-Fi fails to connect | Wrong credentials or weak 2.4 GHz signal | ESP32 only supports 2.4 GHz Wi-Fi. Verify credentials in `include/secrets.h`. |
