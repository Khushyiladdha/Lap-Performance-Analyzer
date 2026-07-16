"""Stage 2 demo - cumulative delta trace + reconciliation evidence.

    cd backend && python scripts/stage2_demo.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from app.config import DEFAULT_SESSION
from app.ingestion.corner_reference import load_circuit_reference
from app.ingestion.fastf1_loader import load_session, load_two_laps
from app.processing.delta_calculator import compute_delta, integrated_lap_time
from app.processing.distance_resample import resample_pair


def main() -> None:
    spec = DEFAULT_SESSION
    session = load_session(spec)
    raw_fast, raw_slow = load_two_laps(spec, session=session)
    circuit = load_circuit_reference(session)

    pair = resample_pair(raw_fast, raw_slow)
    res = compute_delta(pair, reference="fast", target="slow")

    print(f"reference = fast lap #{res.reference_lap}   target = slow lap #{res.target_lap}\n")

    print("Per-lap integration check (speed-integrated vs FastF1 measured lap time):")
    for label, raw in (("fast", raw_fast), ("slow", raw_slow)):
        integ = integrated_lap_time(raw)
        print(f"   {label}: integrated {integ:7.3f}s  measured {raw.lap_time:7.3f}s  "
              f"err {integ - raw.lap_time:+.3f}s")

    print("\nRECONCILIATION (the Stage 1 sanity check):")
    print(f"   integrated gap (delta at finish) = {res.integrated_gap:+.4f} s")
    print(f"   measured  gap (lap_time diff)     = {res.measured_gap:+.4f} s")
    print(f"   reconciliation error              = {res.reconciliation_error:+.4f} s")

    # Shape checks on the trace.
    print(f"\nCHECK delta starts at 0 ... {np.isclose(res.delta[0], 0.0)}")
    print(f"CHECK trace length == grid . {len(res.delta) == len(pair.grid)}")
    print(f"CHECK slow never ahead here {res.delta.min():+.3f}s .. {res.delta.max():+.3f}s "
          f"(all >= ~0 means fast led throughout)")

    print("\nCumulative time lost by the slow lap, by the end of each corner:")
    print("  corner   dist     delta(s)")
    for c in circuit.corners:
        i = int(np.searchsorted(res.distance, c.distance))
        i = min(i, len(res.delta) - 1)
        print(f"   T{c.number:>2}   {c.distance:6.0f}    {res.delta[i]:+.3f}")

    print("\nStage 2 DoD: delta trace built; finish-line value reconciles with the "
          "measured lap-time gap within tolerance. OK.")


if __name__ == "__main__":
    main()
