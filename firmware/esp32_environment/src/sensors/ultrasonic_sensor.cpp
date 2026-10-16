/**
 * @file ultrasonic_sensor.cpp
 * @brief HC-SR04 Timing, Echo Acquisition, Distance & Bin Fill Calculation
 */

#include "ultrasonic_sensor.h"
#include <math.h>

UltrasonicSensor::UltrasonicSensor() {}

bool UltrasonicSensor::begin() {
    pinMode(PIN_ULTRASONIC_TRIG, OUTPUT);
    pinMode(PIN_ULTRASONIC_ECHO, INPUT);
    digitalWrite(PIN_ULTRASONIC_TRIG, LOW);
    delay(20);
    return true;
}

float UltrasonicSensor::calculateFillPercentage(float distanceCm) {
    float emptyDist = BIN_EMPTY_DISTANCE_CM;
    float fullDist = BIN_FULL_DISTANCE_CM;
    float span = emptyDist - fullDist;

    if (span <= 0.0f) {
        return 0.0f;
    }

    float fillPct = ((emptyDist - distanceCm) / span) * 100.0f;
    if (fillPct < 0.0f) fillPct = 0.0f;
    if (fillPct > 100.0f) fillPct = 100.0f;
    return fillPct;
}

UltrasonicReading UltrasonicSensor::read() {
    UltrasonicReading result;

    // Send 10 microsecond trigger pulse
    digitalWrite(PIN_ULTRASONIC_TRIG, LOW);
    delayMicroseconds(2);
    digitalWrite(PIN_ULTRASONIC_TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(PIN_ULTRASONIC_TRIG, LOW);

    // Measure echo pulse duration (timeout 30000 us)
    unsigned long duration = pulseIn(PIN_ULTRASONIC_ECHO, HIGH, ULTRASONIC_TIMEOUT_US);

    if (duration == 0) {
        // Echo timed out or sensor disconnected
        result.distance_cm = 0.0f;
        result.bin_fill_percent = 0.0f;
        result.is_valid = false;
        return result;
    }

    // Distance in cm = (duration_us * 0.0343 cm/us) / 2
    float distance = (duration * 0.0343f) / 2.0f;

    // Boundary check
    if (distance < DISTANCE_MIN_VALID_CM || distance > DISTANCE_MAX_VALID_CM) {
        result.distance_cm = 0.0f;
        result.bin_fill_percent = 0.0f;
        result.is_valid = false;
        return result;
    }

    result.distance_cm = distance;
    result.bin_fill_percent = calculateFillPercentage(distance);
    result.is_valid = true;
    return result;
}

UltrasonicReading UltrasonicSensor::readMock(uint32_t timestampMs) {
    UltrasonicReading mock;
    float timeSec = timestampMs / 1000.0f;

    // Simulate steady waste accumulation: bin fill between 45% and 65%
    float simulatedFill = 55.0f + 10.0f * sinf(timeSec * 0.02f);
    if (simulatedFill < 0.0f) simulatedFill = 0.0f;
    if (simulatedFill > 100.0f) simulatedFill = 100.0f;

    // Corresponding distance: 100cm empty down to 10cm full
    float span = BIN_EMPTY_DISTANCE_CM - BIN_FULL_DISTANCE_CM;
    float simulatedDist = BIN_EMPTY_DISTANCE_CM - (simulatedFill / 100.0f) * span;

    mock.distance_cm = simulatedDist;
    mock.bin_fill_percent = simulatedFill;
    mock.is_valid = true;
    return mock;
}
