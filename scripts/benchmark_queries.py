#!/usr/bin/env python3
"""
Telemetry Query Benchmarking Script (Phase 4).

Generates a realistic time-series dataset of 10,000+ records and benchmarks:
1. Latest telemetry point lookup latency
2. Historical window range query latency
3. Multi-page cursor pagination throughput
4. SQLite index usage verification
"""

import asyncio
import time
import statistics
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, select
from app.models.telemetry import SensorReading
from app.services.telemetry_service import TelemetryService


BENCH_DB_URL = "sqlite+aiosqlite:///./data/bench_test.db"


async def setup_bench_database(total_records: int = 10000) -> async_sessionmaker:
    """Initialize benchmark database and bulk-insert test telemetry."""
    print(f"[*] Initializing benchmark database at {BENCH_DB_URL}...")
    engine = create_async_engine(BENCH_DB_URL, connect_args={"check_same_thread": False})
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    from app.database.session import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    print(f"[*] Seeding {total_records} realistic sensor records across 3 machines...")
    start_seed = time.perf_counter()

    base_time = datetime.now(timezone.utc) - timedelta(hours=48)
    devices = ["motor_001", "motor_002", "chiller_pump_01"]

    async with session_factory() as session:
        batch = []
        for i in range(total_records):
            dev = devices[i % len(devices)]
            ts = base_time + timedelta(seconds=i * 5)
            batch.append(
                SensorReading(
                    device_id=dev,
                    timestamp=ts,
                    is_mock=(i % 5 == 0),
                    temperature=42.0 + (i % 50) * 0.1,
                    accel_x=0.05,
                    accel_y=0.04,
                    accel_z=1.02,
                    gyro_x=0.1,
                    gyro_y=0.2,
                    gyro_z=0.3,
                    current=1.12,
                    voltage=11.8,
                    power=13.2,
                    rpm=1498.0 + (i % 20),
                )
            )
            if len(batch) >= 1000:
                session.add_all(batch)
                await session.commit()
                batch.clear()

        if batch:
            session.add_all(batch)
            await session.commit()

    seed_dur = (time.perf_counter() - start_seed) * 1000.0
    print(f"[+] Seeding complete in {seed_dur:.2f}ms.\n")
    return session_factory


async def benchmark_latest_query(session_factory: async_sessionmaker, iterations: int = 100):
    """Benchmark GET latest machine telemetry point."""
    latencies = []
    async with session_factory() as session:
        for _ in range(iterations):
            t0 = time.perf_counter()
            rec = await TelemetryService.get_latest_telemetry(session, "motor_001")
            latencies.append((time.perf_counter() - t0) * 1000.0)

    p50 = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
    print(f"--- 1. LATEST RECORD LOOKUP (100 iterations) ---")
    print(f"  Min: {min(latencies):.3f}ms | Mean: {statistics.mean(latencies):.3f}ms | P50: {p50:.3f}ms | P95: {p95:.3f}ms | Max: {max(latencies):.3f}ms")
    print(f"  Target Device: motor_001 | Found RPM: {rec.rpm} | Found Temp: {rec.temperature}C\n")


async def benchmark_history_window(session_factory: async_sessionmaker, iterations: int = 50):
    """Benchmark GET historical window query."""
    latencies = []
    async with session_factory() as session:
        for _ in range(iterations):
            t0 = time.perf_counter()
            res = await TelemetryService.get_historical_telemetry(
                session,
                device_id="motor_001",
                hours=48.0,
                limit=100,
            )
            latencies.append((time.perf_counter() - t0) * 1000.0)

    p50 = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
    print(f"--- 2. HISTORICAL WINDOW QUERY (48-hour window, 100 items per page) ---")
    print(f"  Min: {min(latencies):.3f}ms | Mean: {statistics.mean(latencies):.3f}ms | P50: {p50:.3f}ms | P95: {p95:.3f}ms | Max: {max(latencies):.3f}ms")
    print(f"  Total Rows Returned: {res.count} | Has More: {res.has_more}\n")


async def benchmark_cursor_pagination(session_factory: async_sessionmaker, pages: int = 10):
    """Benchmark multi-page cursor traversal."""
    cursor = None
    latencies = []
    total_retrieved = 0

    async with session_factory() as session:
        for p in range(pages):
            t0 = time.perf_counter()
            res = await TelemetryService.get_historical_telemetry(
                session,
                device_id="motor_001",
                hours=48.0,
                limit=100,
                cursor=cursor,
            )
            dur = (time.perf_counter() - t0) * 1000.0
            latencies.append(dur)
            total_retrieved += res.count
            cursor = res.next_cursor
            if not res.has_more:
                break

    print(f"--- 3. CURSOR PAGINATION TRAVERSAL (10 pages x 100 items = 1,000 items) ---")
    print(f"  Total items traversed: {total_retrieved} in {sum(latencies):.2f}ms total")
    print(f"  Per-page latency: Min={min(latencies):.3f}ms | Mean={statistics.mean(latencies):.3f}ms | Max={max(latencies):.3f}ms\n")


async def verify_index_plan(session_factory: async_sessionmaker):
    """Verify SQLite EXPLAIN QUERY PLAN utilizes composite index."""
    async with session_factory() as session:
        plan = await session.execute(
            text(
                "EXPLAIN QUERY PLAN "
                "SELECT * FROM sensor_readings "
                "WHERE device_id = 'motor_001' AND timestamp >= '2026-10-01' "
                "ORDER BY timestamp ASC, id ASC LIMIT 100"
            )
        )
        print("--- 4. EXPLAIN QUERY PLAN (Index Utilization) ---")
        for row in plan.fetchall():
            print(f"  {row}")
        print()


async def main():
    print("==================================================================")
    print("        AIoT MACHINE TELEMETRY QUERY BENCHMARK (PHASE 4)          ")
    print("==================================================================\n")
    session_factory = await setup_bench_database(total_records=10000)
    await verify_index_plan(session_factory)
    await benchmark_latest_query(session_factory, iterations=100)
    await benchmark_history_window(session_factory, iterations=50)
    await benchmark_cursor_pagination(session_factory, pages=10)
    print("==================================================================")
    print("        BENCHMARK COMPLETED SUCCESSFULLY                          ")
    print("==================================================================")


if __name__ == "__main__":
    asyncio.run(main())
