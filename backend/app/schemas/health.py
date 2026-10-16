"""
Schemas for System Health Checks.
"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check endpoint response schema."""

    status: str = Field(default="ok", examples=["ok"])
    database: str = Field(default="connected", examples=["connected", "disconnected"])
    environment: str = Field(default="development", examples=["development", "production"])
