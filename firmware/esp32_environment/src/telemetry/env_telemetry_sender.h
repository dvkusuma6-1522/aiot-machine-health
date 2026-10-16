/**
 * @file env_telemetry_sender.h
 * @brief Telemetry Formatting, JSON Serialization, and HTTP Client Header
 */

#ifndef ENV_TELEMETRY_SENDER_H
#define ENV_TELEMETRY_SENDER_H

#include <Arduino.h>
#include "env_telemetry.h"

class EnvTelemetrySender {
public:
    EnvTelemetrySender();
    void logToSerial(const EnvironmentalTelemetryData& data, bool wifiConnected);
    bool sendHttpTelemetry(const EnvironmentalTelemetryData& data, bool isWifiConnected);
    uint32_t getConsecutiveFailures() const { return _consecutiveFailures; }

private:
    uint32_t _consecutiveFailures;
};

#endif // ENV_TELEMETRY_SENDER_H
