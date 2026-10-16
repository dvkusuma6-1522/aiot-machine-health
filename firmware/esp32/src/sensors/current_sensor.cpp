/**
 * @file current_sensor.cpp
 * @brief Implementation of INA219 Current and Voltage Sensor Driver
 */

#include "current_sensor.h"
#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_INA219.h>

#if MOCK_MODE == 0
static Adafruit_INA219 ina219(INA219_I2C_ADDRESS);
#endif

CurrentSensor::CurrentSensor() : _isHealthy(false), _readCount(0) {}

bool CurrentSensor::begin() {
#if MOCK_MODE == 1
    Serial.println(F("[MOCK_MODE] Initializing Simulated INA219 Current Sensor..."));
    _isHealthy = true;
    return true;
#else
    Serial.print(F("[HARDWARE] Probing INA219 on I2C address 0x"));
    Serial.println(INA219_I2C_ADDRESS, HEX);

    Wire.beginTransmission(INA219_I2C_ADDRESS);
    if (Wire.endTransmission() != 0) {
        Serial.println(F("[ERROR] INA219 not detected at I2C address 0x40!"));
        _isHealthy = false;
        return false;
    }

    if (!ina219.begin(&Wire)) {
        Serial.println(F("[ERROR] Failed to initialize Adafruit INA219 library!"));
        _isHealthy = false;
        return false;
    }

    // Default calibration: 32V, 2A max range with standard 0.1 ohm shunt resistor
    ina219.setCalibration_32V_2A();

    _isHealthy = true;
    Serial.println(F("[HARDWARE] INA219 initialized successfully (32V, 2A calibration)."));
    return true;
#endif
}

bool CurrentSensor::read(CurrentData& outData) {
    _readCount++;

#if MOCK_MODE == 1
    // Deterministic mock readings: 11.8V bus, 1120mA nominal current, 13.2W power
    outData.bus_voltage_v = 11.8f;
    outData.shunt_voltage_mv = 112.0f;
    outData.current_ma = 1120.0f + 10.0f * sinf(_readCount * 0.2f);
    outData.power_mw = outData.bus_voltage_v * outData.current_ma;
    outData.is_valid = true;
    return true;
#else
    if (!_isHealthy) {
        outData.bus_voltage_v = 0.0f;
        outData.shunt_voltage_mv = 0.0f;
        outData.current_ma = 0.0f;
        outData.power_mw = 0.0f;
        outData.is_valid = false;
        return false;
    }

    float busVoltage = ina219.getBusVoltage_V();
    float shuntVoltage = ina219.getShuntVoltage_mV();
    float currentMA = ina219.getCurrent_mA();
    float powerMW = ina219.getPower_mW();

    // Sanity checks on physical bounds
    if (isnan(currentMA) || isnan(busVoltage) || currentMA > INA219_MAX_CURRENT_MA || busVoltage > INA219_MAX_VOLTAGE_V) {
        Serial.println(F("[WARN] INA219 reading out of valid range or communication glitch!"));
        outData.is_valid = false;
        return false;
    }

    outData.bus_voltage_v = busVoltage;
    outData.shunt_voltage_mv = shuntVoltage;
    outData.current_ma = currentMA;
    outData.power_mw = powerMW;
    outData.is_valid = true;
    return true;
#endif
}
