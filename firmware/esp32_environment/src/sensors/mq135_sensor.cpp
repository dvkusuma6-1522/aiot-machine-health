/**
 * @file mq135_sensor.cpp
 * @brief MQ135 Analog Acquisition, Voltage Divider Translation, and Validation
 */

#include "mq135_sensor.h"
#include <math.h>

Mq135Sensor::Mq135Sensor() {}

bool Mq135Sensor::begin() {
    pinMode(PIN_MQ135_ANALOG, INPUT);
    analogSetPinAttenuation(PIN_MQ135_ANALOG, ADC_11db);

    // Initial check: ADC read must be accessible on GPIO 34
    int val = analogRead(PIN_MQ135_ANALOG);
    // ADC1 pins return 0-4095. A completely disconnected pin or grounded input returns 0-100.
    return (val >= 0 && val <= 4095);
}

float Mq135Sensor::readAveragedAdc(uint8_t samples) {
    uint32_t sum = 0;
    for (uint8_t i = 0; i < samples; i++) {
        sum += analogRead(PIN_MQ135_ANALOG);
        delayMicroseconds(50);
    }
    return (float)sum / (float)samples;
}

Mq135Reading Mq135Sensor::read() {
    Mq135Reading result;

    float rawAdc = readAveragedAdc(8);

    // Calculate voltage at the ESP32 pin (0.0V - 3.3V)
    float vAdc = (rawAdc / ESP32_ADC_MAX_COUNT) * ESP32_ADC_VREF;

    // Scale by voltage divider ratio (10k / 20k -> 1.5x) to get true sensor output voltage
    float vSensor = vAdc * MQ135_DIVIDER_RATIO;

    // Physical sanity validation
    if (vSensor < MQ135_VOLTAGE_MIN_VALID || vSensor > MQ135_VOLTAGE_MAX_VALID) {
        result.raw_adc = 0.0f;
        result.voltage_v = 0.0f;
        result.is_valid = false;
        return result;
    }

    result.raw_adc = rawAdc;
    result.voltage_v = vSensor;
    result.is_valid = true;
    return result;
}

Mq135Reading Mq135Sensor::readMock(uint32_t timestampMs) {
    Mq135Reading mock;
    float timeSec = timestampMs / 1000.0f;

    // Normal indoor air quality baseline: 1.15V to 1.35V with slight organic drift
    float simulatedVoltage = 1.25f + 0.15f * sinf(timeSec * 0.04f) + 0.05f * cosf(timeSec * 0.1f);

    // Back-calculate simulated raw ADC
    float vAdc = simulatedVoltage / MQ135_DIVIDER_RATIO;
    float rawAdc = (vAdc / ESP32_ADC_VREF) * ESP32_ADC_MAX_COUNT;

    mock.voltage_v = simulatedVoltage;
    mock.raw_adc = rawAdc;
    mock.is_valid = true;
    return mock;
}
