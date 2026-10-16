#!/usr/bin/env python3
"""
Test Telemetry Transmitter Script.

Sends deterministic test telemetry frames to the FastAPI backend ingestion endpoint.
Used to verify network connectivity, schema validation, and persistence pipeline.

Usage:
    python3 scripts/send_test_telemetry.py [--url http://localhost:8000/api/v1/telemetry] [--count 5] [--delay 1.0]
"""

import sys
import time
import math
import argparse
from datetime import datetime, timezone
import httpx


def generate_telemetry_frame(seq: int, device_id: str, is_mock: bool = True) -> dict:
    """Generate a deterministic synthetic sensor reading frame."""
    t = seq * 0.1
    # Simulated operating conditions: ~42C, ~1.1A, ~12V, ~1500 RPM, ~1g on Z
    temp = 42.5 + 0.3 * math.sin(t)
    curr = 1.10 + 0.05 * math.sin(t * 2.0)
    volt = 11.8 + 0.02 * math.cos(t)
    power = volt * curr  # Exact physical consistency
    rpm = 1495.0 + 10.0 * math.sin(t * 1.5)

    # 3-Axis vibration with DC 1g gravity offset on Z
    accel_x = 0.05 * math.sin(2.0 * math.pi * 25.0 * t)
    accel_y = 0.04 * math.cos(2.0 * math.pi * 25.0 * t)
    accel_z = 1.00 + 0.08 * math.sin(2.0 * math.pi * 25.0 * t)

    return {
        "device_id": device_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_mock": is_mock,
        "sensor_status": {
            "mpu6050": True,
            "ds18b20": True,
            "ina219": True,
            "hall": True,
        },
        "temperature": round(temp, 2),
        "accel_x": round(accel_x, 4),
        "accel_y": round(accel_y, 4),
        "accel_z": round(accel_z, 4),
        "gyro_x": 0.10,
        "gyro_y": 0.15,
        "gyro_z": 0.20,
        "current": round(curr, 3),
        "voltage": round(volt, 2),
        "power": round(power, 3),
        "rpm": round(rpm, 1),
    }


def main():
    parser = argparse.ArgumentParser(description="Send test telemetry to AIoT FastAPI backend.")
    parser.add_argument(
        "--url",
        default="http://localhost:8000/api/v1/telemetry",
        help="FastAPI ingestion endpoint URL (default: http://localhost:8000/api/v1/telemetry)",
    )
    parser.add_argument(
        "--device-id",
        default="motor_001",
        help="Target device identifier (default: motor_001)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of telemetry frames to dispatch (default: 5)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between transmissions in seconds (default: 1.0)",
    )
    args = parser.parse_args()

    print("==================================================================")
    print("      AIoT TELEMETRY TRANSMITTER (INTEGRATION TEST BENCH)         ")
    print(f" Target Endpoint : {args.url}")
    print(f" Device ID       : {args.device_id}")
    print(f" Frame Count     : {args.count}")
    print(f" Delay Interval  : {args.delay}s")
    print(" NOTICE: Transmitting deterministic test telemetry frames.")
    print("==================================================================\n")

    client = httpx.Client(timeout=5.0)
    successful = 0
    failed = 0

    for i in range(1, args.count + 1):
        payload = generate_telemetry_frame(i, args.device_id, is_mock=True)
        start_time = time.perf_counter()

        try:
            response = client.post(args.url, json=payload)
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            if response.status_code == 201:
                res_data = response.json()
                print(
                    f"[{i}/{args.count}] SUCCESS (201 Created) | ID={res_data.get('telemetry_id')} | "
                    f"Temp={payload['temperature']}C | RPM={payload['rpm']} | Latency={latency_ms:.1f}ms"
                )
                successful += 1
            else:
                print(
                    f"[{i}/{args.count}] FAILED (Status {response.status_code}) | "
                    f"Body: {response.text} | Latency={latency_ms:.1f}ms"
                )
                failed += 1

        except httpx.ConnectError:
            print(f"[{i}/{args.count}] CONNECTION ERROR: Could not connect to {args.url}. Is backend running?")
            failed += 1
        except Exception as exc:
            print(f"[{i}/{args.count}] UNEXPECTED ERROR: {exc}")
            failed += 1

        if i < args.count:
            time.sleep(args.delay)

    print("\n------------------------------------------------------------------")
    print(f" Transmit Complete: {successful} successful, {failed} failed.")
    print("------------------------------------------------------------------")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
