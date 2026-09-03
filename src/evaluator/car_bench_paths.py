"""Filesystem paths for the local CAR-bench dependency."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAR_BENCH_REPO = PROJECT_ROOT / "third_party" / "car-bench"
CAR_BENCH_DATA_DIR = (
    CAR_BENCH_REPO
    / "car_bench"
    / "envs"
    / "car_voice_assistant"
    / "mock_data"
)

