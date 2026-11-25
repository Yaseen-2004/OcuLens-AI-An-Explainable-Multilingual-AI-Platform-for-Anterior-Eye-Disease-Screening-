import re
"""AI assistant: red flags, grounded offline answers, guardrails, and the Claude streaming path (faked)."""
import types

import pytest

from oculens.assistant import chat
from oculens.assistant.guardrails import chat_safe

FACTS = {
    "case_id": 7, "patient": "walk-in", "screening": "Infectious keratitis", "eye": "Right eye (OD)",
    "most_likely": "Fungal keratitis", "confidence": 0.317, "prediction_set": ["Bacterial keratitis", "Fungal keratitis"],
    "referral_advised": True, "uncertainty_mi": 0.13, "uncertainty_flagged": True, "image_quality_ok": True,
    "review_status": "pending", "doctor_notes": "",
    "referral_hospitals": [{"hospital": "Narayana Nethralaya", "area": "Rajajinagar", "focus": "Microbial keratitis",
                            "doctor": "Dr. A. Rao (sample)"}],
}


@pytest.mark.parametrize("text", ["I suddenly can't see from my left eye", "a chemical splashed in my eye",
                                  "my eye was hit by a ball", "severe pain in the eye since morning",
                                  "pain and redness after eye surgery"])
def test_red_flags_detected(text):
    assert chat.red_flag(text)


@pytest.mark.parametrize("text", ["What is trachoma?", "How sure is the model?", "my eye is a bit itchy"])
def test_ordinary_questions_are_not_red_flags(text):
    assert not chat.red_flag(text)


def test_offline_result_uses_case_facts():
    ans = chat.offline_answer("What does this result mean?", FACTS)
    assert "Fungal keratitis" in ans and "32%" in ans and "REFER" in ans


def test_offline_hospital_lists_real_hospitals_and_flags_samples():
    ans = chat.offline_answer("Which hospital should I go to?", FACTS)
    assert "Narayana Nethralaya" in ans and "samples" in ans


def test_offline_never_prescribes():
    ans = chat.offline_answer("What medicine drops should I use?", FACTS)
    assert "can't suggest medicines" in ans


def test_offline_red_flag_wins():
    ans = chat.offline_answer("acid splashed in my eye", FACTS)
    assert ans.startswith(chat.URGENT) and "15 minutes" in ans


def test_chat_safe_hedges_and_strips_doses_but_keeps_percentages():
    out = chat_safe("You have fungal keratitis. Use 2 drops 4 times a day. The model is 32% confident.")
    assert out.startswith("The photo shows possible signs of fungal keratitis")
    assert "drops" not in out and "32%" in out


def test_offline_mode_when_no_credentials(monkeypatch):
    monkeypatch.setenv("OCULENS_ASSISTANT", "offline")
    r = chat.Reply("What is trachoma?", [], None)
    text = "".join(r)
    assert r.source == "offline" and "Chlamydia trachomatis" in text and "Offline" in r.note


class _FakeStream:
    def __init__(self, chunks, stop="end_turn"):
        self.chunks, self.stop = chunks, stop

    def __enter__(self):
        self.text_stream = iter(self.chunks)
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return types.SimpleNamespace(stop_reason=self.stop, model="claude-opus-5-5")


def _fake_client(chunks, seen):
    def stream(**kw):
        seen.update(kw)
        return _FakeStream(chunks)
    return types.SimpleNamespace(beta=types.SimpleNamespace(messages=types.SimpleNamespace(stream=stream)))


def test_claude_path_streams_grounded_request(monkeypatch):
    import anthropic
    seen = {}
    monkeypatch.delenv("OCULENS_ASSISTANT", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(anthropic, "Anthropic", lambda: _fake_client(["You have fungal ", "keratitis signs."], seen))
    r = chat.Reply("What does this mean?", [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "Hello"}],
                   FACTS, language="kn", audience="Clinician")
    streamed = "".join(r)
    assert r.source == "claude" and streamed == "You have fungal keratitis signs."
    assert r.text.startswith("The photo shows possible signs of fungal keratitis")   # guardrail on the final text
    assert seen["model"] == "claude-opus-5-5" and seen["fallbacks"] == "default"
    assert seen["system"][0]["cache_control"] == {"type": "ephemeral"}
    last = seen["messages"][-1]["content"]
    assert "Language: Kannada" in last and "Fungal keratitis" in last and "Answer style: Clinician" in last


def test_claude_failure_falls_back_offline(monkeypatch):
    import anthropic

    def boom():
        raise RuntimeError("network down")
    monkeypatch.delenv("OCULENS_ASSISTANT", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(anthropic, "Anthropic", boom)
    r = chat.Reply("What is trachoma?", [], None)
    text = "".join(r)
    assert r.source == "offline" and "Chlamydia" in text and "Claude unavailable" in r.note


def test_doctor_treatment_notes_only_for_clinicians():
    f = dict(FACTS, doctor_notes="Dr. X: fortified topical antibiotics; review 48h")
    patient = chat.offline_answer("What does this result mean?", f, "Patient-friendly")
    clinician = chat.offline_answer("What does this result mean?", f, "Clinician")
    assert "antibiotics" not in patient and "doctor has already reviewed" in patient
    assert "antibiotics" in clinician
    assert "never repeat treatment" in chat.SYSTEM_PROMPT


# ---- answers every patient question: FAQ coverage (offline) and the broadened Claude instructions
@pytest.mark.parametrize("question,expected", [
    ("Will my family catch this?", "do not spread"), ("can i put honey in my eye", "home remedies"),
    ("which drops should I buy", "can't recommend medicines"), ("Can I wear my contacts?", "contact lenses out"),
    ("is it ok to drive to the hospital", "Do not drive"), ("I am pregnant, is treatment safe?", "pregnant"),
    ("sand went into my eye", "Don't rub"), ("I have sugar, does it affect eyes", "Diabetes"),
    ("what food is good for eyes", "balanced diet"), ("is trachoma curable", "Active trachoma is treated"),
    ("will I need an operation", "Surgery"), ("is my data shared", "stored only on the clinic computer"),
    ("How much will treatment cost?", "free"), ("what will the doctor do at the hospital", "slit lamp"),
    ("who are you?", "OcuLens Assistant"), ("Does oculens check for cataract?", "does not screen for cataract"),
])
def test_offline_answers_common_patient_questions(question, expected):
    assert expected.lower() in chat.offline_answer(question, None).lower()


@pytest.mark.parametrize("question", ["What is the capital of France?", "tell me a joke", "how do I cook rice"])
def test_off_topic_gets_honest_fallback_not_a_random_answer(question):
    ans = chat.offline_answer(question, None)
    assert ans.startswith("Thank you for asking") and "online assistant" in ans


@pytest.mark.parametrize("text", ["I see flashes of light", "a curtain came over my vision", "suddenly lots of floaters"])
def test_retinal_detachment_signs_are_red_flags(text):
    assert chat.red_flag(text)


def test_claude_instructed_to_answer_every_question_safely():
    p = chat.SYSTEM_PROMPT
    assert "Answer every question" in p and "never invent" in p and "Never name medicines" in p


# ---- realistic answers, Indian languages and the spoken welcome (25 Nov)
@pytest.mark.parametrize("question,expect", [
    ("i have eye allergi since from 15 years what which i follow?", "Long-standing eye allergy"),
    ("hi, my eyes are itching since morning", "Itchy eyes"),
    ("can i eat non veg with eye infection", "no special food to avoid"),
    ("baby eye watering", "blocked tear duct"),
    ("my eyes burn when i use AC", "Burning eyes"),
    ("is trachoma curable", "Active trachoma is treated"),
])
def test_realistic_patient_questions(question, expect):
    assert expect in chat.offline_answer(question, None)


def test_unclear_eye_question_gets_a_clarifying_question_not_a_refusal():
    ans = chat.offline_answer("my eye feels strange", None)
    assert "tell me a little more" in ans and "since when" in ans


def test_other_body_part_goes_to_a_general_doctor():
    ans = chat.offline_answer("my knee hurts", None)
    assert "general doctor" in ans


def test_offline_answers_in_indian_languages():
    facts = {"case_id": 5, "screening": "Infectious keratitis", "eye": "", "most_likely": "Fungal keratitis",
             "confidence": 0.49, "prediction_set": ["A", "B"], "referral_advised": True, "referral_hospitals": []}
    assert "REFER" in chat.offline_answer("what does this result mean", facts, lang="hi")
    assert "केस #5" in chat.offline_answer("what does this result mean", facts, lang="hi")
    assert chat.offline_answer("hello", None, lang="ta").startswith("வணக்கம்")
    # a question spoken in Kannada about a chemical splash gets the Kannada emergency advice
    assert chat.offline_answer("ಕಣ್ಣಿಗೆ ರಾಸಾಯನಿಕ ಬಿದ್ದಿದೆ", None, lang="kn").startswith("ಇದು ಕಣ್ಣಿನ ತುರ್ತು")
    # knowledge-base answers come from the pre-translated table (translations.json); English only as a fallback
    ans = chat.offline_answer("मेरी आँख में खुजली और एलर्जी है", None, lang="hi")
    assert "Itchy eyes" not in ans and re.search(r"[ऀ-ॿ]", ans)


def test_chat_safe_keeps_list_line_breaks():
    from oculens.assistant.guardrails import chat_safe
    txt = "What helps:\n- Don't rub.\n- Use a cool compress."
    assert chat_safe(txt) == txt


def test_welcome_text_uses_live_numbers_and_language():
    import datetime as dt
    from oculens.assistant.i18n import welcome_text
    u = {"name": "Dr. Test", "role": "doctor"}
    st = {"pending": 3, "referred": 7, "patients": 4, "cases": 10}
    en = welcome_text(u, st, "en", dt.datetime(2026, 11, 25, 9))
    assert en.startswith("Good morning, Dr. Test") and "3 screenings waiting" in en and "7 patients" in en
    assert "समीक्षा" in welcome_text(u, st, "hi") and "Users page" in welcome_text({"name": "A", "role": "admin"}, st)
