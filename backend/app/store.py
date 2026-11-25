"""Scan records and doctor corrections (SQLite for development; PostgreSQL in deployment).

Corrections feed active learning: the export orders them by model uncertainty, so the images
the model was least sure about are relabelled and retrained first.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    scan_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    patient_ref TEXT,
    eye TEXT,
    triage_level TEXT NOT NULL,
    top_condition TEXT,
    top_probability REAL,
    uncertain INTEGER NOT NULL DEFAULT 0,
    report_json TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'pending'
);
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT NOT NULL REFERENCES scans(scan_id),
    reviewer TEXT NOT NULL,
    decision TEXT NOT NULL,
    model_label TEXT,
    doctor_label TEXT,
    note TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, scan_id TEXT
);
"""
PRIORITY = "CASE triage_level WHEN 'urgent' THEN 0 WHEN 'refer' THEN 1 WHEN 'soon' THEN 2 ELSE 3 END"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock:
            self.db.executescript(SCHEMA)

    def _audit(self, actor: str, action: str, scan_id: str | None = None):
        self.db.execute("INSERT INTO audit_log(at, actor, action, scan_id) VALUES (?,?,?,?)",
                        (_now(), actor, action, scan_id))

    def add_scan(self, report: dict, patient_ref: str | None = None) -> None:
        f = report["findings"][0] if report.get("findings") else {}
        with self.lock:
            self.db.execute(
                "INSERT OR REPLACE INTO scans VALUES (?,?,?,?,?,?,?,?,?, 'pending')",
                (report["scan_id"], _now(), patient_ref, report.get("eye"), report["triage"]["level"],
                 f.get("condition"), f.get("probability"), int(bool(f.get("refer"))), json.dumps(report)))
            self._audit("system", "scan_added", report["scan_id"])
            self.db.commit()

    def queue(self, include_routine: bool = False, limit: int = 100) -> list[dict]:
        where = "review_status = 'pending'" + ("" if include_routine else " AND triage_level != 'routine'")
        rows = self.db.execute(
            f"SELECT scan_id, created_at, patient_ref, eye, triage_level, top_condition, top_probability, uncertain "
            f"FROM scans WHERE {where} ORDER BY {PRIORITY}, created_at LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get(self, scan_id: str) -> dict | None:
        r = self.db.execute("SELECT * FROM scans WHERE scan_id = ?", (scan_id,)).fetchone()
        if not r:
            return None
        out = dict(r)
        out["report"] = json.loads(out.pop("report_json"))
        out["reviews"] = [dict(x) for x in self.db.execute(
            "SELECT reviewer, decision, model_label, doctor_label, note, created_at FROM reviews WHERE scan_id = ?",
            (scan_id,)).fetchall()]
        return out

    def review(self, scan_id: str, reviewer: str, decision: str, doctor_label: str | None = None,
               note: str | None = None) -> dict:
        if decision not in ("confirm", "correct"):
            raise ValueError("decision must be 'confirm' or 'correct'")
        scan = self.get(scan_id)
        if scan is None:
            raise KeyError(scan_id)
        model_label = scan["top_condition"]
        label = model_label if decision == "confirm" else doctor_label
        with self.lock:
            self.db.execute("INSERT INTO reviews(scan_id, reviewer, decision, model_label, doctor_label, note, created_at) "
                            "VALUES (?,?,?,?,?,?,?)", (scan_id, reviewer, decision, model_label, label, note, _now()))
            self.db.execute("UPDATE scans SET review_status = ? WHERE scan_id = ?",
                            ("confirmed" if decision == "confirm" else "corrected", scan_id))
            self._audit(reviewer, f"review_{decision}", scan_id)
            self.db.commit()
        return {"scan_id": scan_id, "decision": decision, "model_label": model_label, "doctor_label": label}

    def corrections_for_training(self) -> list[dict]:
        """Doctor-labelled scans, least-confident model predictions first (active learning order)."""
        rows = self.db.execute(
            "SELECT s.scan_id, s.top_condition AS model_label, r.doctor_label, s.top_probability, r.decision "
            "FROM reviews r JOIN scans s USING(scan_id) ORDER BY s.top_probability ASC").fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        q = lambda sql: self.db.execute(sql).fetchone()[0]  # noqa: E731
        return {"scans": q("SELECT COUNT(*) FROM scans"),
                "pending": q("SELECT COUNT(*) FROM scans WHERE review_status='pending'"),
                "confirmed": q("SELECT COUNT(*) FROM scans WHERE review_status='confirmed'"),
                "corrected": q("SELECT COUNT(*) FROM scans WHERE review_status='corrected'")}
