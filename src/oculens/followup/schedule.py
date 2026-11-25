"""Personalised rescan schedule and post-cataract-surgery warning checks."""
from __future__ import annotations

from datetime import date, timedelta

# Days until the next scan by triage level (clinical advisor to confirm).
RESCAN_DAYS = {"urgent": 1, "refer": 7, "soon": 30, "routine": 180}
POST_OP_DAYS = (1, 7, 30)
POST_OP_WARNING_SYMPTOMS = ("pain", "vision_drop", "redness", "discharge")


def next_scan(triage_level: str, scan_date: date, progressed: bool = False) -> date:
    days = RESCAN_DAYS.get(triage_level, 90)
    if progressed:
        days = max(1, days // 2)
    return scan_date + timedelta(days=days)


def post_op_schedule(surgery_date: date) -> list[date]:
    return [surgery_date + timedelta(days=d) for d in POST_OP_DAYS]


def post_op_check(symptoms: dict, change_status: str | None = None) -> dict:
    """Any warning symptom, or a progressing image, after surgery -> alert the surgeon."""
    warnings = [s for s in POST_OP_WARNING_SYMPTOMS if symptoms.get(s)]
    if change_status == "progressed":
        warnings.append("image worse than previous visit")
    return {"alert_surgeon": bool(warnings), "warnings": warnings,
            "message": ("Possible post-operative complication - notify the surgeon today."
                        if warnings else "No warning signs at this visit.")}


def trend(history: list[dict]) -> list[dict]:
    """history: [{'date': 'YYYY-MM-DD', 'probability': float, ...}] -> sorted, with change vs previous."""
    rows = sorted(history, key=lambda r: r["date"])
    out, prev = [], None
    for r in rows:
        delta = None if prev is None else round(r["probability"] - prev["probability"], 3)
        out.append({**r, "delta": delta})
        prev = r
    return out
