/**
 * @file dht_sensor.h
 * @brief DHT22 Digital Temperature & Humidity Sensor Driver
 */

#ifndef DHT_SENSOR_H
#define DHT_SENSOR_H

#include <Arduino.h>
#include <DHT.h>
#include "config.h"

struct DhtReading {
    float temperature_c;
    float humidity_percent;
    bool is_valid;
};

class DhtSensor {
public:
    DhtSensor();
    bool begin();
    DhtReading read();
    DhtReading readMock(uint32_t timestampMs);

private:
    DHT _dht;
    uint32_t _lastReadTimeMs;
    DhtReading _lastValidReading;
};

#endif // DHT_SENSOR_H
