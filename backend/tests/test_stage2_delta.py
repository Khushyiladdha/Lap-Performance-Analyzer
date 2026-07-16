"""Stage 2 acceptance tests + Stage 1.5 delta-integrator closed-form fixtures.

Two kinds of check, kept separate on purpose:
  * synthetic (constant-speed) laps -> the delta and reconciliation are known in
    closed form, so the integrator math is proven EXACT, independent of any data.
  * real data -> reconciliation error is small but nonzero (genuine FastF1
    data-fusion noise); asserted against the documented flag threshold.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest

from app.config import DEFAULT_SESSION, RECONCILIATION_FLAG_TOL_S
from app.ingestion.fastf1_loader import load_session, load_two_laps
from app.processing.delta_calculator import compute_delta, integrated_lap_time
from app.processing.distance_resample import resample_pair
from app.schemas.lap import AlignedLapPair, LapTelemetry


# --------------------------------------------------------------------------- #
# Closed-form synthetic fixtures (Stage 1.5, delta-integrator half)           #
# --------------------------------------------------------------------------- #
def _constant_speed_lap(speed_kmh: float, length_m: float, step: float,
                        lap_number: int) -> LapTelemetry:
    grid = np.arange(0.0, length_m + 1e-9, step)
    ones = np.ones_like(grid)
    speed_ms = speed_kmh * (1000.0 / 3600.0)
    lap_time = length_m / speed_ms
    return LapTelemetry(
        driver="TST", lap_number=lap_number, lap_time=lap_time, session_id="synthetic",
        distance=grid, speed=speed_kmh * ones, throttle=100.0 * ones,
        brake=0.0 * ones, rpm=10000.0 * ones, ngear=6.0 * ones, x=grid, y=grid,
    )


def _synthetic_pair(step: float = 2.0) -> AlignedLapPair:
    # fast = 90 km/h (25 m/s) -> 40.0 s over 1000 m; slow = 72 km/h (20 m/s) -> 50.0 s.
    fast = _constant_speed_lap(90.0, 1000.0, step, lap_number=1)
    slow = _constant_speed_lap(72.0, 1000.0, step, lap_number=2)
    return AlignedLapPair(grid=fast.distance.copy(), fast=fast, slow=slow, step_m=step)


def test_synthetic_delta_endpoint_and_reconciliation_exact():
    res = compute_delta(_synthetic_pair(), reference="fast", target="slow")
    assert np.isclose(res.cum_time_reference[-1], 40.0)
    assert np.isclose(res.cum_time_target[-1], 50.0)
    assert np.isclose(res.integrated_gap, 10.0)
    assert np.isclose(res.measured_gap, 10.0)
    assert abs(res.reconciliation_error) < 1e-9   # math is exact


def test_synthetic_delta_is_linear_in_distance():
    pair = _synthetic_pair()
    res = compute_delta(pair, reference="fast", target="slow")
    # delta(d) = d * (1/20 - 1/25) = d * 0.01
    assert np.isclose(res.delta[0], 0.0)
    assert np.allclose(res.delta, pair.grid * 0.01)


def test_synthetic_sign_convention_flips_when_target_is_faster():
    pair = _synthetic_pair()
    res = compute_delta(pair, reference="slow", target="fast")
    # target (fast) reaches the line sooner -> delta ends negative.
    assert res.integrated_gap < 0
    assert np.isclose(res.integrated_gap, -10.0)


# --------------------------------------------------------------------------- #
# Real-data reconciliation (Stage 0 cache)                                     #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def real_delta():
    session = load_session(DEFAULT_SESSION)
    raw_fast, raw_slow = load_two_laps(DEFAULT_SESSION, session=session)
    pair = resample_pair(raw_fast, raw_slow)
    return raw_fast, raw_slow, compute_delta(pair, reference="fast", target="slow")


def test_delta_starts_at_zero_and_matches_grid(real_delta):
    _, _, res = real_delta
    assert np.isclose(res.delta[0], 0.0)
    assert len(res.delta) == len(res.distance)


def test_cumulative_time_is_monotonic(real_delta):
    _, _, res = real_delta
    assert (np.diff(res.cum_time_reference) >= 0).all()
    assert (np.diff(res.cum_time_target) >= 0).all()


def test_reconciliation_within_threshold(real_delta):
    _, _, res = real_delta
    assert abs(res.reconciliation_error) < RECONCILIATION_FLAG_TOL_S
    # and small relative to the lap itself (< 0.5% of ~80 s)
    assert abs(res.reconciliation_error) / abs(res.measured_gap + res.cum_time_reference[-1]) < 0.005


def test_per_lap_integration_close_to_measured(real_delta):
    raw_fast, raw_slow, _ = real_delta
    for raw in (raw_fast, raw_slow):
        integ = integrated_lap_time(raw)
        assert abs(integ - raw.lap_time) / raw.lap_time < 0.005  # within 0.5%
