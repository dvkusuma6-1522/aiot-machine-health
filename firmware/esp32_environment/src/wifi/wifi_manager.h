/**
 * @file wifi_manager.h
 * @brief Non-Blocking Wi-Fi Connection Manager for Environmental Node
 */

#ifndef ENV_WIFI_MANAGER_H
#define ENV_WIFI_MANAGER_H

#include <Arduino.h>
#include <WiFi.h>
#include "secrets.h"

class WiFiManager {
public:
    WiFiManager();
    void begin();
    void update();
    bool isConnected();
    wl_status_t getStatus();
    IPAddress getLocalIP();
    int8_t getRssi();

private:
    uint32_t _lastReconnectAttemptMs;
    static const uint32_t RECONNECT_INTERVAL_MS = 5000;
};

#endif // ENV_WIFI_MANAGER_H
