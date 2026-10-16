"""
Telemetry Ingestion API Endpoint.

Implements POST /api/v1/telemetry for real-time edge sensor data ingestion.
Supports unambiguous payload discrimination between legacy machine-health telemetry
and multi-sensor environmental telemetry while preserving strict validation.
"""

import json
from typing import Union, Any, Dict
from fastapi import APIRouter, Depends, status, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.schemas.telemetry import TelemetryPayload, TelemetryResponse
from app.schemas.environment import (
    EnvironmentTelemetryPayload,
    EnvironmentTelemetryResponse,
)
from app.schemas.common import StandardErrorResponse
from app.services.telemetry_service import TelemetryService
from app.services.environment_service import EnvironmentService

router = APIRouter(prefix="/telemetry", tags=["Telemetry Ingestion"])

# Discriminator keys
ENV_EXCLUSIVE_KEYS = {
    "temperature_c",
    "humidity_percent",
    "mq135_raw",
    "mq135_voltage",
    "ir_count",
    "ultrasonic_distance_cm",
    "bin_fill_percent",
}

MACHINE_EXCLUSIVE_KEYS = {
    "accel_x",
    "accel_y",
    "accel_z",
    "gyro_x",
    "gyro_y",
    "gyro_z",
    "current",
    "voltage",
    "power",
    "rpm",
}


@router.post(
    "",
    response_model=Union[TelemetryResponse, EnvironmentTelemetryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Edge Sensor Telemetry",
    description=(
        "Receives, validates, and persists high-frequency sensor telemetry "
        "from an ESP32 edge microcontroller node (machine health or environmental)."
    ),
    responses={
        201: {"description": "Telemetry validated and accepted."},
        422: {"model": StandardErrorResponse, "description": "Validation failure or physically impossible sensor value."},
        500: {"model": StandardErrorResponse, "description": "Internal database storage fault."},
    },
)
async def ingest_telemetry(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Union[TelemetryResponse, EnvironmentTelemetryResponse]:
    # 1. Parse JSON body
    try:
        body_bytes = await request.body()
        if not body_bytes:
            raise RequestValidationError(
                [{"loc": ["body"], "msg": "Request body cannot be empty", "type": "value_error"}]
            )
        # Parse JSON; allow NaN/Infinity so Pydantic validators can catch and reject them with domain messages
        raw_payload = json.loads(body_bytes)
    except json.JSONDecodeError as exc:
        raise RequestValidationError(
            [{"loc": ["body"], "msg": f"Malformed JSON: {exc}", "type": "json_invalid"}]
        )

    if not isinstance(raw_payload, dict):
        raise RequestValidationError(
            [{"loc": ["body"], "msg": "Telemetry payload must be a JSON object", "type": "type_error.dict"}]
        )

    # 2. Discriminate payload type unambiguously
    payload_keys = set(raw_payload.keys())
    has_env_keys = bool(payload_keys.intersection(ENV_EXCLUSIVE_KEYS))
    has_machine_keys = bool(payload_keys.intersection(MACHINE_EXCLUSIVE_KEYS))

    # If environmental keys are present and no machine vibration/power keys are present, route to environmental service
    if has_env_keys and not has_machine_keys:
        try:
            env_payload = EnvironmentTelemetryPayload.model_validate(raw_payload)
        except ValidationError as exc:
            raise RequestValidationError(errors=exc.errors())

        request.state.device_id = env_payload.device_id
        request.state.validation_status = "PASSED"
        return await EnvironmentService.save_telemetry(db, env_payload)

    # Otherwise, validate strictly against machine-health TelemetryPayload
    try:
        machine_payload = TelemetryPayload.model_validate(raw_payload)
    except ValidationError as exc:
        raise RequestValidationError(errors=exc.errors())

    request.state.device_id = machine_payload.device_id
    request.state.validation_status = "PASSED"
    return await TelemetryService.save_telemetry(db, machine_payload)
