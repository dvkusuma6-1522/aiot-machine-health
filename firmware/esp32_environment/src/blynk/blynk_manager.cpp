/**
 * @file blynk_manager.cpp
 * @brief Implementation of Non-Blocking Blynk IoT Client & Datastream Synchronization
 */

#include "blynk_manager.h"

// Define Blynk credentials before including BlynkSimpleEsp32.h
#define BLYNK_PRINT Serial

#include <WiFi.h>
#include <WiFiClient.h>
#include <BlynkSimpleEsp32.h>

// Global storage for incoming AI model feedback written from cloud/app
static float g_latestForecast = 0.0f;
static int   g_latestAnomalyStatus = 0;

// Handler for V5 write from Blynk Cloud (Forecast)
BLYNK_WRITE(BLYNK_VPIN_FORECAST) {
    g_latestForecast = param.asFloat();
    Serial.print(F("[BLYNK] Received V5 1-Hour Forecast update: "));
    Serial.println(g_latestForecast, 3);
}

// Handler for V6 write from Blynk Cloud (Anomaly Status)
BLYNK_WRITE(BLYNK_VPIN_ANOMALY) {
    g_latestAnomalyStatus = param.asInt();
    Serial.print(F("[BLYNK] Received V6 Anomaly Status update: "));
    Serial.println(g_latestAnomalyStatus == 0 ? F("NORMAL") : F("ANOMALY_FLAGGED"));
}

BlynkManager::BlynkManager()
    : m_configured(false),
      m_lastPublishMs(0),
      m_lastGasAlertMs(0),
      m_lastTempAlertMs(0),
      m_lastBinAlertMs(0),
      m_lastFaultAlertMs(0) {}

void BlynkManager::begin() {
    String token = String(BLYNK_AUTH_TOKEN);
    token.trim();

    // Check if token is configured and not default template placeholder
    if (token.length() > 10 && !token.startsWith("YOUR_")) {
        m_configured = true;
        Serial.println(F("[BLYNK] Initializing Blynk client with configured token..."));
        // Configure in non-blocking mode: does not block Wi-Fi loop
        Blynk.config(token.c_str(), "blynk.cloud", 80);
        Serial.println(F("[BLYNK] Non-blocking client configured."));
    } else {
        m_configured = false;
        Serial.println(F("[BLYNK] Notice: Auth token unconfigured in secrets.h."));
        Serial.println(F("[BLYNK] Running in offline local mode (Blynk cloud sync disabled)."));
    }
}

bool BlynkManager::isConfigured() const {
    return m_configured;
}

bool BlynkManager::isConnected() const {
    return m_configured && Blynk.connected();
}

void BlynkManager::update(const EnvironmentalTelemetryData& data, bool wifiConnected) {
    if (!m_configured || !wifiConnected) {
        return;
    }

    // Run Blynk protocol state machine (non-blocking)
    Blynk.run();

    // Rate-limited datastream publication
    uint32_t now = millis();
    if (now - m_lastPublishMs >= BLYNK_PUBLISH_INTERVAL_MS) {
        m_lastPublishMs = now;

        if (Blynk.connected()) {
            publishTelemetry(data);
            evaluateThresholdAlerts(data);
        }
    }
}

void BlynkManager::publishTelemetry(const EnvironmentalTelemetryData& data) {
    // V0: Temperature (°C)
    if (data.dht.is_valid) {
        Blynk.virtualWrite(BLYNK_VPIN_TEMP, data.dht.temperature_c);
    }

    // V1: Relative Humidity (%)
    if (data.dht.is_valid) {
        Blynk.virtualWrite(BLYNK_VPIN_HUM, data.dht.humidity_percent);
    }

    // V2: MQ135 Gas Voltage (V)
    if (data.mq135.is_valid) {
        Blynk.virtualWrite(BLYNK_VPIN_MQ135, data.mq135.voltage_v);
    }

    // V3: Cumulative IR Footfall Event Count
    if (data.ir.is_valid) {
        Blynk.virtualWrite(BLYNK_VPIN_IR, (long)data.ir.count);
    }

    // V4: Waste-Bin Fill Percentage (%)
    if (data.ultrasonic.is_valid) {
        Blynk.virtualWrite(BLYNK_VPIN_BIN_FILL, data.ultrasonic.bin_fill_percent);
    }

    // V7: Device Status String
    String statusStr = String(DEVICE_ID);
    statusStr += data.is_mock ? " [DEMO_MOCK]" : " [LIVE_HW]";
    Blynk.virtualWrite(BLYNK_VPIN_STATUS, statusStr.c_str());
}

void BlynkManager::evaluateThresholdAlerts(const EnvironmentalTelemetryData& data) {
    uint32_t now = millis();

    // 1. High Gas Response Threshold Alert
    if (data.mq135.is_valid && data.mq135.voltage_v >= ALERT_MQ135_THRESHOLD_VOLTS) {
        if (now - m_lastGasAlertMs >= ALERT_COOLDOWN_MS || m_lastGasAlertMs == 0) {
            m_lastGasAlertMs = now;
            String msg = "Elevated air quality response: " + String(data.mq135.voltage_v, 2) + "V";
            Blynk.logEvent("high_gas_alert", msg.c_str());
            Serial.print(F("[BLYNK_ALERT] High Gas Event Dispatched: "));
            Serial.println(msg);
        }
    }

    // 2. High Thermal Threshold Alert
    if (data.dht.is_valid && data.dht.temperature_c >= ALERT_TEMP_HIGH_C) {
        if (now - m_lastTempAlertMs >= ALERT_COOLDOWN_MS || m_lastTempAlertMs == 0) {
            m_lastTempAlertMs = now;
            String msg = "High temperature reading: " + String(data.dht.temperature_c, 1) + "C";
            Blynk.logEvent("high_temp_alert", msg.c_str());
            Serial.print(F("[BLYNK_ALERT] High Temp Event Dispatched: "));
            Serial.println(msg);
        }
    }

    // 3. Waste Bin Fill Threshold Alert
    if (data.ultrasonic.is_valid && data.ultrasonic.bin_fill_percent >= ALERT_BIN_FULL_PERCENT) {
        if (now - m_lastBinAlertMs >= ALERT_COOLDOWN_MS || m_lastBinAlertMs == 0) {
            m_lastBinAlertMs = now;
            String msg = "Waste bin capacity reached: " + String(data.ultrasonic.bin_fill_percent, 1) + "%";
            Blynk.logEvent("bin_full_alert", msg.c_str());
            Serial.print(F("[BLYNK_ALERT] Bin Full Event Dispatched: "));
            Serial.println(msg);
        }
    }

    // 4. Hardware Sensor Probe Disconnection Alert
    bool hasFault = (!data.status_dht22 || !data.status_mq135 || !data.status_ir || !data.status_ultrasonic);
    if (hasFault && !data.is_mock) {
        if (now - m_lastFaultAlertMs >= ALERT_COOLDOWN_MS || m_lastFaultAlertMs == 0) {
            m_lastFaultAlertMs = now;
            Blynk.logEvent("sensor_fault", "One or more hardware sensor probes disconnected or failing.");
            Serial.println(F("[BLYNK_ALERT] Sensor Fault Event Dispatched"));
        }
    }
}
