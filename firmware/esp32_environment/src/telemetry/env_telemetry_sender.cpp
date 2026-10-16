/**
 * @file env_telemetry_sender.cpp
 * @brief Telemetry Formatting, JSON Serialization, and HTTP Client Implementation
 */

#include "env_telemetry_sender.h"
#include <Arduino.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "secrets.h"
#include "config.h"

EnvTelemetrySender::EnvTelemetrySender() : _consecutiveFailures(0) {}

void EnvTelemetrySender::logToSerial(const EnvironmentalTelemetryData& data, bool wifiConnected) {
    if (data.is_mock) {
        Serial.print(F("[MOCK] "));
    } else {
        Serial.print(F("[REAL] "));
    }

    // Temperature & Humidity
    Serial.print(F("TEMP="));
    if (data.dht.is_valid) {
        Serial.print(data.dht.temperature_c, 1);
        Serial.print(F("C "));
    } else {
        Serial.print(F("NULL "));
    }

    Serial.print(F("HUM="));
    if (data.dht.is_valid) {
        Serial.print(data.dht.humidity_percent, 1);
        Serial.print(F("% "));
    } else {
        Serial.print(F("NULL "));
    }

    // Air Quality
    Serial.print(F("MQ135_V="));
    if (data.mq135.is_valid) {
        Serial.print(data.mq135.voltage_v, 2);
        Serial.print(F("V "));
    } else {
        Serial.print(F("NULL "));
    }

    // IR Count
    Serial.print(F("IR_COUNT="));
    if (data.ir.is_valid) {
        Serial.print(data.ir.count);
        Serial.print(F(" "));
    } else {
        Serial.print(F("NULL "));
    }

    // Ultrasonic & Bin Fill
    Serial.print(F("FILL="));
    if (data.ultrasonic.is_valid) {
        Serial.print(data.ultrasonic.bin_fill_percent, 1);
        Serial.print(F("% (DIST="));
        Serial.print(data.ultrasonic.distance_cm, 1);
        Serial.print(F("cm) "));
    } else {
        Serial.print(F("NULL "));
    }

    // Wi-Fi Status
    Serial.print(F("WIFI="));
    Serial.println(wifiConnected ? F("CONNECTED") : F("DISCONNECTED"));
}

bool EnvTelemetrySender::sendHttpTelemetry(const EnvironmentalTelemetryData& data, bool isWifiConnected) {
    if (!isWifiConnected) {
        return false;
    }

    // Construct JSON document adhering to Phase 2 EnvironmentTelemetryPayload schema
    JsonDocument doc;
    doc["device_id"] = DEVICE_ID;
    doc["timestamp"] = data.timestamp_ms;
    doc["is_mock"] = data.is_mock;

    // Ambient Climate (DHT22)
    if (data.dht.is_valid) {
        doc["temperature_c"] = data.dht.temperature_c;
        doc["humidity_percent"] = data.dht.humidity_percent;
    } else {
        doc["temperature_c"] = nullptr;
        doc["humidity_percent"] = nullptr;
    }

    // Air Quality (MQ135)
    if (data.mq135.is_valid) {
        doc["mq135_raw"] = data.mq135.raw_adc;
        doc["mq135_voltage"] = data.mq135.voltage_v;
    } else {
        doc["mq135_raw"] = nullptr;
        doc["mq135_voltage"] = nullptr;
    }

    // IR Traffic / Pulse Counter
    if (data.ir.is_valid) {
        doc["ir_count"] = data.ir.count;
    } else {
        doc["ir_count"] = nullptr;
    }

    // Ultrasonic Bin Level
    if (data.ultrasonic.is_valid) {
        doc["ultrasonic_distance_cm"] = data.ultrasonic.distance_cm;
        doc["bin_fill_percent"] = data.ultrasonic.bin_fill_percent;
    } else {
        doc["ultrasonic_distance_cm"] = nullptr;
        doc["bin_fill_percent"] = nullptr;
    }

    // Diagnostic sensor status
    JsonObject statusObj = doc["sensor_status"].to<JsonObject>();
    statusObj["dht22"] = data.status_dht22 ? "OK" : "FAIL";
    statusObj["mq135"] = data.status_mq135 ? "OK" : "FAIL";
    statusObj["ir"] = data.status_ir ? "OK" : "FAIL";
    statusObj["ultrasonic"] = data.status_ultrasonic ? "OK" : "FAIL";

    String jsonString;
    serializeJson(doc, jsonString);

    // Initialize HTTP Client
    HTTPClient http;
    String targetUrl = String(BACKEND_BASE_URL) + String(TELEMETRY_ENDPOINT);

    http.begin(targetUrl);
    http.addHeader(F("Content-Type"), F("application/json"));
    http.setTimeout(3000); // 3-second timeout

    int httpResponseCode = http.POST(jsonString);

    if (httpResponseCode == HTTP_CODE_CREATED || httpResponseCode == HTTP_CODE_OK) {
        _consecutiveFailures = 0;
        http.end();
        return true;
    } else {
        _consecutiveFailures++;
        Serial.print(F("[HTTP FAIL] Target: "));
        Serial.print(targetUrl);
        Serial.print(F(" Code: "));
        Serial.print(httpResponseCode);
        Serial.print(F(" Error: "));
        Serial.println(http.errorToString(httpResponseCode).c_str());
        http.end();
        return false;
    }
}
