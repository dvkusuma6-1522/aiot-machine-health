"""
Main API Router Configuration.
"""

from fastapi import APIRouter
from app.api.v1.telemetry import router as telemetry_router
from app.api.v1.health import router as health_router
from app.api.v1.machine import router as machine_router
from app.api.v1.environment import router as environment_router

api_router = APIRouter()

# Include versioned endpoints under /api/v1
api_router.include_router(telemetry_router)
api_router.include_router(health_router)
api_router.include_router(machine_router)
api_router.include_router(environment_router)
