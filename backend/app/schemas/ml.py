"""
Pydantic v2 Schemas for Environmental AI Models (Forecasting & Anomaly Detection).

Defines request/response contracts for:
- 60-minute ahead MQ135 Random Forest forecast
- Multivariate Isolation Forest anomaly detection
- Model lifecycle status tracking and retraining
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ModelStatusEnum(str):
    MODEL_NOT_TRAINED = "MODEL_NOT_TRAINED"
    WAITING_FOR_DATA = "WAITING_FOR_DATA"
    MODEL_TRAINED = "MODEL_TRAINED"
    MODEL_EVALUATED = "MODEL_EVALUATED"
    MODEL_ERROR = "MODEL_ERROR"


class PredictionResponse(BaseModel):
    """60-Minute Ahead MQ135 Air Quality Sensor Forecast Response."""

    device_id: str = Field(..., description="Monitored environmental node ID.")
    model_status: str = Field(..., description="Lifecycle status: MODEL_NOT_TRAINED, WAITING_FOR_DATA, MODEL_EVALUATED.")
    target_variable: str = Field("mq135_voltage", description="Forecast target sensor stream.")
    horizon_minutes: int = Field(60, description="Forecast lookahead horizon in minutes.")
    target_timestamp: Optional[datetime] = Field(None, description="Projected target timestamp in UTC.")
    predicted_value: Optional[float] = Field(None, description="Point forecast value (Volts).")
    confidence_lower: Optional[float] = Field(None, description="10th percentile tree ensemble interval bound.")
    confidence_upper: Optional[float] = Field(None, description="90th percentile tree ensemble interval bound.")
    model_name: Optional[str] = Field("RandomForestRegressor", description="Model architecture.")
    model_version: Optional[str] = Field(None, description="Trained model version tag.")
    is_demonstration: bool = Field(False, description="Flag indicating if forecast is from demonstration mode.")
    message: str = Field(..., description="Explanatory status message.")
    mae: Optional[float] = Field(None, description="Held-out evaluation Mean Absolute Error, if evaluated.")
    rmse: Optional[float] = Field(None, description="Held-out evaluation Root Mean Squared Error, if evaluated.")


class AnomalyItemResponse(BaseModel):
    """Multivariate Anomaly Event Item."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(None, description="Database record ID.")
    device_id: str = Field(..., description="Monitored environmental node ID.")
    timestamp: datetime = Field(..., description="Observation timestamp in UTC.")
    anomaly_score: float = Field(..., description="Isolation Forest decision score.")
    is_anomaly: bool = Field(..., description="True if flagged as an anomalous event.")
    severity: str = Field("NORMAL", description="Severity classification: NORMAL, WARNING, CRITICAL.")
    affected_sensors: Optional[List[str]] = Field(None, description="Sensors contributing most to the anomaly.")
    explanation: Optional[str] = Field(None, description="Scientific explanation of sensor deviations.")
    model_name: str = Field("IsolationForest", description="Model name.")
    model_version: str = Field("1.0.0", description="Model version.")


class AnomalyListResponse(BaseModel):
    """List of Detected Anomaly Events for a Device."""

    device_id: str = Field(..., description="Monitored environmental node ID.")
    hours_queried: float = Field(..., description="Query window duration in hours.")
    count: int = Field(..., description="Number of anomaly records returned.")
    items: List[AnomalyItemResponse] = Field(..., description="Detected anomaly events.")


class ModelTrainingRequest(BaseModel):
    """Parameters for Model Training / Retraining Execution."""

    device_id: Optional[str] = Field(None, description="Filter training data to specific device (None = all nodes).")
    allow_mock_data: bool = Field(
        False,
        description="Allow training on synthetic/demonstration records (is_mock=True) for demo setups.",
    )
    min_samples: int = Field(100, ge=30, le=100000, description="Minimum required aligned samples to train.")


class ModelTrainingResponse(BaseModel):
    """Summary Report of Model Training Execution."""

    status: str = Field(..., description="Training outcome status: SUCCESS, WAITING_FOR_DATA, ERROR.")
    message: str = Field(..., description="Detailed training outcome message.")
    forecaster: Dict[str, Any] = Field(..., description="Forecaster training metrics and sample counts.")
    anomaly_detector: Dict[str, Any] = Field(..., description="Anomaly detector training metrics.")
    trained_at: Optional[str] = Field(None, description="Completion timestamp in UTC.")


class ModelSystemStatusResponse(BaseModel):
    """Global Operational Status for All Environmental AI Models."""

    forecaster_status: str = Field(..., description="Lifecycle status of Random Forest forecaster.")
    anomaly_detector_status: str = Field(..., description="Lifecycle status of Isolation Forest.")
    database_reading_count: int = Field(..., description="Total available physical records in database.")
    database_mock_count: int = Field(..., description="Total synthetic records in database.")
    forecaster_metadata: Dict[str, Any] = Field(..., description="Forecaster model metadata and metrics.")
    anomaly_metadata: Dict[str, Any] = Field(..., description="Anomaly detector metadata.")
