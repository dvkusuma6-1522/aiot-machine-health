/**
 * @file rpm_sensor.h
 * @brief Interrupt-Driven A3144 Hall-Effect RPM Sensor Driver
 */

#ifndef RPM_SENSOR_H
#define RPM_SENSOR_H

#include <stdint.h>
#include <Arduino.h>
#include "config.h"

struct RpmData {
    uint32_t raw_pulses;
    float rpm;
    bool is_valid;
};

class RpmSensor {
public:
    RpmSensor();

    /**
     * @brief Configure GPIO 18 as INPUT_PULLUP and attach hardware interrupt
     * @return true if interrupt attached successfully
     */
    bool begin();

    /**
     * @brief Compute rotational speed based on accumulated pulses over interval
     * @param elapsedMs Time elapsed since last calculation in milliseconds
     * @param outData Reference to RpmData struct
     * @return true if valid calculation completed
     */
    bool calculateRPM(uint32_t elapsedMs, RpmData& outData);

    /**
     * @brief Sensor health check
     */
    bool isHealthy() const { return _isHealthy; }

    /**
     * @brief Static interrupt service routine (ISR) called on magnetic pulse
     */
    static void onPulseISR();

private:
    bool _isHealthy;
    uint32_t _readCount;
};

#endif // RPM_SENSOR_H
