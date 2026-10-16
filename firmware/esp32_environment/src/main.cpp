/**
 * @file main.cpp
 * @brief Edge Node Main Application for Environmental Monitoring System
 * @project AI-Powered Multi-Sensor Environmental Monitoring and Prediction System
 *
 * Hardware Target: ESP32 DevKit V1
 * Framework: Arduino C++
 */

#include <Arduino.h>
#include "config.h"
#include "sensors/dht_sensor.h"
#include "sensors/mq135_sensor.h"
#include "sensors/ir_counter.h"
#include "sensors/ultrasonic_sensor.h"
#include "wifi/wifi_manager.h"
#include "telemetry/env_telemetry_sender.h"
#include "blynk/blynk_manager.h"

// ==============================================================================
// GLOBAL SUBSYSTEM INSTANCES
// ==============================================================================
static DhtSensor          dhtSensor;
static Mq135Sensor        mq135Sensor;
static IrCounter          irCounter;
static UltrasonicSensor   ultrasonicSensor;
static WiFiManager        wifiManager;
static EnvTelemetrySender telemetrySender;
static BlynkManager       blynkManager;

// Operational runtime state
static bool isMockModeActive = (MOCK_MODE == 1);
static bool dhtStatusOk        = false;
static bool mq135StatusOk      = false;
static bool irStatusOk         = false;
static bool ultrasonicStatusOk = false;

// Timing trackers
static uint32_t lastPublishMs = 0;

// Base timestamp tracking for millisecond epoch simulation
static uint64_t baseEpochMs = 1728835200000ULL; // Baseline 2026-10-13T16:00:00Z

// ==============================================================================
// SETUP: HARDWARE BRING-UP & SENSOR HEALTH SELF-TEST
// ==============================================================================
void setup() {
    Serial.begin(SERIAL_BAUD_RATE);
    delay(1000); // Allow USB serial terminal to initialize

    Serial.println();
    Serial.println(F("=================================================================="));
    Serial.println(F("   AI-POWERED MULTI-SENSOR ENVIRONMENTAL MONITORING SYSTEM        "));
    Serial.println(F("                    ESP32 EDGE FIRMWARE                           "));
    Serial.print(F("   DEVICE ID : ")); Serial.println(DEVICE_ID);
    Serial.print(F("   MODE      : "));
    if (isMockModeActive) {
        Serial.println(F("MOCK_MODE (Simulated Environmental Telemetry)"));
    } else {
        Serial.println(F("REAL HARDWARE MODE (Reading Physical Sensors)"));
    }
    Serial.println(F("=================================================================="));

    // 1. Startup Sensor Health Self-Test
    Serial.println(F("\n--- RUNNING ENVIRONMENTAL SENSOR SELF-TEST ---"));

    dhtStatusOk        = dhtSensor.begin();
    mq135StatusOk      = mq135Sensor.begin();
    irStatusOk         = irCounter.begin();
    ultrasonicStatusOk = ultrasonicSensor.begin();

    Serial.println(F("------------------------------------------------------------------"));
    Serial.print(F("  DHT22 Temp & Humidity : "));
    Serial.println(dhtStatusOk ? F("[ OK ]") : F("[ FAIL ] (Check GPIO 4 & 10k pull-up)"));

    Serial.print(F("  MQ135 Gas Sensor ADC  : "));
    Serial.println(mq135StatusOk ? F("[ OK ]") : F("[ FAIL ] (Check GPIO 34 & Voltage Divider)"));

    Serial.print(F("  IR Obstacle Counter   : "));
    Serial.println(irStatusOk ? F("[ OK ]") : F("[ FAIL ] (Check GPIO 27 Interrupt)"));

    Serial.print(F("  HC-SR04 Ultrasonic    : "));
    Serial.println(ultrasonicStatusOk ? F("[ OK ]") : F("[ FAIL ] (Check TRIG=5, ECHO=18 Divider)"));
    Serial.println(F("------------------------------------------------------------------"));

    if (!dhtStatusOk && !mq135StatusOk && !irStatusOk && !ultrasonicStatusOk) {
        Serial.println(F("[NOTICE] No physical sensors detected on GPIO pins."));
        Serial.println(F("[NOTICE] Send 'm' over Serial Monitor at any time to toggle Mock Mode."));
    } else {
        Serial.println(F("[SUCCESS] Sensor initialization complete."));
    }

    // 2. Initialize Wi-Fi
    Serial.println(F("\n--- INITIALIZING NETWORK ---"));
    wifiManager.begin();

    // 3. Initialize Blynk IoT Cloud Client (Non-Blocking)
    Serial.println(F("\n--- INITIALIZING BLYNK IOT CLIENT ---"));
    blynkManager.begin();

    Serial.println(F("\n[READY] Entering continuous environmental telemetry loop...\n"));
    Serial.println(F("[COMMANDS] Type 'm' to toggle Mock/Real mode | 's' for status summary."));
    lastPublishMs = millis();
}

// ==============================================================================
// MAIN LOOP: NON-BLOCKING SENSING & TELEMETRY DISPATCH
// ==============================================================================
static EnvironmentalTelemetryData currentPacket;

void loop() {
    uint32_t now = millis();

    // 1. Keep Wi-Fi updated in background
    wifiManager.update();

    // 2. Process interactive serial commands
    if (Serial.available() > 0) {
        char cmd = Serial.read();
        if (cmd == 'm' || cmd == 'M') {
            isMockModeActive = !isMockModeActive;
            Serial.print(F("\n>>> [MODE SWITCH] Mode changed to: "));
            Serial.println(isMockModeActive ? F("MOCK_MODE (Simulated)") : F("REAL HARDWARE MODE"));
        } else if (cmd == 's' || cmd == 'S') {
            Serial.println(F("\n>>> [DIAGNOSTIC STATUS]"));
            Serial.print(F("  Device ID    : ")); Serial.println(DEVICE_ID);
            Serial.print(F("  Wi-Fi Status : ")); Serial.println(wifiManager.isConnected() ? F("CONNECTED") : F("DISCONNECTED"));
            Serial.print(F("  IP Address   : ")); Serial.println(wifiManager.getLocalIP());
            Serial.print(F("  Blynk Status : ")); Serial.println(blynkManager.isConnected() ? F("CONNECTED") : (blynkManager.isConfigured() ? F("CONNECTING...") : F("OFFLINE (UNCONFIGURED)")));
            Serial.print(F("  Current Mode : ")); Serial.println(isMockModeActive ? F("MOCK") : F("REAL"));
        }
    }

    // 3. Periodic Telemetry Dispatch
    if (now - lastPublishMs >= TELEMETRY_PUBLISH_INTERVAL_MS) {
        lastPublishMs = now;

        currentPacket.timestamp_ms = baseEpochMs + now;
        currentPacket.is_mock = isMockModeActive;
        currentPacket.status_dht22 = dhtStatusOk;
        currentPacket.status_mq135 = mq135StatusOk;
        currentPacket.status_ir = irStatusOk;
        currentPacket.status_ultrasonic = ultrasonicStatusOk;

        if (isMockModeActive) {
            // Simulated telemetry mode
            currentPacket.dht = dhtSensor.readMock(now);
            currentPacket.mq135 = mq135Sensor.readMock(now);
            currentPacket.ir = irCounter.readMock(now);
            currentPacket.ultrasonic = ultrasonicSensor.readMock(now);
        } else {
            // Physical hardware acquisition
            currentPacket.dht = dhtSensor.read();
            currentPacket.mq135 = mq135Sensor.read();
            currentPacket.ir = irCounter.readCumulativeCount();
            currentPacket.ultrasonic = ultrasonicSensor.read();
        }

        // Print human-readable diagnostics to Serial Monitor
        telemetrySender.logToSerial(currentPacket, wifiManager.isConnected());

        // Dispatch JSON packet to FastAPI backend
        if (wifiManager.isConnected()) {
            telemetrySender.sendHttpTelemetry(currentPacket, true);
        }
    }

    // 4. Update Blynk Client State Machine & Sync Virtual Pins
    blynkManager.update(currentPacket, wifiManager.isConnected());
}
