"""M1 reproducible benchmark: per-phase cost of the UUMA pipeline.

Writes bench/m1_benchmark.json with a full reproducibility block
(CPU, OS, Python, iteration count, timestamp) plus mean/median/p95/
stdev/ops-per-sec per phase and for the full 5-phase pipeline.

Run from the project root:
    python bench/run_benchmark.py
"""
from __future__ import annotations
import json
import os
import platform
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from uuma.core.algorithm import UnifiedUniversalMiningAlgorithm  # noqa: E402
from uuma.core.phases import build_default_simulated_phases  # noqa: E402

ITERATIONS = 200
DATA = b"uuma-benchmark-fixed-input"


def _stats(samples: list[float]) -> dict:
    samples_sorted = sorted(samples)
    mean = statistics.mean(samples)
    return {
        "mean_seconds": mean,
        "median_seconds": statistics.median(samples),
        "p95_seconds": samples_sorted[max(int(0.95 * len(samples_sorted)) - 1, 0)],
        "stdev_seconds": statistics.stdev(samples) if len(samples) > 1 else 0.0,
        "ops_per_sec": (1.0 / mean) if mean > 0 else None,
    }


def main() -> None:
    phase_stats = {}
    for phase in build_default_simulated_phases():
        samples = []
        for nonce in range(ITERATIONS):
            t0 = time.perf_counter()
            phase.execute(DATA, nonce)
            samples.append(time.perf_counter() - t0)
        phase_stats[phase.name] = _stats(samples)

    algo = UnifiedUniversalMiningAlgorithm(build_default_simulated_phases())
    full_samples = []
    for nonce in range(ITERATIONS):
        t0 = time.perf_counter()
        algo.hash_once(DATA, nonce)
        full_samples.append(time.perf_counter() - t0)

    report = {
        "reproducibility": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor() or platform.machine(),
            "cpu_count": os.cpu_count(),
            "iterations_per_phase": ITERATIONS,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "per_phase": phase_stats,
        "full_pipeline": _stats(full_samples),
    }

    out_path = os.path.join(os.path.dirname(__file__), "m1_benchmark.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
