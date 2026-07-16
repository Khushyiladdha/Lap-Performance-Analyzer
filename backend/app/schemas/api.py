"""Pydantic request/response models for the HTTP API (Stage 5).

Kept separate from the internal dataclasses in schemas/lap.py: these are the
JSON-serializable contract the frontend consumes.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ComparisonRequest(BaseModel):
    year: int = 2023
    event: str = "Monza"
    session: str = "Q"
    driver: str = "LEC"
    reference_lap: int | None = Field(
        default=None, description="Explicit reference lap number; omit to auto-pick the fastest lap")
    target_lap: int | None = Field(
        default=None, description="Explicit target lap number; omit to auto-pick a slower flying lap")


class DeltaTraceOut(BaseModel):
    distance: list[float]
    delta: list[float]
    reference_speed: list[float]
    target_speed: list[float]
    reference_throttle: list[float]
    target_throttle: list[float]
    reference_brake: list[float]
    target_brake: list[float]


class TrackMapOut(BaseModel):
    """Target lap racing line with the delta value at each point, for the
    colour-coded Delta Track Map."""
    x: list[float]
    y: list[float]
    delta: list[float]


class CornerOut(BaseModel):
    corner: int
    distance: float
    magnitude_s: float
    cause: str
    confidence: str
    # These are None when undefined for a corner (e.g. no braking, or no clear
    # post-apex throttle re-application to compare) - not zero, which would lie.
    brake_point_delta_m: float | None
    apex_speed_delta_kmh: float | None
    throttle_point_delta_m: float | None
    signals: list[str]
    lockup: bool
    wheelspin: bool


class ReconciliationOut(BaseModel):
    integrated_gap_s: float
    measured_gap_s: float
    reconciliation_error_s: float
    within_tolerance: bool


class VehicleStateOut(BaseModel):
    lockups_flagged: int
    wheelspins_flagged: int
    lockup_delta_agreement: float | None
    wheelspin_delta_agreement: float | None


class ComparisonResponse(BaseModel):
    source: str = "fastf1"  # "fastf1" | "sim" — drives the SELF-RECORDED badge
    session_id: str
    reference_lap: int
    target_lap: int
    reference_lap_time_s: float
    target_lap_time_s: float
    delta_trace: DeltaTraceOut
    track_map: TrackMapOut
    corners: list[CornerOut]
    reconciliation: ReconciliationOut
    vehicle_state: VehicleStateOut
