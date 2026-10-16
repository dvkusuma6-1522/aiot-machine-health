/**
 * @file wifi_manager.cpp
 * @brief Non-blocking Wi-Fi lifecycle implementation
 */

#include "wifi_manager.h"

WiFiManager::WiFiManager() : _lastReconnectAttemptMs(0) {}

void WiFiManager::begin() {
    Serial.print(F("[WIFI] Connecting to SSID: "));
    Serial.println(WIFI_SSID);

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    // Initial brief non-blocking wait (up to 2 seconds)
    uint32_t startMs = millis();
    while (WiFi.status() != WL_CONNECTED && (millis() - startMs < 2000)) {
        delay(100);
        Serial.print(F("."));
    }
    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {
        Serial.print(F("[WIFI] Connected! IP Address: "));
        Serial.println(WiFi.localIP());
        Serial.print(F("[WIFI] RSSI Signal: "));
        Serial.print(WiFi.RSSI());
        Serial.println(F(" dBm"));
    } else {
        Serial.println(F("[WIFI] Initial connection pending. Background auto-reconnect active."));
    }
}

void WiFiManager::update() {
    if (WiFi.status() != WL_CONNECTED) {
        uint32_t now = millis();
        if (now - _lastReconnectAttemptMs >= RECONNECT_INTERVAL_MS) {
            _lastReconnectAttemptMs = now;
            Serial.println(F("[WIFI] Connection lost. Attempting background reconnect..."));
            WiFi.disconnect();
            WiFi.reconnect();
        }
    }
}

bool WiFiManager::isConnected() {
    return (WiFi.status() == WL_CONNECTED);
}

wl_status_t WiFiManager::getStatus() {
    return WiFi.status();
}

IPAddress WiFiManager::getLocalIP() {
    return WiFi.localIP();
}

int8_t WiFiManager::getRssi() {
    return WiFi.RSSI();
}
