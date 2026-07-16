"""Stage 3 acceptance tests.

Synthetic corners are hand-built so the correct cause + confidence are known;
real-data tests assert the structural invariants and the telescoping tie-back to
the Stage 2 reconciled gap.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest

from app.config import DEFAULT_SESSION
from app.ingestion.corner_reference import load_circuit_reference
from app.ingestion.fastf1_loader import load_session, load_two_laps
from app.processing.cause_classifier import CAUSES, analyze_corners
from app.processing.delta_calculator import compute_delta
from app.processing.distance_resample import resample_pair
from app.schemas.lap import (
    AlignedLapPair,
    CircuitReference,
    CornerMarker,
    DeltaResult,
    LapTelemetry,
)

STEP = 2.0
GRID = np.arange(0.0, 400.0 + 1e-9, STEP)


def _corner_lap(brake_start, apex_dist, apex_speed, throttle_on, lap_number,
                top_speed=300.0):
    """A single-corner lap: brake -> V-shaped speed dip -> back on power."""
    d = GRID
    speed = np.full_like(d, top_speed)
    down = (d >= brake_start) & (d <= apex_dist)
    speed[down] = np.interp(d[down], [brake_start, apex_dist], [top_speed, apex_speed])
    up = (d > apex_dist) & (d <= throttle_on)
    speed[up] = np.interp(d[up], [apex_dist, throttle_on], [apex_speed, top_speed])
    brake = ((d >= brake_start) & (d < apex_dist)).astype(float)
    throttle = np.where((d >= brake_start) & (d <= throttle_on), 0.0, 100.0)
    return LapTelemetry(
        driver="TST", lap_number=lap_number, lap_time=90.0, session_id="synthetic",
        distance=d.copy(), speed=speed, throttle=throttle, brake=brake,
        rpm=np.full_like(d, 10000.0), ngear=np.full_like(d, 5.0), x=d.copy(), y=d.copy(),
    )


def _analyze(fast, slow, delta_end=0.30, reconciliation=0.05):
    pair = AlignedLapPair(grid=GRID.copy(), fast=fast, slow=slow, step_m=STEP)
    delta = np.linspace(0.0, delta_end, GRID.size)
    dres = DeltaResult(
        distance=GRID.copy(), cum_time_reference=np.zeros_like(GRID),
        cum_time_target=delta.copy(), delta=delta, reference_lap=1, target_lap=2,
        integrated_gap=float(delta[-1]), measured_gap=float(delta[-1]) - reconciliation,
        reconciliation_error=reconciliation,
    )
    circuit = CircuitReference("synthetic", [CornerMarker(1, 200.0, 0.0, 0.0)])
    return analyze_corners(pair, dres, circuit)


def test_single_clear_cause_is_high_confidence():
    # Only apex speed differs; brake + throttle identical -> one signal, high.
    fast = _corner_lap(150, 200, 100, 205, 1)
    slow = _corner_lap(150, 200, 90, 205, 2)   # 10 km/h lower apex
    a = _analyze(fast, slow).corners[0]
    assert a.cause == "lower apex speed"
    assert a.confidence == "high"
    assert a.signals == ["lower apex speed"]


def test_multiple_consistent_signals_is_medium():
    # Target brakes early, lower apex, later throttle -> all consistent -> medium.
    fast = _corner_lap(150, 200, 100, 205, 1)
    slow = _corner_lap(140, 200, 90, 215, 2)
    a = _analyze(fast, slow).corners[0]
    assert a.confidence == "medium"
    assert set(a.signals) == {"early braking", "lower apex speed", "delayed throttle"}
    assert a.cause in a.signals


def test_conflicting_signals_is_low_confidence():
    # Target brakes LATER (aggressive) yet carries LESS apex speed -> ambiguous.
    fast = _corner_lap(150, 200, 100, 205, 1)
    slow = _corner_lap(162, 200, 90, 205, 2)   # brakes 12m late, apex 10 low
    a = _analyze(fast, slow).corners[0]
    assert "late braking" in a.signals and "lower apex speed" in a.signals
    assert a.confidence == "low"


def test_negligible_loss_is_high_and_negligible():
    fast = _corner_lap(150, 200, 100, 205, 1)
    slow = _corner_lap(150, 200, 100, 205, 2)  # identical
    a = _analyze(fast, slow, delta_end=0.0).corners[0]
    assert a.cause == "negligible"
    assert a.confidence == "high"


# --------------------------------------------------------------------------- #
# Real-data structural invariants                                             #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def real_analysis():
    session = load_session(DEFAULT_SESSION)
    raw_fast, raw_slow = load_two_laps(DEFAULT_SESSION, session=session)
    circuit = load_circuit_reference(session)
    pair = resample_pair(raw_fast, raw_slow)
    delta = compute_delta(pair, reference="fast", target="slow")
    return delta, analyze_corners(pair, delta, circuit)


def test_every_corner_classified(real_analysis):
    _, analysis = real_analysis
    assert len(analysis.corners) == 11          # Monza
    for a in analysis.corners:
        assert a.cause in CAUSES
        assert a.confidence in {"high", "medium", "low"}


def test_magnitudes_telescope_to_integrated_gap(real_analysis):
    delta, analysis = real_analysis
    assert np.isclose(analysis.total_attributed_s, delta.integrated_gap, atol=1e-6)


def test_reconciliation_error_carried_through(real_analysis):
    delta, analysis = real_analysis
    assert analysis.reconciliation_error_s == delta.reconciliation_error
