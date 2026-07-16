"""Stage 3 - corner segmentation and cause classification (+ confidence).

The delta trace (Stage 2) is sliced into one window per official corner
(midpoint-partitioned, so the per-corner magnitudes telescope back to the total
gap). Within each window we compare three driver-input features between the two
laps - braking point, apex speed, throttle-reapplication point - using the
documented thresholds in config.py, and attribute the dominant cause.

Confidence keys off whether those signals AGREE:
  * high   - a single clear signal (or nothing to explain)
  * medium - several signals, all consistent with the target under-driving
  * low    - signals conflict (the trail-braking vs late-braking ambiguity:
             the target braked *later* yet also carried *less* apex speed or got
             on power later), or a real loss no input explains.

UNCERTAINTY NOTE: every magnitude here comes from telemetry that carries a
measured *global* reconciliation error (Stage 2, ~0.1 s on the sample data).
That error is deliberately NOT folded into the confidence score - confidence is
purely about signal agreement - but it is carried through on CornerAnalysis so
the UI/README can state that per-corner attributions inherit a global
reconciliation uncertainty. Keeps the project's uncertainty story consistent.
"""
from __future__ import annotations

from collections import namedtuple

import numpy as np

from ..config import (
    APEX_SPEED_TOL_KMH,
    BRAKE_ENGAGED,
    BRAKE_POINT_TOL_M,
    NEGLIGIBLE_CORNER_LOSS_S,
    THROTTLE_POINT_TOL_M,
    THROTTLE_REAPPLY_PCT,
)
from ..schemas.lap import (
    AlignedLapPair,
    CircuitReference,
    CornerAnalysis,
    CornerAttribution,
    DeltaResult,
    LapTelemetry,
)

_Feat = namedtuple("_Feat", "apex_speed apex_distance brake_point throttle_point")

CAUSES = (
    "negligible",
    "time gained by target",
    "unclassified",
    "early braking",
    "late braking",
    "lower apex speed",
    "delayed throttle",
)


def _corner_boundaries(grid: np.ndarray, corners) -> list[float]:
    """Midpoints between consecutive corners; ends clamped to the grid extent."""
    dists = [c.distance for c in corners]
    bounds = [float(grid[0])]
    bounds += [(a + b) / 2.0 for a, b in zip(dists, dists[1:])]
    bounds.append(float(grid[-1]))
    return bounds


def _features(lap: LapTelemetry, grid: np.ndarray, lo: float, hi: float) -> _Feat:
    win = (grid >= lo) & (grid <= hi)
    d = grid[win]
    if d.size == 0:
        return _Feat(np.nan, np.nan, np.nan, np.nan)
    speed, brake, thr = lap.speed[win], lap.brake[win], lap.throttle[win]

    apex_i = int(np.argmin(speed))
    brake_mask = brake > BRAKE_ENGAGED
    brake_point = float(d[np.argmax(brake_mask)]) if brake_mask.any() else np.nan

    post_apex = np.arange(d.size) > apex_i
    thr_mask = post_apex & (thr > THROTTLE_REAPPLY_PCT)
    throttle_point = float(d[np.argmax(thr_mask)]) if thr_mask.any() else np.nan

    return _Feat(float(speed[apex_i]), float(d[apex_i]), brake_point, throttle_point)


def _delta_at(grid: np.ndarray, delta: np.ndarray, x: float) -> float:
    i = int(np.searchsorted(grid, x))
    i = min(max(i, 0), len(delta) - 1)
    return float(delta[i])


def _classify(mag: float, d_brake: float, d_apex: float,
              d_throttle: float) -> tuple[str, str, list[str]]:
    """Return (cause, confidence, significant-signals)."""
    candidates: list[tuple[str, float]] = []
    if np.isfinite(d_brake):
        if d_brake < -BRAKE_POINT_TOL_M:
            candidates.append(("early braking", abs(d_brake) / BRAKE_POINT_TOL_M))
        elif d_brake > BRAKE_POINT_TOL_M:
            candidates.append(("late braking", abs(d_brake) / BRAKE_POINT_TOL_M))
    if np.isfinite(d_apex) and d_apex < -APEX_SPEED_TOL_KMH:
        candidates.append(("lower apex speed", abs(d_apex) / APEX_SPEED_TOL_KMH))
    if np.isfinite(d_throttle) and d_throttle > THROTTLE_POINT_TOL_M:
        candidates.append(("delayed throttle", abs(d_throttle) / THROTTLE_POINT_TOL_M))

    signals = [name for name, _ in candidates]

    if abs(mag) < NEGLIGIBLE_CORNER_LOSS_S:
        return "negligible", "high", signals
    if mag < 0:
        # target was actually faster through this corner
        return "time gained by target", "high", signals
    if not candidates:
        return "unclassified", "low", signals

    cause = max(candidates, key=lambda c: c[1])[0]
    # Conflict = target more aggressive on entry (late braking) yet still shows a
    # speed/throttle deficit -> genuinely ambiguous, report low confidence.
    conflict = ("late braking" in signals) and (
        ("lower apex speed" in signals) or ("delayed throttle" in signals)
    )
    if conflict:
        confidence = "low"
    elif len(candidates) == 1:
        confidence = "high"
    else:
        confidence = "medium"
    return cause, confidence, signals


def analyze_corners(pair: AlignedLapPair, delta_result: DeltaResult,
                    circuit: CircuitReference) -> CornerAnalysis:
    grid, delta = pair.grid, delta_result.delta
    corners = sorted(circuit.corners, key=lambda c: c.distance)
    bounds = _corner_boundaries(grid, corners)

    attributions: list[CornerAttribution] = []
    for k, corner in enumerate(corners):
        lo, hi = bounds[k], bounds[k + 1]
        ref = _features(pair.fast, grid, lo, hi)   # reference = fast lap
        tgt = _features(pair.slow, grid, lo, hi)   # target = slow lap

        d_brake = tgt.brake_point - ref.brake_point
        d_apex = tgt.apex_speed - ref.apex_speed
        d_throttle = tgt.throttle_point - ref.throttle_point
        mag = _delta_at(grid, delta, hi) - _delta_at(grid, delta, lo)

        cause, confidence, signals = _classify(mag, d_brake, d_apex, d_throttle)
        attributions.append(CornerAttribution(
            corner=corner.number, distance=corner.distance, window=(lo, hi),
            magnitude_s=mag, cause=cause, confidence=confidence,
            brake_point_delta_m=d_brake, apex_speed_delta_kmh=d_apex,
            throttle_point_delta_m=d_throttle, signals=signals,
        ))

    total = float(sum(a.magnitude_s for a in attributions))
    return CornerAnalysis(
        corners=attributions,
        reconciliation_error_s=delta_result.reconciliation_error,
        total_attributed_s=total,
    )
