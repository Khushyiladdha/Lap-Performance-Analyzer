"""v2 backend enablement — catalog dropdowns + import inspect/validate."""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from app.main import app

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_sim" / "supra_autocross.csv"
client = TestClient(app)


# ---- catalog (uses the Monza 2023 session already cached by other tests) ----
def test_events_lists_the_season():
    r = client.get("/catalog/events/2023")
    assert r.status_code == 200
    events = r.json()["events"]
    assert len(events) > 15
    names = [e["name"] for e in events]
    assert any("Italian" in n for n in names)      # Monza is in the calendar


def test_drivers_have_full_names():
    r = client.get("/catalog/session/2023/Monza/Q/drivers")
    assert r.status_code == 200
    drivers = r.json()["drivers"]
    codes = [d["code"] for d in drivers]
    assert "LEC" in codes
    lec = next(d for d in drivers if d["code"] == "LEC")
    assert "Leclerc" in lec["name"]                 # full name, not just code


def test_laps_flag_the_fastest():
    r = client.get("/catalog/session/2023/Monza/Q/laps", params={"driver": "LEC"})
    assert r.status_code == 200
    laps = r.json()["laps"]
    assert len(laps) >= 2
    assert sum(1 for l in laps if l["is_fastest"]) == 1
    assert all("lap_time_s" in l for l in laps)


# ---- import inspect / validate ----
@pytest.mark.skipif(not SAMPLE.exists(), reason="run gen_sim_sample.py first")
def test_inspect_good_csv_passes_quality():
    with SAMPLE.open("rb") as f:
        r = client.post("/import/inspect", files={"file": ("supra.csv", f, "text/csv")},
                        data={"driver": "STU", "label": "SUPRA"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["n_laps"] == 2
    assert body["channels"]["position"] is True
    assert len(body["track_preview"]["x"]) > 20
    names = {c["name"]: c["ok"] for c in body["quality"]}
    assert names["Track closes into a loop"] is True
    assert names["Braking + acceleration zones"] is True
    assert body["all_ok"] is True


def test_inspect_rejects_csv_without_speed():
    bad = io.BytesIO(b"foo,bar\n1,2\n3,4\n")
    r = client.post("/import/inspect", files={"file": ("bad.csv", bad, "text/csv")},
                    data={"label": "BAD"})
    assert r.status_code == 422
