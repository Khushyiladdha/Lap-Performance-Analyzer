"""Central configuration for the telemetry pipeline.

Everything session-specific lives here so the rest of the code never hardcodes a
driver, event, or file path. Swap DEFAULT_SESSION to analyze anything else.
"""
from dataclasses import dataclass
from pathlib import Path

# backend/  (this file is backend/app/config.py)
BACKEND_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BACKEND_DIR / "data" / "fastf1_cache"


@dataclass(frozen=True)
class SessionSpec:
    """Identifies one FastF1 session plus the driver of interest."""
    year: int
    event: str      # event name or location, e.g. "Monza" (fuzzy-matched by FastF1)
    session: str    # "Q", "R", "FP1", "Sprint", ...
    driver: str     # 3-letter code, e.g. "LEC"

    @property
    def session_id(self) -> str:
        return f"{self.year}_{self.event}_{self.session}"


# Stage 0 default: same driver, two laps (a fast one + a slower one) at Monza 2023 Q.
# Stated assumption — comparing same driver/car isolates technique from setup.
DEFAULT_SESSION = SessionSpec(year=2023, event="Monza", session="Q", driver="LEC")

# Stage 1 (distance-grid resampling) grid resolution.
DISTANCE_STEP_M = 2.0

# Stage 2 reconciliation: a comparison whose |reconciliation error| exceeds this
# is flagged rather than silently shown. It reflects real FastF1 data-fusion
# noise (speed is ECU-sampled, distance is position-derived, lap time is from
# timing loops), and is surfaced as a credibility metric in the UI later.
RECONCILIATION_FLAG_TOL_S = 0.15

# Stage 3 - cause-classification thresholds (documented, not magic numbers).
BRAKE_ENGAGED = 0.5              # FastF1's public brake channel is boolean 0/1
THROTTLE_REAPPLY_PCT = 50.0     # throttle back above this after apex = "on power"
BRAKE_POINT_TOL_M = 5.0         # min brake-point gap to call it early/late braking
APEX_SPEED_TOL_KMH = 3.0        # min apex-speed gap to be a significant signal
THROTTLE_POINT_TOL_M = 5.0      # min throttle-reapply gap to be a significant signal
NEGLIGIBLE_CORNER_LOSS_S = 0.02 # |per-corner time| below this -> nothing to attribute

# Stage 3.5 - vehicle-state (lockup / wheelspin) detection.
# The Speed-RPM baseline is calibrated per gear from stable samples above this speed.
CALIB_MIN_SPEED_KMH = 60.0
# Wheelspin: engine RPM this fraction above the per-gear expectation, while on power.
WHEELSPIN_RPM_EXCESS = 0.06
WHEELSPIN_MIN_THROTTLE = 50.0
WHEELSPIN_MIN_SPEED_KMH = 30.0
# Lockup: longitudinal deceleration spike (in g) beyond sustained grip-limited
# braking - set from the observed decel distribution (see stage3_5 demo notes).
LOCKUP_DECEL_G = 6.5
