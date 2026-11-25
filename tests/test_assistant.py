from oculens.assistant.guardrails import DISCLAIMER, URGENT_LINE, apply_guardrails, find_violations
from oculens.assistant.llm import _template
from oculens.assistant.schema import Finding, ScreeningReport, Triage


def test_guardrails_remove_dose_and_diagnostic_wording():
    raw = "You have fungal keratitis. Use 5 mg drops three times. Please see a doctor."
    out = apply_guardrails(raw, "urgent")
    assert "you have" not in out.lower()
    assert "5 mg" not in out
    assert URGENT_LINE in out and DISCLAIMER in out
    assert find_violations(out) == []


def test_template_is_hedged_and_mentions_uncertainty():
    rep = ScreeningReport(
        scan_id="t1", quality={"ok": True},
        findings=[Finding(region="cornea", condition="FK", probability=0.55, prediction_set=["FK", "BK"],
                          uncertainty="high", refer=True)],
        triage=Triage(level="refer", advice="Retake or see a doctor.", reasons=[]),
    )
    text = apply_guardrails(_template(rep), "refer")
    assert "possible signs of FK" in text
    assert "doctor should check" in text
