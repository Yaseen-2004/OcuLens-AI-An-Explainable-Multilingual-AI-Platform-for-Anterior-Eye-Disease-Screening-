# Part N - Statistical rigor: bootstrap 95% confidence intervals (23 Nov 2026).
import os as _oN, json as _jN

_CIP = _oN.path.join(r"D:\Capston_Project", "experiments", "ci", "ci.json")


def _fmt(d):
    if not d:
        return "n/a"
    pt = d.get("point")
    ci = d.get("ci95") or []
    if pt is None:
        return "n/a"
    return f"{pt:.3f} [{ci[0]:.3f}, {ci[1]:.3f}]" if len(ci) == 2 else f"{pt:.3f}"


if _oN.path.exists(_CIP):
    _ci = _jN.load(open(_CIP, encoding="utf-8"))
    s.append(PageBreak())
    s += [p("Part N - Statistical rigor: 95% confidence intervals", H1),
          p("Point metrics on small test sets can mislead. Each model below was re-run on its held-out test split and every "
            "headline metric was bootstrapped (1,000 resamples with replacement); the 95% interval is the 2.5-97.5 percentile "
            "range. Overlapping intervals between variants mean a difference is not yet statistically meaningful - important "
            "context when comparing, e.g., the RQ1 anatomy variants. Computed on the project PC (CPU).")]
    _rows = [["Model", "Test n", "Balanced accuracy [95% CI]", "Macro F1 [95% CI]", "AUROC [95% CI]"]]
    for _task, _r in _ci.items():
        _rows.append([_r.get("label", _task), str(_r.get("n", "")),
                      _fmt(_r.get("balanced_accuracy")), _fmt(_r.get("macro_f1")), _fmt(_r.get("auroc"))])
    s.append(table(_rows, [4.6*cm, 1.6*cm, 4.2*cm, 3.3*cm, 3.3*cm]))
    s.append(p("Read: the balanced-accuracy interval width scales with test-set size - trachoma (n=237) and keratitis (n=429) "
               "give tighter bounds than ulcer pattern (n=102). These are first baselines on public data, not clinical claims."))
