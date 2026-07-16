"""Import inspect/validate endpoint — powers the Upload → Inspect → Validate step
of the Formula Student / sim import flow, before any analysis is run.
"""
from __future__ import annotations

import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..ingestion.sim_import import load_sim_session
from ..processing.data_quality import quality_checks, track_preview

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/inspect")
async def inspect(
    file: UploadFile = File(...),
    driver: str = Form("SIM"),
    label: str = Form("IMPORTED SESSION"),
) -> dict:
    """Parse an uploaded CSV and report what was found + data-quality checks.
    Does NOT run the analysis — that happens later on Run."""
    content = await file.read()
    try:
        laps = load_sim_session(io.BytesIO(content), driver=driver, label=label)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    checks, ref = quality_checks(laps)
    return {
        "label": label,
        "driver": driver,
        "n_laps": len(laps),
        "laps": [
            {"lap_number": l.lap_number, "lap_time_s": round(l.lap_time, 3)}
            for l in laps
        ],
        "channels": {
            "speed": True,
            "throttle": bool(ref is not None and (ref.throttle > 0).any()),
            "brake": bool(ref is not None and (ref.brake > 0).any()),
            "rpm": bool(ref is not None and ref.rpm.max() > 0),
            "gear": bool(ref is not None and ref.ngear.max() >= 1),
            "position": bool(ref is not None and not (ref.x == 0).all()),
        },
        "track_preview": track_preview(ref) if ref is not None else {"x": [], "y": []},
        "quality": checks,
        "all_ok": all(c["ok"] for c in checks) if checks else False,
    }
