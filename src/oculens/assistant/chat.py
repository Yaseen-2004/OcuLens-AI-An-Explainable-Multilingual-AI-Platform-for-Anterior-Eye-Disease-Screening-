"""OcuLens AI assistant: a grounded, safety-guarded chat about screening results and eye conditions.

Two engines behind one interface:
  * Claude (Anthropic API, claude-opus-5-5, streamed) when credentials are configured
    (ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN or an `ant auth login` profile);
  * an offline, rule-based assistant built from the same knowledge base and the case facts,
    used when there are no credentials, no network, or the API call fails.

Both are grounded: they may use only the case facts passed in and the knowledge base below, never
diagnose, never name medicines or doses, and send emergencies straight to a doctor.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Iterator

from oculens.assistant.guardrails import chat_safe
from oculens.assistant.i18n import to_english_keywords, tr, tr_static

MODEL = "claude-opus-5-5"
LANGUAGES = {"en": ("English", "en-IN"), "hi": ("Hindi", "hi-IN"), "kn": ("Kannada", "kn-IN"),
             "ta": ("Tamil", "ta-IN"), "te": ("Telugu", "te-IN")}

URGENT = ("This could be an eye emergency. Please see an eye doctor today, or go to the nearest hospital "
          "emergency department now. Do not wait for an online answer.")

_RED_FLAGS = [
    r"sudden(ly)?\s+(loss|lost|can'?t see|cannot see|blur|blind)", r"\b(lost|losing)\s+(my\s+)?(vision|sight)\b",
    r"\bcan'?t see\b", r"\bcannot see\b", r"\bblind(ness)?\s+(sudden|now|today)", r"\bchemical", r"\bacid\b",
    r"\balkali", r"\bbleach\b", r"\bsplash", r"\b(hit|injur|trauma|stabbed|cut)\w*\b.*\beye\b",
    r"\beye\b.*\b(hit|injur|trauma|stabbed|cut)\w*\b", r"\bsevere\s+(eye\s+)?pain", r"\bunbearable\b",
    r"\bblood\s+in\s+(my\s+)?eye", r"\bafter\s+(eye\s+)?(surgery|operation)\b.*\b(pain|red|blur)",
    r"\b(pain|red|blur)\w*\b.*\bafter\s+(eye\s+)?(surgery|operation)\b",
    r"\bflash(es|ing)?\s+of\s+light", r"\bcurtain\b", r"\bshadow\s+(over|across|in)\s+(my\s+)?(vision|sight)",
    r"\bsudden(ly)?\s+(lots\s+of\s+|many\s+|new\s+)?floaters",
]
_RED = [re.compile(p, re.I) for p in _RED_FLAGS]


def red_flag(text: str) -> bool:
    """True when the message describes symptoms that need same-day care."""
    return any(p.search(text or "") for p in _RED)


KNOWLEDGE = """
ABOUT OCULENS-AI
OcuLens-AI is a capstone research prototype that screens photographs of the front of the eye for three
conditions: infectious keratitis (four types: bacterial, fungal, herpes simplex, other corneal abnormality),
corneal ulcer pattern (three patterns, from fluorescein-stained photos), and trachoma (the TF sign on the
inside of the upper eyelid). It is a screening and referral aid, not a diagnosis and not a medical device.

HOW A SCREENING WORKS
1. Guided capture photographs the right eye, then the left; a focus meter and checks make sure the photo is usable.
2. An eye check refuses images that are not an eye; a quality check flags blur, poor light and glare.
3. A U-Net segmentation model outlines the cornea.
4. An EfficientNet-B0 classifier scores each possible condition. For keratitis this model was trained with
   extra synthetic (diffusion-generated) images of the rare infection types.
5. Calibration makes the confidence honest; a conformal prediction set lists every condition the model cannot
   rule out at 95% coverage; a 10-model ensemble measures disagreement (mutual information) as uncertainty.
6. A Grad-CAM++ heat-map shows where the model looked.
7. If the model is unsure (several conditions in the prediction set, or low confidence) it says REFER: the
   patient should see an eye specialist. Uncertain cases are never reported as normal.
8. The portal suggests three Bengaluru eye hospitals for the condition; the doctor names shown are clearly
   marked samples, the hospitals are real.

HOW GOOD THE MODELS ARE (held-out test images, balanced accuracy; chance = 1 / number of classes)
- Trachoma (2 classes, chance 0.50): 0.81, AUROC 0.90.
- Corneal ulcer pattern (3 classes, chance 0.33): 0.68 with the cornea mask as an extra input; the portal runs
  the image-only model, 0.63.
- Infectious keratitis (4 classes, chance 0.25): the hardest task. The portal's model scored 0.488, the best of
  four training seeds; the average across seeds is about 0.42, and an ensemble of four is 0.474.
- Test sets come from one hospital each and are small, so results are first baselines, not clinical claims.
- The heat-maps mostly fall on the cornea, but rarely on the ulcer lesion itself.

CONDITIONS (general education only)
- Keratitis is inflammation of the cornea, the clear window at the front of the eye. Infectious keratitis is
  caused by bacteria, fungi, viruses or parasites. Typical complaints: a red, painful, watering eye, blurred
  vision, sensitivity to light, sometimes discharge or a white spot on the cornea. It can damage sight quickly
  and needs an eye doctor promptly.
- Bacterial keratitis is often linked to contact-lens wear (especially sleeping in lenses) or a scratch or
  injury to the eye. It can worsen within a day or two.
- Fungal keratitis is common in hot, humid regions such as South India, often after an injury with plant
  matter (for example during farm work). It can progress more slowly but is serious and needs a specialist.
- Herpes simplex keratitis is caused by the herpes simplex virus and can come back. Eye drops not prescribed
  for this problem, especially steroid drops, can make some infections worse, so nothing should be used without
  an eye doctor.
- A corneal ulcer is an open sore on the cornea, usually from infection. It is an emergency. In clinics a
  harmless orange dye (fluorescein) makes the ulcer glow green under cobalt-blue light, which is what the ulcer
  photographs show.
- Trachoma is an infectious eye disease caused by the bacterium Chlamydia trachomatis, spread by eye and nose
  discharge, hands, cloths and flies. TF (trachomatous inflammation, follicular) means small bumps (follicles)
  on the inside of the upper eyelid. Repeated infections can scar the eyelid so the lashes turn inward and
  scratch the eye, which can lead to blindness. The WHO SAFE strategy fights it: Surgery for in-turned lashes,
  Antibiotics, Facial cleanliness, and Environmental improvement.

SAFE GENERAL EYE CARE (never instead of a doctor)
- Do not rub the eye; wash hands before touching the eyes; do not share towels or face cloths.
- Contact-lens wearers with a red or painful eye should remove the lenses and see an eye doctor.
- Do not use leftover, borrowed or home-made eye drops or remedies.
- Wear protective glasses for farm work, grinding or welding.

WHEN TO GO TODAY (red flags): sudden loss of vision, severe eye pain, a chemical splash (rinse with clean water
for at least 15 minutes, then go to hospital), an injury to the eye, a white spot on the cornea with pain, or
pain or redness after eye surgery.

TAKING A GOOD PHOTO: one eye fills the circle, the eye is open, the camera is steady, light comes from the side
(not straight on, to avoid glare), and the focus bar is green before capture.
"""

SYSTEM_PROMPT = f"""You are the OcuLens assistant inside an eye-screening portal used by doctors, community health
workers and patients in Bengaluru, India.

Answer every question the person asks, as helpfully as you can:
- Anything about this patient's result, numbers or referral must come from the CASE FACTS; never invent
  findings, numbers, doctors or hospitals.
- For general eye-health and health questions (symptoms, causes, daily life, prevention, what to expect at the
  hospital), answer from sound general medical knowledge and the KNOWLEDGE section below.
- If a question is unrelated to eyes or health, answer it briefly and kindly, then offer to help with the eyes.
- If you are genuinely unsure, say so and suggest asking the eye doctor rather than guessing.

Safety rules:
- This is screening, not diagnosis. Say "the photo shows possible signs of", never "you have".
- Never name medicines, doses or home remedies, and never tell anyone to start, stop or change a treatment.
- If the person describes a red-flag symptom (sudden vision loss, severe pain, chemical splash, eye injury,
  pain after eye surgery), tell them first and clearly to get care today.
- If the case says REFER, say plainly that the result needs an eye specialist, and mention the suggested
  Bengaluru hospitals from the case facts when it helps. Doctor names in the facts are samples; say so if you
  name one.
- Be honest about the model's limits when asked how reliable it is.
- Doctor notes in the case facts are for clinicians. In the Patient-friendly style, say only that a doctor
  has reviewed the case and to follow their advice; never repeat treatment or medicine details from them.

Style: answer in the language given in the context. For "Patient-friendly", use short, warm, simple sentences
without jargon, under 120 words. For "Clinician", be precise and concise, use the medical terms and the numbers
from the case facts, under 180 words. Plain text, no tables; short lists are fine.

KNOWLEDGE
{KNOWLEDGE}"""


def has_credentials() -> bool:
    """Credentials the Anthropic SDK would find, without making a request."""
    if os.environ.get("OCULENS_ASSISTANT", "").lower() == "offline":
        return False
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    for d in (Path.home() / ".config" / "anthropic", Path(os.environ.get("APPDATA", "")) / "anthropic"):
        if d.is_dir() and any(d.iterdir()):
            return True
    return False


# ---------------------------------------------------------------- offline engine
def _pct(p) -> str:
    try:
        return f"{float(p) * 100:.0f}%"
    except (TypeError, ValueError):
        return "unknown"


def _facts_line(f: dict) -> str:
    return (f"Case #{f.get('case_id')} ({f.get('screening')}, {f.get('eye') or 'eye not recorded'}): most likely "
            f"{f.get('most_likely')} at {_pct(f.get('confidence'))} confidence.")


def _hospitals(f: dict, lang: str = "en") -> str:
    hs = f.get("referral_hospitals") or []
    if not hs:
        return ""
    lines = [f"- {h['hospital']} ({h['area']}): {h['focus']}" for h in hs]
    return tr("hosp_head", lang) + "\n" + "\n".join(lines)


_INTENTS = [
    ("identity", r"\b(who are you|what('?s| is) your name|introduce yourself|are you (a |an )?(bot|robot|human|ai))\b"),
    ("greeting", r"^\s*(hi|hello|hey|namaste|good (morning|afternoon|evening))\b"),
    ("hospital", r"\b(hospital|doctor|clinic|where (should|do|can) i go|specialist|appointment|refer\w*)\b"),
    ("confidence", r"\b(sure|confiden\w*|certain|uncertain\w*|reliab\w*|trust|accura\w*|how good|mutual information|prediction set)\b"),
    ("next", r"\b(what (should|do) i do|next step|what now|treat\w*|cure|medicine|drops?|tablet)\b"),
    ("result", r"\b(result|mean|explain|report|finding|diagnos\w*|what (is|does) (my|this|the) (case|scan|screening))\b"),
    ("trachoma", r"\btrachoma|\btf\b|follic"),
    ("ulcer", r"\bulcer"),
    ("fungal", r"\bfung"),
    ("bacterial", r"\bbacter"),
    ("herpes", r"\bherpes|\bhsk\b|\bviral\b"),
    ("keratitis", r"\bkeratitis\b|\bcornea"),
    ("photo", r"\b(photo|picture|capture|camera|focus|blur\w*|image quality)\b"),
    ("care", r"\b(prevent\w*|care|protect\w*|hygiene|contact lens\w*|rub\w*)\b"),
    ("howitworks", r"\b(how (does|do) (it|this|oculens|the (app|portal|model|ai)) work|model|pipeline|ai|grad-?cam|heat-?map)\b"),
]
_INT = [(n, re.compile(p, re.I)) for n, p in _INTENTS]


def _section(title: str) -> str:
    """One entry from the CONDITIONS part of the knowledge base (the performance list also starts with
    condition names, so it must not be searched)."""
    conditions = KNOWLEDGE.split("CONDITIONS (general education only)")[1].split("SAFE GENERAL EYE CARE")[0]
    m = re.search(rf"^- {title}.*?(?=^- |\n\n|\Z)", conditions, re.S | re.M)
    return re.sub(r"\s+", " ", m.group(0)[2:]).strip() if m else ""


def offline_answer(question: str, facts: dict | None, audience: str = "Patient-friendly", lang: str = "en") -> str:
    """Deterministic, grounded answer from the knowledge base and the case facts. The sentences built here are
    translated (i18n.T); knowledge-base answers stay English, introduced by a line in the chosen language."""
    ans = _offline(question, facts, audience, lang)
    if lang != "en" and not re.search(r"[\u0900-\u097F\u0B80-\u0BFF\u0C00-\u0CFF]", ans):
        done = tr_static(ans, lang)          # knowledge-base text: pre-translated (translations.json)
        ans = done if done else tr("english_follows", lang) + "\n\n" + ans
    return ans


def static_texts() -> list[str]:
    """Every fixed English answer the offline engine can give (the set that is pre-translated)."""
    from oculens.assistant.faq import FAQ
    out = [a for _, _, a in FAQ]
    out += [condition_text(k) for k in _CONDITION_TITLES.values()]
    out += [photo_text(), care_text(), HOWITWORKS]
    return out


_CONDITION_TITLES = {"trachoma": "Trachoma", "ulcer": "A corneal ulcer", "fungal": "Fungal keratitis",
                     "bacterial": "Bacterial keratitis", "herpes": "Herpes simplex keratitis", "keratitis": "Keratitis"}
HOWITWORKS = ("OcuLens checks the photo is an eye and usable, outlines the cornea with a U-Net, scores each condition "
              "with an EfficientNet-B0 model, measures how sure it is (calibration, a 95% prediction set and a "
              "10-model ensemble), shows a Grad-CAM heat-map of where it looked, and refers uncertain cases to a "
              "specialist. It is a screening aid, not a diagnosis.")


def condition_text(title: str) -> str:
    return _section(title) + " If you notice these signs, please see an eye doctor."


def photo_text() -> str:
    return re.sub(r"\s+", " ", KNOWLEDGE.split("TAKING A GOOD PHOTO:")[1]).strip().capitalize()


def care_text() -> str:
    block = KNOWLEDGE.split("SAFE GENERAL EYE CARE (never instead of a doctor)")[1].split("WHEN TO GO TODAY")[0]
    return "Some safe, general eye-care habits (never instead of a doctor):" + block.rstrip()


def _offline(question: str, facts: dict | None, audience: str, lang: str) -> str:
    q = question or ""
    extra = to_english_keywords(q)          # questions typed or spoken in Hindi, Kannada, Tamil or Telugu
    if extra:
        q = f"{q} {extra}"
    if red_flag(q):
        tip = ""
        if re.search(r"chemical|acid|alkali|bleach|splash|lime|cement", q, re.I):
            tip = " " + tr("firstaid_chem", lang)
        elif re.search(r"hit|injur|trauma|stab|cut|poke", q, re.I):
            tip = " " + tr("firstaid_injury", lang)
        return tr("urgent", lang) + tip
    intent = next((n for n, p in _INT if p.search(q)), None)
    clin = audience.lower().startswith("clin")
    f = facts or {}
    has_case = bool(f.get("case_id"))
    if intent == "identity":
        return tr("identity", lang)
    if intent == "greeting" and len(q.split()) <= 4:
        return tr("greeting", lang)
    # "What is trachoma?" wants the description, not a related FAQ such as "is trachoma contagious"
    if intent in _CONDITION_TITLES and re.match(r"\s*(what('?s| is| are)|tell me about|explain|describe|define)\b", q, re.I):
        return condition_text(_CONDITION_TITLES[intent])
    from oculens.assistant.faq import best as _faq
    faq_ans, faq_score = _faq(q)
    case_intent = intent in ("result", "next", "confidence", "hospital")
    if not (has_case and case_intent) and faq_ans and faq_score >= 0.23:
        return faq_ans
    if case_intent and not has_case:
        return tr("choose_case", lang)
    if intent == "result":
        parts = [tr("case_line", lang, cid=f.get("case_id"), screening=f.get("screening"),
                    eye=f.get("eye") or "eye not recorded", label=f.get("most_likely"), conf=_pct(f.get("confidence")))]
        pset = f.get("prediction_set") or []
        if len(pset) > 1:
            parts.append(tr("case_set", lang, n=len(pset), items=", ".join(pset)))
        parts.append(tr("case_refer" if f.get("referral_advised") else "case_ok", lang))
        if f.get("doctor_notes"):
            if clin:
                parts.append(f"Doctor's note on this case: {f['doctor_notes']}")
            else:   # treatment details are for clinicians, never relayed to patients
                parts.append(tr("case_reviewed", lang))
        if clin:
            parts.append(f"Model disagreement (mutual information) {f.get('uncertainty_mi', 'n/a')}; image quality "
                         f"{'OK' if f.get('image_quality_ok') else 'flagged'}.")
        return " ".join(parts)
    if intent == "confidence":
        mi = f.get("uncertainty_mi")
        txt = (f"The model gave its top answer {_pct(f.get('confidence'))} confidence. Its 95% prediction set "
               f"contains {len(f.get('prediction_set') or [])} condition(s); the more it contains, the less sure "
               f"the model is.")
        if mi is not None:
            txt += (f" Ten models disagreed with a score of {mi} (higher means more uncertain; above 0.12 is "
                    f"flagged).")
        txt += (" For context, keratitis is the hardest task: about 0.42 to 0.49 balanced accuracy on four classes "
                "(chance is 0.25). That is why uncertain results are referred, never called normal.")
        return txt
    if intent == "next":
        txt = (tr("next_head", lang) + " " + tr("next_refer" if f.get("referral_advised") else "next_confirm", lang)
               + " " + tr("next_care", lang))
        h = _hospitals(f, lang)
        return (txt + ("\n\n" + h if h else "")).strip()
    if intent == "hospital":
        h = _hospitals(f, lang)
        return (h + "\n\n" + tr("hosp_tail", lang)) if h else \
            "Open the case page to see the suggested Bengaluru hospitals for this result."
    if intent in _CONDITION_TITLES:
        return condition_text(_CONDITION_TITLES[intent])
    if intent == "photo":
        return photo_text()
    if intent == "care":
        return care_text()
    if intent == "howitworks":
        return HOWITWORKS
    if faq_ans and faq_score >= 0.23:
        return faq_ans
    from oculens.assistant.faq import on_topic_norm as _on_topic, other_body_part
    if other_body_part(q):
        return tr("other_body", lang)
    if not _on_topic(q):
        return tr("offtopic", lang)
    # on topic but not understood: ask what a doctor would ask, instead of refusing
    return tr("clarify", lang)


# ---------------------------------------------------------------- one reply
class Reply:
    """Iterate to stream the answer text; afterwards `.text`, `.source` and `.note` are set."""

    def __init__(self, question: str, history: list[dict], facts: dict | None, language: str = "en",
                 audience: str = "Patient-friendly", allow_online: bool = True):
        self.question, self.history, self.facts = question, history, facts
        self.language, self.audience = language, audience
        self.allow_online = allow_online
        self.text, self.source, self.note = "", "offline", ""
        self.urgent = red_flag(question)

    def _context(self) -> str:
        import json
        lang = LANGUAGES.get(self.language, LANGUAGES["en"])[0]
        facts = json.dumps(self.facts, ensure_ascii=False) if self.facts else "No case selected (general question)."
        return (f"<context>\nLanguage: {lang}\nAnswer style: {self.audience}\nCASE FACTS: {facts}\n</context>\n\n"
                f"Question: {self.question}")

    def _claude(self) -> Iterator[str]:
        import anthropic
        client = anthropic.Anthropic()
        msgs = [{"role": m["role"], "content": m["content"]} for m in self.history[-12:]
                if m.get("role") in ("user", "assistant") and m.get("content")]
        msgs.append({"role": "user", "content": self._context()})
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",                      # a policy decline is re-run on a fallback model
            output_config={"effort": "low"},          # chat: quick replies; Opus 5.5 always thinks adaptively
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=msgs,
        ) as stream:
            for chunk in stream.text_stream:
                yield chunk
            final = stream.get_final_message()
        if final.stop_reason == "refusal":
            yield "\n\nI can't help with that request. Please ask the eye doctor."
        self.note = f"Claude ({final.model})"

    def __iter__(self) -> Iterator[str]:
        buf = []
        if self.allow_online and has_credentials():
            try:
                for chunk in self._claude():
                    buf.append(chunk)
                    yield chunk
                self.source = "claude"
                self.text = chat_safe("".join(buf))
                return
            except Exception as exc:  # noqa: BLE001 - no network, bad key, rate limit: fall back below
                import anthropic
                kinds = [(anthropic.AuthenticationError, "the API key was rejected"),
                         (anthropic.PermissionDeniedError, "the API key lacks permission"),
                         (anthropic.RateLimitError, "the API is busy (rate limit)"),
                         (anthropic.APIConnectionError, "no internet connection"),
                         (anthropic.APIStatusError, "the API returned an error")]
                why = next((w for k, w in kinds if isinstance(exc, k)), type(exc).__name__)
                self.note = f"Claude unavailable ({why}); offline answer."
                if buf:
                    yield "\n\n"
        else:
            self.note = "Offline assistant (no Claude credentials configured)."
        text = offline_answer(self.question, self.facts, self.audience, self.language)
        for word in re.split(r"(\s+)", text):   # stream word by word so it feels the same as online mode
            yield word
            time.sleep(0.012)
        self.source = "offline"
        self.text = chat_safe("".join(buf) + text if buf else text)
