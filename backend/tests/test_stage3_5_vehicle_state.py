"""Stage 3.5 acceptance tests.

Synthetic laps make each detector's trigger condition explicit and known; the
real-data test asserts the cross-check is computed consistently.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest

from app.config import DEFAULT_SESSION
from app.ingestion.corner_reference import load_circuit_reference
from app.ingestion.fastf1_loader import load_session, load_two_laps
from app.processing.cause_classifier import analyze_corners
from app.processing.delta_calculator import compute_delta
from app.processing.distance_resample import resample_pair
from app.processing.vehicle_state_flags import (
    annotate_vehicle_state,
    calibrate_speed_rpm,
    detect_events,
)
from app.schemas.lap import (
    AlignedLapPair,
    CornerAnalysis,
    CornerAttribution,
    LapTelemetry,
)

RATIO = 53.0  # RPM per km/h in the synthetic gear


def _lap(speed, rpm, brake, throttle, gear=5.0, n=2):
    speed = np.asarray(speed, float)
    d = np.arange(speed.size, dtype=float) * 2.0
    ones = np.ones_like(speed)
    return LapTelemetry(
        driver="TST", lap_number=n, lap_time=90.0, session_id="synthetic",
        distance=d, speed=speed, throttle=throttle * ones if np.isscalar(throttle) else np.asarray(throttle, float),
        brake=brake * ones if np.isscalar(brake) else np.asarray(brake, float),
        rpm=np.asarray(rpm, float), ngear=gear * ones, x=d.copy(), y=d.copy(),
    )


def test_calibration_recovers_per_gear_ratio():
    speed = np.linspace(70.0, 300.0, 60)
    lap = _lap(speed, RATIO * speed, brake=0.0, throttle=100.0)
    ratios = calibrate_speed_rpm(lap)
    assert 5 in ratios
    assert np.isclose(ratios[5], RATIO, rtol=0.02)


def test_wheelspin_detected_as_rpm_excess_on_power():
    speed = np.full(30, 120.0)
    rpm = np.full(30, RATIO * 120.0)
    rpm[15] *= 1.20                       # 20% RPM excess at one on-power sample
    lap = _lap(speed, rpm, brake=0.0, throttle=100.0)
    lockup, wheelspin = detect_events(lap, calibrate_speed_rpm(lap))
    assert wheelspin[15]
    assert not lockup.any()               # no braking -> no lockup
    assert wheelspin.sum() == 1


def test_lockup_detected_as_decel_spike_under_braking():
    speed = np.full(21, 180.0)
    speed[11] = 168.0                     # ~12 km/h drop over 2 m at ~50 m/s -> ~8 g
    lap = _lap(speed, RATIO * speed, brake=1.0, throttle=0.0)
    lockup, wheelspin = detect_events(lap, calibrate_speed_rpm(lap))
    assert lockup[11]
    assert not wheelspin.any()            # on the brakes -> no wheelspin


def _one_corner_analysis(magnitude_s):
    attr = CornerAttribution(
        corner=1, distance=20.0, window=(0.0, 40.0), magnitude_s=magnitude_s,
        cause="x", confidence="high", brake_point_delta_m=0.0,
        apex_speed_delta_kmh=0.0, throttle_point_delta_m=0.0, signals=[],
    )
    return CornerAnalysis(corners=[attr], reconciliation_error_s=0.0,
                          total_attributed_s=magnitude_s)


def _lockup_pair():
    speed = np.full(21, 180.0)
    speed[11] = 168.0
    slow = _lap(speed, RATIO * speed, brake=1.0, throttle=0.0, n=2)
    fast = _lap(np.full(21, 180.0), RATIO * 180.0, brake=0.0, throttle=100.0, n=1)
    return AlignedLapPair(grid=slow.distance.copy(), fast=fast, slow=slow, step_m=2.0)


def test_crosscheck_confirms_lockup_that_coincides_with_time_loss():
    analysis = annotate_vehicle_state(_one_corner_analysis(+0.10), _lockup_pair())
    assert analysis.corners[0].lockup
    assert analysis.lockups_flagged == 1
    assert analysis.lockup_delta_agreement == 1.0


def test_crosscheck_does_not_confirm_lockup_on_a_time_gain():
    analysis = annotate_vehicle_state(_one_corner_analysis(-0.10), _lockup_pair())
    assert analysis.corners[0].lockup          # still detected...
    assert analysis.lockup_delta_agreement == 0.0   # ...but not confirmed by delta


# --------------------------------------------------------------------------- #
# Real data                                                                   #
# --------------------------------------------------------------------------- #
def test_real_vehicle_state_crosscheck_is_consistent():
    session = load_session(DEFAULT_SESSION)
    raw_fast, raw_slow = load_two_laps(DEFAULT_SESSION, session=session)
    circuit = load_circuit_reference(session)
    pair = resample_pair(raw_fast, raw_slow)
    delta = compute_delta(pair, reference="fast", target="slow")
    analysis = annotate_vehicle_state(analyze_corners(pair, delta, circuit), pair)

    assert analysis.lockups_flagged == sum(a.lockup for a in analysis.corners)
    assert analysis.wheelspins_flagged == sum(a.wheelspin for a in analysis.corners)
    for agreement in (analysis.lockup_delta_agreement, analysis.wheelspin_delta_agreement):
        assert agreement is None or 0.0 <= agreement <= 1.0
