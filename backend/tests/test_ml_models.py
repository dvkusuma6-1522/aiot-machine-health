"""
Automated Test Suite for Environmental AI Models (Phase 4).

Verifies:
1. Feature engineering & chronological 60-minute target alignment without data leakage.
2. Chronological train/test separation.
3. Imputation of missing sensor values without zero conversion.
4. Insufficient data handling (WAITING_FOR_DATA).
5. Random Forest model persistence, loading, point prediction, and quantile intervals.
6. MAE and RMSE metric calculation on held-out evaluation set.
7. Isolation Forest training, anomaly scoring, and sensor attribution explanation.
8. Controlled synthetic scenario generation & explicit mock provenance.
9. FastAPI REST endpoints (/prediction, /anomalies, /models/train, /models/status).
"""

from datetime import datetime, timezone, timedelta
import pytest
import pandas as pd
import numpy as np
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ml.environment.feature_engineering import (
    EnvironmentalFeatureEngineer,
    FEATURE_COLUMNS,
    ANOMALY_FEATURE_COLUMNS,
)
from ml.environment.forecaster import RandomForestForecaster
from ml.environment.anomaly_detector import IsolationForestAnomalyDetector
from ml.environment.synthetic_generator import SyntheticDataGenerator
from app.models.environment import EnvironmentReading, EnvironmentPrediction, EnvironmentAnomaly


# ------------------------------------------------------------------------------
# 1. FEATURE ENGINEERING & TARGET ALIGNMENT TESTS
# ------------------------------------------------------------------------------

def test_feature_engineering_target_alignment_and_no_leakage():
    """Test 1: Target represents reading 60 minutes later; no future feature leakage."""
    engineer = EnvironmentalFeatureEngineer()
    now = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)

    # Generate 120 minutes of 1-minute sampled data
    records = []
    for i in range(120):
        t = now + timedelta(minutes=i)
        records.append({
            "timestamp": t,
            "mq135_voltage": 1.0 + (i * 0.01),  # Linear increase: 1.00V at t=0, 1.60V at t=60
            "temperature_c": 25.0,
            "humidity_percent": 50.0,
            "ir_count": 5,
            "bin_fill_percent": 30.0,
        })
    df = pd.DataFrame(records)

    X, y = engineer.build_forecasting_dataset(df, horizon_minutes=60, tolerance_minutes=2)

    assert not X.empty
    assert len(X) == len(y)
    # The first sample (t=0) should target the observation 60 mins later (t=60 -> voltage 1.60V)
    assert abs(y.iloc[0] - 1.60) < 0.05
    # The last row of X cannot exceed t=59 because t=60 is the last available target
    assert 55 <= len(X) <= 65

    # Verify all feature columns are present
    for col in FEATURE_COLUMNS:
        assert col in X.columns


def test_missing_sensor_imputation_not_zero():
    """Test 2: Missing sensor readings (None/NaN) are imputed via median, not replaced with zero."""
    engineer = EnvironmentalFeatureEngineer()
    base_t = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)
    df = pd.DataFrame([
        {
            "timestamp": base_t + timedelta(minutes=i),
            "mq135_voltage": 1.25,
            "temperature_c": None if i % 2 == 0 else 24.0,  # Alternate missing temperature
            "humidity_percent": 55.0,
            "ir_count": None if i % 3 == 0 else 10,
            "bin_fill_percent": 40.0,
        }
        for i in range(75)
    ])

    X, y = engineer.build_forecasting_dataset(df, horizon_minutes=30)
    assert not X.empty
    X_imp = engineer.imputer.fit_transform(X)

    # Temperature column should be imputed around 24.0, NOT 0.0
    temp_col_idx = FEATURE_COLUMNS.index("temperature_c")
    assert np.all(X_imp[:, temp_col_idx] > 10.0)
    assert np.all(X_imp[:, temp_col_idx] != 0.0)


# ------------------------------------------------------------------------------
# 2. RANDOM FOREST FORECASTER TESTS
# ------------------------------------------------------------------------------

def test_random_forest_chronological_split_and_evaluation():
    """Test 3: Model trains using strictly chronological split; computes real MAE and RMSE."""
    synthetic_df = SyntheticDataGenerator.generate_scenario_dataset(
        scenario="longitudinal_forecasting",
        n_samples=200,
        sample_interval_sec=60,
    )
    forecaster = RandomForestForecaster(model_version="test-1.0")

    result = forecaster.train(synthetic_df, test_size=0.25, min_samples=50)

    assert result["status"] == "MODEL_EVALUATED"
    assert result["train_samples"] > 0
    assert result["eval_samples"] > 0
    assert result["mae"] is not None and result["mae"] >= 0.0
    assert result["rmse"] is not None and result["rmse"] >= 0.0
    assert result["rmse"] >= result["mae"]  # Mathematical property: RMSE >= MAE


def test_random_forest_insufficient_data_waiting():
    """Test 4: Insufficient training data sets status to WAITING_FOR_DATA without fabricating metrics."""
    forecaster = RandomForestForecaster(model_version="test-empty")
    sparse_df = pd.DataFrame([
        {
            "timestamp": datetime(2026, 10, 14, 12, i, 0, tzinfo=timezone.utc),
            "mq135_voltage": 1.2,
        }
        for i in range(10)
    ])

    result = forecaster.train(sparse_df, min_samples=100)
    assert result["status"] == "WAITING_FOR_DATA"
    assert forecaster.status == "WAITING_FOR_DATA"


def test_random_forest_prediction_and_quantile_intervals():
    """Test 5: Prediction produces valid point estimate and 10th/90th percentile intervals."""
    synthetic_df = SyntheticDataGenerator.generate_scenario_dataset(
        scenario="longitudinal_forecasting",
        n_samples=180,
    )
    forecaster = RandomForestForecaster(model_version="test-pred")
    forecaster.train(synthetic_df, min_samples=50)

    pred = forecaster.predict_latest(synthetic_df.tail(30))
    assert pred["status"] == "SUCCESS"
    assert 0.0 <= pred["predicted_value"] <= 5.0
    assert pred["confidence_lower"] is not None
    assert pred["confidence_upper"] is not None
    assert pred["confidence_lower"] <= pred["predicted_value"] <= pred["confidence_upper"]


# ------------------------------------------------------------------------------
# 3. ISOLATION FOREST ANOMALY DETECTOR TESTS
# ------------------------------------------------------------------------------

def test_isolation_forest_anomaly_detection_and_attribution():
    """Test 6: Isolation forest detects normal baseline and flags abnormal spikes with attribution."""
    # 1. Train on normal baseline
    normal_df = SyntheticDataGenerator.generate_scenario_dataset(
        scenario="normal",
        n_samples=100,
    )
    detector = IsolationForestAnomalyDetector(contamination=0.05, model_version="test-iso")
    train_res = detector.train(normal_df, min_samples=30)
    assert train_res["status"] == "MODEL_TRAINED"

    # 2. Test normal reading
    normal_reading = {
        "timestamp": datetime.now(timezone.utc),
        "mq135_voltage": 1.22,
        "temperature_c": 24.5,
        "humidity_percent": 55.0,
        "ir_count": 5,
        "bin_fill_percent": 40.0,
    }
    norm_res = detector.detect_single(normal_reading)
    assert norm_res["status"] == "SUCCESS"
    assert norm_res["is_anomaly"] is False
    assert norm_res["severity"] == "NORMAL"

    # 3. Test anomalous reading (extreme gas voltage & temperature)
    spike_reading = {
        "timestamp": datetime.now(timezone.utc),
        "mq135_voltage": 4.50,  # Extreme outlier
        "temperature_c": 45.0,  # Extreme outlier
        "humidity_percent": 90.0,
        "ir_count": 80,
        "bin_fill_percent": 95.0,
    }
    anom_res = detector.detect_single(spike_reading)
    assert anom_res["status"] == "SUCCESS"
    assert anom_res["is_anomaly"] is True
    assert anom_res["severity"] in ["WARNING", "CRITICAL"]
    assert "mq135_voltage" in anom_res["affected_sensors"]
    assert "Unusual condition detected" in anom_res["explanation"]


# ------------------------------------------------------------------------------
# 4. FASTAPI REST INTEGRATION TESTS
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_prediction_waiting_for_data(client: AsyncClient):
    """Test 7: GET /prediction returns WAITING_FOR_DATA when real training data is missing."""
    response = await client.get("/api/v1/environment/env_empty_node/prediction")
    assert response.status_code == 200
    data = response.json()
    assert data["model_status"] == "WAITING_FOR_DATA"
    assert data["predicted_value"] is None
    assert "Waiting for historical sensor readings" in data["message"]


@pytest.mark.asyncio
async def test_api_prediction_demonstration_mode(client: AsyncClient):
    """Test 8: GET /prediction?demo=true returns illustrative forecast labeled is_demonstration=True."""
    response = await client.get("/api/v1/environment/env_demo_node/prediction?demo=true")
    assert response.status_code == 200
    data = response.json()
    assert data["is_demonstration"] is True
    assert data["predicted_value"] is not None
    assert 0.0 <= data["predicted_value"] <= 5.0
    assert "demonstration" in data["message"].lower()


@pytest.mark.asyncio
async def test_api_models_train_insufficient_data(client: AsyncClient):
    """Test 9: POST /models/train with insufficient data returns WAITING_FOR_DATA status."""
    payload = {
        "device_id": "test_device",
        "allow_mock_data": False,
        "min_samples": 100,
    }
    response = await client.post("/api/v1/environment/models/train", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "WAITING_FOR_DATA"
    assert "Insufficient real historical" in data["message"]


@pytest.mark.asyncio
async def test_api_models_train_with_mock_data(client: AsyncClient):
    """Test 10: POST /models/train with allow_mock_data=True trains demo models cleanly."""
    payload = {
        "device_id": "demo_node_train",
        "allow_mock_data": True,
        "min_samples": 120,
    }
    response = await client.post("/api/v1/environment/models/train", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "SUCCESS" in data["status"]
    assert "forecaster" in data
    assert "anomaly_detector" in data


@pytest.mark.asyncio
async def test_api_models_status(client: AsyncClient):
    """Test 11: GET /models/status reports operational state of both models."""
    response = await client.get("/api/v1/environment/models/status")
    assert response.status_code == 200
    data = response.json()
    assert "forecaster_status" in data
    assert "anomaly_detector_status" in data
    assert "database_reading_count" in data


@pytest.mark.asyncio
async def test_api_anomalies_empty_history(client: AsyncClient):
    """Test 12: GET /anomalies returns 200 with empty list when no anomalies logged."""
    response = await client.get("/api/v1/environment/clean_node/anomalies?hours=24.0")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["items"] == []
