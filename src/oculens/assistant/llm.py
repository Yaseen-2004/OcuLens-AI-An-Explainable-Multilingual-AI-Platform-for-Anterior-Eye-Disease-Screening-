"""Patient-facing explanation of a screening report.

Uses the Anthropic API when credentials are available (ANTHROPIC_API_KEY or an `ant auth login`
profile); otherwise falls back to a fixed template so the app still works offline.
Either way the output passes through the guardrails.
"""
from __future__ import annotations

import json
import logging
import os

from oculens.assistant.guardrails import apply_guardrails
from oculens.assistant.schema import ScreeningReport

log = logging.getLogger(__name__)

LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "kn": "Kannada", "ta": "Tamil", "te": "Telugu"}

SYSTEM_PROMPT = """You explain eye screening results to patients and community health workers in India.

You receive a JSON screening report produced by validated image models and a rule-based triage engine.
You never see the image, and you must not add findings, conditions or causes that are not in the report.

How to write:
- Use simple, warm language a person without medical training understands. Short sentences.
- Say "possible signs of", never "you have". This is screening, not diagnosis.
- State the triage level and what to do next, in plain words, near the start.
- If a finding is marked uncertain or the explanation is marked unreliable, say the result needs a doctor to check it.
- Do not name medicines, doses or home remedies. Do not tell anyone to stop or change treatment.
- If the triage level is urgent, say clearly to see an eye doctor within 24 hours.
- Answer only in the requested language. Keep it under 150 words."""


def _template(report: ScreeningReport) -> str:
    lines = []
    t = report.triage
    lines.append(f"Result: {t.level.upper()}. {t.advice}")
    abnormal = [f for f in report.findings if f.condition.lower() not in ("normal", "0")]
    for f in abnormal:
        txt = f"The image shows possible signs of {f.condition.replace('_', ' ')} in the {f.region.replace('_', ' ')}"
        txt += f" (model confidence {f.probability:.0%})."
        if f.refer or f.uncertainty == "high":
            txt += " The model is not sure, so a doctor should check this."
        if f.explanation_reliable is False:
            txt += " The model's attention was not on the expected part of the eye, so treat this result with caution."
        lines.append(txt)
    if not abnormal:
        lines.append("No clear sign of disease was found in this image.")
    return " ".join(lines)


def explain(report: ScreeningReport, language: str = "en", model: str = "claude-opus-5-5",
            effort: str = "medium", max_tokens: int = 16000) -> dict:
    """Return {"text": ..., "source": "llm" | "template", "note": ...}."""
    level = report.triage.level
    try:
        if os.environ.get("OCULENS_ASSISTANT") == "template":
            raise RuntimeError("template mode requested")
        import anthropic

        client = anthropic.Anthropic()
        response = client.beta.messages.create(
            model=model,
            max_tokens=max_tokens,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": effort},
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": (f"Language: {LANGUAGE_NAMES.get(language, 'English')}\n\n"
                            f"Screening report (JSON):\n{json.dumps(report.model_dump(), indent=2)}"),
            }],
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("model declined the request")
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        if not text:
            raise RuntimeError("empty response")
        return {"text": apply_guardrails(text, level), "source": "llm", "model": response.model}
    except Exception as exc:  # no credentials, no network, API error -> deterministic template
        log.info("assistant falling back to template: %s", exc)
        return {"text": apply_guardrails(_template(report), level), "source": "template",
                "note": f"LLM unavailable ({type(exc).__name__}); English template used."}
