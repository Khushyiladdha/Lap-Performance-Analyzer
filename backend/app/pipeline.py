"""End-to-end analysis pipeline: raw laps -> aligned -> delta -> per-corner
attribution -> vehicle-state flags. One shared path for the API (and anything
else) so the stages are never re-wired inconsistently.
"""
from __future__ import annotations

from dataclasses import dataclass

from typing import IO

from .config import SessionSpec
from .ingestion.corner_reference import load_circuit_reference
from .ingestion.fastf1_loader import (
    load_lap_by_number,
    load_session_cached,
    load_two_laps,
)
from .ingestion.sim_import import load_sim_session, pick_reference_target
from .processing.cause_classifier import analyze_corners
from .processing.corner_detect import detect_corners
from .processing.delta_calculator import compute_delta
from .processing.distance_resample import resample_pair
from .processing.vehicle_state_flags import annotate_vehicle_state
from .schemas.lap import (
    AlignedLapPair,
    CircuitReference,
    CornerAnalysis,
    DeltaResult,
    LapTelemetry,
)


@dataclass
class PipelineResult:
    pair: AlignedLapPair
    delta: DeltaResult
    analysis: CornerAnalysis
    reference: LapTelemetry
    target: LapTelemetry


def analyze_laps(ref: LapTelemetry, tgt: LapTelemetry,
                 circuit: CircuitReference | None = None) -> PipelineResult:
    """Shared analysis core for any two laps, whatever the source.

    If `circuit` is None (imported data with no official markers) corners are
    detected from the reference lap's speed trace (see corner_detect)."""
    pair = resample_pair(ref, tgt)
    if circuit is None:
        circuit = detect_corners(pair.fast)
    delta = compute_delta(pair, reference="fast", target="slow")
    analysis = analyze_corners(pair, delta, circuit)
    annotate_vehicle_state(analysis, pair)
    return PipelineResult(pair=pair, delta=delta, analysis=analysis,
                          reference=ref, target=tgt)


def run_pipeline(spec: SessionSpec, reference_lap: int | None = None,
                 target_lap: int | None = None) -> PipelineResult:
    """Run the full comparison from FastF1. If both lap numbers are given they
    are used; otherwise the driver's fastest + a slower flying lap are picked."""
    session = load_session_cached(spec.year, spec.event, spec.session)

    if reference_lap is not None and target_lap is not None:
        ref = load_lap_by_number(spec, session, reference_lap)
        tgt = load_lap_by_number(spec, session, target_lap)
    else:
        ref, tgt = load_two_laps(spec, session=session)

    return analyze_laps(ref, tgt, circuit=load_circuit_reference(session))


def run_pipeline_sim(source: str | IO, driver: str = "SIM",
                     label: str = "SIM SESSION",
                     reference_lap: int | None = None,
                     target_lap: int | None = None) -> PipelineResult:
    """Run the full comparison from an imported sim / student-logger CSV."""
    laps = load_sim_session(source, driver=driver, label=label)
    if reference_lap is not None and target_lap is not None:
        by_no = {l.lap_number: l for l in laps}
        if reference_lap not in by_no or target_lap not in by_no:
            raise ValueError("requested lap number not present in the CSV")
        ref, tgt = by_no[reference_lap], by_no[target_lap]
    else:
        ref, tgt = pick_reference_target(laps)
    return analyze_laps(ref, tgt, circuit=None)
