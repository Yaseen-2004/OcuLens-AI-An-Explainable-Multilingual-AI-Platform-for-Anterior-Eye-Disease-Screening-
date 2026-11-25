"""OcuLens-AI web service.

Run:
    uvicorn backend.app.main:app --reload
Then open http://127.0.0.1:8000

Environment:
    OCULENS_TASK      which trained model to load (default: keratitis)
    OCULENS_BACKBONE  backbone name used in the checkpoint file name (default from config)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from oculens.assistant.llm import explain
from oculens.assistant.report import doctor_report
from oculens.assistant.schema import ScreeningReport
from oculens.config import load_config, resolve
from oculens.pipeline import ScreeningPipeline

from backend.app.store import Store

STATIC = Path(__file__).parent / "static"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

app = FastAPI(title="OcuLens-AI", version="0.1.0",
              description="Anterior eye screening - decision support only, not a diagnosis.")
_cfg = load_config()
pipeline = ScreeningPipeline.from_task(os.environ.get("OCULENS_TASK", "keratitis"),
                                       os.environ.get("OCULENS_BACKBONE"))
store = Store(os.environ.get("OCULENS_DB", resolve("data/oculens.db")))


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": pipeline.has_model,
            "model": pipeline.meta and {k: pipeline.meta.get(k) for k in ("task", "backbone", "classes")}}


@app.post("/analyze")
async def analyze(image: UploadFile = File(...), symptoms: str = Form("{}"), eye: str = Form(""),
                  language: str = Form("en"), patient_ref: str = Form("")):
    data = await image.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "image too large")
    bgr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if bgr is None:
        raise HTTPException(400, "could not read the image")
    try:
        sym = json.loads(symptoms or "{}")
    except json.JSONDecodeError:
        raise HTTPException(400, "symptoms must be JSON")
    out = pipeline.run(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), symptoms=sym,
                       eye=eye if eye in ("left", "right") else None)
    report: ScreeningReport = out["report"]
    report.language = language
    a = _cfg["assistant"]
    assistant = explain(report, language=language, model=a["model"], effort=a["effort"], max_tokens=a["max_tokens"])
    store.add_scan(report.model_dump(), patient_ref or None)
    return {"report": report.model_dump(), "assistant": assistant, "overlay_png_base64": out["overlay_png_base64"]}


@app.post("/report/doctor", response_class=PlainTextResponse)
def report_for_doctor(report: ScreeningReport):
    return doctor_report(report)


# ------------------------------------------------------------------ doctor dashboard (Step 11)

class Review(BaseModel):
    reviewer: str
    decision: str                 # confirm | correct
    doctor_label: str | None = None
    note: str | None = None


@app.get("/dashboard")
def dashboard():
    return FileResponse(STATIC / "dashboard.html")


@app.get("/doctor/queue")
def doctor_queue(include_routine: bool = False):
    return {"stats": store.stats(), "queue": store.queue(include_routine)}


@app.get("/doctor/scan/{scan_id}")
def doctor_scan(scan_id: str):
    scan = store.get(scan_id)
    if scan is None:
        raise HTTPException(404, "scan not found")
    return scan


@app.post("/doctor/scan/{scan_id}/review")
def doctor_review(scan_id: str, body: Review):
    if body.decision == "correct" and not body.doctor_label:
        raise HTTPException(400, "a correction needs doctor_label")
    try:
        return store.review(scan_id, body.reviewer, body.decision, body.doctor_label, body.note)
    except KeyError:
        raise HTTPException(404, "scan not found")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/doctor/corrections")
def doctor_corrections():
    """Doctor labels for retraining, least-confident first (active learning)."""
    return store.corrections_for_training()
