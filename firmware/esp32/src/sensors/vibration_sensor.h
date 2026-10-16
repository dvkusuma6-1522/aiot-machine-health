/**
 * @file vibration_sensor.h
 * @brief MPU-6050 3-Axis Accelerometer and Gyroscope Driver
 */

#ifndef VIBRATION_SENSOR_H
#define VIBRATION_SENSOR_H

#include <stdint.h>
#include "config.h"

struct VibrationData {
    float accel_x; // Acceleration in g
    float accel_y; // Acceleration in g
    float accel_z; // Acceleration in g
    float gyro_x;  // Angular velocity in deg/s
    float gyro_y;  // Angular velocity in deg/s
    float gyro_z;  // Angular velocity in deg/s
    bool is_valid; // True if reading succeeded within physical bounds
};

class VibrationSensor {
public:
    VibrationSensor();
    
    /**
     * @brief Initialize I2C communication and configure MPU-6050
     * @return true if sensor responded and initialized, false otherwise
     */
    bool begin();

    /**
     * @brief Sample current acceleration and gyro values
     * @param outData Reference to VibrationData struct to receive readings
     * @return true if valid reading was captured
     */
    bool read(VibrationData& outData);

    /**
     * @brief Check if the hardware sensor passed initialization
     */
    bool isHealthy() const { return _isHealthy; }

private:
    bool _isHealthy;
    uint32_t _sampleCount;
};

#endif // VIBRATION_SENSOR_H
