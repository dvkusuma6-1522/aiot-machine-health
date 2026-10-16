/**
 * @file config.h
 * @brief Central Hardware Pinout, Timing, and Configuration for Environmental Node
 * @project AI-Powered Multi-Sensor Environmental Monitoring System
 *
 * All hardware pins, timing intervals, physical conversion factors,
 * and operational thresholds are centralized in this header.
 */

#ifndef ENV_CONFIG_H
#define ENV_CONFIG_H

#include <stdint.h>

// ==============================================================================
// 1. OPERATION & DEMONSTRATION MODE DEFINITIONS
// ==============================================================================
/**
 * @brief Mock Mode Toggle
 * Set to 0: Read actual physical hardware sensors.
 * Set to 1: Generate deterministic simulated telemetry for bench/testing without hardware.
 *
 * IMPORTANT: Simulated data is explicitly flagged with "is_mock": true in telemetry
 * and clearly tagged in serial logs as [MOCK].
 */
#ifndef MOCK_MODE
#define MOCK_MODE 0
#endif

/// Unique Identifier for this monitored environmental node
#define DEVICE_ID "env_node_001"

/// Serial Monitor Baud Rate
#define SERIAL_BAUD_RATE 115200

// ==============================================================================
// 2. HARDWARE GPIO PIN DEFINITIONS
// ==============================================================================

// --- DHT22 Temperature & Humidity Sensor ---
// Requires 10k ohm pull-up resistor to 3.3V
#define PIN_DHT_DATA            4    // Digital I/O (3.3V logic)

// --- MQ135 Air Quality Sensor ---
// Module powered by 5V (heater). Output 0V-5V connected via voltage divider:
// 10k ohm (series from AOUT) + 20k ohm (to GND) -> 0V-3.33V safe into GPIO 34.
// GPIO 34 is on ADC1 (safe during Wi-Fi operation).
#define PIN_MQ135_ANALOG        34   // ADC1 Channel 6 (Input Only)

// --- IR Obstacle / People Counter Sensor ---
// Active LOW pulse when object is detected in front of IR beam.
#define PIN_IR_SENSOR           27   // Hardware Interrupt (INPUT_PULLUP)

// --- HC-SR04 Ultrasonic Waste Bin Level Sensor ---
// Module powered by 5V.
// TRIG: 3.3V trigger from ESP32 is compatible with 5V HC-SR04 trigger threshold.
// ECHO: 5V output MUST connect via voltage divider (1k ohm / 2k ohm) to GPIO 18.
#define PIN_ULTRASONIC_TRIG     5    // Digital Output (Trigger pulse)
#define PIN_ULTRASONIC_ECHO     18   // Digital Input (Echo response, 3.3V protected)

// ==============================================================================
// 3. ELECTRICAL SAFETY & VOLTAGE DIVIDER CONSTANTS
// ==============================================================================
// MQ135 Voltage Divider:
// R_top = 10.0k, R_bottom = 20.0k
// V_adc = V_sensor * (R_bottom / (R_top + R_bottom)) = V_sensor * (20 / 30) = V_sensor * 0.6667
// V_sensor = V_adc * (30 / 20) = V_adc * 1.50
#define MQ135_DIVIDER_RATIO     1.50f
#define ESP32_ADC_VREF          3.30f
#define ESP32_ADC_MAX_COUNT     4095.0f

// ==============================================================================
// 4. SMART WASTE BIN GEOMETRY CALIBRATION
// ==============================================================================
// Configurable empty vs full distances (cm) for bin fill percentage calculation
#define BIN_EMPTY_DISTANCE_CM   100.0f  // Distance from sensor to bottom of empty bin
#define BIN_FULL_DISTANCE_CM    10.0f   // Distance from sensor to surface when 100% full

// ==============================================================================
// 5. SAMPLING & PUBLISHING INTERVALS
// ==============================================================================
// DHT22 minimum polling cycle: 2000 ms (2.0 seconds hardware constraint)
#define DHT_SAMPLE_INTERVAL_MS         2000

// IR counter debounce lockout (microseconds)
#define IR_DEBOUNCE_MICROS             50000  // 50 ms debounce lockout

// Ultrasonic pulse timeout (microseconds) -> ~5 meters maximum range
#define ULTRASONIC_TIMEOUT_US          30000

// Telemetry upload rate to FastAPI backend (3000 ms = 3.0 seconds)
#define TELEMETRY_PUBLISH_INTERVAL_MS  3000

// Sensor health check polling interval (5000 ms)
#define HEALTH_CHECK_INTERVAL_MS       5000

// ==============================================================================
// 6. PHYSICAL SANITY BOUNDARIES & VALIDATION
// ==============================================================================
#define TEMP_MIN_VALID_C               (-40.0f)
#define TEMP_MAX_VALID_C               (85.0f)

#define HUMIDITY_MIN_VALID             (0.0f)
#define HUMIDITY_MAX_VALID             (100.0f)

#define DISTANCE_MIN_VALID_CM          (2.0f)
#define DISTANCE_MAX_VALID_CM          (400.0f)

#define MQ135_VOLTAGE_MIN_VALID        (0.0f)
#define MQ135_VOLTAGE_MAX_VALID        (5.0f)

// ==============================================================================
// 7. BLYNK IOT VIRTUAL DATASTREAM MAPPINGS
// ==============================================================================
#define BLYNK_VPIN_TEMP                V0   // Temperature (°C)
#define BLYNK_VPIN_HUM                 V1   // Relative Humidity (%)
#define BLYNK_VPIN_MQ135               V2   // MQ135 Sensor Voltage (V)
#define BLYNK_VPIN_IR                  V3   // Cumulative IR Footfall Event Count
#define BLYNK_VPIN_BIN_FILL            V4   // Smart Waste-Bin Fill (%)
#define BLYNK_VPIN_FORECAST            V5   // 1-Hour Ahead MQ135 Forecast (V)
#define BLYNK_VPIN_ANOMALY             V6   // AI Anomaly Status (0 = Normal, 1 = Outlier)
#define BLYNK_VPIN_STATUS              V7   // Node Status / Active Notification String

// Blynk cloud synchronization interval (5000 ms)
#define BLYNK_PUBLISH_INTERVAL_MS      5000

// ==============================================================================
// 8. ENVIRONMENTAL ALERT THRESHOLDS & COOLDOWNS
// ==============================================================================
#define ALERT_MQ135_THRESHOLD_VOLTS    2.0f    // Elevated air quality response threshold (Volts)
#define ALERT_TEMP_HIGH_C              35.0f   // High ambient thermal threshold (°C)
#define ALERT_BIN_FULL_PERCENT         80.0f   // Waste bin capacity threshold (%)
#define ALERT_COOLDOWN_MS              300000  // 5-minute notification cooldown lockout

#endif // ENV_CONFIG_H
