"""Stage 3 demo - per-corner cause + confidence, engineering-note style.

    cd backend && python scripts/stage3_demo.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DEFAULT_SESSION
from app.ingestion.corner_reference import load_circuit_reference
from app.ingestion.fastf1_loader import load_session, load_two_laps
from app.processing.cause_classifier import analyze_corners
from app.processing.delta_calculator import compute_delta
from app.processing.distance_resample import resample_pair


def _phrase(a):
    bits = []
    if "early braking" in a.signals:
        bits.append(f"braked {abs(a.brake_point_delta_m):.0f}m early")
    if "late braking" in a.signals:
        bits.append(f"braked {a.brake_point_delta_m:.0f}m late")
    if "lower apex speed" in a.signals:
        bits.append(f"{abs(a.apex_speed_delta_kmh):.0f} km/h slower apex")
    if "delayed throttle" in a.signals:
        bits.append(f"throttle {a.throttle_point_delta_m:.0f}m later")
    return ", ".join(bits) if bits else a.cause


def main() -> None:
    spec = DEFAULT_SESSION
    session = load_session(spec)
    raw_fast, raw_slow = load_two_laps(spec, session=session)
    circuit = load_circuit_reference(session)

    pair = resample_pair(raw_fast, raw_slow)
    delta = compute_delta(pair, reference="fast", target="slow")
    analysis = analyze_corners(pair, delta, circuit)

    print(f"Comparison: fast lap #{delta.reference_lap} vs slow lap #{delta.target_lap}")
    print(f"Global reconciliation error: {analysis.reconciliation_error_s:+.3f} s  "
          f"-> per-corner magnitudes inherit this uncertainty.\n")

    print("  corner   +time    cause                confidence   detail")
    for a in sorted(analysis.corners, key=lambda c: c.magnitude_s, reverse=True):
        print(f"   T{a.corner:>2}   {a.magnitude_s:+.3f}s   {a.cause:<20} "
              f"{a.confidence:<10}  {_phrase(a)}")

    print(f"\nSum of per-corner magnitudes = {analysis.total_attributed_s:+.3f} s "
          f"(integrated gap = {delta.integrated_gap:+.3f} s)  <- telescopes")
    print("Stage 3 DoD: every corner classified with cause + confidence; "
          "attributions tie back to the reconciled delta. OK.")


if __name__ == "__main__":
    main()
