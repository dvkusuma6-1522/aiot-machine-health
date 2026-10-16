/**
 * @file dht_sensor.cpp
 * @brief DHT22 Sensor Implementation with Validation and Mock Fallback
 */

#include "dht_sensor.h"
#include <math.h>

DhtSensor::DhtSensor()
    : _dht(PIN_DHT_DATA, DHT22), _lastReadTimeMs(0) {
    _lastValidReading = {24.0f, 50.0f, false};
}

bool DhtSensor::begin() {
    _dht.begin();
    delay(50);

    // Initial probe to verify communication
    float t = _dht.readTemperature();
    float h = _dht.readHumidity();

    if (isnan(t) || isnan(h)) {
        return false;
    }
    if (t < TEMP_MIN_VALID_C || t > TEMP_MAX_VALID_C ||
        h < HUMIDITY_MIN_VALID || h > HUMIDITY_MAX_VALID) {
        return false;
    }

    _lastValidReading.temperature_c = t;
    _lastValidReading.humidity_percent = h;
    _lastValidReading.is_valid = true;
    _lastReadTimeMs = millis();
    return true;
}

DhtReading DhtSensor::read() {
    uint32_t now = millis();

    // Respect hardware minimum interval (2000 ms)
    if (now - _lastReadTimeMs < DHT_SAMPLE_INTERVAL_MS && _lastValidReading.is_valid) {
        return _lastValidReading;
    }

    float t = _dht.readTemperature();
    float h = _dht.readHumidity();
    _lastReadTimeMs = now;

    DhtReading result;
    if (isnan(t) || isnan(h)) {
        result.temperature_c = 0.0f;
        result.humidity_percent = 0.0f;
        result.is_valid = false;
        return result;
    }

    if (t < TEMP_MIN_VALID_C || t > TEMP_MAX_VALID_C ||
        h < HUMIDITY_MIN_VALID || h > HUMIDITY_MAX_VALID) {
        result.temperature_c = 0.0f;
        result.humidity_percent = 0.0f;
        result.is_valid = false;
        return result;
    }

    result.temperature_c = t;
    result.humidity_percent = h;
    result.is_valid = true;
    _lastValidReading = result;
    return result;
}

DhtReading DhtSensor::readMock(uint32_t timestampMs) {
    DhtReading mock;
    float timeSec = timestampMs / 1000.0f;

    // Smooth sinusoidal temperature between 23.5C and 26.5C
    mock.temperature_c = 25.0f + 1.5f * sinf(timeSec * 0.05f);

    // Complementary humidity variation between 52% and 62%
    mock.humidity_percent = 57.0f + 5.0f * cosf(timeSec * 0.03f);

    mock.is_valid = true;
    return mock;
}
