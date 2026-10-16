"""
Controlled Synthetic Environmental Telemetry Generator for Demonstration & Testing.

Generates reproducible multi-sensor scenario sequences labeled with is_mock=True.
Supports demonstration training and test verification prior to live hardware collection.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd


class SyntheticDataGenerator:
    """Produces controlled, reproducible environmental time-series scenarios."""

    @staticmethod
    def generate_scenario_dataset(
        scenario: str = "longitudinal_forecasting",
        n_samples: int = 180,
        device_id: str = "env_node_demo",
        start_time: Optional[datetime] = None,
        sample_interval_sec: int = 60,
        seed: Optional[int] = 42,
    ) -> pd.DataFrame:
        """
        Generates a synthetic scenario DataFrame strictly marked with is_mock=True.

        Supported scenarios:
        - "longitudinal_forecasting": Multi-hour time series with realistic diurnal curves for 60m RF training.
        - "normal": Baseline indoor climate without anomalies.
        - "increasing_mq135": Gradual upward drift in gas concentration.
        - "spike_mq135": Sharp transient gas voltage spike.
        - "multivariate_anomaly": Simultaneous thermal and air quality divergence.
        """
        rng = np.random.RandomState(seed) if seed is not None else np.random.RandomState()

        if start_time is None:
            start_time = datetime.now(timezone.utc) - timedelta(seconds=n_samples * sample_interval_sec)

        timestamps = [start_time + timedelta(seconds=i * sample_interval_sec) for i in range(n_samples)]
        time_seconds = np.arange(n_samples) * sample_interval_sec
        time_hours = time_seconds / 3600.0

        records: List[Dict[str, Any]] = []

        for idx, (t, t_sec, t_hr) in enumerate(zip(timestamps, time_seconds, time_hours)):
            # Baseline normal curves
            temp = 24.0 + 2.0 * np.sin(2.0 * np.pi * t_hr / 12.0) + rng.normal(0, 0.2)
            hum = 55.0 - 4.0 * np.sin(2.0 * np.pi * t_hr / 12.0) + rng.normal(0, 0.5)
            gas_v = 1.20 + 0.15 * np.sin(2.0 * np.pi * t_hr / 6.0) + rng.normal(0, 0.02)
            ir = int(max(0, 5 + 4 * np.sin(2.0 * np.pi * t_hr / 3.0) + rng.poisson(2)))
            fill = min(100.0, max(0.0, 40.0 + 5.0 * t_hr + rng.normal(0, 0.5)))
            dist = 100.0 - (fill / 100.0) * 90.0

            # Inject scenario specific dynamics
            if scenario == "increasing_mq135":
                # Linear increase over time up to 3.2V
                gas_v += 1.8 * (idx / float(n_samples))

            elif scenario == "spike_mq135":
                # Sharp transient spike in middle of series
                mid = n_samples // 2
                if abs(idx - mid) <= 4:
                    gas_v += 2.2 * np.exp(-0.5 * ((idx - mid) / 1.5) ** 2)

            elif scenario == "multivariate_anomaly":
                # Simultaneous divergence in last 10 samples
                if idx >= (n_samples - 10):
                    temp += 10.5
                    hum += 25.0
                    gas_v += 1.8
                    ir += 35

            elif scenario == "longitudinal_forecasting":
                # Smooth organic variations with cross-correlation for ML learning
                gas_v += 0.25 * np.sin(2.0 * np.pi * t_hr / 2.0)

            # Clamp physical limits
            temp = float(np.clip(temp, -10.0, 60.0))
            hum = float(np.clip(hum, 10.0, 95.0))
            gas_v = float(np.clip(gas_v, 0.2, 4.8))
            raw_adc = float(np.clip((gas_v / 1.5) / 3.3 * 4095.0, 0.0, 4095.0))

            records.append({
                "device_id": device_id,
                "timestamp": t,
                "is_mock": True,  # Explicit provenance tracking
                "temperature_c": round(temp, 2),
                "humidity_percent": round(hum, 2),
                "mq135_raw": round(raw_adc, 1),
                "mq135_voltage": round(gas_v, 3),
                "ir_count": ir,
                "ultrasonic_distance_cm": round(dist, 1),
                "bin_fill_percent": round(fill, 1),
                "sensor_status": {
                    "dht22": "OK",
                    "mq135": "OK",
                    "ir": "OK",
                    "ultrasonic": "OK",
                },
            })

        return pd.DataFrame(records)
