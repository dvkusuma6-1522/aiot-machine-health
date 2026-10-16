/**
 * @file ultrasonic_sensor.h
 * @brief HC-SR04 Ultrasonic Waste Bin Level Sensor Driver
 */

#ifndef ULTRASONIC_SENSOR_H
#define ULTRASONIC_SENSOR_H

#include <Arduino.h>
#include "config.h"

struct UltrasonicReading {
    float distance_cm;
    float bin_fill_percent;
    bool is_valid;
};

class UltrasonicSensor {
public:
    UltrasonicSensor();
    bool begin();
    UltrasonicReading read();
    UltrasonicReading readMock(uint32_t timestampMs);

private:
    float calculateFillPercentage(float distanceCm);
};

#endif // ULTRASONIC_SENSOR_H
