"""Stage 3.5 demo - vehicle-state flags + physical-realism cross-check.

Also prints the deceleration distribution used to justify LOCKUP_DECEL_G.

    cd backend && python scripts/stage3_5_demo.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from app.config import DEFAULT_SESSION, LOCKUP_DECEL_G
from app.ingestion.corner_reference import load_circuit_reference
from app.ingestion.fastf1_loader import load_session, load_two_laps
from app.processing.cause_classifier import analyze_corners
from app.processing.delta_calculator import compute_delta
from app.processing.distance_resample import resample_pair
from app.processing.vehicle_state_flags import (
    _decel_g,
    annotate_vehicle_state,
    calibrate_speed_rpm,
    detect_events,
)


def main() -> None:
    spec = DEFAULT_SESSION
    session = load_session(spec)
    raw_fast, raw_slow = load_two_laps(spec, session=session)
    circuit = load_circuit_reference(session)

    pair = resample_pair(raw_fast, raw_slow)
    delta = compute_delta(pair, reference="fast", target="slow")
    analysis = analyze_corners(pair, delta, circuit)

    # --- calibration + decel distribution (justify the lockup threshold) ---
    ratios = calibrate_speed_rpm(pair.slow)
    print("Per-gear Speed-RPM ratios (slow lap):")
    print("  " + "  ".join(f"g{g}:{r:.0f}" for g, r in sorted(ratios.items())))

    decel = _decel_g(pair.slow)
    braking = pair.slow.brake > 0.5
    bd = decel[braking]
    print(f"\nDeceleration under braking (g): median {np.median(bd):.1f}, "
          f"95th pct {np.percentile(bd, 95):.1f}, max {bd.max():.1f}")
    print(f"Lockup threshold = {LOCKUP_DECEL_G} g  -> "
          f"{int((bd > LOCKUP_DECEL_G).sum())} of {bd.size} braking samples above it")

    annotate_vehicle_state(analysis, pair)

    print("\nCorners with a vehicle-state flag (target = slow lap):")
    print("  corner   +time    lockup  wheelspin")
    for a in analysis.corners:
        if a.lockup or a.wheelspin:
            print(f"   T{a.corner:>2}   {a.magnitude_s:+.3f}s    "
                  f"{'YES' if a.lockup else ' - '}     {'YES' if a.wheelspin else ' - '}")

    print("\nPHYSICAL-REALISM CROSS-CHECK (flag should coincide with local time loss):")
    print(f"   lockups flagged   : {analysis.lockups_flagged}, "
          f"agreement with delta loss: {analysis.lockup_delta_agreement}")
    print(f"   wheelspins flagged: {analysis.wheelspins_flagged}, "
          f"agreement with delta loss: {analysis.wheelspin_delta_agreement}")

    print("\nStage 3.5 DoD: each corner optionally carries {lockup, wheelspin} from "
          "documented thresholds; cross-check reported. OK.")


if __name__ == "__main__":
    main()
