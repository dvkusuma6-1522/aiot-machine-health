import {
  EnvironmentRecord,
  HistoricalEnvironmentResponse,
  EnvironmentSummaryResponse,
  PredictionResponse,
  AnomalyListResponse,
  ModelSystemStatusResponse,
  DemoScenarioRequest,
  DemoScenarioResponse,
  AlertRecord,
  AlertListResponse,
  BlynkStatusResponse,
} from "../types/environment";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  code?: string;
  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...options?.headers,
      },
    });

    if (!res.ok) {
      let errorMsg = `HTTP ${res.status} ${res.statusText}`;
      let errorCode: string | undefined;
      try {
        const errorData = await res.json();
        if (errorData.message) errorMsg = errorData.message;
        if (errorData.code) errorCode = errorData.code;
        if (errorData.detail) {
          errorMsg = typeof errorData.detail === "string" ? errorData.detail : JSON.stringify(errorData.detail);
        }
      } catch {
        // Fallback to default errorMsg
      }
      throw new ApiError(errorMsg, res.status, errorCode);
    }

    return (await res.json()) as T;
  } catch (err: unknown) {
    if (err instanceof ApiError) {
      throw err;
    }
    const message = err instanceof Error ? err.message : "Unknown network connection failure";
    throw new ApiError(message, 0, "NETWORK_ERROR");
  }
}

export async function checkBackendHealth(): Promise<{ status: string; database: string } | null> {
  try {
    return await fetchJson<{ status: string; database: string }>("/health");
  } catch {
    return null;
  }
}

export async function getLatestTelemetry(deviceId: string): Promise<EnvironmentRecord | null> {
  try {
    return await fetchJson<EnvironmentRecord>(`/api/v1/environment/${encodeURIComponent(deviceId)}/latest`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return null;
    }
    throw err;
  }
}

export async function getHistoricalTelemetry(
  deviceId: string,
  hours: number = 1.0,
  limit: number = 100
): Promise<HistoricalEnvironmentResponse> {
  return await fetchJson<HistoricalEnvironmentResponse>(
    `/api/v1/environment/${encodeURIComponent(deviceId)}/history?hours=${hours}&limit=${limit}`
  );
}

export async function getEnvironmentSummary(
  deviceId: string,
  hours: number = 24.0
): Promise<EnvironmentSummaryResponse> {
  return await fetchJson<EnvironmentSummaryResponse>(
    `/api/v1/environment/${encodeURIComponent(deviceId)}/summary?hours=${hours}`
  );
}

export async function getPrediction(
  deviceId: string,
  demo: boolean = false
): Promise<PredictionResponse> {
  return await fetchJson<PredictionResponse>(
    `/api/v1/environment/${encodeURIComponent(deviceId)}/prediction?demo=${demo}`
  );
}

export async function getAnomalies(
  deviceId: string,
  hours: number = 24.0,
  limit: number = 50
): Promise<AnomalyListResponse> {
  return await fetchJson<AnomalyListResponse>(
    `/api/v1/environment/${encodeURIComponent(deviceId)}/anomalies?hours=${hours}&limit=${limit}`
  );
}

export async function getModelStatus(): Promise<ModelSystemStatusResponse> {
  return await fetchJson<ModelSystemStatusResponse>("/api/v1/environment/models/status");
}

export async function trainModels(payload: {
  device_id: string;
  allow_mock_data: boolean;
  min_samples: number;
  test_size?: number;
}): Promise<Record<string, unknown>> {
  return await fetchJson<Record<string, unknown>>("/api/v1/environment/models/train", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function injectDemoScenario(
  payload: DemoScenarioRequest
): Promise<DemoScenarioResponse> {
  return await fetchJson<DemoScenarioResponse>("/api/v1/environment/demo/scenario", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAlerts(
  deviceId: string,
  hours: number = 24.0,
  limit: number = 50
): Promise<AlertListResponse> {
  return await fetchJson<AlertListResponse>(
    `/api/v1/environment/${encodeURIComponent(deviceId)}/alerts?hours=${hours}&limit=${limit}`
  );
}

export async function getBlynkStatus(): Promise<BlynkStatusResponse> {
  return await fetchJson<BlynkStatusResponse>("/api/v1/environment/blynk/status");
}

export async function triggerTestAlert(payload: {
  device_id?: string;
  alert_type?: string;
  metric_value?: number;
  severity?: string;
  message?: string;
}): Promise<AlertRecord> {
  return await fetchJson<AlertRecord>("/api/v1/environment/alerts/test", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

