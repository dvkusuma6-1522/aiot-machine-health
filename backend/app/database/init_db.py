"""
Database Table Initialization Utility.

Creates necessary database tables on application startup if they do not exist.
"""

from app.database.session import engine, Base
from app.models.telemetry import SensorReading  # noqa: F401
from app.models.environment import (  # noqa: F401
    EnvironmentReading,
    EnvironmentPrediction,
    EnvironmentAnomaly,
    EnvironmentAlert,
)
import logging

logger = logging.getLogger("aiot.db_init")


async def init_db() -> None:
    """Create database tables using async engine metadata."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully.")
