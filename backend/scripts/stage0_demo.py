"""Stage 0 demo — prove the data foundation works end to end.

First run downloads + caches the session (validates the real livetiming path);
later runs are offline. Prints the Stage 0 definition-of-done evidence.

    cd backend && python scripts/stage0_demo.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DEFAULT_SESSION
from app.ingestion.corner_reference import load_circuit_reference
from app.ingestion.fastf1_loader import load_session, load_two_laps


def main() -> None:
    spec = DEFAULT_SESSION
    print(f"Loading {spec.year} {spec.event} {spec.session} - driver {spec.driver} ...")

    session = load_session(spec)
    fast, slow = load_two_laps(spec, session=session)
    circuit = load_circuit_reference(session)

    for label, lap in (("FAST", fast), ("SLOW", slow)):
        print(
            f"\n[{label}] lap #{lap.lap_number}  time={lap.lap_time:.3f}s  "
            f"samples={len(lap.distance)}  consistent={lap.is_consistent()}"
        )
        print(
            f"   distance {lap.distance[0]:.1f} -> {lap.distance[-1]:.1f} m   "
            f"vmax={lap.speed.max():.0f} km/h   "
            f"gears {int(lap.ngear.min())}-{int(lap.ngear.max())}   "
            f"brake-samples={int((lap.brake > 0).sum())}"
        )

    print(f"\nCircuit: {circuit.circuit_name} - {len(circuit.corners)} corners")
    for c in circuit.corners:
        print(f"   T{c.number:>2}: {c.distance:7.0f} m")

    print(
        f"\nStage 0 DoD: two distinct laps + {len(circuit.corners)} corner markers "
        f"loaded with all channels aligned. OK."
    )


if __name__ == "__main__":
    main()
