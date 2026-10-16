/**
 * @file telemetry_sender.h
 * @brief Telemetry Serialization, HTTP REST Transmission, and Serial Logging
 */

#ifndef TELEMETRY_SENDER_H
#define TELEMETRY_SENDER_H

#include <stdint.h>
#include "config.h"
#include "sensors/vibration_sensor.h"
#include "sensors/temperature_sensor.h"
#include "sensors/current_sensor.h"
#include "sensors/rpm_sensor.h"

struct UnifiedTelemetry {
    uint32_t timestamp_ms;
    bool is_mock;
    
    // Sensor Health Status
    bool status_mpu6050;
    bool status_ds18b20;
    bool status_ina219;
    bool status_hall;

    // Physical Measurements
    TemperatureData temp;
    VibrationData vib;
    CurrentData curr;
    RpmData rpm;
};

class TelemetrySender {
public:
    TelemetrySender();

    /**
     * @brief Output formatted human-readable diagnostic line to Serial
     * Format: [REAL] TEMP=43.2C ACCEL=(0.12,0.08,1.04) CURRENT=1120mA RPM=1498 WIFI=CONNECTED
     */
    void logToSerial(const UnifiedTelemetry& data, bool wifiConnected);

    /**
     * @brief Serialize reading into JSON buffer and HTTP POST to FastAPI backend
     * @param data Unified sensor telemetry
     * @param isWifiConnected Current Wi-Fi link status
     * @return true if HTTP 200/201 response received
     */
    bool sendHttpTelemetry(const UnifiedTelemetry& data, bool isWifiConnected);

private:
    uint32_t _consecutiveFailures;
};

#endif // TELEMETRY_SENDER_H
