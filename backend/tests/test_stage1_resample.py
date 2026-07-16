"""Stage 1 acceptance tests - one check per invariant.

test_synthetic_* uses a hand-built lap whose resampled values are known in
closed form, so resampling correctness does not depend on any downloaded data.
The real-data tests reuse the Stage 0 cache (offline after first download).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest

from app.config import DEFAULT_SESSION
from app.ingestion.fastf1_loader import load_session, load_two_laps
from app.processing.distance_resample import (
    build_common_grid,
    resample_lap,
    resample_pair,
)
from app.schemas.lap import LapTelemetry


# --------------------------------------------------------------------------- #
# Closed-form synthetic checks (no network, exact expected values)            #
# --------------------------------------------------------------------------- #
def _synthetic_lap() -> LapTelemetry:
    # Non-uniform raw distance; linear channels so linear interp is exact.
    d = np.array([0.0, 1.0, 3.0, 4.0, 7.0, 10.0])
    return LapTelemetry(
        driver="TST", lap_number=1, lap_time=12.34, session_id="synthetic",
        distance=d,
        speed=2.0 * d,          # exact under linear interp
        throttle=d,
        rpm=1000.0 * d,
        x=d,
        y=-d,
        brake=np.array([0.0, 0.0, 1.0, 1.0, 0.0, 0.0]),  # discrete
        ngear=np.array([2.0, 3.0, 4.0, 5.0, 6.0, 7.0]),  # discrete/stepped
    )


def test_synthetic_linear_channels_exact():
    lap = _synthetic_lap()
    grid = np.arange(0.0, 10.0 + 1e-9, 2.0)   # [0,2,4,6,8,10]
    out = resample_lap(lap, grid)
    assert np.allclose(out.speed, 2.0 * grid)
    assert np.allclose(out.throttle, grid)
    assert np.allclose(out.rpm, 1000.0 * grid)
    assert np.allclose(out.x, grid)
    assert np.allclose(out.y, -grid)


def test_synthetic_discrete_channels_not_interpolated():
    lap = _synthetic_lap()
    grid = np.arange(0.0, 10.0 + 1e-9, 2.0)
    out = resample_lap(lap, grid)
    # nearest-neighbour: only real gear/brake values appear, never averages.
    assert set(np.unique(out.brake)).issubset({0.0, 1.0})
    assert np.allclose(out.ngear, np.round(out.ngear))
    assert set(np.unique(out.ngear)).issubset(set(lap.ngear.tolist()))


def test_synthetic_nan_boundary_is_dropped():
    lap = _synthetic_lap()
    lap.speed[0] = np.nan          # simulate a get_telemetry() boundary gap
    lap.distance[-1] = np.nan
    grid = np.arange(0.0, 8.0 + 1e-9, 2.0)
    out = resample_lap(lap, grid)
    assert not np.isnan(out.speed).any()


# --------------------------------------------------------------------------- #
# Real-data invariants (Stage 0 cache)                                        #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def pair():
    session = load_session(DEFAULT_SESSION)
    raw_fast, raw_slow = load_two_laps(DEFAULT_SESSION, session=session)
    return raw_fast, raw_slow, resample_pair(raw_fast, raw_slow)


def test_shared_grid(pair):
    _, _, p = pair
    assert np.array_equal(p.fast.distance, p.slow.distance)
    assert np.array_equal(p.fast.distance, p.grid)


def test_grid_is_uniform_step(pair):
    _, _, p = pair
    assert np.allclose(np.diff(p.grid), p.step_m)
    assert (np.diff(p.grid) > 0).all()


def test_channels_consistent_and_no_nan(pair):
    _, _, p = pair
    for lap in (p.fast, p.slow):
        assert lap.is_consistent()
        assert len(lap.speed) == len(p.grid)
        for ch in (lap.speed, lap.throttle, lap.brake, lap.rpm, lap.ngear, lap.x, lap.y):
            assert not np.isnan(ch).any()


def test_no_extrapolation(pair):
    raw_fast, raw_slow, p = pair
    upper = min(raw_fast.distance.max(), raw_slow.distance.max())
    assert p.grid[-1] <= upper + 1e-6
    assert p.grid[0] >= 0.0


def test_discrete_channels_valid_on_real_data(pair):
    _, _, p = pair
    for lap in (p.fast, p.slow):
        assert set(np.unique(lap.brake)).issubset({0.0, 1.0})
        assert np.allclose(lap.ngear, np.round(lap.ngear))
        assert lap.ngear.min() >= 1 and lap.ngear.max() <= 8


def test_continuous_channel_not_inflated(pair):
    raw_fast, _, p = pair
    # linear interpolation stays within the raw envelope (no invented peaks).
    assert p.fast.speed.max() <= raw_fast.speed.max() + 1e-6
    assert p.fast.speed.min() >= raw_fast.speed.min() - 1e-6
