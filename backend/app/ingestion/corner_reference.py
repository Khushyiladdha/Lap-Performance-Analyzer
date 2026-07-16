"""Official corner markers from FastF1 circuit info.

These are ground truth (F1's own circuit data), not re-derived from curvature —
re-deriving them would solve an already-solved problem and add a new error source.
"""
from __future__ import annotations

from ..schemas.lap import CircuitReference, CornerMarker


def load_circuit_reference(session) -> CircuitReference:
    """Extract sorted [number, distance, x, y] corner markers for the session's circuit."""
    circuit_info = session.get_circuit_info()
    corners_df = circuit_info.corners

    markers = [
        CornerMarker(
            number=int(row["Number"]),
            distance=float(row["Distance"]),
            x=float(row["X"]),
            y=float(row["Y"]),
        )
        for _, row in corners_df.iterrows()
    ]
    markers.sort(key=lambda c: c.distance)

    try:
        circuit_name = str(session.event["EventName"])
    except Exception:
        circuit_name = "unknown"

    return CircuitReference(circuit_name=circuit_name, corners=markers)
