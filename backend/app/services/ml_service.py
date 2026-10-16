"""
Environmental Machine Learning Service.

Orchestrates 60-minute Random Forest forecasting, Isolation Forest anomaly detection,
training lifecycle locks, database persistence, and demonstration fallbacks.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.environment import (
    EnvironmentReading,
    EnvironmentPrediction,
    EnvironmentAnomaly,
)
from app.schemas.ml import (
    PredictionResponse,
    AnomalyItemResponse,
    AnomalyListResponse,
    ModelTrainingRequest,
    ModelTrainingResponse,
    ModelSystemStatusResponse,
)
from ml.environment.forecaster import RandomForestForecaster
from ml.environment.anomaly_detector import IsolationForestAnomalyDetector
from ml.environment.synthetic_generator import SyntheticDataGenerator

import logging

logger = logging.getLogger("aiot.ml_service")

# Module singletons
_forecaster = RandomForestForecaster()
_anomaly_detector = IsolationForestAnomalyDetector()
_training_lock = asyncio.Lock()


class EnvironmentalMLService:
    """Coordinates model inference, training lifecycle, and database persistence."""

    @staticmethod
    async def get_latest_prediction(
        session: AsyncSession,
        device_id: str,
        demo: bool = False,
    ) -> PredictionResponse:
        """
        Retrieves or computes the 60-minute ahead forecast for MQ135 voltage.
        Returns WAITING_FOR_DATA if genuine training data has not yet accumulated.
        """
        global _forecaster

        # 1. If trained model exists, execute real inference on recent telemetry
        if _forecaster.status in ["MODEL_TRAINED", "MODEL_EVALUATED"] and _forecaster.model is not None:
            # Query recent 60-minute window of observations for this device
            cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
            stmt = (
                select(EnvironmentReading)
                .where(
                    and_(
                        EnvironmentReading.device_id == device_id,
                        EnvironmentReading.timestamp >= cutoff,
                    )
                )
                .order_by(EnvironmentReading.timestamp.asc())
            )
            res = await session.execute(stmt)
            records = res.scalars().all()

            if len(records) >= 3:
                recent_df = pd.DataFrame([
                    {
                        "timestamp": r.timestamp,
                        "mq135_voltage": r.mq135_voltage,
                        "temperature_c": r.temperature_c,
                        "humidity_percent": r.humidity_percent,
                        "ir_count": r.ir_count,
                        "bin_fill_percent": r.bin_fill_percent,
                    }
                    for r in records
                ])

                pred_dict = _forecaster.predict_latest(recent_df)
                if pred_dict["status"] == "SUCCESS":
                    target_time = datetime.now(timezone.utc) + timedelta(minutes=60)

                    # Persist prediction in environment_predictions table
                    pred_record = EnvironmentPrediction(
                        device_id=device_id,
                        timestamp=target_time,
                        target_variable="mq135_voltage",
                        horizon_minutes=60,
                        predicted_value=pred_dict["predicted_value"],
                        confidence_lower=pred_dict["confidence_lower"],
                        confidence_upper=pred_dict["confidence_upper"],
                        model_name="RandomForestRegressor",
                        model_version=_forecaster.model_version,
                    )
                    session.add(pred_record)
                    await session.commit()

                    return PredictionResponse(
                        device_id=device_id,
                        model_status=_forecaster.status,
                        target_variable="mq135_voltage",
                        horizon_minutes=60,
                        target_timestamp=target_time,
                        predicted_value=pred_dict["predicted_value"],
                        confidence_lower=pred_dict["confidence_lower"],
                        confidence_upper=pred_dict["confidence_upper"],
                        model_name="RandomForestRegressor",
                        model_version=_forecaster.model_version,
                        is_demonstration=False,
                        message="Active 60-minute Random Forest prediction based on real sensor history.",
                        mae=pred_dict.get("mae"),
                        rmse=pred_dict.get("rmse"),
                    )

        # 2. Demonstration mode fallback (if requested or for interactive bench testing)
        if demo:
            demo_df = SyntheticDataGenerator.generate_scenario_dataset(
                scenario="longitudinal_forecasting",
                n_samples=180,
                device_id=device_id,
            )
            # Train an ad-hoc demonstration model if needed
            demo_forecaster = RandomForestForecaster(model_version="1.0.0-demo")
            demo_forecaster.train(demo_df, min_samples=30)
            demo_pred = demo_forecaster.predict_latest(demo_df)
            target_time = datetime.now(timezone.utc) + timedelta(minutes=60)

            return PredictionResponse(
                device_id=device_id,
                model_status="MODEL_EVALUATED (DEMO_MODE)",
                target_variable="mq135_voltage",
                horizon_minutes=60,
                target_timestamp=target_time,
                predicted_value=demo_pred.get("predicted_value", 1.25),
                confidence_lower=demo_pred.get("confidence_lower", 1.15),
                confidence_upper=demo_pred.get("confidence_upper", 1.35),
                model_name="RandomForestRegressor",
                model_version="1.0.0-demo",
                is_demonstration=True,
                message="Controlled demonstration forecast generated from synthetic benchmark dataset.",
                mae=demo_forecaster.metadata.get("mae"),
                rmse=demo_forecaster.metadata.get("rmse"),
            )

        # 3. Default honest state when real data is not yet accumulated
        count_stmt = select(func.count(EnvironmentReading.id)).where(
            and_(EnvironmentReading.device_id == device_id, EnvironmentReading.is_mock == False)
        )
        count_res = await session.execute(count_stmt)
        real_count = count_res.scalar_one() or 0

        return PredictionResponse(
            device_id=device_id,
            model_status="WAITING_FOR_DATA",
            target_variable="mq135_voltage",
            horizon_minutes=60,
            target_timestamp=None,
            predicted_value=None,
            confidence_lower=None,
            confidence_upper=None,
            model_name="RandomForestRegressor",
            model_version=_forecaster.model_version,
            is_demonstration=False,
            message=(
                f"Waiting for historical sensor readings: {real_count} real observations available. "
                f"A minimum of 100 aligned historical samples (~24-48 hours) is required to train a "
                f"scientifically valid 60-minute Random Forest forecaster without data fabrication."
            ),
            mae=None,
            rmse=None,
        )

    @staticmethod
    async def get_anomalies(
        session: AsyncSession,
        device_id: str,
        hours: float = 24.0,
        limit: int = 50,
    ) -> AnomalyListResponse:
        """
        Retrieves logged anomaly events from environment_anomalies table.
        If an anomaly detector is trained, also scans recent unanalyzed readings.
        """
        global _anomaly_detector

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)

        # 1. Query persisted anomalies
        stmt = (
            select(EnvironmentAnomaly)
            .where(
                and_(
                    EnvironmentAnomaly.device_id == device_id,
                    EnvironmentAnomaly.timestamp >= start_time,
                    EnvironmentAnomaly.timestamp <= end_time,
                )
            )
            .order_by(EnvironmentAnomaly.timestamp.desc())
            .limit(limit)
        )
        res = await session.execute(stmt)
        records = res.scalars().all()

        # 2. If no persisted records exist, scan recent readings if model is ready
        if not records and _anomaly_detector.model is not None:
            reading_stmt = (
                select(EnvironmentReading)
                .where(
                    and_(
                        EnvironmentReading.device_id == device_id,
                        EnvironmentReading.timestamp >= start_time,
                        EnvironmentReading.timestamp <= end_time,
                    )
                )
                .order_by(EnvironmentReading.timestamp.desc())
                .limit(limit)
            )
            r_res = await session.execute(reading_stmt)
            recent_readings = r_res.scalars().all()

            for r in recent_readings:
                det = _anomaly_detector.detect_single({
                    "timestamp": r.timestamp,
                    "mq135_voltage": r.mq135_voltage,
                    "temperature_c": r.temperature_c,
                    "humidity_percent": r.humidity_percent,
                    "ir_count": r.ir_count,
                    "bin_fill_percent": r.bin_fill_percent,
                })
                if det.get("is_anomaly", False):
                    anom = EnvironmentAnomaly(
                        device_id=device_id,
                        timestamp=r.timestamp,
                        anomaly_score=det["anomaly_score"],
                        is_anomaly=True,
                        severity=det["severity"],
                        affected_sensors=det.get("affected_sensors"),
                        explanation=det.get("explanation"),
                        model_name="IsolationForest",
                        model_version=_anomaly_detector.model_version,
                    )
                    session.add(anom)
            await session.commit()

            # Re-query
            res = await session.execute(stmt)
            records = res.scalars().all()

        items = [
            AnomalyItemResponse(
                id=rec.id,
                device_id=rec.device_id,
                timestamp=rec.timestamp,
                anomaly_score=rec.anomaly_score,
                is_anomaly=rec.is_anomaly,
                severity=rec.severity,
                affected_sensors=rec.affected_sensors or [],
                explanation=rec.explanation or "Unusual multivariate pattern detected.",
                model_name=rec.model_name,
                model_version=rec.model_version,
            )
            for rec in records
        ]

        return AnomalyListResponse(
            device_id=device_id,
            hours_queried=hours,
            count=len(items),
            items=items,
        )

    @staticmethod
    async def train_models(
        session: AsyncSession,
        request: ModelTrainingRequest,
    ) -> ModelTrainingResponse:
        """
        Executes model training for both forecaster and anomaly detector
        under a concurrency lock.
        """
        global _forecaster, _anomaly_detector

        if _training_lock.locked():
            return ModelTrainingResponse(
                status="BUSY",
                message="Model training is already currently executing in background. Please wait.",
                forecaster={},
                anomaly_detector={},
                trained_at=None,
            )

        async with _training_lock:
            # Query observations from database
            conditions = []
            if not request.allow_mock_data:
                conditions.append(EnvironmentReading.is_mock == False)
            if request.device_id:
                conditions.append(EnvironmentReading.device_id == request.device_id)

            stmt = select(EnvironmentReading).order_by(EnvironmentReading.timestamp.asc())
            if conditions:
                stmt = stmt.where(and_(*conditions))

            res = await session.execute(stmt)
            records = res.scalars().all()

            # Handle case where real data is insufficient
            if len(records) < request.min_samples:
                if request.allow_mock_data:
                    # Demonstration training path on synthetic scenario
                    demo_df = SyntheticDataGenerator.generate_scenario_dataset(
                        scenario="longitudinal_forecasting",
                        n_samples=max(200, request.min_samples),
                        device_id=request.device_id or "env_node_001",
                    )
                    rf_res = _forecaster.train(demo_df, min_samples=30)
                    iso_res = _anomaly_detector.train(demo_df, min_samples=30)

                    return ModelTrainingResponse(
                        status="SUCCESS (DEMO_MODE)",
                        message=(
                            f"Demonstration training completed using {len(demo_df)} synthetic records. "
                            f"Model explicitly tagged for demonstration purposes."
                        ),
                        forecaster=rf_res,
                        anomaly_detector=iso_res,
                        trained_at=datetime.now(timezone.utc).isoformat(),
                    )
                else:
                    return ModelTrainingResponse(
                        status="WAITING_FOR_DATA",
                        message=(
                            f"Insufficient real historical sensor readings to train models. "
                            f"Required: at least {request.min_samples} observations; Available: {len(records)}. "
                            f"To train on simulated data for demonstration, pass allow_mock_data=True."
                        ),
                        forecaster={"status": "WAITING_FOR_DATA", "available": len(records), "required": request.min_samples},
                        anomaly_detector={"status": "WAITING_FOR_DATA"},
                        trained_at=None,
                    )

            # Sufficient data exists: build training DataFrame
            df = pd.DataFrame([
                {
                    "device_id": r.device_id,
                    "timestamp": r.timestamp,
                    "mq135_voltage": r.mq135_voltage,
                    "temperature_c": r.temperature_c,
                    "humidity_percent": r.humidity_percent,
                    "ir_count": r.ir_count,
                    "bin_fill_percent": r.bin_fill_percent,
                    "is_mock": r.is_mock,
                }
                for r in records
            ])

            rf_meta = _forecaster.train(df, min_samples=request.min_samples)
            iso_meta = _anomaly_detector.train(df, min_samples=max(30, request.min_samples // 2))

            return ModelTrainingResponse(
                status="SUCCESS",
                message=f"Model training successfully completed using {len(df)} historical readings.",
                forecaster=rf_meta,
                anomaly_detector=iso_meta,
                trained_at=datetime.now(timezone.utc).isoformat(),
            )

    @staticmethod
    async def get_system_status(session: AsyncSession) -> ModelSystemStatusResponse:
        """Returns the system-wide operational readiness of all ML models."""
        global _forecaster, _anomaly_detector

        real_stmt = select(func.count(EnvironmentReading.id)).where(EnvironmentReading.is_mock == False)
        mock_stmt = select(func.count(EnvironmentReading.id)).where(EnvironmentReading.is_mock == True)

        real_count = (await session.execute(real_stmt)).scalar_one() or 0
        mock_count = (await session.execute(mock_stmt)).scalar_one() or 0

        return ModelSystemStatusResponse(
            forecaster_status=_forecaster.status,
            anomaly_detector_status=_anomaly_detector.status,
            database_reading_count=real_count,
            database_mock_count=mock_count,
            forecaster_metadata=_forecaster.metadata,
            anomaly_metadata=_anomaly_detector.metadata,
        )
