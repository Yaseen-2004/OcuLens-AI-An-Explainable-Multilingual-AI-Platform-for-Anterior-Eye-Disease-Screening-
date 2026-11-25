"""Doctor-facing plain-text report built directly from the structured findings (no LLM)."""
from __future__ import annotations

from oculens.assistant.schema import ScreeningReport


def doctor_report(report: ScreeningReport) -> str:
    q = report.quality
    out = [
        f"OcuLens-AI screening report - scan {report.scan_id}",
        f"Image source: {report.image_source}; eye: {report.eye or 'not recorded'}",
        f"Quality: {'accepted' if q.get('ok') else 'REJECTED'} {q.get('metrics', {})}",
        f"Triage: {report.triage.level.upper()} - {report.triage.advice}",
        "Reasons: " + "; ".join(report.triage.reasons),
        "",
        "Findings:",
    ]
    for f in report.findings:
        out.append(
            f"  - {f.region}: {f.condition} p={f.probability:.2f} set={f.prediction_set} "
            f"uncertainty={f.uncertainty} attention_in_region={f.attention_in_region} reliable={f.explanation_reliable}"
        )
    sym = [k for k, v in report.symptoms.model_dump().items() if v]
    out += ["", "Symptoms reported: " + (", ".join(sym) or "none"), f"Model: {report.model_info}",
            "", "Screening result only - requires confirmation by an ophthalmologist."]
    return "\n".join(out)
