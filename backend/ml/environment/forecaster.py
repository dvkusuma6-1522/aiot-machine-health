"""
Random Forest Regression Forecaster for MQ135 Air Quality Sensor (60-Minute Ahead).

Implements strict chronological train/test splitting, ensemble quantile prediction intervals,
joblib model persistence, and explicit status lifecycle management.
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from ml.environment.feature_engineering import (
    EnvironmentalFeatureEngineer,
    FEATURE_COLUMNS,
)

MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../models/environment"))
MODEL_PATH = os.path.join(MODEL_DIR, "rf_mq135_forecaster.joblib")
METADATA_PATH = os.path.join(MODEL_DIR, "rf_mq135_metadata.json")


class RandomForestForecaster:
    """Trains, persists, evaluates, and serves 60-minute ahead MQ135 forecasts."""

    def __init__(self, model_version: str = "1.0.0"):
        self.model_version = model_version
        self.model: Optional[RandomForestRegressor] = None
        self.engineer = EnvironmentalFeatureEngineer()
        self.metadata: Dict[str, Any] = {
            "status": "MODEL_NOT_TRAINED",
            "model_version": self.model_version,
            "target_variable": "mq135_voltage",
            "horizon_minutes": 60,
            "feature_names": FEATURE_COLUMNS,
            "train_samples": 0,
            "eval_samples": 0,
            "mae": None,
            "rmse": None,
            "trained_at": None,
        }
        self.load_if_exists()

    @property
    def status(self) -> str:
        return self.metadata.get("status", "MODEL_NOT_TRAINED")

    def load_if_exists(self) -> bool:
        """Attempts to load a previously persisted model and metadata from disk."""
        if os.path.exists(MODEL_PATH) and os.path.exists(METADATA_PATH):
            try:
                bundle = joblib.load(MODEL_PATH)
                self.model = bundle["model"]
                self.engineer = bundle["engineer"]
                with open(METADATA_PATH, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                return True
            except Exception:
                self.metadata["status"] = "MODEL_ERROR"
                return False
        return False

    def train(
        self,
        df: pd.DataFrame,
        test_size: float = 0.2,
        min_samples: int = 100,
    ) -> Dict[str, Any]:
        """
        Trains the Random Forest model on historical observations using a strictly
        chronological split without shuffling to prevent future information leakage.
        """
        if df.empty or len(df) < min_samples:
            self.metadata["status"] = "WAITING_FOR_DATA"
            self.metadata["required_samples"] = min_samples
            self.metadata["current_samples"] = len(df)
            return {
                "status": "WAITING_FOR_DATA",
                "message": (
                    f"Insufficient historical data to train 60-minute forecast model. "
                    f"Required: at least {min_samples} aligned sensor observations; Available: {len(df)}."
                ),
                "required_samples": min_samples,
                "current_samples": len(df),
            }

        # 1. Feature Engineering & Target Alignment
        X, y = self.engineer.build_forecasting_dataset(df, horizon_minutes=60)

        if len(X) < 30:
            self.metadata["status"] = "WAITING_FOR_DATA"
            return {
                "status": "WAITING_FOR_DATA",
                "message": (
                    "Data exists but fewer than 30 timestamp-aligned pairs could be formed "
                    "with a 60-minute future target horizon."
                ),
                "required_samples": 30,
                "aligned_samples": len(X),
            }

        # 2. Chronological Train/Test Split (No Random Shuffling)
        split_idx = int(len(X) * (1.0 - test_size))
        if split_idx < 10 or (len(X) - split_idx) < 5:
            split_idx = len(X) - 5

        X_train, y_train = X.iloc[:split_idx], y.iloc[:split_idx]
        X_test, y_test = X.iloc[split_idx:], y.iloc[split_idx:]

        # 3. Fit Imputer on Train Split Only (No Data Leakage)
        X_train_imp = self.engineer.imputer.fit_transform(X_train)
        X_test_imp = self.engineer.imputer.transform(X_test)
        self.engineer.is_fitted = True

        # 4. Train Random Forest Regressor
        rf = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=4,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )
        rf.fit(X_train_imp, y_train)
        self.model = rf

        # 5. Evaluate Held-Out Chronological Test Set
        y_pred = rf.predict(X_test_imp)
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))

        # 6. Update Metadata
        now_iso = datetime.now(timezone.utc).isoformat()
        self.metadata = {
            "status": "MODEL_EVALUATED",
            "model_name": "RandomForestRegressor",
            "model_version": self.model_version,
            "target_variable": "mq135_voltage",
            "horizon_minutes": 60,
            "train_samples": len(X_train),
            "eval_samples": len(X_test),
            "total_aligned_samples": len(X),
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "features": FEATURE_COLUMNS,
            "trained_at": now_iso,
        }

        # 7. Persist Model and Metadata
        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump({"model": self.model, "engineer": self.engineer}, MODEL_PATH)
        with open(METADATA_PATH, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

        return self.metadata

    def predict_latest(
        self,
        recent_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        Generates a 60-minute ahead forecast with tree ensemble prediction intervals.
        """
        if self.model is None:
            self.load_if_exists()

        if self.model is None or self.status not in ["MODEL_TRAINED", "MODEL_EVALUATED"]:
            return {
                "status": self.status,
                "target_variable": "mq135_voltage",
                "horizon_minutes": 60,
                "predicted_value": None,
                "confidence_lower": None,
                "confidence_upper": None,
                "model_version": self.model_version,
                "message": "Model not trained yet or waiting for sufficient longitudinal sensor data.",
            }

        feat_vec = self.engineer.extract_single_feature_vector(recent_df)
        if feat_vec is None:
            return {
                "status": "MODEL_ERROR",
                "target_variable": "mq135_voltage",
                "horizon_minutes": 60,
                "predicted_value": None,
                "confidence_lower": None,
                "confidence_upper": None,
                "model_version": self.model_version,
                "message": "Unable to extract feature vector from provided telemetry window.",
            }

        # Point Prediction
        point_pred = float(self.model.predict(feat_vec)[0])

        # Prediction Intervals via Tree Estimator Ensemble Quantiles
        tree_predictions = [float(tree.predict(feat_vec)[0]) for tree in self.model.estimators_]
        lower_bound = float(np.percentile(tree_predictions, 10))
        upper_bound = float(np.percentile(tree_predictions, 90))

        # Clamp physically to 0.0V - 5.0V
        point_pred = max(0.0, min(5.0, round(point_pred, 3)))
        lower_bound = max(0.0, min(5.0, round(lower_bound, 3)))
        upper_bound = max(0.0, min(5.0, round(upper_bound, 3)))

        return {
            "status": "SUCCESS",
            "target_variable": "mq135_voltage",
            "horizon_minutes": 60,
            "predicted_value": point_pred,
            "confidence_lower": lower_bound,
            "confidence_upper": upper_bound,
            "model_version": self.model_version,
            "model_name": "RandomForestRegressor",
            "mae": self.metadata.get("mae"),
            "rmse": self.metadata.get("rmse"),
        }
