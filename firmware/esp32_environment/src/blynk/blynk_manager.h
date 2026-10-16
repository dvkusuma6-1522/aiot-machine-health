/**
 * @file blynk_manager.h
 * @brief Non-Blocking Blynk IoT Cloud Manager for ESP32 Environmental Node
 * @project AI-Powered Multi-Sensor Environmental Monitoring System
 *
 * Maps environmental telemetry to Blynk Virtual Pins V0-V7:
 * V0: Temperature (°C)
 * V1: Humidity (%)
 * V2: MQ135 Voltage (V)
 * V3: IR Event Count
 * V4: Waste-Bin Fill (%)
 * V5: 1-Hour Ahead MQ135 Forecast (V)
 * V6: AI Anomaly Status (0 = Normal, 1 = Outlier)
 * V7: Device Status / Alert Notification String
 */

#ifndef ENV_BLYNK_MANAGER_H
#define ENV_BLYNK_MANAGER_H

#include <Arduino.h>
#include "config.h"
#include "secrets.h"
#include "telemetry/env_telemetry.h"

class BlynkManager {
public:
    BlynkManager();

    /**
     * @brief Configure and initialize Blynk client in non-blocking mode.
     * If credentials are empty or dummy, safely disables Blynk cloud calls.
     */
    void begin();

    /**
     * @brief Periodic update function. Runs Blynk event loop and syncs datastreams.
     * @param data Current environmental observation packet.
     * @param wifiConnected Current Wi-Fi link status.
     */
    void update(const EnvironmentalTelemetryData& data, bool wifiConnected);

    /**
     * @brief Check whether Blynk is actively connected to Blynk Cloud.
     */
    bool isConnected() const;

    /**
     * @brief Check whether valid Blynk credentials were provided.
     */
    bool isConfigured() const;

private:
    bool m_configured;
    uint32_t m_lastPublishMs;

    // Alert cooldown trackers (timestamps in ms)
    uint32_t m_lastGasAlertMs;
    uint32_t m_lastTempAlertMs;
    uint32_t m_lastBinAlertMs;
    uint32_t m_lastFaultAlertMs;

    void publishTelemetry(const EnvironmentalTelemetryData& data);
    void evaluateThresholdAlerts(const EnvironmentalTelemetryData& data);
};

#endif // ENV_BLYNK_MANAGER_H
