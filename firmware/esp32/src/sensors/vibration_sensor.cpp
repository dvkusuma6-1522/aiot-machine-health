/**
 * @file vibration_sensor.cpp
 * @brief Implementation of MPU-6050 Vibration Sensor Driver
 */

#include "vibration_sensor.h"
#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <math.h>

#if MOCK_MODE == 0
static Adafruit_MPU6050 mpu;
#endif

VibrationSensor::VibrationSensor() : _isHealthy(false), _sampleCount(0) {}

bool VibrationSensor::begin() {
#if MOCK_MODE == 1
    Serial.println(F("[MOCK_MODE] Initializing Simulated MPU-6050 Vibration Sensor..."));
    _isHealthy = true;
    return true;
#else
    Serial.println(F("[HARDWARE] Probing MPU-6050 on I2C Bus (SDA=21, SCL=22, Addr=0x68)..."));
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, I2C_FREQUENCY_HZ);

    // Verify sensor presence on I2C address
    Wire.beginTransmission(MPU6050_I2C_ADDRESS);
    if (Wire.endTransmission() != 0) {
        Serial.println(F("[ERROR] MPU-6050 not detected at I2C address 0x68!"));
        _isHealthy = false;
        return false;
    }

    if (!mpu.begin(MPU6050_I2C_ADDRESS, &Wire)) {
        Serial.println(F("[ERROR] Failed to initialize Adafruit MPU6050 library!"));
        _isHealthy = false;
        return false;
    }

    // Configure accelerometer for machine vibration (+/- 4g range)
    mpu.setAccelerometerRange(MPU6050_RANGE_4_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_44_HZ);

    _isHealthy = true;
    Serial.println(F("[HARDWARE] MPU-6050 successfully initialized. Range: +/-4G, Filter: 44Hz."));
    return true;
#endif
}

bool VibrationSensor::read(VibrationData& outData) {
    _sampleCount++;

#if MOCK_MODE == 1
    // Deterministic mock vibration waveform for bench testing
    // Z-axis: 1.0g gravity baseline + 25Hz motor rotational fundamental vibration
    float t = (_sampleCount * VIBRATION_SAMPLE_INTERVAL_MS) / 1000.0f;
    float fundamental = 0.08f * sinf(2.0f * 3.14159f * 25.0f * t);
    float harmonic = 0.02f * sinf(2.0f * 3.14159f * 50.0f * t);

    outData.accel_x = 0.05f * sinf(2.0f * 3.14159f * 25.0f * t);
    outData.accel_y = 0.04f * cosf(2.0f * 3.14159f * 25.0f * t);
    outData.accel_z = 1.00f + fundamental + harmonic;

    outData.gyro_x = 0.10f;
    outData.gyro_y = 0.15f;
    outData.gyro_z = 0.20f;
    outData.is_valid = true;
    return true;
#else
    if (!_isHealthy) {
        outData.accel_x = 0.0f;
        outData.accel_y = 0.0f;
        outData.accel_z = 0.0f;
        outData.gyro_x = 0.0f;
        outData.gyro_y = 0.0f;
        outData.gyro_z = 0.0f;
        outData.is_valid = false;
        return false;
    }

    sensors_event_t a, g, temp;
    if (!mpu.getEvent(&a, &g, &temp)) {
        outData.is_valid = false;
        return false;
    }

    // Convert m/s^2 to g (1g = 9.80665 m/s^2)
    const float G_TO_MS2 = 9.80665f;
    outData.accel_x = a.acceleration.x / G_TO_MS2;
    outData.accel_y = a.acceleration.y / G_TO_MS2;
    outData.accel_z = a.acceleration.z / G_TO_MS2;

    // Convert rad/s to deg/s
    const float RAD_TO_DEG_FACTOR = 57.29578f;
    outData.gyro_x = g.gyro.x * RAD_TO_DEG_FACTOR;
    outData.gyro_y = g.gyro.y * RAD_TO_DEG_FACTOR;
    outData.gyro_z = g.gyro.z * RAD_TO_DEG_FACTOR;

    // Validate sensor reading within physical safety bounds
    if (fabsf(outData.accel_x) > ACCEL_MAX_G ||
        fabsf(outData.accel_y) > ACCEL_MAX_G ||
        fabsf(outData.accel_z) > ACCEL_MAX_G) {
        outData.is_valid = false;
        return false;
    }

    outData.is_valid = true;
    return true;
#endif
}
