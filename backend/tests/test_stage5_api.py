"""Stage 5 API acceptance tests (FastAPI TestClient - no live server needed).

The first request triggers a real (cached) FastF1 load; later ones reuse the
in-process session cache.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_openapi_and_docs_available():
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200      # Swagger UI


@pytest.fixture(scope="module")
def analysis_payload():
    r = client.post("/comparison/analyze", json={})    # all defaults
    assert r.status_code == 200, r.text
    return r.json()


def test_response_has_all_corners(analysis_payload):
    assert len(analysis_payload["corners"]) == 11      # Monza
    c = analysis_payload["corners"][0]
    for key in ("corner", "magnitude_s", "cause", "confidence", "lockup", "wheelspin"):
        assert key in c


def test_undefined_corner_deltas_are_null_not_nan(analysis_payload):
    # undefined deltas must serialize as null (None), never NaN.
    for c in analysis_payload["corners"]:
        for key in ("brake_point_delta_m", "apex_speed_delta_kmh", "throttle_point_delta_m"):
            v = c[key]
            assert v is None or isinstance(v, (int, float))
            assert v is None or v == v          # NaN != NaN would fail here


def test_delta_trace_arrays_aligned(analysis_payload):
    t = analysis_payload["delta_trace"]
    n = len(t["distance"])
    assert n > 100
    assert len(t["delta"]) == n
    assert len(t["reference_speed"]) == n
    assert len(t["target_speed"]) == n


def test_track_map_present_for_delta_map(analysis_payload):
    m = analysis_payload["track_map"]
    n = len(m["x"])
    assert n > 100
    assert len(m["y"]) == n
    assert len(m["delta"]) == n


def test_reconciliation_is_first_class(analysis_payload):
    rec = analysis_payload["reconciliation"]
    for key in ("integrated_gap_s", "measured_gap_s", "reconciliation_error_s", "within_tolerance"):
        assert key in rec
    assert isinstance(rec["within_tolerance"], bool)


def test_vehicle_state_summary_present(analysis_payload):
    vs = analysis_payload["vehicle_state"]
    assert vs["lockups_flagged"] == sum(c["lockup"] for c in analysis_payload["corners"])
    assert vs["wheelspins_flagged"] == sum(c["wheelspin"] for c in analysis_payload["corners"])


def test_explicit_lap_selection_and_bad_lap_errors():
    # a lap number that cannot exist -> 422 with a helpful message
    r = client.post("/comparison/analyze", json={"reference_lap": 1, "target_lap": 999})
    assert r.status_code == 422
