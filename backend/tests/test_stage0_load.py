"""Stage 0 acceptance tests.

Integration test: the first run downloads the session (needs network); every run
after is offline via the FastF1 cache. The closed-form math tests arrive at
Stage 1.5 — this file only asserts the data foundation is sound.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app.config import DEFAULT_SESSION
from app.ingestion.corner_reference import load_circuit_reference
from app.ingestion.fastf1_loader import load_session, load_two_laps


@pytest.fixture(scope="module")
def loaded():
    session = load_session(DEFAULT_SESSION)
    fast, slow = load_two_laps(DEFAULT_SESSION, session=session)
    circuit = load_circuit_reference(session)
    return fast, slow, circuit


def test_two_distinct_laps(loaded):
    fast, slow, _ = loaded
    assert fast.lap_number != slow.lap_number
    assert fast.lap_time <= slow.lap_time  # "fast" really is the quicker lap


def test_channels_present_and_equal_length(loaded):
    fast, slow, _ = loaded
    for lap in (fast, slow):
        assert lap.is_consistent(), lap.channel_lengths()
        assert len(lap.distance) > 100
        for channel in (lap.speed, lap.throttle, lap.brake,
                        lap.rpm, lap.ngear, lap.x, lap.y):
            assert len(channel) == len(lap.distance)


def test_distance_is_monotonic(loaded):
    fast, _, _ = loaded
    d = fast.distance
    assert (d[1:] >= d[:-1]).all(), "distance channel should be non-decreasing"


def test_corner_markers_sorted_and_nonempty(loaded):
    _, _, circuit = loaded
    assert len(circuit.corners) >= 5
    distances = [c.distance for c in circuit.corners]
    assert distances == sorted(distances)
    numbers = [c.number for c in circuit.corners]
    assert all(n > 0 for n in numbers)
