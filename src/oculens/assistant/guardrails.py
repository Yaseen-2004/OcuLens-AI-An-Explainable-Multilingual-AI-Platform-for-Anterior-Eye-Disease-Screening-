"""Safety guardrails applied to every assistant reply, whichever way it was generated.

  * hedged wording: "possible signs of", never "you have";
  * no medication names with doses;
  * urgent results always end with the urgent instruction;
  * a screening disclaimer is always present.
"""
from __future__ import annotations

import re

DISCLAIMER = ("This is a screening result, not a diagnosis. Only an eye doctor can confirm it.")
URGENT_LINE = "Please see an eye doctor within 24 hours. If vision is getting worse quickly, go today."

_DOSE = re.compile(r"\b\d+(\.\d+)?\s?(mg|mcg|ml|mL|%|drops?|tablets?|times a day|x/day)\b", re.I)
_DIAGNOSTIC = [
    (re.compile(r"\byou have\b", re.I), "the image shows possible signs of"),
    (re.compile(r"\byou are suffering from\b", re.I), "the image shows possible signs of"),
    (re.compile(r"\bdiagnosed with\b", re.I), "showing possible signs of"),
]


def find_violations(text: str) -> list[str]:
    v = []
    if _DOSE.search(text):
        v.append("dosage")
    if any(p.search(text) for p, _ in _DIAGNOSTIC):
        v.append("diagnostic_wording")
    return v


def apply_guardrails(text: str, triage_level: str) -> str:
    out = text
    for pattern, repl in _DIAGNOSTIC:
        out = pattern.sub(repl, out)
    # Drop any sentence that contains a dose.
    sentences = re.split(r"(?<=[.!?])\s+", out)
    out = " ".join(s for s in sentences if not _DOSE.search(s)).strip()
    if triage_level == "urgent" and URGENT_LINE not in out:
        out = f"{out}\n\n{URGENT_LINE}"
    if DISCLAIMER not in out:
        out = f"{out}\n\n{DISCLAIMER}"
    return out.strip()


# ---- chat replies (the assistant page shows the screening disclaimer once, so it is not appended here)
# "%" is left out on purpose: chat answers quote confidence percentages, which are not doses.
_CHAT_DOSE = re.compile(r"\b\d+(\.\d+)?\s?(mg|mcg|ml|mL|drops?|tablets?|capsules?|times a day|x/day)\b", re.I)
_CHAT_DIAGNOSTIC = re.compile(
    r"\byou (have|are suffering from|are diagnosed with|definitely have)\s+(an?\s+)?"
    r"(bacterial|fungal|herpes|viral|keratitis|corneal ulcer|ulcer|trachoma|infection|eye infection)", re.I)


def chat_safe(text: str) -> str:
    """Hedge diagnostic wording about a condition and drop any sentence that gives a dose."""
    def _hedge(m):
        lead = "The photo" if m.group(0)[0].isupper() else "the photo"
        return f"{lead} shows possible signs of {m.group(2) or ''}{m.group(3)}"
    out = _CHAT_DIAGNOSTIC.sub(_hedge, text)
    # keep the original spacing (line breaks of lists) between the sentences that stay
    pieces = re.split(r"(?<=[.!?।])(\s+)", out)
    kept, gap = [], ""
    for i, p in enumerate(pieces):
        if i % 2:                       # whitespace separator
            gap = p
            continue
        if _CHAT_DOSE.search(p):
            continue
        kept.append((gap if kept else "") + p)
        gap = ""
    return "".join(kept).strip()
