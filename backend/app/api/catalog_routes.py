"""Catalog endpoints — populate the frontend's cascading dropdowns from live
FastF1 data, so the tool visibly works for ANY season/event/session/driver
(not just the Monza default).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..ingestion.fastf1_loader import list_drivers, list_events, list_laps

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/events/{year}")
def events(year: int) -> dict:
    try:
        return {"year": year, "events": list_events(year)}
    except Exception as exc:  # schedule fetch can fail if offline
        raise HTTPException(status_code=502, detail=f"schedule unavailable: {exc}") from exc


@router.get("/session/{year}/{event}/{session}/drivers")
def drivers(year: int, event: str, session: str) -> dict:
    try:
        return {"drivers": list_drivers(year, event, session)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"could not load session: {exc}") from exc


@router.get("/session/{year}/{event}/{session}/laps")
def laps(year: int, event: str, session: str, driver: str) -> dict:
    try:
        return {"laps": list_laps(year, event, session, driver)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"could not load laps: {exc}") from exc
