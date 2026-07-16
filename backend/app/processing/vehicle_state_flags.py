"""Stage 3.5 - vehicle-state signal: lockup & wheelspin detection.

One real, defensible vehicle-behaviour signal derived transparently from public
FastF1 channels (Speed, RPM, nGear, Brake) - not a full vehicle-dynamics suite,
not a black-box classifier.

Method:
  1. Calibrate the expected Speed-RPM relationship PER GEAR from stable samples
     (gear held constant, above a speed floor). In a fixed gear RPM ~= ratio*Speed;
     we take the median ratio, which is robust to the very slip/lock events we then
     want to flag as deviations from it.
  2. WHEELSPIN: engine RPM rising above the per-gear expectation while on power and
     off the brakes (typically corner exit).
  3. LOCKUP: a longitudinal deceleration spike under braking (a = v*dv/dx, in g)
     sharper than sustained grip-limited braking can produce.

PHYSICAL-REALISM CROSS-CHECK: a real lockup should cost time, so a flagged lockup
should sit on a corner where the target lap actually lost time (delta magnitude
> 0). We report that agreement fraction as the signal's primary validation -
agreement between two independent signals is stronger than either alone.

LIMITATIONS (stated honestly): FastF1's Speed is derived from car telemetry, so
wheelspin sensitivity is reduced if that speed is itself wheel-derived; and the
lockup rule is a proxy that can fire on legitimate hard braking. The cross-check
exists precisely to quantify that.
"""
from __future__ import annotations

import numpy as np

from ..config import (
    CALIB_MIN_SPEED_KMH,
    BRAKE_ENGAGED,
    LOCKUP_DECEL_G,
    NEGLIGIBLE_CORNER_LOSS_S,
    WHEELSPIN_MIN_SPEED_KMH,
    WHEELSPIN_MIN_THROTTLE,
    WHEELSPIN_RPM_EXCESS,
)
from ..schemas.lap import AlignedLapPair, CornerAnalysis, LapTelemetry

_KMH_TO_MS = 1000.0 / 3600.0
_G = 9.80665


def calibrate_speed_rpm(lap: LapTelemetry) -> dict[int, float]:
    """Median RPM/Speed ratio per gear, from samples away from shift boundaries."""
    gear = np.round(lap.ngear).astype(int)
    same_as_prev = np.concatenate(([False], gear[1:] == gear[:-1]))
    same_as_next = np.concatenate((gear[1:] == gear[:-1], [False]))
    stable = same_as_prev & same_as_next          # gear[i-1]==gear[i]==gear[i+1]

    ratios: dict[int, float] = {}
    for g in np.unique(gear):
        if g < 1:
            continue
        m = stable & (gear == g) & (lap.speed > CALIB_MIN_SPEED_KMH)
        if m.sum() >= 5:
            ratios[int(g)] = float(np.median(lap.rpm[m] / lap.speed[m]))
    return ratios


def _expected_rpm(lap: LapTelemetry, ratios: dict[int, float]) -> np.ndarray:
    gear = np.round(lap.ngear).astype(int)
    exp = np.full(gear.shape, np.nan)
    for g, r in ratios.items():
        exp[gear == g] = r * lap.speed[gear == g]
    return exp


def _decel_g(lap: LapTelemetry) -> np.ndarray:
    """Longitudinal deceleration (positive when slowing), in g, via a = v*dv/dx."""
    v = lap.speed * _KMH_TO_MS
    dv = np.diff(v)
    dx = np.diff(lap.distance)
    a = np.zeros_like(v)
    a[1:] = v[1:] * dv / np.where(dx == 0, np.nan, dx)
    return -a / _G


def detect_events(lap: LapTelemetry,
                  ratios: dict[int, float]) -> tuple[np.ndarray, np.ndarray]:
    """Per-sample boolean (lockup, wheelspin) arrays for one lap."""
    braking = lap.brake > BRAKE_ENGAGED
    lockup = braking & (_decel_g(lap) > LOCKUP_DECEL_G)

    exp = _expected_rpm(lap, ratios)
    with np.errstate(invalid="ignore", divide="ignore"):
        excess = (lap.rpm - exp) / exp
    wheelspin = (
        ~braking
        & (lap.throttle > WHEELSPIN_MIN_THROTTLE)
        & (lap.speed > WHEELSPIN_MIN_SPEED_KMH)
        & np.isfinite(excess)
        & (excess > WHEELSPIN_RPM_EXCESS)
    )
    return lockup, wheelspin


def annotate_vehicle_state(analysis: CornerAnalysis,
                           pair: AlignedLapPair) -> CornerAnalysis:
    """Flag lockup/wheelspin per corner on the target (slow) lap and run the
    physical-realism cross-check against the delta magnitudes already computed."""
    lap = pair.slow                      # target lap - the one whose loss we explain
    ratios = calibrate_speed_rpm(lap)
    lockup, wheelspin = detect_events(lap, ratios)
    grid = pair.grid

    lock_flagged = lock_confirmed = spin_flagged = spin_confirmed = 0
    for a in analysis.corners:
        lo, hi = a.window
        win = (grid >= lo) & (grid <= hi)
        a.lockup = bool(lockup[win].any())
        a.wheelspin = bool(wheelspin[win].any())
        lost_time = a.magnitude_s > NEGLIGIBLE_CORNER_LOSS_S
        if a.lockup:
            lock_flagged += 1
            lock_confirmed += int(lost_time)
        if a.wheelspin:
            spin_flagged += 1
            spin_confirmed += int(lost_time)

    analysis.lockups_flagged = lock_flagged
    analysis.wheelspins_flagged = spin_flagged
    analysis.lockup_delta_agreement = (lock_confirmed / lock_flagged) if lock_flagged else None
    analysis.wheelspin_delta_agreement = (spin_confirmed / spin_flagged) if spin_flagged else None
    return analysis
