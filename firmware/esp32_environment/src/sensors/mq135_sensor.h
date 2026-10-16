/**
 * @file mq135_sensor.h
 * @brief MQ135 Air Quality Analog Voltage Sensor Driver
 */

#ifndef MQ135_SENSOR_H
#define MQ135_SENSOR_H

#include <Arduino.h>
#include "config.h"

struct Mq135Reading {
    float raw_adc;
    float voltage_v;
    bool is_valid;
};

class Mq135Sensor {
public:
    Mq135Sensor();
    bool begin();
    Mq135Reading read();
    Mq135Reading readMock(uint32_t timestampMs);

private:
    float readAveragedAdc(uint8_t samples = 8);
};

#endif // MQ135_SENSOR_H
