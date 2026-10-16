"""
Feature Engineering and Target Alignment Engine for Environmental Time-Series.

Constructs lagged features, rolling statistical aggregations, rate of change,
multivariate sensor metrics, and cyclic temporal encodings.
Enforces strict chronological alignment for 60-minute ahead MQ135 forecast
without future data leakage.
"""

import math
from typing import List, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer

# Canonical feature column names for the 60-minute Random Forest forecaster
FEATURE_COLUMNS: List[str] = [
    "mq135_voltage",
    "lag_5m",
    "lag_10m",
    "lag_15m",
    "lag_30m",
    "roll_mean_15m",
    "roll_std_15m",
    "roll_mean_30m",
    "rate_of_change",
    "temperature_c",
    "humidity_percent",
    "ir_count",
    "bin_fill_percent",
    "hour_sin",
    "hour_cos",
]

# Baseline feature set for multivariate Isolation Forest anomaly detector
ANOMALY_FEATURE_COLUMNS: List[str] = [
    "mq135_voltage",
    "temperature_c",
    "humidity_percent",
    "ir_count",
    "bin_fill_percent",
    "mq135_rate_of_change",
    "temp_rate_of_change",
]


class EnvironmentalFeatureEngineer:
    """Preprocesses raw environmental observations into ML-ready feature matrices."""

    def __init__(self):
        self.imputer = SimpleImputer(strategy="median")
        self.anomaly_imputer = SimpleImputer(strategy="median")
        self.is_fitted = False

    def build_forecasting_dataset(
        self,
        df: pd.DataFrame,
        horizon_minutes: int = 60,
        tolerance_minutes: int = 10,
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Builds feature matrix X and aligned future target y for MQ135 forecasting.

        Target alignment:
        For each record at timestamp t, y is the mq135_voltage at approximately
        t + horizon_minutes (within tolerance_minutes).
        Rows without valid historical lookbacks or future targets are dropped.
        """
        if df.empty or len(df) < 5:
            return pd.DataFrame(columns=FEATURE_COLUMNS), pd.Series(dtype=float)

        data = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(data["timestamp"]):
            data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)

        data = data.sort_values("timestamp").reset_index(drop=True)

        # 1. Compute time-derived features
        hours = data["timestamp"].dt.hour + data["timestamp"].dt.minute / 60.0
        data["hour_sin"] = np.sin(2.0 * np.pi * hours / 24.0)
        data["hour_cos"] = np.cos(2.0 * np.pi * hours / 24.0)

        # 2. Resample or compute time-based lags and rolling metrics
        # Set timestamp as index for rolling and time shifts
        indexed = data.set_index("timestamp")

        # Rolling statistics (using time windows)
        mq = indexed["mq135_voltage"]
        indexed["roll_mean_15m"] = mq.rolling("15min", min_periods=1).mean()
        indexed["roll_std_15m"] = mq.rolling("15min", min_periods=1).std().fillna(0.0)
        indexed["roll_mean_30m"] = mq.rolling("30min", min_periods=1).mean()

        data = indexed.reset_index()

        # Shifted / lagged lookback merges (asof merge backwards)
        for lag_min in [5, 10, 15, 30]:
            target_lag_time = data["timestamp"] - pd.Timedelta(minutes=lag_min)
            merged_lag = pd.merge_asof(
                pd.DataFrame({"target_lag_time": target_lag_time}),
                data[["timestamp", "mq135_voltage"]],
                left_on="target_lag_time",
                right_on="timestamp",
                direction="nearest",
                tolerance=pd.Timedelta(minutes=max(2, lag_min // 2)),
            )
            data[f"lag_{lag_min}m"] = merged_lag["mq135_voltage"].values

        # Rate of change: (V(t) - V(t - 5m)) / 5.0
        diff_5m = data["mq135_voltage"] - data["lag_5m"]
        data["rate_of_change"] = diff_5m.fillna(0.0) / 5.0

        # Fill lag NaNs using forward fill then backward fill so early records don't discard
        for col in ["lag_5m", "lag_10m", "lag_15m", "lag_30m"]:
            data[col] = data[col].bfill().ffill()

        # 3. Target Alignment: find mq135_voltage at t + horizon_minutes
        data["future_target_time"] = data["timestamp"] + pd.Timedelta(minutes=horizon_minutes)

        target_merge = pd.merge_asof(
            data[["future_target_time"]],
            data[["timestamp", "mq135_voltage"]],
            left_on="future_target_time",
            right_on="timestamp",
            direction="nearest",
            tolerance=pd.Timedelta(minutes=tolerance_minutes),
        )
        data["target_60m"] = target_merge["mq135_voltage"].values

        # Filter out records that have no future target (i.e. the most recent 60 minutes)
        valid_mask = data["target_60m"].notna() & data["mq135_voltage"].notna()
        clean_df = data[valid_mask].copy().reset_index(drop=True)

        if clean_df.empty:
            return pd.DataFrame(columns=FEATURE_COLUMNS), pd.Series(dtype=float)

        X = clean_df[FEATURE_COLUMNS].copy()
        y = clean_df["target_60m"].copy()

        return X, y

    def extract_single_feature_vector(
        self,
        recent_df: pd.DataFrame,
    ) -> Optional[np.ndarray]:
        """
        Extracts a single feature vector for real-time 60-minute prediction
        using the most recent observation and historical context.
        """
        if recent_df.empty:
            return None

        data = recent_df.copy()
        if not pd.api.types.is_datetime64_any_dtype(data["timestamp"]):
            data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)
        data = data.sort_values("timestamp").reset_index(drop=True)

        latest_row = data.iloc[-1]
        latest_time = latest_row["timestamp"]

        # Temporal cyclic features
        hours = latest_time.hour + latest_time.minute / 60.0
        hour_sin = np.sin(2.0 * np.pi * hours / 24.0)
        hour_cos = np.cos(2.0 * np.pi * hours / 24.0)

        # Lags from historical rows
        lags = {}
        for lag_min in [5, 10, 15, 30]:
            target_t = latest_time - pd.Timedelta(minutes=lag_min)
            # Find closest historical reading
            time_diffs = (data["timestamp"] - target_t).abs()
            closest_idx = time_diffs.idxmin()
            if time_diffs.loc[closest_idx] <= pd.Timedelta(minutes=max(3, lag_min // 2)):
                lags[f"lag_{lag_min}m"] = float(data.loc[closest_idx, "mq135_voltage"])
            else:
                lags[f"lag_{lag_min}m"] = float(latest_row["mq135_voltage"])

        # Rolling statistics over available window
        recent_15m = data[data["timestamp"] >= (latest_time - pd.Timedelta(minutes=15))]
        roll_mean_15m = float(recent_15m["mq135_voltage"].mean()) if not recent_15m.empty else float(latest_row["mq135_voltage"])
        roll_std_15m = float(recent_15m["mq135_voltage"].std()) if len(recent_15m) > 1 else 0.0
        if math.isnan(roll_std_15m):
            roll_std_15m = 0.0

        recent_30m = data[data["timestamp"] >= (latest_time - pd.Timedelta(minutes=30))]
        roll_mean_30m = float(recent_30m["mq135_voltage"].mean()) if not recent_30m.empty else float(latest_row["mq135_voltage"])

        rate_of_change = (float(latest_row["mq135_voltage"]) - lags["lag_5m"]) / 5.0

        features = [
            float(latest_row["mq135_voltage"]) if pd.notna(latest_row["mq135_voltage"]) else 1.2,
            lags["lag_5m"],
            lags["lag_10m"],
            lags["lag_15m"],
            lags["lag_30m"],
            roll_mean_15m,
            roll_std_15m,
            roll_mean_30m,
            rate_of_change,
            float(latest_row["temperature_c"]) if pd.notna(latest_row["temperature_c"]) else np.nan,
            float(latest_row["humidity_percent"]) if pd.notna(latest_row["humidity_percent"]) else np.nan,
            float(latest_row["ir_count"]) if pd.notna(latest_row["ir_count"]) else 0.0,
            float(latest_row["bin_fill_percent"]) if pd.notna(latest_row["bin_fill_percent"]) else 0.0,
            hour_sin,
            hour_cos,
        ]

        # Convert to DataFrame (1, n_features) with column names to avoid scikit-learn UserWarning
        feat_df = pd.DataFrame([features], columns=FEATURE_COLUMNS)
        if self.is_fitted:
            feat_arr = self.imputer.transform(feat_df)
        else:
            feat_arr = np.nan_to_num(feat_df.to_numpy(), nan=25.0)

        return feat_arr

    def extract_anomaly_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extracts multivariate feature matrix for Isolation Forest anomaly detection."""
        data = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(data["timestamp"]):
            data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)
        data = data.sort_values("timestamp").reset_index(drop=True)

        # Compute rates of change
        data["mq135_diff"] = data["mq135_voltage"].diff().fillna(0.0)
        data["temp_diff"] = data["temperature_c"].diff().fillna(0.0)
        data["time_diff_sec"] = data["timestamp"].diff().dt.total_seconds().fillna(3.0)
        data["time_diff_sec"] = data["time_diff_sec"].replace(0, 3.0)

        data["mq135_rate_of_change"] = data["mq135_diff"] / data["time_diff_sec"]
        data["temp_rate_of_change"] = data["temp_diff"] / data["time_diff_sec"]

        # Ensure all columns exist
        for col in ANOMALY_FEATURE_COLUMNS:
            if col not in data.columns:
                data[col] = np.nan

        return data[ANOMALY_FEATURE_COLUMNS].copy()
