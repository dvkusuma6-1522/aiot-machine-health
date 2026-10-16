/**
 * @file current_sensor.h
 * @brief INA219 High-Side I2C DC Current and Voltage Sensor Driver
 */

#ifndef CURRENT_SENSOR_H
#define CURRENT_SENSOR_H

#include <stdint.h>
#include "config.h"

struct CurrentData {
    float bus_voltage_v;    // Total voltage at load (V)
    float shunt_voltage_mv; // Shunt drop (mV)
    float current_ma;       // Current in milliamperes (mA)
    float power_mw;         // Power in milliwatts (mW)
    bool is_valid;
};

class CurrentSensor {
public:
    CurrentSensor();

    /**
     * @brief Initialize INA219 sensor on I2C bus
     * @return true if detected and initialized, false otherwise
     */
    bool begin();

    /**
     * @brief Read current, bus voltage, and power
     * @param outData Reference to CurrentData struct
     * @return true if valid reading obtained
     */
    bool read(CurrentData& outData);

    /**
     * @brief Check if hardware sensor is operational
     */
    bool isHealthy() const { return _isHealthy; }

private:
    bool _isHealthy;
    uint32_t _readCount;
};

#endif // CURRENT_SENSOR_H
