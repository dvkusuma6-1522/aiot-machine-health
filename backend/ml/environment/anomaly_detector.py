"""
Isolation Forest Anomaly Detector for Multivariate Environmental Monitoring.

Identifies atypical multidimensional patterns across gas, temperature, humidity,
traffic, and bin fill metrics. Generates sensor attribution explanations
without diagnosing false causes.
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from ml.environment.feature_engineering import (
    EnvironmentalFeatureEngineer,
    ANOMALY_FEATURE_COLUMNS,
)

MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../models/environment"))
MODEL_PATH = os.path.join(MODEL_DIR, "isolation_forest.joblib")
METADATA_PATH = os.path.join(MODEL_DIR, "isolation_forest_metadata.json")


class IsolationForestAnomalyDetector:
    """Unsupervised multivariate anomaly detector with feature attribution."""

    def __init__(self, contamination: float = 0.05, model_version: str = "1.0.0"):
        self.contamination = contamination
        self.model_version = model_version
        self.model: Optional[IsolationForest] = None
        self.imputer = SimpleImputer(strategy="median")
        self.engineer = EnvironmentalFeatureEngineer()
        self.baseline_stats: Dict[str, Dict[str, float]] = {}
        self.metadata: Dict[str, Any] = {
            "status": "MODEL_NOT_TRAINED",
            "model_version": self.model_version,
            "contamination": self.contamination,
            "features": ANOMALY_FEATURE_COLUMNS,
            "train_samples": 0,
            "trained_at": None,
        }
        self.load_if_exists()

    @property
    def status(self) -> str:
        return self.metadata.get("status", "MODEL_NOT_TRAINED")

    def load_if_exists(self) -> bool:
        """Loads serialized model and baseline distribution statistics from disk."""
        if os.path.exists(MODEL_PATH) and os.path.exists(METADATA_PATH):
            try:
                bundle = joblib.load(MODEL_PATH)
                self.model = bundle["model"]
                self.imputer = bundle["imputer"]
                self.baseline_stats = bundle["baseline_stats"]
                with open(METADATA_PATH, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                return True
            except Exception:
                self.metadata["status"] = "MODEL_ERROR"
                return False
        return False

    def train(self, df: pd.DataFrame, min_samples: int = 50) -> Dict[str, Any]:
        """
        Trains Isolation Forest on historical baseline observations and records
        mean and standard deviation for subsequent feature attribution explanations.
        """
        if df.empty or len(df) < min_samples:
            self.metadata["status"] = "WAITING_FOR_DATA"
            return {
                "status": "WAITING_FOR_DATA",
                "message": (
                    f"Insufficient baseline readings to train anomaly detector. "
                    f"Required: {min_samples} observations; Available: {len(df)}."
                ),
                "required_samples": min_samples,
                "current_samples": len(df),
            }

        X = self.engineer.extract_anomaly_features(df)
        X_imp = self.imputer.fit_transform(X)

        # Record baseline distributions for explainability
        self.baseline_stats = {}
        for idx, col in enumerate(ANOMALY_FEATURE_COLUMNS):
            col_vals = X_imp[:, idx]
            self.baseline_stats[col] = {
                "mean": float(np.mean(col_vals)),
                "std": float(np.std(col_vals)) if np.std(col_vals) > 1e-4 else 1.0,
                "median": float(np.median(col_vals)),
            }

        iso = IsolationForest(
            n_estimators=100,
            contamination=self.contamination,
            random_state=42,
            n_jobs=-1,
        )
        iso.fit(X_imp)
        self.model = iso

        now_iso = datetime.now(timezone.utc).isoformat()
        self.metadata = {
            "status": "MODEL_TRAINED",
            "model_name": "IsolationForest",
            "model_version": self.model_version,
            "contamination": self.contamination,
            "train_samples": len(X),
            "features": ANOMALY_FEATURE_COLUMNS,
            "trained_at": now_iso,
        }

        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump(
            {
                "model": self.model,
                "imputer": self.imputer,
                "baseline_stats": self.baseline_stats,
            },
            MODEL_PATH,
        )
        with open(METADATA_PATH, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

        return self.metadata

    def detect_single(self, row_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs anomaly inference on a single observation with feature attribution.
        """
        if self.model is None:
            self.load_if_exists()

        if self.model is None:
            return {
                "status": "MODEL_NOT_TRAINED",
                "is_anomaly": False,
                "anomaly_score": 0.0,
                "severity": "NORMAL",
                "affected_sensors": [],
                "explanation": "Anomaly detection model not yet trained.",
            }

        single_df = pd.DataFrame([row_dict])
        X = self.engineer.extract_anomaly_features(single_df)
        X_imp = self.imputer.transform(X)

        # Raw decision score: lower values indicate greater outlier severity
        raw_score = float(self.model.decision_function(X_imp)[0])
        pred = int(self.model.predict(X_imp)[0])  # -1 = anomaly, 1 = normal

        is_anomaly = (pred == -1)

        # Determine severity
        if raw_score < -0.15:
            severity = "CRITICAL"
        elif raw_score < 0.0:
            severity = "WARNING"
        else:
            severity = "NORMAL"

        # Explainability: attribute which features contributed most to deviation
        deviations = []
        affected_sensors = []
        for idx, col in enumerate(ANOMALY_FEATURE_COLUMNS):
            val = float(X_imp[0, idx])
            stats = self.baseline_stats.get(col, {"mean": 0.0, "std": 1.0})
            z_score = abs(val - stats["mean"]) / stats["std"]
            if z_score >= 1.8:
                affected_sensors.append(col)
                direction = "higher" if val > stats["mean"] else "lower"
                deviations.append(f"{col} ({direction} than baseline by {z_score:.1f}σ)")

        if is_anomaly:
            if deviations:
                explanation = "Unusual condition detected: " + ", ".join(deviations) + ". Signal requires verification."
            else:
                explanation = "Multivariate sensor relationship diverged from baseline profile."
        else:
            explanation = "Sensor parameters conform to learned normal baseline."

        return {
            "status": "SUCCESS",
            "is_anomaly": is_anomaly,
            "anomaly_score": round(raw_score, 4),
            "severity": severity,
            "affected_sensors": affected_sensors,
            "explanation": explanation,
            "model_name": "IsolationForest",
            "model_version": self.model_version,
        }
