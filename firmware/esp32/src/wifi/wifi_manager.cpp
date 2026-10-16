/**
 * @file wifi_manager.cpp
 * @brief Non-Blocking Wi-Fi Connection and Reconnection Implementation
 */

#include "wifi_manager.h"
#include <Arduino.h>
#include <WiFi.h>
#include "config.h"
#include "secrets.h"

WiFiManager::WiFiManager() 
    : _lastReconnectAttemptMs(0), _wasConnected(false) {}

void WiFiManager::begin() {
    Serial.println(F("[WIFI] Initializing Wi-Fi in Station (STA) mode..."));
    WiFi.mode(WIFI_STA);
    WiFi.disconnect(true);
    delay(100);

    Serial.print(F("[WIFI] Connecting to SSID: "));
    Serial.println(WIFI_SSID);

    // Initiate non-blocking connection
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    _lastReconnectAttemptMs = millis();
}

void WiFiManager::update() {
    bool currentConnected = (WiFi.status() == WL_CONNECTED);

    // Transition: Disconnected -> Connected
    if (currentConnected && !_wasConnected) {
        _wasConnected = true;
        Serial.println(F("[WIFI] Successfully connected!"));
        Serial.print(F("[WIFI] IP Address: "));
        Serial.println(WiFi.localIP());
        Serial.print(F("[WIFI] Signal Strength (RSSI): "));
        Serial.print(WiFi.RSSI());
        Serial.println(F(" dBm"));
    }
    // Transition: Connected -> Disconnected
    else if (!currentConnected && _wasConnected) {
        _wasConnected = false;
        Serial.println(F("[WIFI] Connection lost! Will attempt background reconnection."));
        _lastReconnectAttemptMs = millis();
    }
    // Continuous background reconnection attempt without blocking
    else if (!currentConnected) {
        uint32_t now = millis();
        if (now - _lastReconnectAttemptMs >= WIFI_RECONNECT_INTERVAL_MS) {
            _lastReconnectAttemptMs = now;
            Serial.println(F("[WIFI] Retrying connection to AP..."));
            WiFi.disconnect();
            WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
        }
    }
}

bool WiFiManager::isConnected() const {
    return (WiFi.status() == WL_CONNECTED);
}

IPAddress WiFiManager::getIP() const {
    return WiFi.localIP();
}

int32_t WiFiManager::getRSSI() const {
    return WiFi.RSSI();
}
