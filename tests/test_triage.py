from oculens.triage.engine import TriageEngine

engine = TriageEngine()


def test_safety_override_wins_over_normal_image():
    r = engine.decide([{"region": "whole_eye", "condition": "Normal"}], {"pain": True, "sudden_vision_loss": True})
    assert r.level == "urgent"


def test_post_surgery_redness_is_urgent():
    assert engine.decide([], {"recent_eye_surgery": True, "redness": True}).level == "urgent"


def test_uncertain_result_is_referred_not_normal():
    r = engine.decide([{"region": "cornea", "condition": "other_corneal_abnormalities", "refer": True}])
    assert r.level == "refer"


def test_infection_finding_is_urgent():
    assert engine.decide([{"region": "cornea", "condition": "FK"}]).level == "urgent"


def test_cataract_is_soon():
    assert engine.decide([{"region": "whole_eye", "condition": "Cataract"}]).level == "soon"


def test_normal_without_symptoms_is_routine():
    assert engine.decide([{"region": "whole_eye", "condition": "Normal"}]).level == "routine"


def test_symptoms_without_findings_need_review():
    assert engine.decide([], {"blurred_vision": True}).level == "soon"


def test_unreliable_explanation_triggers_review():
    r = engine.decide([{"region": "whole_eye", "condition": "Cataract", "explanation_reliable": False}])
    assert r.level == "refer"
