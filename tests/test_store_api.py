import os

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path):
    os.environ["OCULENS_DB"] = str(tmp_path / "test.db")
    os.environ["OCULENS_TASK"] = "no_such_task"          # no model: quality + symptom triage only
    import importlib

    import backend.app.main as main
    importlib.reload(main)
    return TestClient(main.app)


def eye_png():
    rng = np.random.default_rng(0)
    img = rng.integers(40, 200, (256, 256, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def test_analyze_store_and_review(client):
    r = client.post("/analyze", files={"image": ("eye.png", eye_png(), "image/png")},
                    data={"symptoms": '{"pain": true, "sudden_vision_loss": true}', "patient_ref": "P001"})
    assert r.status_code == 200
    rep = r.json()["report"]
    assert rep["triage"]["level"] == "urgent"
    assert r.json()["assistant"]["text"]

    q = client.get("/doctor/queue").json()
    assert q["stats"]["pending"] == 1 and q["queue"][0]["scan_id"] == rep["scan_id"]

    rv = client.post(f"/doctor/scan/{rep['scan_id']}/review", json={"reviewer": "dr_a", "decision": "confirm"})
    assert rv.status_code == 200
    assert client.get("/doctor/queue").json()["stats"]["confirmed"] == 1
    assert client.post(f"/doctor/scan/{rep['scan_id']}/review", json={"reviewer": "dr_a", "decision": "correct"}).status_code == 400


def test_bad_image_rejected(client):
    assert client.post("/analyze", files={"image": ("x.png", b"not an image", "image/png")}).status_code == 400
