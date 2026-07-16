"""Stage 8 - import sim / student-logger telemetry into the same LapTelemetry.

The internal schema (schemas/lap.py) is the seam: as long as a CSV carries the
real channels, it runs through the exact same pipeline as FastF1 data. Column
names are matched case-insensitively against common aliases, so a SAE-SUPRA /
Formula-Student logger export drops in without renaming.
"""
from __future__ import annotations

from typing import IO

import numpy as np
import pandas as pd

from ..schemas.lap import LapTelemetry

# canonical channel -> accepted header aliases (lower-cased)
ALIASES: dict[str, list[str]] = {
    "lap": ["lap", "lap_number", "lapno", "lap_no", "lapnum"],
    "time": ["time", "time_s", "t", "timestamp", "time_ms"],
    "distance": ["distance", "dist", "dist_m", "distance_m", "lapdist", "lap_dist"],
    "speed": ["speed", "speed_kph", "speed_kmh", "velocity", "v", "gps_speed", "vehicle_speed"],
    "rpm": ["rpm", "engine_rpm", "enginerpm", "nrpm"],
    "gear": ["gear", "ngear", "n_gear", "gear_pos"],
    "throttle": ["throttle", "throttle_pct", "tps", "tps_pct", "ap", "accel_pedal"],
    "brake": ["brake", "brake_pct", "brakepress", "brake_press", "brake_bar", "brake_pressure"],
    "x": ["x", "pos_x", "gps_x", "world_x"],
    "y": ["y", "pos_y", "gps_y", "world_y"],
}

# A brake reading above this counts as "on the brakes". Applied against a %/pressure
# scale; if the column is already 0/1 the >0.5 rule is used instead.
BRAKE_ON = 8.0


def _resolve(columns) -> dict[str, str]:
    low = {str(c).lower().strip(): c for c in columns}
    resolved: dict[str, str] = {}
    for canon, aliases in ALIASES.items():
        for a in aliases:
            if a in low:
                resolved[canon] = low[a]
                break
    return resolved


def _col(g: pd.DataFrame, m: dict[str, str], key: str, default=None):
    if key in m:
        return g[m[key]].to_numpy(dtype=float)
    return default


def _to_lap(g: pd.DataFrame, m: dict[str, str], lap_no: int, driver: str, label: str) -> LapTelemetry:
    g = g.reset_index(drop=True)
    speed = _col(g, m, "speed")
    n = len(speed)

    if "distance" in m:
        distance = _col(g, m, "distance")
    elif "time" in m:
        t = _col(g, m, "time")
        vms = np.clip(speed / 3.6, 0.1, None)
        distance = np.concatenate(([0.0], np.cumsum(0.5 * (vms[1:] + vms[:-1]) * np.diff(t))))
    else:
        raise ValueError("CSV needs a distance or a time column to place samples")

    if "time" in m:
        t = _col(g, m, "time")
        lap_time = float(t[-1] - t[0])
    else:
        inv = 1.0 / np.clip(speed / 3.6, 0.1, None)
        lap_time = float(np.sum(0.5 * (inv[1:] + inv[:-1]) * np.diff(distance)))

    brake_raw = _col(g, m, "brake", np.zeros(n))
    brake = (brake_raw > BRAKE_ON).astype(float) if brake_raw.max() > 1.5 else (brake_raw > 0.5).astype(float)

    return LapTelemetry(
        driver=driver, lap_number=lap_no, lap_time=lap_time, session_id=label,
        distance=distance.astype(float), speed=speed,
        throttle=_col(g, m, "throttle", np.full(n, 100.0)),
        brake=brake,
        rpm=_col(g, m, "rpm", np.zeros(n)),
        ngear=_col(g, m, "gear", np.ones(n)),
        x=_col(g, m, "x", np.zeros(n)),
        y=_col(g, m, "y", np.zeros(n)),
    )


def load_sim_session(source: str | IO, driver: str = "SIM",
                     label: str = "SIM SESSION") -> list[LapTelemetry]:
    """Parse a CSV (path or file-like) into one LapTelemetry per lap."""
    df = pd.read_csv(source)
    m = _resolve(df.columns)
    if "speed" not in m:
        raise ValueError("CSV must contain a speed column (e.g. 'speed_kph')")

    groups = list(df.groupby(m["lap"])) if "lap" in m else [(1, df)]
    return [_to_lap(g, m, int(lap_no), driver, label) for lap_no, g in groups]


def pick_reference_target(laps: list[LapTelemetry]) -> tuple[LapTelemetry, LapTelemetry]:
    """Fastest lap as reference, a slower flying lap as target (mirrors FastF1)."""
    timed = [l for l in laps if l.lap_time == l.lap_time and l.lap_time > 0]
    timed.sort(key=lambda l: l.lap_time)
    if len(timed) < 2:
        raise ValueError("need at least 2 timed laps in the CSV")
    return timed[0], timed[len(timed) // 2]
