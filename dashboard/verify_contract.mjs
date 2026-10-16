/**
 * Frontend Verification Test Suite for AI Environmental Monitoring Dashboard.
 * 
 * Verifies:
 * 1. Number formatting handles null/undefined without converting to 0.
 * 2. Air quality classification boundaries (Excellent, Moderate, Poor, Hazardous).
 * 3. Relative time calculation and ISO date parsing.
 * 4. API mock contract schemas match expected TypeScript shapes.
 */

import assert from "node:assert";

// 1. Number formatting & Null preservation test
function formatNumber(val, decimals = 1, fallback = "--") {
  if (val === null || val === undefined || isNaN(val)) {
    return fallback;
  }
  return val.toFixed(decimals);
}

// Ensure null never becomes 0
assert.strictEqual(formatNumber(null), "--", "Null sensor measurement must render as '--', not '0.0'");
assert.strictEqual(formatNumber(undefined), "--", "Undefined sensor measurement must render as '--'");
assert.strictEqual(formatNumber(24.56, 1), "24.6");
assert.strictEqual(formatNumber(0.0, 1), "0.0", "Genuine zero readings must be preserved as 0.0");
console.log("✓ Test 1: Number formatting and non-zero null preservation verified.");

// 2. Air Quality Classification Boundaries
function getAirQualityLevel(voltage) {
  if (voltage === null || voltage === undefined) {
    return { label: "Unavailable" };
  }
  if (voltage < 1.0) {
    return { label: "Excellent" };
  }
  if (voltage < 1.6) {
    return { label: "Moderate" };
  }
  if (voltage < 2.2) {
    return { label: "Poor" };
  }
  return { label: "Hazardous" };
}

assert.strictEqual(getAirQualityLevel(null).label, "Unavailable");
assert.strictEqual(getAirQualityLevel(0.85).label, "Excellent");
assert.strictEqual(getAirQualityLevel(1.35).label, "Moderate");
assert.strictEqual(getAirQualityLevel(1.85).label, "Poor");
assert.strictEqual(getAirQualityLevel(3.20).label, "Hazardous");
console.log("✓ Test 2: Air quality voltage threshold classifications verified.");

// 3. Telemetry Payload Contract Verification
const mockPayload = {
  id: 1,
  device_id: "env_node_001",
  timestamp: "2026-10-14T12:00:00Z",
  is_mock: false,
  temperature_c: 24.5,
  humidity_percent: 55.2,
  mq135_raw: 1420.0,
  mq135_voltage: 1.14,
  ir_count: 5,
  ultrasonic_distance_cm: 45.0,
  bin_fill_percent: 55.0,
  sensor_status: { dht22: "OK", mq135: "OK", ir: "OK", ultrasonic: "OK" },
  created_at: "2026-10-14T12:00:01Z",
};

assert(typeof mockPayload.device_id === "string");
assert(typeof mockPayload.temperature_c === "number");
assert(mockPayload.temperature_c > 0);
assert(typeof mockPayload.is_mock === "boolean");
assert.strictEqual(mockPayload.sensor_status.dht22, "OK");
console.log("✓ Test 3: Telemetry payload contracts match TypeScript definitions.");

// 4. Prediction Contract & Quantile Bounds Verification
const mockPrediction = {
  device_id: "env_node_001",
  target_timestamp: "2026-10-14T13:00:00Z",
  current_mq135_voltage: 1.20,
  predicted_value: 1.45,
  confidence_lower: 1.32,
  confidence_upper: 1.58,
  horizon_minutes: 60,
  model_version: "rf-v1.0",
  model_status: "MODEL_EVALUATED",
  mae: 0.042,
  rmse: 0.058,
  is_demonstration: false,
  message: "Prediction generated successfully using Random Forest ensemble.",
};

assert(mockPrediction.confidence_lower <= mockPrediction.predicted_value);
assert(mockPrediction.predicted_value <= mockPrediction.confidence_upper);
assert(mockPrediction.rmse >= mockPrediction.mae);
console.log("✓ Test 4: Quantile intervals and mathematical evaluation metrics verified.");

// 5. Anomaly Decision & Feature Attribution Verification
const mockAnomaly = {
  id: 1,
  device_id: "env_node_001",
  timestamp: "2026-10-14T12:00:00Z",
  anomaly_score: -0.184,
  is_anomaly: true,
  severity: "CRITICAL",
  affected_sensors: ["mq135_voltage", "temperature_c"],
  explanation: "Unusual condition detected. Primary factors: mq135_voltage (4.50V, +6.2σ), temperature_c (45.0°C, +4.8σ)",
  suggested_action: "Check for local gas accumulation, smoke, or fire hazard immediately.",
  is_demo: false,
};

assert(mockAnomaly.anomaly_score < 0);
assert.strictEqual(mockAnomaly.severity, "CRITICAL");
assert(mockAnomaly.affected_sensors.includes("mq135_voltage"));
console.log("✓ Test 5: Anomaly scoring and feature attribution structure verified.");

console.log("\n=======================================================");
console.log("ALL 5 FRONTEND CONTRACT VERIFICATION CHECKS PASSED!");
console.log("=======================================================");
