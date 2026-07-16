"""Data-quality inspection for imported telemetry (Stage 8 / v2 Import flow).

Before an imported CSV is analysed, we inspect it and run honest checks — does
the X/Y path close into a loop, are the channels physically plausible, are there
real braking and acceleration zones. This is what makes the importer read as an
engineering tool rather than a blind file upload.
"""
from __future__ import annotations

import numpy as np

from ..schemas.lap import LapTelemetry

TRACK_CLOSE_TOL = 0.08  # start-end gap must be within 8% of track extent


def _has_position(lap: LapTelemetry) -> bool:
    return not (np.allclose(lap.x, 0.0) and np.allclose(lap.y, 0.0))


def _track_closure(lap: LapTelemetry) -> tuple[bool, float]:
    span = max(lap.x.max() - lap.x.min(), lap.y.max() - lap.y.min())
    if span <= 0:
        return False, 0.0
    gap = float(np.hypot(lap.x[-1] - lap.x[0], lap.y[-1] - lap.y[0]))
    pct = round(gap / span * 100, 1)
    return gap <= TRACK_CLOSE_TOL * span, pct


def quality_checks(laps: list[LapTelemetry]) -> tuple[list[dict], LapTelemetry | None]:
    """Return (checks, reference_lap). Each check: {name, ok, detail}."""
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    ref = min(laps, key=lambda l: l.lap_time) if laps else None
    add("At least 2 timed laps", len(laps) >= 2, f"{len(laps)} lap(s) found")

    if ref is not None:
        has_xy = _has_position(ref)
        closes, pct = _track_closure(ref)
        add("Position (X/Y) present", has_xy,
            "GPS/position channel found" if has_xy else "no position data — track map disabled")
        add("Track closes into a loop", closes if has_xy else False,
            f"start↔end gap is {pct}% of track size" if has_xy else "needs position data")
        add("Distance is monotonic", bool(np.all(np.diff(ref.distance) >= 0)),
            f"{len(ref.distance)} samples")
        add("Speed physically plausible", 0 < ref.speed.max() < 400,
            f"max {ref.speed.max():.0f} km/h")
        add("Engine RPM present", ref.rpm.max() > 0, f"max {ref.rpm.max():.0f} rpm")
        add("Gears in range", 1 <= ref.ngear.max() <= 8, f"up to gear {int(ref.ngear.max())}")
        add("Braking detected", bool((ref.brake > 0).any()),
            f"{int((ref.brake > 0).sum())} braking samples")
        add("Braking + acceleration zones", bool((ref.brake > 0).any() and (ref.throttle > 80).any()),
            "both present" if (ref.brake > 0).any() and (ref.throttle > 80).any() else "missing one")

    return checks, ref


def track_preview(lap: LapTelemetry, n: int = 200) -> dict:
    step = max(1, len(lap.x) // n)
    return {
        "x": [round(float(v), 2) for v in lap.x[::step]],
        "y": [round(float(v), 2) for v in lap.y[::step]],
    }
