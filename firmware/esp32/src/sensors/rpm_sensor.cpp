/**
 * @file rpm_sensor.cpp
 * @brief Implementation of Interrupt-Driven Hall-Effect RPM Sensor
 */

#include "rpm_sensor.h"
#include <Arduino.h>

static volatile uint32_t s_pulseCount = 0;
static volatile uint32_t s_lastPulseMicros = 0;
static portMUX_TYPE s_rpmMux = portMUX_INITIALIZER_UNLOCKED;

void IRAM_ATTR RpmSensor::onPulseISR() {
    uint32_t now = micros();
    // Software debouncing: reject transitions faster than HALL_DEBOUNCE_MICROS
    if ((now - s_lastPulseMicros) >= HALL_DEBOUNCE_MICROS) {
        portENTER_CRITICAL_ISR(&s_rpmMux);
        s_pulseCount++;
        s_lastPulseMicros = now;
        portEXIT_CRITICAL_ISR(&s_rpmMux);
    }
}

RpmSensor::RpmSensor() : _isHealthy(false), _readCount(0) {}

bool RpmSensor::begin() {
#if MOCK_MODE == 1
    Serial.println(F("[MOCK_MODE] Initializing Simulated Hall RPM Sensor..."));
    _isHealthy = true;
    return true;
#else
    Serial.print(F("[HARDWARE] Configuring Hall-Effect Sensor on GPIO "));
    Serial.print(PIN_HALL_SENSOR);
    Serial.println(F(" (INPUT_PULLUP, FALLING edge interrupt)..."));

    pinMode(PIN_HALL_SENSOR, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_HALL_SENSOR), RpmSensor::onPulseISR, FALLING);

    _isHealthy = true;
    Serial.println(F("[HARDWARE] Hall RPM interrupt attached successfully."));
    return true;
#endif
}

bool RpmSensor::calculateRPM(uint32_t elapsedMs, RpmData& outData) {
    _readCount++;

#if MOCK_MODE == 1
    // Deterministic mock RPM: 1498 RPM with minor +/- 2 RPM natural variation
    outData.raw_pulses = 25;
    outData.rpm = 1498.0f + 2.0f * sinf(_readCount * 0.3f);
    outData.is_valid = true;
    return true;
#else
    if (elapsedMs == 0) {
        outData.raw_pulses = 0;
        outData.rpm = 0.0f;
        outData.is_valid = false;
        return false;
    }

    // Atomic fetch and reset of interrupt pulse accumulator
    portENTER_CRITICAL(&s_rpmMux);
    uint32_t count = s_pulseCount;
    s_pulseCount = 0;
    portEXIT_CRITICAL(&s_rpmMux);

    outData.raw_pulses = count;

    // RPM = (pulses * 60,000 ms/min) / (elapsedMs * pulses_per_revolution)
    float factor = 60000.0f / (float)(elapsedMs * PULSES_PER_REVOLUTION);
    outData.rpm = (float)count * factor;
    outData.is_valid = true;
    return true;
#endif
}
