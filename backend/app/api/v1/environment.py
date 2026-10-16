"""
Environmental Telemetry and Query API Endpoints.

Provides:
- POST /api/v1/environment/telemetry
- GET  /api/v1/environment/{device_id}/latest
- GET  /api/v1/environment/{device_id}/history
- GET  /api/v1/environment/{device_id}/summary
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.schemas.environment import (
    EnvironmentTelemetryPayload,
    EnvironmentTelemetryResponse,
    EnvironmentRecordResponse,
    HistoricalEnvironmentResponse,
    EnvironmentSummaryResponse,
    DemoScenarioRequest,
    DemoScenarioResponse,
    AlertItemResponse,
    AlertListResponse,
    BlynkStatusResponse,
    TestAlertRequest,
)
from app.schemas.ml import (
    PredictionResponse,
    AnomalyListResponse,
    ModelTrainingRequest,
    ModelTrainingResponse,
    ModelSystemStatusResponse,
)
from app.schemas.common import StandardErrorResponse
from app.services.environment_service import EnvironmentService
from app.services.ml_service import EnvironmentalMLService
from app.services.blynk_service import BlynkService

router = APIRouter(prefix="/environment", tags=["Environmental Monitoring"])


@router.post(
    "/telemetry",
    response_model=EnvironmentTelemetryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Environmental Sensor Telemetry",
    description=(
        "Receives, validates, and persists environmental sensor telemetry "
        "(DHT22, MQ135, IR counter, HC-SR04 ultrasonic) from an ESP32 edge node."
    ),
    responses={
        201: {"model": EnvironmentTelemetryResponse, "description": "Environmental telemetry validated and accepted."},
        422: {"model": StandardErrorResponse, "description": "Validation failure or physically out-of-range sensor value."},
        500: {"model": StandardErrorResponse, "description": "Internal database storage fault."},
    },
)
async def ingest_environment_telemetry(
    payload: EnvironmentTelemetryPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> EnvironmentTelemetryResponse:
    request.state.device_id = payload.device_id
    request.state.validation_status = "PASSED"

    return await EnvironmentService.save_telemetry(db, payload)


@router.get(
    "/{device_id}/latest",
    response_model=EnvironmentRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Environmental Telemetry Record",
    description="Fetches the most recently recorded environmental observation for the specified device.",
    responses={
        200: {"model": EnvironmentRecordResponse, "description": "Latest environmental record."},
        404: {"model": StandardErrorResponse, "description": "No environmental telemetry found for this device."},
    },
)
async def get_latest_environment_telemetry(
    device_id: str,
    db: AsyncSession = Depends(get_db),
) -> EnvironmentRecordResponse:
    return await EnvironmentService.get_latest_telemetry(db, device_id)


@router.get(
    "/{device_id}/history",
    response_model=HistoricalEnvironmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Historical Environmental Telemetry Window",
    description=(
        "Retrieves a chronologically ordered sequence of environmental sensor readings within a "
        "lookback window. Supports cursor-based pagination for reliable frontend charting and ML ingestion."
    ),
    responses={
        200: {"model": HistoricalEnvironmentResponse, "description": "Historical environmental records."},
        422: {"model": StandardErrorResponse, "description": "Invalid query parameters or pagination cursor."},
    },
)
async def get_historical_environment_telemetry(
    device_id: str,
    hours: float = Query(
        default=1.0,
        gt=0.0,
        le=720.0,
        description="Time window in hours to look back (minimum > 0, maximum 720.0 hours / 30 days).",
        examples=[1.0, 24.0],
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum records to return per page (1 to 1000).",
        examples=[50, 100],
    ),
    cursor: Optional[str] = Query(
        default=None,
        description="Opaque base64 cursor token returned in 'next_cursor' of previous page.",
    ),
    db: AsyncSession = Depends(get_db),
) -> HistoricalEnvironmentResponse:
    return await EnvironmentService.get_historical_telemetry(
        session=db,
        device_id=device_id,
        hours=hours,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/{device_id}/summary",
    response_model=EnvironmentSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Environmental Sensor Summary Statistics",
    description=(
        "Computes aggregate statistics (min, max, average, count, latest) across all environmental "
        "sensor streams for a device over the specified lookback window."
    ),
    responses={
        200: {"model": EnvironmentSummaryResponse, "description": "Environmental metric statistics summary."},
        422: {"model": StandardErrorResponse, "description": "Invalid query parameters."},
    },
)
async def get_environment_summary(
    device_id: str,
    hours: float = Query(
        default=24.0,
        gt=0.0,
        le=720.0,
        description="Lookback window in hours (minimum > 0, maximum 720.0 hours).",
        examples=[24.0],
    ),
    db: AsyncSession = Depends(get_db),
) -> EnvironmentSummaryResponse:
    return await EnvironmentService.get_environment_summary(
        session=db,
        device_id=device_id,
        hours=hours,
    )


# ------------------------------------------------------------------------------
# AI & MACHINE LEARNING ENDPOINTS (PHASE 4)
# ------------------------------------------------------------------------------

@router.get(
    "/{device_id}/prediction",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get 60-Minute Ahead MQ135 Air Quality Forecast",
    description=(
        "Retrieves the 60-minute ahead forecast for MQ135 gas sensor voltage "
        "using a Random Forest regressor with tree ensemble prediction intervals. "
        "Returns WAITING_FOR_DATA if sufficient real sensor data has not yet accumulated."
    ),
    responses={
        200: {"model": PredictionResponse, "description": "Forecast output or data accumulation status."},
        422: {"model": StandardErrorResponse, "description": "Invalid query parameters."},
    },
)
async def get_environment_prediction(
    device_id: str,
    demo: bool = Query(
        default=False,
        description="Enable controlled demonstration forecast if real model is not yet trained.",
    ),
    db: AsyncSession = Depends(get_db),
) -> PredictionResponse:
    return await EnvironmentalMLService.get_latest_prediction(
        session=db,
        device_id=device_id,
        demo=demo,
    )


@router.get(
    "/{device_id}/anomalies",
    response_model=AnomalyListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Detected Environmental Anomaly Events",
    description=(
        "Retrieves multivariate anomaly events flagged by the Isolation Forest model "
        "within the specified lookback window, including sensor attribution explanations."
    ),
    responses={
        200: {"model": AnomalyListResponse, "description": "List of detected anomaly records."},
        422: {"model": StandardErrorResponse, "description": "Invalid query parameters."},
    },
)
async def get_environment_anomalies(
    device_id: str,
    hours: float = Query(
        default=24.0,
        gt=0.0,
        le=720.0,
        description="Query window in hours (minimum > 0, maximum 720.0 hours).",
        examples=[24.0],
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Maximum anomaly events to return (1 to 500).",
        examples=[50],
    ),
    db: AsyncSession = Depends(get_db),
) -> AnomalyListResponse:
    return await EnvironmentalMLService.get_anomalies(
        session=db,
        device_id=device_id,
        hours=hours,
        limit=limit,
    )


@router.post(
    "/models/train",
    response_model=ModelTrainingResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger Environmental Model Training",
    description=(
        "Trains the Random Forest forecaster and Isolation Forest anomaly detector "
        "using stored environmental observations. Enforces concurrency protection "
        "and chronological validation splitting."
    ),
    responses={
        200: {"model": ModelTrainingResponse, "description": "Training execution outcome and metrics."},
        422: {"model": StandardErrorResponse, "description": "Invalid training parameters."},
    },
)
async def train_environmental_models(
    request: ModelTrainingRequest,
    db: AsyncSession = Depends(get_db),
) -> ModelTrainingResponse:
    return await EnvironmentalMLService.train_models(
        session=db,
        request=request,
    )


@router.get(
    "/models/status",
    response_model=ModelSystemStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Environmental AI Model Operational Status",
    description="Reports model readiness, metadata, sample counts, and evaluation metrics.",
    responses={
        200: {"model": ModelSystemStatusResponse, "description": "System operational status."},
    },
)
async def get_model_status(
    db: AsyncSession = Depends(get_db),
) -> ModelSystemStatusResponse:
    return await EnvironmentalMLService.get_system_status(session=db)


@router.post(
    "/demo/scenario",
    response_model=DemoScenarioResponse,
    status_code=status.HTTP_200_OK,
    summary="Inject Controlled Demonstration Scenario",
    description=(
        "Injects a reproducible multi-sensor scenario dataset (normal, increasing_mq135, "
        "spike_mq135, multivariate_anomaly, or longitudinal_forecasting) marked with is_mock=True."
    ),
    responses={
        200: {"model": DemoScenarioResponse, "description": "Scenario injected successfully."},
        422: {"model": StandardErrorResponse, "description": "Invalid scenario parameters."},
    },
)
async def inject_demo_scenario(
    request: DemoScenarioRequest,
    db: AsyncSession = Depends(get_db),
) -> DemoScenarioResponse:
    return await EnvironmentService.inject_demo_scenario(session=db, request=request)


@router.get(
    "/blynk/status",
    response_model=BlynkStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Blynk IoT Integration Status",
    description="Reports Blynk Cloud connectivity, configured virtual pins, active cooldowns, and threshold limits.",
    responses={
        200: {"model": BlynkStatusResponse, "description": "Blynk service operational status."},
    },
)
async def get_blynk_status() -> BlynkStatusResponse:
    return BlynkService.get_status()


@router.post(
    "/alerts/test",
    response_model=AlertItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger Test Demonstration Alert",
    description="Programmatically dispatches an alert to verify the local and Blynk cloud notification pipelines.",
    responses={
        200: {"model": AlertItemResponse, "description": "Alert dispatched and logged."},
        422: {"model": StandardErrorResponse, "description": "Invalid alert request."},
    },
)
async def trigger_test_alert(
    request: TestAlertRequest,
    db: AsyncSession = Depends(get_db),
) -> AlertItemResponse:
    return await BlynkService.trigger_test_alert(session=db, request=request)


@router.get(
    "/{device_id}/alerts",
    response_model=AlertListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Environmental Alerts History",
    description="Retrieves threshold and AI anomaly alert records dispatched for the device.",
    responses={
        200: {"model": AlertListResponse, "description": "List of historical alert records."},
        422: {"model": StandardErrorResponse, "description": "Invalid query parameters."},
    },
)
async def get_environment_alerts(
    device_id: str,
    hours: float = Query(
        default=24.0,
        gt=0.0,
        le=720.0,
        description="Query window in hours (0.1 to 720.0).",
        examples=[24.0],
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Maximum alert records to return (1 to 500).",
        examples=[50],
    ),
    db: AsyncSession = Depends(get_db),
) -> AlertListResponse:
    return await BlynkService.get_alerts(session=db, device_id=device_id, hours=hours, limit=limit)



