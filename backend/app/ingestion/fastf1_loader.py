"""FastF1 ingestion — load a session and turn laps into LapTelemetry.

Uses FastF1's native on-disk cache: the first pull hits the network, every pull
after is instant and offline. PostgreSQL is deliberately deferred to Stage 5
(storing comparison runs), where it actually earns its place.
"""
from __future__ import annotations

from functools import lru_cache

import fastf1
import pandas as pd

from ..config import CACHE_DIR, SessionSpec
from ..schemas.lap import LapTelemetry

_cache_enabled = False


def enable_cache() -> None:
    """Enable FastF1's disk cache once per process."""
    global _cache_enabled
    if not _cache_enabled:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(CACHE_DIR))
        _cache_enabled = True


def load_session(spec: SessionSpec):
    """Load a FastF1 session with laps + telemetry (weather/messages skipped)."""
    enable_cache()
    session = fastf1.get_session(spec.year, spec.event, spec.session)
    session.load(telemetry=True, laps=True, weather=False, messages=False)
    return session


def _lap_to_telemetry(lap, session_id: str) -> LapTelemetry:
    """Convert a single FastF1 lap row into our normalized schema.

    get_telemetry() merges car + positional data and adds a Distance channel,
    giving Speed/Throttle/Brake/nGear/RPM and X/Y in one frame — the X/Y is
    pre-fetched here for the Delta Track Map in a later stage.
    """
    tel = lap.get_telemetry()
    lap_time_raw = lap["LapTime"]
    lap_time = lap_time_raw.total_seconds() if pd.notna(lap_time_raw) else float("nan")
    return LapTelemetry(
        driver=str(lap["Driver"]),
        lap_number=int(lap["LapNumber"]),
        lap_time=lap_time,
        session_id=session_id,
        distance=tel["Distance"].to_numpy(dtype=float),
        speed=tel["Speed"].to_numpy(dtype=float),
        throttle=tel["Throttle"].to_numpy(dtype=float),
        brake=tel["Brake"].to_numpy(dtype=float),
        rpm=tel["RPM"].to_numpy(dtype=float),
        ngear=tel["nGear"].to_numpy(dtype=float),
        x=tel["X"].to_numpy(dtype=float),
        y=tel["Y"].to_numpy(dtype=float),
    )


def load_two_laps(spec: SessionSpec, session=None) -> tuple[LapTelemetry, LapTelemetry]:
    """Return (fast_lap, slow_lap) for the spec's driver.

    fast = the driver's quickest lap; slow = a clearly slower flying lap (the
    median of their accurate laps by time). Any two laps satisfy Stage 0 — the
    quality of the pairing only matters from Stage 2 onward.
    """
    if session is None:
        session = load_session(spec)

    drv_laps = session.laps[session.laps["Driver"] == spec.driver]

    # Prefer accurate flying laps; fall back to all timed laps if too few.
    flying = drv_laps.pick_quicklaps() if hasattr(drv_laps, "pick_quicklaps") else drv_laps
    flying = flying.dropna(subset=["LapTime"]).sort_values("LapTime")
    if len(flying) < 2:
        flying = drv_laps.dropna(subset=["LapTime"]).sort_values("LapTime")
    if len(flying) < 2:
        raise ValueError(
            f"Need >=2 timed laps for {spec.driver} in {spec.session_id}, "
            f"found {len(flying)}."
        )

    fast_lap = flying.iloc[0]
    slow_lap = flying.iloc[len(flying) // 2]  # a distinctly slower flying lap
    return (_lap_to_telemetry(fast_lap, spec.session_id),
            _lap_to_telemetry(slow_lap, spec.session_id))


@lru_cache(maxsize=8)
def load_session_cached(year: int, event: str, session: str):
    """Process-level cache of loaded sessions so the API doesn't re-parse on every
    request. Driver is irrelevant to session loading, so it isn't part of the key.
    """
    return load_session(SessionSpec(year=year, event=event, session=session, driver="NA"))


def load_lap_by_number(spec: SessionSpec, session, lap_number: int) -> LapTelemetry:
    """Load one specific lap by number for the spec's driver."""
    drv = session.laps[session.laps["Driver"] == spec.driver]
    row = drv[drv["LapNumber"] == lap_number]
    if len(row) == 0:
        raise ValueError(
            f"lap {lap_number} not found for {spec.driver} in {spec.session_id}")
    return _lap_to_telemetry(row.iloc[0], spec.session_id)


# --------------------------------------------------------------------------- #
# Catalog helpers — power the frontend dropdowns (proves it's not Monza-only). #
# --------------------------------------------------------------------------- #
def list_events(year: int) -> list[dict]:
    """All championship rounds for a season (fast — schedule only, no telemetry)."""
    enable_cache()
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    events = []
    for _, r in schedule.iterrows():
        if int(r.get("RoundNumber", 0)) < 1:
            continue
        events.append({
            "round": int(r["RoundNumber"]),
            "name": str(r["EventName"]),
            "country": str(r.get("Country", "")),
            "location": str(r.get("Location", "")),
            "date": str(r.get("EventDate", ""))[:10],
        })
    return events


def list_drivers(year: int, event: str, session: str) -> list[dict]:
    """Drivers in a session, with full names (cached session load)."""
    loaded = load_session_cached(year, event, session)
    drivers = []
    for num in loaded.drivers:
        d = loaded.get_driver(num)
        code = str(d.get("Abbreviation", num))
        drivers.append({
            "code": code,
            "name": str(d.get("FullName", code)),
            "team": str(d.get("TeamName", "")),
            "number": str(num),
        })
    drivers.sort(key=lambda x: x["name"])
    return drivers


def list_laps(year: int, event: str, session: str, driver: str) -> list[dict]:
    """A driver's laps with times + which is fastest (for the plain-language picker)."""
    loaded = load_session_cached(year, event, session)
    drv = loaded.laps[loaded.laps["Driver"] == driver]
    if len(drv) == 0:
        raise ValueError(f"no laps found for driver '{driver}' in {year} {event} {session}")

    fastest_num = None
    try:
        fastest = drv.pick_fastest()
        if fastest is not None and pd.notna(fastest["LapNumber"]):
            fastest_num = int(fastest["LapNumber"])
    except Exception:
        fastest_num = None

    laps = []
    for _, r in drv.iterrows():
        lt = r["LapTime"]
        n = int(r["LapNumber"])
        laps.append({
            "lap_number": n,
            "lap_time_s": round(lt.total_seconds(), 3) if pd.notna(lt) else None,
            "is_accurate": bool(r.get("IsAccurate", False)),
            "is_fastest": n == fastest_num,
        })
    return laps
