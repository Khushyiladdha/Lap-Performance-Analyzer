"""Normalized internal telemetry schema.

Nothing downstream of ingestion touches FastF1 types directly — every stage
consumes these plain dataclasses. That boundary is what makes the Stage 8 sim
importer a drop-in: it only has to produce a LapTelemetry.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class LapTelemetry:
    """One lap, all channels sampled on the raw (time-based) FastF1 index.

    All channel arrays are the same length. Stage 1 resamples these onto a
    common distance grid; Stage 0 only guarantees they are present and aligned.
    """
    driver: str
    lap_number: int
    lap_time: float          # seconds (NaN if unavailable)
    session_id: str
    distance: np.ndarray     # meters from lap start
    speed: np.ndarray        # km/h
    throttle: np.ndarray     # 0-100 %
    brake: np.ndarray        # 0/1 (FastF1 exposes brake as boolean)
    rpm: np.ndarray          # engine RPM
    ngear: np.ndarray        # gear number
    x: np.ndarray            # track position X (for the Delta Track Map, later)
    y: np.ndarray            # track position Y

    def _channels(self) -> tuple[np.ndarray, ...]:
        return (self.distance, self.speed, self.throttle, self.brake,
                self.rpm, self.ngear, self.x, self.y)

    def channel_lengths(self) -> set[int]:
        return {len(a) for a in self._channels()}

    def is_consistent(self) -> bool:
        """True iff every channel is the same non-zero length."""
        lengths = self.channel_lengths()
        return len(lengths) == 1 and next(iter(lengths)) > 0


@dataclass
class CornerMarker:
    """One official corner marker from FastF1's circuit info."""
    number: int
    distance: float          # meters from lap start
    x: float
    y: float


@dataclass
class CircuitReference:
    """Ground-truth corner markers for a circuit (not re-derived)."""
    circuit_name: str
    corners: list[CornerMarker]


@dataclass
class AlignedLapPair:
    """Two laps resampled onto one shared distance grid.

    Invariant: fast.distance and slow.distance are both exactly `grid`. This is
    the precondition Stage 2 relies on to difference the laps index-by-index.
    """
    grid: np.ndarray          # meters, strictly increasing at step_m
    fast: LapTelemetry        # on grid
    slow: LapTelemetry        # on grid
    step_m: float


@dataclass
class DeltaResult:
    """Cumulative time-delta trace between two laps, plus reconciliation.

    Sign convention: delta = time(target) - time(reference), so delta rises
    where the reference lap is faster (the target is losing time).
    """
    distance: np.ndarray            # shared grid (m)
    cum_time_reference: np.ndarray  # elapsed time of the reference lap (s)
    cum_time_target: np.ndarray     # elapsed time of the target lap (s)
    delta: np.ndarray               # cumulative time delta (s)
    reference_lap: int
    target_lap: int
    integrated_gap: float           # delta[-1] - the trace's finish-line value
    measured_gap: float             # target.lap_time - reference.lap_time (ground truth)
    reconciliation_error: float     # integrated_gap - measured_gap


@dataclass
class CornerAttribution:
    """Why the target lap lost (or gained) time at one corner.

    magnitude_s is the change in the delta trace across the corner's window;
    the *_delta fields are target-minus-reference so a negative brake-point
    delta means the target braked earlier, a negative apex-speed delta means it
    carried less speed, a positive throttle-point delta means it got on power later.
    """
    corner: int
    distance: float
    window: tuple[float, float]
    magnitude_s: float
    cause: str
    confidence: str                 # "high" | "medium" | "low"
    brake_point_delta_m: float      # target - reference (neg = target braked earlier)
    apex_speed_delta_kmh: float     # target - reference (neg = target slower apex)
    throttle_point_delta_m: float   # target - reference (pos = target later on power)
    signals: list[str]              # significant driver-input signals found
    lockup: bool = False            # Stage 3.5: lockup detected on the target lap here
    wheelspin: bool = False         # Stage 3.5: wheelspin detected on the target lap here


@dataclass
class CornerAnalysis:
    """Per-corner attribution for one comparison.

    IMPORTANT (uncertainty consistency): these per-corner magnitudes are derived
    from telemetry that carries a measured *global* reconciliation error
    (`reconciliation_error_s`, from Stage 2). The confidence field reflects only
    conflicting driver-input signals - it does NOT encode the reconciliation
    error - but any per-corner magnitude comparable to the global error spread
    should be read in that light. `total_attributed_s` telescopes to the
    integrated gap, so the whole attribution inherits that same uncertainty.
    """
    corners: list[CornerAttribution]
    reconciliation_error_s: float
    total_attributed_s: float
    # Stage 3.5 physical-realism cross-check: a genuine lockup should coincide with
    # local time loss. These record how many flags were raised and what fraction
    # sit on a corner where the target actually lost time (agreement in [0, 1],
    # None if nothing was flagged). This is the vehicle-state signal's validation.
    lockups_flagged: int = 0
    wheelspins_flagged: int = 0
    lockup_delta_agreement: float | None = None
    wheelspin_delta_agreement: float | None = None
