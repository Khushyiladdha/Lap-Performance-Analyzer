"""POST /comparison/analyze - run a two-lap comparison and return the full
decomposition as JSON.
"""
from __future__ import annotations

import io
import math

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..config import RECONCILIATION_FLAG_TOL_S, SessionSpec
from ..pipeline import PipelineResult, run_pipeline, run_pipeline_sim
from ..schemas.api import (
    ComparisonRequest,
    ComparisonResponse,
    CornerOut,
    DeltaTraceOut,
    ReconciliationOut,
    TrackMapOut,
    VehicleStateOut,
)

router = APIRouter(prefix="/comparison", tags=["comparison"])


def _round(values, n: int) -> list[float]:
    return [round(float(v), n) for v in values]


def _num(value, n: int) -> float | None:
    """Round, but map NaN/inf to None so undefined deltas serialize as null."""
    v = float(value)
    return None if (math.isnan(v) or math.isinf(v)) else round(v, n)


def _to_response(session_id: str, result: PipelineResult,
                 source: str = "fastf1") -> ComparisonResponse:
    pair, delta, analysis = result.pair, result.delta, result.analysis
    return ComparisonResponse(
        source=source,
        session_id=session_id,
        reference_lap=delta.reference_lap,
        target_lap=delta.target_lap,
        reference_lap_time_s=round(pair.fast.lap_time, 3),
        target_lap_time_s=round(pair.slow.lap_time, 3),
        delta_trace=DeltaTraceOut(
            distance=_round(pair.grid, 1),
            delta=_round(delta.delta, 4),
            reference_speed=_round(pair.fast.speed, 1),
            target_speed=_round(pair.slow.speed, 1),
            reference_throttle=_round(pair.fast.throttle, 1),
            target_throttle=_round(pair.slow.throttle, 1),
            reference_brake=_round(pair.fast.brake, 2),
            target_brake=_round(pair.slow.brake, 2),
        ),
        track_map=TrackMapOut(
            x=_round(pair.slow.x, 1),
            y=_round(pair.slow.y, 1),
            delta=_round(delta.delta, 4),
        ),
        corners=[
            CornerOut(
                corner=a.corner, distance=round(a.distance, 1),
                magnitude_s=round(a.magnitude_s, 4), cause=a.cause,
                confidence=a.confidence,
                brake_point_delta_m=_num(a.brake_point_delta_m, 1),
                apex_speed_delta_kmh=_num(a.apex_speed_delta_kmh, 1),
                throttle_point_delta_m=_num(a.throttle_point_delta_m, 1),
                signals=a.signals, lockup=a.lockup, wheelspin=a.wheelspin,
            )
            for a in analysis.corners
        ],
        reconciliation=ReconciliationOut(
            integrated_gap_s=round(delta.integrated_gap, 4),
            measured_gap_s=round(delta.measured_gap, 4),
            reconciliation_error_s=round(delta.reconciliation_error, 4),
            within_tolerance=abs(delta.reconciliation_error) <= RECONCILIATION_FLAG_TOL_S,
        ),
        vehicle_state=VehicleStateOut(
            lockups_flagged=analysis.lockups_flagged,
            wheelspins_flagged=analysis.wheelspins_flagged,
            lockup_delta_agreement=analysis.lockup_delta_agreement,
            wheelspin_delta_agreement=analysis.wheelspin_delta_agreement,
        ),
    )


@router.post("/analyze", response_model=ComparisonResponse)
def analyze(req: ComparisonRequest) -> ComparisonResponse:
    spec = SessionSpec(year=req.year, event=req.event,
                       session=req.session, driver=req.driver)
    try:
        result = run_pipeline(spec, req.reference_lap, req.target_lap)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_response(spec.session_id, result, source="fastf1")


@router.post("/analyze-sim", response_model=ComparisonResponse)
async def analyze_sim(
    file: UploadFile = File(...),
    driver: str = Form("SIM"),
    label: str = Form("SIM SESSION"),
    reference_lap: int | None = Form(None),
    target_lap: int | None = Form(None),
) -> ComparisonResponse:
    """Import a sim / student-logger CSV and run the identical decomposition."""
    content = await file.read()
    try:
        result = run_pipeline_sim(
            io.BytesIO(content), driver=driver.strip().upper() or "SIM",
            label=label, reference_lap=reference_lap, target_lap=target_lap,
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_response(label, result, source="sim")
