/**
 * @file ir_counter.h
 * @brief IR Obstacle / People Counter Driver with Hardware Interrupts & Debouncing
 */

#ifndef IR_COUNTER_H
#define IR_COUNTER_H

#include <Arduino.h>
#include "config.h"

struct IrReading {
    uint32_t count;
    bool is_valid;
};

class IrCounter {
public:
    IrCounter();
    bool begin();
    IrReading readWindowCount();
    IrReading readCumulativeCount();
    IrReading readMock(uint32_t timestampMs);

    // Static ISR handler
    static void IRAM_ATTR handleInterrupt();

private:
    static volatile uint32_t _pulseCountWindow;
    static volatile uint32_t _pulseCountTotal;
    static volatile uint32_t _lastInterruptMicros;
    static portMUX_TYPE _spinlock;
};

#endif // IR_COUNTER_H
