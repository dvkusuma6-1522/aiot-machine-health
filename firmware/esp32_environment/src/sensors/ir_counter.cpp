/**
 * @file ir_counter.cpp
 * @brief Thread-Safe Interrupt Service Routine and Debouncing for IR Sensor
 */

#include "ir_counter.h"

volatile uint32_t IrCounter::_pulseCountWindow = 0;
volatile uint32_t IrCounter::_pulseCountTotal = 0;
volatile uint32_t IrCounter::_lastInterruptMicros = 0;
portMUX_TYPE IrCounter::_spinlock = portMUX_INITIALIZER_UNLOCKED;

IrCounter::IrCounter() {}

void IRAM_ATTR IrCounter::handleInterrupt() {
    uint32_t now = micros();
    // 50ms software debounce lockout
    if (now - _lastInterruptMicros >= IR_DEBOUNCE_MICROS) {
        portENTER_CRITICAL_ISR(&_spinlock);
        _pulseCountWindow++;
        _pulseCountTotal++;
        _lastInterruptMicros = now;
        portEXIT_CRITICAL_ISR(&_spinlock);
    }
}

bool IrCounter::begin() {
    pinMode(PIN_IR_SENSOR, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_IR_SENSOR), handleInterrupt, FALLING);
    return true;
}

IrReading IrCounter::readWindowCount() {
    IrReading reading;
    portENTER_CRITICAL(&_spinlock);
    reading.count = _pulseCountWindow;
    _pulseCountWindow = 0; // Reset for next window
    portEXIT_CRITICAL(&_spinlock);

    reading.is_valid = true;
    return reading;
}

IrReading IrCounter::readCumulativeCount() {
    IrReading reading;
    portENTER_CRITICAL(&_spinlock);
    reading.count = _pulseCountTotal;
    portEXIT_CRITICAL(&_spinlock);

    reading.is_valid = true;
    return reading;
}

IrReading IrCounter::readMock(uint32_t timestampMs) {
    IrReading mock;
    // Simulate incremental pedestrian/object count based on elapsed seconds
    uint32_t sec = timestampMs / 1000;
    // Approx 1 count every 3 to 8 seconds
    mock.count = (sec / 5) % 100;
    mock.is_valid = true;
    return mock;
}
