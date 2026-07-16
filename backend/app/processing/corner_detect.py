"""Corner detection for imported telemetry that has no official markers.

FastF1 gives ground-truth corner locations, so we use those (Stage 0) and never
re-derive them. Imported sim / student-logger data has no such reference, so here
corners are detected as prominent local minima in the speed trace (apexes). This
is a deliberate, stated fallback used ONLY when official markers are unavailable.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import find_peaks

from ..schemas.lap import CircuitReference, CornerMarker, LapTelemetry


def detect_corners(
    lap: LapTelemetry,
    min_prominence_kph: float = 8.0,
    min_separation_m: float = 30.0,
    apex_fraction: float = 0.92,
) -> CircuitReference:
    """Corners = speed minima with real prominence, below apex_fraction of vmax."""
    v = lap.speed
    d = lap.distance
    step = float(np.median(np.diff(d))) if len(d) > 1 else 2.0
    distance_samples = max(1, int(min_separation_m / max(step, 1e-6)))

    idx, _ = find_peaks(-v, prominence=min_prominence_kph, distance=distance_samples)
    vmax = float(v.max())
    idx = [i for i in idx if v[i] < apex_fraction * vmax]

    corners = [
        CornerMarker(number=k + 1, distance=float(d[i]), x=float(lap.x[i]), y=float(lap.y[i]))
        for k, i in enumerate(idx)
    ]
    return CircuitReference(circuit_name="imported (corners auto-detected)", corners=corners)
