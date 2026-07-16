"""Stage 8 acceptance tests - sim / student-logger import.

Uses the generated sample CSV (backend/data/sample_sim/supra_autocross.csv). If
it is missing, the tests are skipped with a hint to run the generator.
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.ingestion.sim_import import load_sim_session, pick_reference_target
from app.main import app
from app.pipeline import analyze_laps, run_pipeline_sim
from app.processing.corner_detect import detect_corners
from app.schemas.lap import LapTelemetry

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_sim" / "supra_autocross.csv"
client = TestClient(app)

pytestmark = pytest.mark.skipif(
    not SAMPLE.exists(),
    reason="run `python scripts/gen_sim_sample.py` to create the sample CSV",
)


def test_import_maps_channels_and_laps():
    laps = load_sim_session(str(SAMPLE), driver="STU", label="SUPRA")
    assert len(laps) == 2
    for lap in laps:
        assert lap.is_consistent()
        assert lap.speed.max() < 130          # student car, not F1
        assert set(np.unique(lap.brake)).issubset({0.0, 1.0})
        assert lap.ngear.max() <= 6
        assert lap.lap_time > 0


def test_reference_is_faster_than_target():
    ref, tgt = pick_reference_target(load_sim_session(str(SAMPLE)))
    assert ref.lap_time < tgt.lap_time


def test_corner_detection_finds_corners():
    laps = load_sim_session(str(SAMPLE))
    ref, tgt = pick_reference_target(laps)
    result = analyze_laps(ref, tgt, circuit=None)
    assert len(result.analysis.corners) >= 4      # ~7 designed corners


def test_sim_pipeline_reconciles_tightly():
    result = run_pipeline_sim(str(SAMPLE))
    # clean synthetic data should reconcile far tighter than noisy FastF1.
    # (DeltaResult.reconciliation_error — the _s suffix is only on the API model.)
    assert abs(result.delta.reconciliation_error) < 0.05
    total = sum(a.magnitude_s for a in result.analysis.corners)
    assert np.isclose(total, result.delta.integrated_gap, atol=1e-6)


def test_synthetic_corner_detect_unit():
    d = np.arange(0.0, 200.0, 2.0)
    speed = np.full_like(d, 100.0)
    speed[(d > 40) & (d < 60)] = 40.0     # one clear apex
    lap = LapTelemetry(
        driver="T", lap_number=1, lap_time=10.0, session_id="s",
        distance=d, speed=speed, throttle=np.full_like(d, 100.0),
        brake=np.zeros_like(d), rpm=np.zeros_like(d), ngear=np.ones_like(d),
        x=d.copy(), y=np.zeros_like(d),
    )
    circuit = detect_corners(lap)
    assert len(circuit.corners) == 1


def test_sim_endpoint_uploads_and_flags_source():
    with SAMPLE.open("rb") as f:
        r = client.post(
            "/comparison/analyze-sim",
            files={"file": ("supra_autocross.csv", f, "text/csv")},
            data={"driver": "STU", "label": "SUPRA AUTOCROSS"},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "sim"
    assert body["session_id"] == "SUPRA AUTOCROSS"
    assert len(body["corners"]) >= 4
    assert "reconciliation_error_s" in body["reconciliation"]


def test_sim_endpoint_rejects_garbage_csv():
    bad = io.BytesIO(b"foo,bar\n1,2\n3,4\n")
    r = client.post(
        "/comparison/analyze-sim",
        files={"file": ("bad.csv", bad, "text/csv")},
        data={"label": "BAD"},
    )
    assert r.status_code == 422
