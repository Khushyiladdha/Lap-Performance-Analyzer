"""Stage 1 - distance-grid resampling.

Each raw lap is naturally indexed by time and the two laps take different total
times, so comparing them by timestamp would misregister every corner. Here we
put both laps on ONE shared distance grid so array index i means the same point
on track for both laps - the precondition for the Stage 2 time delta.

Interpolation kind is chosen per channel on purpose:
  * linear  for continuous signals (speed/throttle/rpm/x/y)
  * nearest for discrete signals (brake 0/1, nGear) - linear interpolation would
    invent a half-pressed brake (0.5) or a fractional gear (6.4) that never
    physically existed.
"""
from __future__ import annotations

import numpy as np
from scipy.interpolate import interp1d  # available and stable in scipy>=1.11

from ..config import DISTANCE_STEP_M
from ..schemas.lap import AlignedLapPair, LapTelemetry

_LINEAR_CHANNELS = ("speed", "throttle", "rpm", "x", "y")
_NEAREST_CHANNELS = ("brake", "ngear")


def _clean_monotonic(distance: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Drop non-finite samples and collapse duplicate distances.

    interp1d requires strictly increasing x. Raw FastF1 distance is sorted but
    can carry NaNs at lap boundaries and repeated values; we keep the first
    sample of any repeated distance.
    """
    d = np.asarray(distance, dtype=float)
    v = np.asarray(values, dtype=float)
    finite = np.isfinite(d) & np.isfinite(v)
    d, v = d[finite], v[finite]
    if d.size == 0:
        raise ValueError("channel has no finite samples")
    strictly_increasing = np.concatenate(([True], np.diff(d) > 0))
    return d[strictly_increasing], v[strictly_increasing]


def _interp_channel(distance: np.ndarray, values: np.ndarray,
                    grid: np.ndarray, kind: str) -> np.ndarray:
    d, v = _clean_monotonic(distance, values)
    # bounds_error=False + edge fill guards against tiny FP overshoot at the
    # grid endpoints; the grid is otherwise constructed to stay interior.
    f = interp1d(d, v, kind=kind, bounds_error=False, fill_value=(v[0], v[-1]))
    return f(grid)


def build_common_grid(lap_a: LapTelemetry, lap_b: LapTelemetry,
                      step: float = DISTANCE_STEP_M) -> np.ndarray:
    """A shared grid covering only the distance range both laps actually span."""
    da = lap_a.distance[np.isfinite(lap_a.distance)]
    db = lap_b.distance[np.isfinite(lap_b.distance)]
    start = max(da.min(), db.min(), 0.0)
    end = min(da.max(), db.max())          # min -> no extrapolation for either lap
    if end <= start:
        raise ValueError("laps do not overlap in distance")
    n = int(np.floor((end - start) / step)) + 1
    return start + np.arange(n) * step


def resample_lap(lap: LapTelemetry, grid: np.ndarray) -> LapTelemetry:
    """Resample one lap onto the given distance grid."""
    ch = {name: _interp_channel(lap.distance, getattr(lap, name), grid, "linear")
          for name in _LINEAR_CHANNELS}
    for name in _NEAREST_CHANNELS:
        ch[name] = _interp_channel(lap.distance, getattr(lap, name), grid, "nearest")
    # nearest already returns real samples; round is a defensive no-op that
    # guarantees clean 0/1 brake and integer-valued gears.
    ch["brake"] = np.round(ch["brake"])
    ch["ngear"] = np.round(ch["ngear"])
    return LapTelemetry(
        driver=lap.driver, lap_number=lap.lap_number, lap_time=lap.lap_time,
        session_id=lap.session_id, distance=grid.copy(),
        speed=ch["speed"], throttle=ch["throttle"], brake=ch["brake"],
        rpm=ch["rpm"], ngear=ch["ngear"], x=ch["x"], y=ch["y"],
    )


def resample_pair(lap_a: LapTelemetry, lap_b: LapTelemetry,
                  step: float = DISTANCE_STEP_M) -> AlignedLapPair:
    """Resample both laps onto one shared grid and return the aligned pair."""
    grid = build_common_grid(lap_a, lap_b, step)
    return AlignedLapPair(
        grid=grid,
        fast=resample_lap(lap_a, grid),
        slow=resample_lap(lap_b, grid),
        step_m=step,
    )
