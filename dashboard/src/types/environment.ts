/**
 * TypeScript Type Definitions for Environmental IoT Telemetry & AI Models.
 * Strictly aligned with FastAPI Pydantic v2 schemas.
 */

export interface SensorStatusMap {
  dht22?: "OK" | "FAIL" | string;
  mq135?: "OK" | "FAIL" | string;
  ir?: "OK" | "FAIL" | string;
  ultrasonic?: "OK" | "FAIL" | string;
  [key: string]: string | undefined;
}

export interface EnvironmentRecord {
  id: number;
  device_id: string;
  timestamp: string; // ISO 8601 string
  is_mock: boolean;
  temperature_c: number | null;
  humidity_percent: number | null;
  mq135_raw: number | null;
  mq135_voltage: number | null;
  ir_count: number | null;
  ultrasonic_distance_cm: number | null;
  bin_fill_percent: number | null;
  sensor_status: SensorStatusMap | null;
  created_at: string;
}

export interface HistoricalEnvironmentResponse {
  device_id: string;
  hours_queried: number;
  start_time: string;
  end_time: string;
  limit: number;
  count: number;
  has_more: boolean;
  next_cursor: string | null;
  items: EnvironmentRecord[];
}

export interface MetricStats {
  count: number;
  min: number | null;
  max: number | null;
  avg: number | null;
  latest: number | null;
}

export interface EnvironmentSummaryResponse {
  device_id: string;
  hours_queried: number;
  start_time: string;
  end_time: string;
  total_records: number;
  metrics: Record<string, MetricStats>;
}

export type ModelStatusType =
  | "WAITING_FOR_DATA"
  | "MODEL_EVALUATED"
  | "MODEL_TRAINED"
  | "MODEL_NOT_TRAINED"
  | "TRAINING"
  | "ERROR";

export interface PredictionResponse {
  device_id: string;
  target_timestamp: string | null;
  current_mq135_voltage: number | null;
  predicted_value: number | null;
  confidence_lower: number | null;
  confidence_upper: number | null;
  horizon_minutes: number;
  model_version: string;
  model_status: ModelStatusType;
  mae: number | null;
  rmse: number | null;
  is_demonstration: boolean;
  message: string;
}

export type AnomalySeverity = "NORMAL" | "WARNING" | "CRITICAL";

export interface AnomalyItem {
  id: number;
  device_id: string;
  timestamp: string;
  anomaly_score: number;
  is_anomaly: boolean;
  severity: AnomalySeverity;
  affected_sensors: string[];
  explanation: string;
  suggested_action: string;
  is_demo: boolean;
}

export interface AnomalyListResponse {
  device_id: string;
  hours_analyzed: number;
  count: number;
  items: AnomalyItem[];
}

export interface ModelSystemStatusResponse {
  forecaster_status: ModelStatusType;
  forecaster_version: string;
  forecaster_mae: number | null;
  forecaster_rmse: number | null;
  anomaly_detector_status: ModelStatusType;
  anomaly_detector_version: string;
  models_directory: string;
  models_persisted: boolean;
  database_reading_count: number;
  min_samples_required: number;
}

export interface DemoScenarioRequest {
  scenario: "normal" | "increasing_mq135" | "spike_mq135" | "multivariate_anomaly" | "longitudinal_forecasting";
  device_id: string;
  n_samples: number;
  sample_interval_sec: number;
  clear_previous_demo: boolean;
}

export interface DemoScenarioResponse {
  status: string;
  scenario: string;
  device_id: string;
  records_inserted: number;
  start_time: string;
  end_time: string;
  message: string;
}

export interface AlertRecord {
  id: number;
  device_id: string;
  timestamp: string;
  alert_type: string;
  severity: "WARNING" | "CRITICAL" | string;
  message: string;
  metric_value: number | null;
  threshold_value: number | null;
  is_mock: boolean;
  blynk_delivered: boolean;
  created_at: string;
}

export interface AlertListResponse {
  device_id: string;
  hours_analyzed: number;
  count: number;
  items: AlertRecord[];
}

export interface BlynkStatusResponse {
  blynk_configured: boolean;
  blynk_enabled: boolean;
  server_url: string;
  active_cooldowns: Record<string, number>;
  thresholds: Record<string, number>;
  virtual_pins: Record<string, string>;
}

