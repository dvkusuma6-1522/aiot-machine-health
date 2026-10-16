/**
 * @file temperature_sensor.h
 * @brief DS18B20 1-Wire Digital Temperature Sensor Driver
 */

#ifndef TEMPERATURE_SENSOR_H
#define TEMPERATURE_SENSOR_H

#include <stdint.h>
#include "config.h"

enum TemperatureError {
    TEMP_ERR_NONE = 0,
    TEMP_ERR_DISCONNECTED,
    TEMP_ERR_OUT_OF_RANGE,
    TEMP_ERR_COMM_FAIL
};

struct TemperatureData {
    float temperature_c;
    bool is_valid;
    TemperatureError error;
};

class TemperatureSensor {
public:
    TemperatureSensor();

    /**
     * @brief Initialize 1-Wire bus and probe DS18B20
     * @return true if at least one DS18B20 was found, false otherwise
     */
    bool begin();

    /**
     * @brief Request temperature conversion and read value
     * @param outData Reference to TemperatureData struct
     * @return true if valid reading obtained
     */
    bool read(TemperatureData& outData);

    /**
     * @brief Check if hardware sensor is operational
     */
    bool isHealthy() const { return _isHealthy; }

private:
    bool _isHealthy;
    uint32_t _readCount;
};

#endif // TEMPERATURE_SENSOR_H
