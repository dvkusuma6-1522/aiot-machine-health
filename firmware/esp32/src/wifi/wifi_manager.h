/**
 * @file wifi_manager.h
 * @brief Non-Blocking Wi-Fi Manager for ESP32
 */

#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <stdint.h>
#include <IPAddress.h>

class WiFiManager {
public:
    WiFiManager();

    /**
     * @brief Start Wi-Fi connection in station mode (non-blocking)
     */
    void begin();

    /**
     * @brief Periodic update called in main loop to maintain Wi-Fi connection
     */
    void update();

    /**
     * @brief Check whether currently connected to Wi-Fi AP
     */
    bool isConnected() const;

    /**
     * @brief Get local assigned IP address
     */
    IPAddress getIP() const;

    /**
     * @brief Get Wi-Fi Received Signal Strength Indicator (RSSI) in dBm
     */
    int32_t getRSSI() const;

private:
    uint32_t _lastReconnectAttemptMs;
    bool _wasConnected;
};

#endif // WIFI_MANAGER_H
