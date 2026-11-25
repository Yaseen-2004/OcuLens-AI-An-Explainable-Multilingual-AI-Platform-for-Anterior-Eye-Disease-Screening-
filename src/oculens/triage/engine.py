"""Clinical decision engine (Step 8): image findings + symptoms -> routine / soon / urgent / refer.

Order of precedence:
  1. safety overrides from symptoms (always win)
  2. uncertain image result -> refer (never report 'normal' when unsure)
  3. most severe matching image finding
  4. symptoms without a finding -> soon
  5. otherwise routine
"""
from __future__ import annotations

from dataclasses import dataclass, field

from oculens.config import CONFIG_DIR, load_yaml

SEVERITY = {"routine": 0, "soon": 1, "refer": 2, "urgent": 3}


@dataclass
class TriageResult:
    level: str
    advice: str
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"level": self.level, "advice": self.advice, "reasons": self.reasons}


class TriageEngine:
    def __init__(self, rules: dict | None = None):
        self.rules = rules or load_yaml(CONFIG_DIR / "triage_rules.yaml")

    def _symptom_overrides(self, symptoms: dict) -> list[tuple[str, str]]:
        hits = []
        present = {k for k, v in symptoms.items() if v}
        for rule in self.rules.get("safety_overrides", []):
            all_ok = set(rule.get("when_all", [])) <= present
            any_list = rule.get("when_any", [])
            any_ok = not any_list or bool(present & set(any_list))
            if all_ok and any_ok and (rule.get("when_all") or any_list):
                hits.append((rule["level"], f"safety rule: {rule['name']}"))
        return hits

    def _finding_level(self, finding: dict) -> str | None:
        if str(finding.get("condition")) in map(str, self.rules.get("normal_labels", [])):
            return None
        for rule in self.rules.get("finding_rules", []):
            if rule["region"] == finding.get("region") and str(rule["condition"]) == str(finding.get("condition")):
                return rule["level"]
        return "soon"  # unknown abnormal finding: be conservative

    def decide(self, findings: list[dict], symptoms: dict | None = None) -> TriageResult:
        symptoms = symptoms or {}
        candidates: list[tuple[str, str]] = self._symptom_overrides(symptoms)

        for f in findings:
            if f.get("refer") or f.get("uncertainty") == "high":
                candidates.append(("refer", f"uncertain result for {f.get('region')}"))
                continue
            if f.get("explanation_reliable") is False:
                candidates.append(("refer", f"explanation not on {f.get('region')} - needs doctor review"))
            lvl = self._finding_level(f)
            if lvl:
                candidates.append((lvl, f"possible {f.get('condition')} ({f.get('region')})"))

        if not candidates:
            review = [s for s in self.rules.get("symptoms_needing_review", []) if symptoms.get(s)]
            if review:
                candidates.append(("soon", "symptoms reported: " + ", ".join(review)))

        if not candidates:
            return TriageResult("routine", self.rules["levels"]["routine"], ["no significant finding"])
        level = max(candidates, key=lambda c: SEVERITY[c[0]])[0]
        return TriageResult(level, self.rules["levels"][level], [r for _, r in candidates])
