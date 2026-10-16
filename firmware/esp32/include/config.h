/**
 * @file config.h
 * @brief Central Hardware Pinout, Timing, and Operational Configuration
 * @project AIoT-Based Machine Health Monitoring System
 * 
 * All hardware pins, sampling rates, thresholds, and operational flags
 * are centralized in this single header file.
 */

#ifndef CONFIG_H
#define CONFIG_H

#include <stdint.h>

// ==============================================================================
// 1. OPERATION & MOCK MODE DEFINITIONS
// ==============================================================================
/**
 * @brief Mock Mode Toggle
 * Set to 0: Read actual physical hardware sensors.
 * Set to 1: Generate deterministic mock telemetry for bench/testing without hardware.
 * 
 * IMPORTANT: Mock data is explicitly flagged with "is_mock": true in telemetry
 * and clearly tagged in serial logs as [MOCK].
 */
#ifndef MOCK_MODE
#define MOCK_MODE 0
#endif

/// Unique Identifier for this monitored motor/machine node
#define DEVICE_ID "motor_001"

/// Serial Monitor Baud Rate
#define SERIAL_BAUD_RATE 115200

// ==============================================================================
// 2. HARDWARE GPIO PIN DEFINITIONS
// ==============================================================================

// --- Shared I2C Bus (MPU-6050 & INA219) ---
#define PIN_I2C_SDA             21   // ESP32 default I2C Data
#define PIN_I2C_SCL             22   // ESP32 default I2C Clock
#define I2C_FREQUENCY_HZ        400000 // Fast Mode 400 kHz

// --- MPU-6050 3-Axis Accelerometer / Gyroscope ---
#define MPU6050_I2C_ADDRESS     0x68 // AD0 connected to GND

// --- DS18B20 1-Wire Digital Temperature Sensor ---
#define PIN_DS18B20_DATA        4    // Requires 4.7k ohm pull-up to 3.3V

// --- INA219 High-Side DC Current & Voltage Monitor ---
#define INA219_I2C_ADDRESS      0x40 // Default I2C address (A0, A1 to GND)

// --- A3144 Hall-Effect Speed Sensor ---
#define PIN_HALL_SENSOR         18   // Hardware Interrupt (INPUT_PULLUP)

// --- Optoisolated Relay Module ---
#define PIN_RELAY               5    // Active-LOW control pin

// ==============================================================================
// 3. RELAY HARDWARE CONFIGURATION & SAFETY
// ==============================================================================
// Active-LOW configuration:
// LOW  (0V)  = Relay coil energized (Circuit CLOSED / Motor RUNNING)
// HIGH (3.3V)= Relay coil de-energized (Circuit OPEN / Motor DISCONNECTED)
#define RELAY_ACTIVE_STATE      0    // LOW triggers active state
#define RELAY_INACTIVE_STATE    1    // HIGH triggers inactive state

// Default boot state: MUST BE SAFE / OFF
#define RELAY_DEFAULT_STATE     RELAY_INACTIVE_STATE

// ==============================================================================
// 4. SAMPLING INTERVALS & TIMING CONFIGURATION
// ==============================================================================
// Accelerometer acquisition: 200 Hz sampling (5 ms interval)
#define VIBRATION_SAMPLE_INTERVAL_MS   5

// RPM pulse counting integration window: 1000 ms (1 second)
#define RPM_MEASUREMENT_INTERVAL_MS    1000

// Hall Sensor: Pulses per full mechanical shaft revolution
#define PULSES_PER_REVOLUTION          1

// Hall Sensor: Software debounce minimum threshold in microseconds (1 ms)
// Rejects contact chatter or spurious magnetic edge ringings
#define HALL_DEBOUNCE_MICROS           1000

// Telemetry dispatch rate to FastAPI backend (1 Hz = 1000 ms)
#define TELEMETRY_PUBLISH_INTERVAL_MS  1000

// Sensor health check polling interval (5 seconds)
#define HEALTH_CHECK_INTERVAL_MS       5000

// ==============================================================================
// 5. SENSOR VALIDATION THRESHOLDS & BOUNDS
// ==============================================================================
// DS18B20 Valid Operating Range
#define TEMP_MIN_VALID_C               (-10.0f)
#define TEMP_MAX_VALID_C               (125.0f)
#define TEMP_DISCONNECTED_SENTINEL     (-127.0f)

// INA219 Maximum Expected Ratings for DC motor
#define INA219_MAX_CURRENT_MA          3200.0f
#define INA219_MAX_VOLTAGE_V           26.0f

// MPU6050 Acceleration limits (+/- 16g peak)
#define ACCEL_MAX_G                    16.0f

// ==============================================================================
// 6. COMMUNICATION TIMEOUTS & RETRIES
// ==============================================================================
// HTTP Request timeout in milliseconds
#define HTTP_CLIENT_TIMEOUT_MS         3000

// Maximum consecutive HTTP retries before exponential backoff
#define HTTP_MAX_RETRIES               3

// Delay between connection retries in milliseconds
#define HTTP_RETRY_BACKOFF_MS          1000

// Wi-Fi Connection retry interval
#define WIFI_RECONNECT_INTERVAL_MS     10000

#endif // CONFIG_H
