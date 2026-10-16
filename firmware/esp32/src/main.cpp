/**
 * @file main.cpp
 * @brief Edge Node Main Application for AIoT Machine Health Monitoring
 * @project AIoT-Based Machine Health Monitoring and Predictive Maintenance System
 * 
 * Hardware Target: ESP32 DevKit V1
 * Framework: Arduino C++
 */

#include <Arduino.h>
#include "config.h"
#include "sensors/vibration_sensor.h"
#include "sensors/temperature_sensor.h"
#include "sensors/current_sensor.h"
#include "sensors/rpm_sensor.h"
#include "relay/relay_controller.h"
#include "wifi/wifi_manager.h"
#include "telemetry/telemetry_sender.h"

// ==============================================================================
// GLOBAL SUBSYSTEM INSTANCES
// ==============================================================================
static VibrationSensor   vibrationSensor;
static TemperatureSensor tempSensor;
static CurrentSensor     currentSensor;
static RpmSensor         rpmSensor;
static RelayController   relayController;
static WiFiManager       wifiManager;
static TelemetrySender   telemetrySender;

// Timing trackers for non-blocking execution
static uint32_t lastVibSampleMs = 0;
static uint32_t lastPublishMs   = 0;

// ==============================================================================
// SETUP: HARDWARE BRING-UP & SENSOR HEALTH SELF-TEST
// ==============================================================================
void setup() {
    Serial.begin(SERIAL_BAUD_RATE);
    delay(1000); // Allow USB serial terminal to attach

    Serial.println();
    Serial.println(F("=================================================================="));
    Serial.println(F("    AIoT MACHINE HEALTH MONITORING SYSTEM - EDGE FIRMWARE         "));
    Serial.print(F("    DEVICE ID : ")); Serial.println(DEVICE_ID);
    Serial.print(F("    MODE      : "));
#if MOCK_MODE == 1
    Serial.println(F("MOCK_MODE (Simulated Deterministic Telemetry)"));
#else
    Serial.println(F("REAL HARDWARE MODE"));
#endif
    Serial.println(F("=================================================================="));

    // 1. Initialize Relay in SAFE / OFF State
    relayController.begin();

    // 2. Perform Sensor Health Self-Test at Startup
    Serial.println(F("\n--- RUNNING SENSOR HEALTH SELF-TEST ---"));

    bool mpuOk  = vibrationSensor.begin();
    bool tempOk = tempSensor.begin();
    bool inaOk  = currentSensor.begin();
    bool hallOk = rpmSensor.begin();

    Serial.println(F("---------------------------------------"));
    Serial.print(F("  MPU6050 Accelerometer : "));
    Serial.println(mpuOk ? F("[ OK ]") : F("[ FAIL ] (Check I2C SDA=21, SCL=22, Addr 0x68)"));

    Serial.print(F("  DS18B20 Temperature   : "));
    Serial.println(tempOk ? F("[ OK ]") : F("[ FAIL ] (Check 1-Wire GPIO 4 & 4.7k pull-up)"));

    Serial.print(F("  INA219 Current/Volt   : "));
    Serial.println(inaOk ? F("[ OK ]") : F("[ FAIL ] (Check I2C SDA=21, SCL=22, Addr 0x40)"));

    Serial.print(F("  A3144 Hall RPM Sensor : "));
    Serial.println(hallOk ? F("[ OK ]") : F("[ FAIL ] (Check GPIO 18 interrupt pin)"));
    Serial.println(F("---------------------------------------"));

    if (!mpuOk || !tempOk || !inaOk || !hallOk) {
        Serial.println(F("[NOTICE] One or more sensors reported failure."));
        Serial.println(F("[NOTICE] The firmware will continue running and report valid sensors."));
    } else {
        Serial.println(F("[SUCCESS] All sensors passed startup health check!"));
    }

    // 3. Initialize Non-blocking Wi-Fi
    Serial.println(F("\n--- INITIALIZING NETWORK ---"));
    wifiManager.begin();

    Serial.println(F("\n[READY] Entering continuous sensing loop...\n"));
    lastVibSampleMs = millis();
    lastPublishMs   = millis();
}

// ==============================================================================
// MAIN LOOP: NON-BLOCKING SENSING, LOCAL STATS & TELEMETRY
// ==============================================================================
void loop() {
    uint32_t now = millis();

    // 1. Maintain Wi-Fi state machine (non-blocking)
    wifiManager.update();

    // 2. High-Rate Vibration Sampling (configurable interval, default 5ms = 200 Hz)
    static VibrationData latestVib;
    if (now - lastVibSampleMs >= VIBRATION_SAMPLE_INTERVAL_MS) {
        lastVibSampleMs = now;
        vibrationSensor.read(latestVib);
    }

    // 3. Periodic Telemetry Packaging & Dispatch (configurable, default 1000ms = 1 Hz)
    if (now - lastPublishMs >= TELEMETRY_PUBLISH_INTERVAL_MS) {
        uint32_t elapsedMs = now - lastPublishMs;
        lastPublishMs = now;

        // Acquire DC telemetry
        TemperatureData latestTemp;
        tempSensor.read(latestTemp);

        CurrentData latestCurr;
        currentSensor.read(latestCurr);

        RpmData latestRpm;
        rpmSensor.calculateRPM(elapsedMs, latestRpm);

        // Package unified packet
        UnifiedTelemetry packet;
        packet.timestamp_ms   = now;
#if MOCK_MODE == 1
        packet.is_mock        = true;
#else
        packet.is_mock        = false;
#endif
        packet.status_mpu6050 = vibrationSensor.isHealthy();
        packet.status_ds18b20 = tempSensor.isHealthy();
        packet.status_ina219  = currentSensor.isHealthy();
        packet.status_hall    = rpmSensor.isHealthy();

        packet.temp = latestTemp;
        packet.vib  = latestVib;
        packet.curr = latestCurr;
        packet.rpm  = latestRpm;

        // Log formatted diagnostic line to Serial
        telemetrySender.logToSerial(packet, wifiManager.isConnected());

        // HTTP POST to FastAPI backend if Wi-Fi connected
        telemetrySender.sendHttpTelemetry(packet, wifiManager.isConnected());
    }

    // Yield to allow ESP32 background FreeRTOS tasks / Wi-Fi stack to process
    yield();
}
