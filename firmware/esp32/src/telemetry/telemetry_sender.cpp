/**
 * @file telemetry_sender.cpp
 * @brief Telemetry Formatting, JSON Serialization, and HTTP Client Implementation
 */

#include "telemetry_sender.h"
#include <Arduino.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "secrets.h"

TelemetrySender::TelemetrySender() : _consecutiveFailures(0) {}

void TelemetrySender::logToSerial(const UnifiedTelemetry& data, bool wifiConnected) {
    // Prefix tag
    if (data.is_mock) {
        Serial.print(F("[MOCK] "));
    } else {
        Serial.print(F("[REAL] "));
    }

    // Temperature
    Serial.print(F("TEMP="));
    if (data.temp.is_valid) {
        Serial.print(data.temp.temperature_c, 1);
        Serial.print(F("C "));
    } else {
        Serial.print(F("FAIL "));
    }

    // Acceleration
    Serial.print(F("ACCEL=("));
    if (data.vib.is_valid) {
        Serial.print(data.vib.accel_x, 2);
        Serial.print(F(","));
        Serial.print(data.vib.accel_y, 2);
        Serial.print(F(","));
        Serial.print(data.vib.accel_z, 2);
    } else {
        Serial.print(F("FAIL"));
    }
    Serial.print(F(") "));

    // Current
    Serial.print(F("CURRENT="));
    if (data.curr.is_valid) {
        Serial.print(data.curr.current_ma, 0);
        Serial.print(F("mA "));
    } else {
        Serial.print(F("FAIL "));
    }

    // RPM
    Serial.print(F("RPM="));
    if (data.rpm.is_valid) {
        Serial.print(data.rpm.rpm, 0);
        Serial.print(F(" "));
    } else {
        Serial.print(F("FAIL "));
    }

    // Wi-Fi Status
    Serial.print(F("WIFI="));
    Serial.println(wifiConnected ? F("CONNECTED") : F("DISCONNECTED"));
}

bool TelemetrySender::sendHttpTelemetry(const UnifiedTelemetry& data, bool isWifiConnected) {
    if (!isWifiConnected) {
        // Continue local sensing without blocking
        return false;
    }

    // Build JSON payload
    JsonDocument doc;
    doc["device_id"] = DEVICE_ID;
    doc["timestamp"] = data.timestamp_ms;
    doc["is_mock"] = data.is_mock;

    JsonObject status = doc["sensor_status"].to<JsonObject>();
    status["mpu6050"] = data.status_mpu6050;
    status["ds18b20"] = data.status_ds18b20;
    status["ina219"] = data.status_ina219;
    status["hall"] = data.status_hall;

    // Physical sensor metrics
    doc["temperature"] = data.temp.is_valid ? data.temp.temperature_c : 0.0f;
    doc["accel_x"] = data.vib.is_valid ? data.vib.accel_x : 0.0f;
    doc["accel_y"] = data.vib.is_valid ? data.vib.accel_y : 0.0f;
    doc["accel_z"] = data.vib.is_valid ? data.vib.accel_z : 0.0f;
    doc["gyro_x"] = data.vib.is_valid ? data.vib.gyro_x : 0.0f;
    doc["gyro_y"] = data.vib.is_valid ? data.vib.gyro_y : 0.0f;
    doc["gyro_z"] = data.vib.is_valid ? data.vib.gyro_z : 0.0f;
    
    // Converted electrical values (A, V, W)
    doc["current"] = data.curr.is_valid ? (data.curr.current_ma / 1000.0f) : 0.0f;
    doc["voltage"] = data.curr.is_valid ? data.curr.bus_voltage_v : 0.0f;
    doc["power"] = data.curr.is_valid ? (data.curr.power_mw / 1000.0f) : 0.0f;

    // Shaft RPM
    doc["rpm"] = data.rpm.is_valid ? data.rpm.rpm : 0.0f;

    String jsonString;
    serializeJson(doc, jsonString);

    // Dispatch HTTP POST
    HTTPClient http;
    http.begin(BACKEND_API_URL);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(HTTP_CLIENT_TIMEOUT_MS);

    int httpCode = http.POST(jsonString);

    if (httpCode >= 200 && httpCode < 300) {
        _consecutiveFailures = 0;
        http.end();
        return true;
    } else {
        _consecutiveFailures++;
        Serial.print(F("[HTTP WARN] Telemetry POST to "));
        Serial.print(BACKEND_API_URL);
        Serial.print(F(" failed with code: "));
        Serial.print(httpCode);
        Serial.print(F(" (Consecutive failures: "));
        Serial.print(_consecutiveFailures);
        Serial.println(F(")"));
        http.end();
        return false;
    }
}
