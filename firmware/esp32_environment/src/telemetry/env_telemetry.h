/**
 * @file env_telemetry.h
 * @brief Unified Data Structure for Ingested Environmental Sensor Telemetry
 */

#ifndef ENV_TELEMETRY_H
#define ENV_TELEMETRY_H

#include <stdint.h>
#include "sensors/dht_sensor.h"
#include "sensors/mq135_sensor.h"
#include "sensors/ir_counter.h"
#include "sensors/ultrasonic_sensor.h"

struct EnvironmentalTelemetryData {
    uint64_t timestamp_ms;
    bool is_mock;

    // Startup / run-time hardware health statuses
    bool status_dht22;
    bool status_mq135;
    bool status_ir;
    bool status_ultrasonic;

    // Sensor reading payloads
    DhtReading dht;
    Mq135Reading mq135;
    IrReading ir;
    UltrasonicReading ultrasonic;
};

#endif // ENV_TELEMETRY_H
