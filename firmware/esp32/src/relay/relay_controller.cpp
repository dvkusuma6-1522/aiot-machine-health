/**
 * @file relay_controller.cpp
 * @brief Implementation of Safe Active-LOW Relay Controller
 */

#include "relay_controller.h"
#include <Arduino.h>

RelayController::RelayController() : _isRelayOn(false) {}

void RelayController::begin() {
    Serial.print(F("[SAFETY] Initializing Relay on GPIO "));
    Serial.print(PIN_RELAY);
    Serial.println(F(" (Active-LOW, Default: SAFE / OFF)..."));

    // CRITICAL SAFETY SEQUENCE:
    // Write HIGH (inactive state for active-LOW) to output latch BEFORE setting pin mode
    // to prevent any brief ground glitch that could briefly trigger the relay during boot.
    digitalWrite(PIN_RELAY, RELAY_INACTIVE_STATE);
    pinMode(PIN_RELAY, OUTPUT);
    digitalWrite(PIN_RELAY, RELAY_INACTIVE_STATE);

    _isRelayOn = false;
    Serial.println(F("[SAFETY] Relay verified in SAFE / DE-ENERGIZED (OFF) state."));
}

void RelayController::relayOn() {
    // Active LOW: Drive pin LOW to energize coil
    digitalWrite(PIN_RELAY, RELAY_ACTIVE_STATE);
    _isRelayOn = true;
    Serial.println(F("[RELAY] State changed to ON (Energized / Motor circuit closed)."));
}

void RelayController::relayOff() {
    // Active LOW: Drive pin HIGH to de-energize coil (SAFE default)
    digitalWrite(PIN_RELAY, RELAY_INACTIVE_STATE);
    _isRelayOn = false;
    Serial.println(F("[RELAY] State changed to OFF (De-energized / Motor circuit open / SAFE)."));
}
