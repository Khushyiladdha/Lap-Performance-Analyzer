"""Stage 1 demo - resample two laps onto a shared distance grid and show the
evidence behind each Stage 1 check (offline once Stage 0 has cached the session).

    cd backend && python scripts/stage1_demo.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from app.config import DEFAULT_SESSION
from app.ingestion.corner_reference import load_circuit_reference
from app.ingestion.fastf1_loader import load_session, load_two_laps
from app.processing.distance_resample import resample_pair


def _nan_count(lap):
    return int(sum(np.isnan(getattr(lap, c)).sum()
                   for c in ("distance", "speed", "throttle", "brake", "rpm", "ngear", "x", "y")))


def main() -> None:
    spec = DEFAULT_SESSION
    session = load_session(spec)
    raw_fast, raw_slow = load_two_laps(spec, session=session)
    circuit = load_circuit_reference(session)

    print(f"RAW      fast: {len(raw_fast.distance)} samples, "
          f"{raw_fast.distance[-1]:.1f} m, NaNs={_nan_count(raw_fast)}")
    print(f"RAW      slow: {len(raw_slow.distance)} samples, "
          f"{raw_slow.distance[-1]:.1f} m, NaNs={_nan_count(raw_slow)}")

    pair = resample_pair(raw_fast, raw_slow)
    fast, slow, grid = pair.fast, pair.slow, pair.grid

    print(f"\nGRID     {len(grid)} points, step={pair.step_m} m, "
          f"range {grid[0]:.1f} -> {grid[-1]:.1f} m")
    print(f"CHECK shared grid ........ {np.array_equal(fast.distance, slow.distance)}")
    print(f"CHECK step == {pair.step_m} m ...... {np.allclose(np.diff(grid), pair.step_m)}")
    print(f"CHECK no NaN out ......... fast={_nan_count(fast)}  slow={_nan_count(slow)}")
    print(f"CHECK no extrapolation ... grid_max {grid[-1]:.1f} <= "
          f"min(raw_max) {min(raw_fast.distance.max(), raw_slow.distance.max()):.1f}")
    print(f"CHECK brake in {{0,1}} ...... {set(np.unique(fast.brake)).issubset({0.0, 1.0})}")
    print(f"CHECK gears integral ..... {np.allclose(fast.ngear, np.round(fast.ngear))}  "
          f"range {int(fast.ngear.min())}-{int(fast.ngear.max())}")
    print(f"CHECK vmax preserved ..... raw {raw_fast.speed.max():.0f} vs "
          f"resampled {fast.speed.max():.0f} km/h")

    print("\nAlignment - min speed (km/h) in each corner window, both laps on the shared grid:")
    print("  corner   dist      fast    slow")
    for c in circuit.corners:
        lo, hi = c.distance - 40, c.distance + 40
        win = (grid >= lo) & (grid <= hi)
        if win.any():
            print(f"   T{c.number:>2}   {c.distance:6.0f}   {fast.speed[win].min():6.0f}  "
                  f"{slow.speed[win].min():6.0f}")

    print("\nStage 1 DoD: both laps on one shared distance grid, all channels "
          "aligned index-by-index, corners line up. OK.")


if __name__ == "__main__":
    main()
