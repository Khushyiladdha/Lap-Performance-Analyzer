"""Stage 2 - cumulative time-delta calculation and reconciliation.

Each lap's elapsed time vs distance is the integral of (1 / speed) along the
distance axis. The delta trace is the difference of the two laps' elapsed-time
curves - the professional-standard metric, not just an overlaid speed trace.

Reconciliation: the delta at the finish line must equal the measured lap-time
gap. If it doesn't, the Stage 1 resampling has an error - this is the pipeline's
first hard sanity check, and (later) a visible credibility metric in the UI.
"""
from __future__ import annotations

import numpy as np
from scipy.integrate import cumulative_trapezoid

from ..schemas.lap import AlignedLapPair, DeltaResult, LapTelemetry

_KMH_TO_MS = 1000.0 / 3600.0
_MIN_SPEED_MS = 0.1  # floor to keep 1/v finite if a sample ever reads ~0


def _seconds_per_meter(speed_kmh: np.ndarray) -> np.ndarray:
    v = np.asarray(speed_kmh, dtype=float) * _KMH_TO_MS
    v = np.clip(v, _MIN_SPEED_MS, None)
    return 1.0 / v


def _cumulative_time(distance: np.ndarray, speed_kmh: np.ndarray) -> np.ndarray:
    """Elapsed time at each grid point (starts at 0). Assumes a clean grid."""
    return cumulative_trapezoid(_seconds_per_meter(speed_kmh), distance, initial=0.0)


def integrated_lap_time(lap: LapTelemetry) -> float:
    """Speed-integrated total time over a lap's own distance axis.

    Cleans non-finite / duplicate-distance samples so it works on raw laps too;
    used to check the integration against the FastF1-measured lap time.
    """
    d = np.asarray(lap.distance, dtype=float)
    v = np.asarray(lap.speed, dtype=float)
    finite = np.isfinite(d) & np.isfinite(v)
    d, v = d[finite], v[finite]
    strictly_increasing = np.concatenate(([True], np.diff(d) > 0))
    d, v = d[strictly_increasing], v[strictly_increasing]
    return float(_cumulative_time(d, v)[-1])


def compute_delta(pair: AlignedLapPair,
                  reference: str = "fast", target: str = "slow") -> DeltaResult:
    """Build the cumulative delta trace + reconciliation for an aligned pair."""
    laps = {"fast": pair.fast, "slow": pair.slow}
    ref_lap, tgt_lap = laps[reference], laps[target]

    grid = pair.grid
    t_ref = _cumulative_time(grid, ref_lap.speed)
    t_tgt = _cumulative_time(grid, tgt_lap.speed)
    delta = t_tgt - t_ref

    integrated_gap = float(delta[-1])
    measured_gap = float(tgt_lap.lap_time - ref_lap.lap_time)
    return DeltaResult(
        distance=grid,
        cum_time_reference=t_ref,
        cum_time_target=t_tgt,
        delta=delta,
        reference_lap=ref_lap.lap_number,
        target_lap=tgt_lap.lap_number,
        integrated_gap=integrated_gap,
        measured_gap=measured_gap,
        reconciliation_error=integrated_gap - measured_gap,
    )
