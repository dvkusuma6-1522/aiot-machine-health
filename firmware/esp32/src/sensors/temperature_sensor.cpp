/**
 * @file temperature_sensor.cpp
 * @brief Implementation of DS18B20 1-Wire Temperature Sensor Driver
 */

#include "temperature_sensor.h"
#include <Arduino.h>
#include <OneWire.h>
#include <DallasTemperature.h>

#if MOCK_MODE == 0
static OneWire oneWire(PIN_DS18B20_DATA);
static DallasTemperature dallasSensors(&oneWire);
#endif

TemperatureSensor::TemperatureSensor() : _isHealthy(false), _readCount(0) {}

bool TemperatureSensor::begin() {
#if MOCK_MODE == 1
    Serial.println(F("[MOCK_MODE] Initializing Simulated DS18B20 Temperature Sensor..."));
    _isHealthy = true;
    return true;
#else
    Serial.print(F("[HARDWARE] Probing DS18B20 on 1-Wire Pin GPIO "));
    Serial.print(PIN_DS18B20_DATA);
    Serial.println(F(" (requires 4.7k pull-up)..."));

    dallasSensors.begin();
    int count = dallasSensors.getDeviceCount();

    if (count == 0) {
        Serial.println(F("[ERROR] No DS18B20 temperature sensor detected on 1-Wire bus!"));
        _isHealthy = false;
        return false;
    }

    // Set 10-bit conversion resolution (0.25 C precision, ~187ms conversion time)
    dallasSensors.setResolution(10);
    // Enable non-blocking conversion wait
    dallasSensors.setWaitForConversion(true);

    _isHealthy = true;
    Serial.print(F("[HARDWARE] DS18B20 initialized successfully. Device count: "));
    Serial.println(count);
    return true;
#endif
}

bool TemperatureSensor::read(TemperatureData& outData) {
    _readCount++;

#if MOCK_MODE == 1
    // Deterministic mock temperature: 43.2 C nominal baseline with subtle slow drift
    outData.temperature_c = 43.2f + 0.1f * sinf(_readCount * 0.1f);
    outData.is_valid = true;
    outData.error = TEMP_ERR_NONE;
    return true;
#else
    if (!_isHealthy) {
        outData.temperature_c = TEMP_DISCONNECTED_SENTINEL;
        outData.is_valid = false;
        outData.error = TEMP_ERR_COMM_FAIL;
        return false;
    }

    dallasSensors.requestTemperatures();
    float tempC = dallasSensors.getTempCByIndex(0);

    // 1. Detect disconnected sensor sentinel (-127.0 C)
    if (tempC <= -126.9f && tempC >= -127.1f) {
        Serial.println(F("[WARN] DS18B20 reported -127C: Sensor disconnected or pull-up missing!"));
        outData.temperature_c = tempC;
        outData.is_valid = false;
        outData.error = TEMP_ERR_DISCONNECTED;
        return false;
    }

    // 2. Validate range bounds
    if (tempC < TEMP_MIN_VALID_C || tempC > TEMP_MAX_VALID_C) {
        Serial.print(F("[WARN] DS18B20 reading out of physical bounds: "));
        Serial.println(tempC);
        outData.temperature_c = tempC;
        outData.is_valid = false;
        outData.error = TEMP_ERR_OUT_OF_RANGE;
        return false;
    }

    outData.temperature_c = tempC;
    outData.is_valid = true;
    outData.error = TEMP_ERR_NONE;
    return true;
#endif
}
