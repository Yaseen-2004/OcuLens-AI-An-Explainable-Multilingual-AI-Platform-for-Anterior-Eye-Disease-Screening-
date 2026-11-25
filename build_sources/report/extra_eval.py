# Part M - Evaluation: deeper metrics, calibration, referral curves, subgroup fairness (23 Nov 2026).
import os as _oM, json as _jM, math as _mM
from reportlab.graphics.charts.lineplots import LinePlot as _LP
from reportlab.graphics.shapes import Drawing as _Dw, String as _Str

_EF = _oM.path.join(r"D:\Capston_Project", "experiments", "eval_final")
_CV = _oM.path.join(r"D:\Capston_Project", "experiments", "curves")

def _ld(d, n):
    fp = _oM.path.join(d, n)
    try:
        return _jM.load(open(fp, encoding="utf-8")) if _oM.path.exists(fp) else None
    except Exception:
        return None

def _n3(v):
    try:
        if v is None or (isinstance(v, float) and _mM.isnan(v)):
            return "n/a"
        return f"{float(v):.3f}"
    except Exception:
        return "n/a"

s.append(PageBreak())
s += [p("Part M - Evaluation: calibration, referral and fairness", H1),
      p("This part goes beyond headline accuracy. On 23 Nov 2026 every trained model was re-evaluated on its held-out "
        "test split on the 0034 GPU, writing the full metric set (accuracy, calibration error, conformal coverage, the "
        "referral/triage effect and subgroup breakdowns). Reliability and referral curves were computed for four key "
        "models. Numbers are read straight from experiments/eval_final and experiments/curves. "
        "These remain first baselines on public data, not clinical performance claims.")]

_MAP = [
    ("eval_keratitis_image.json",        "keratitis",     "image (baseline)"),
    ("eval_keratitis_mask_input.json",   "keratitis",     "mask_input"),
    ("eval_keratitis_region_crop.json",  "keratitis",     "region_crop"),
    ("eval_keratitis_synthetic.json",    "keratitis",     "+ diffusion (RQ2a)"),
    ("eval_keratitis_harmonized.json",   "keratitis",     "+ CycleGAN (RQ2b)"),
    ("eval_keratitis_ensemble.json",     "keratitis",     "5-model ensemble (RQ3)"),
    ("eval_ulcer_image.json",            "ulcer_pattern", "image (baseline)"),
    ("eval_ulcer_mask_input.json",       "ulcer_pattern", "mask_input"),
    ("eval_ulcer_region_crop.json",      "ulcer_pattern", "region_crop"),
    ("eval_ulcer_multitask.json",        "ulcer_pattern", "multitask"),
    ("eval_trachoma_image.json",         "trachoma_tf",   "image (baseline)"),
]
s += [p("M1. Full metrics with calibration, conformal coverage and referral", H2)]
_rows = [["Task", "Variant", "Bal.acc", "AUROC", "ECE", "Conf.cov", "Set size", "Referral", "Acc kept"]]
for _nm, _tk, _vr in _MAP:
    _d = _ld(_EF, _nm)
    if not _d:
        continue
    _o = _d.get("overall", {}); _c = _d.get("conformal", {}); _r = _d.get("referral", {})
    _rows.append([_tk, _vr, _n3(_o.get("balanced_accuracy")), _n3(_o.get("auroc_macro_ovr", _o.get("auroc"))),
                  _n3(_o.get("ece")), _n3(_c.get("coverage")), _n3(_c.get("mean_set_size")),
                  _n3(_r.get("referral_rate")), _n3(_r.get("accuracy_kept"))])
s.append(table(_rows, [2.3*cm, 3.5*cm, 1.5*cm, 1.4*cm, 1.2*cm, 1.5*cm, 1.4*cm, 1.5*cm, 1.4*cm]))
s.append(p("Conf.cov = empirical coverage of the 95 percent conformal prediction sets (should be near 0.95); "
           "Set size = mean number of classes kept (1 = confident single label); Referral = fraction sent for review "
           "at the conformal threshold; Acc kept = accuracy on the cases the model keeps. A high set size / full "
           "referral on keratitis reflects honest uncertainty on a hard 4-class problem."))

def _chart(series, xmax, ymax, xlabel, colors_hex, title):
    d = _Dw(470, 215)
    lp = _LP(); lp.x, lp.y, lp.width, lp.height = 40, 32, 400, 150
    lp.data = [ser[1] for ser in series]
    for i, _ in enumerate(series):
        lp.lines[i].strokeColor = colors.HexColor(colors_hex[i]); lp.lines[i].strokeWidth = 1.8
    lp.xValueAxis.valueMin, lp.xValueAxis.valueMax = 0, xmax
    lp.yValueAxis.valueMin, lp.yValueAxis.valueMax = 0, ymax
    lp.xValueAxis.labels.fontSize = lp.yValueAxis.labels.fontSize = 7
    d.add(lp)
    d.add(_Str(230, 198, title, fontSize=10, fontName="Helvetica-Bold", textAnchor="middle"))
    d.add(_Str(230, 6, xlabel, fontSize=8, textAnchor="middle"))
    for i, ser in enumerate(series):
        d.add(_Str(70 + i*150, 188, ser[0], fontSize=7, fillColor=colors.HexColor(colors_hex[i])))
    return d

_CURVES = [("keratitis_baseline.json", "Keratitis baseline"), ("keratitis_ensemble.json", "Keratitis ensemble"),
           ("keratitis_harmonized.json", "Keratitis harmonized"), ("ulcer_region_crop.json", "Ulcer region-crop")]
_cl = [c for c in _CURVES if _ld(_CV, c[0])]
if _cl:
    s += [p("M2. Calibration (reliability): predicted confidence vs. actual accuracy", H2)]
    for _f, _lab in _cl:
        _d = _ld(_CV, _f); _cb = _d.get("calibration", [])
        if not _cb:
            continue
        _pts = [(b["conf"], b["acc"]) for b in _cb]
        s.append(_chart([("model", _pts), ("perfect", [(0, 0), (1, 1)])], 1.0, 1.0, "confidence",
                        ["#0F7C80", "#B0B0B0"], f"{_lab} (ECE {_n3(_d.get('ece'))})"))
        s.append(Spacer(1, 6))
    s.append(p("A well-calibrated model sits on the grey diagonal (confidence = accuracy). Points above the line are "
               "under-confident, below the line over-confident; the summed gap is the ECE."))

if _cl:
    s += [p("M3. Referral / triage curves: send the least-confident cases for review", H2)]
    for _f, _lab in _cl:
        _d = _ld(_CV, _f); _rf = _d.get("referral", [])
        if not _rf:
            continue
        _acc = [(r["referral_rate"], r["accuracy_kept"]) for r in _rf if r["accuracy_kept"] == r["accuracy_kept"]]
        _mis = [(r["referral_rate"], r["missed_rate"]) for r in _rf if r.get("missed_rate") == r.get("missed_rate")]
        series = [("acc on kept", _acc)]; cols = ["#0F7C80"]
        if _mis:
            series.append(("missed-sick rate", _mis)); cols.append("#C0392B")
        s.append(_chart(series, 1.0, 1.0, "referral rate", cols, f"{_lab}: referral trade-off"))
        s.append(Spacer(1, 6))
    s.append(p("As more low-confidence cases are referred (x to the right), accuracy on the kept cases should rise and "
               "the missed-disease rate should fall - the safety argument for the referral gate."))

s += [p("M4. Subgroup fairness", H2),
      p("Balanced accuracy within subgroups, from the per-group breakdowns in the eval files. A large gap between "
        "groups flags a fairness risk to watch as real hospital data arrives.")]
for _nm, _tk, _vr in [("eval_keratitis_image.json", "keratitis", "baseline"),
                      ("eval_ulcer_region_crop.json", "ulcer_pattern", "region_crop")]:
    _d = _ld(_EF, _nm)
    if not _d:
        continue
    _sg = _d.get("subgroups", {})
    if not _sg:
        continue
    _rows = [["Group", "Value", "n", "Balanced acc", "Macro F1"]]
    for _g, _vals in _sg.items():
        for _v, _m in _vals.items():
            _rows.append([_g, _v, str(_m["n"]), _n3(_m["balanced_accuracy"]), _n3(_m["macro_f1"])])
    if len(_rows) > 1:
        s += [p(f"{_tk} ({_vr})", H2)]
        s.append(table(_rows, [3.6*cm, 3.6*cm, 2.0*cm, 3.6*cm, 3.6*cm]))

_b = _ld(_EF, "eval_keratitis_image.json"); _h = _ld(_EF, "eval_keratitis_harmonized.json")
if _b and _h:
    s += [p("M5. Domain shift and harmonisation (RQ2b)", H2),
          p("The keratitis test split is drawn from a single site, so a pure train-one-site / test-the-other split was "
            "not possible here. Instead, robustness to appearance shift was probed with CycleGAN harmonisation (training "
            "images restyled toward the second hospital look, using its images only as an unlabelled style target). "
            f"Baseline balanced accuracy {_n3(_b['overall'].get('balanced_accuracy'))} "
            f"(AUROC {_n3(_b['overall'].get('auroc_macro_ovr'))}) vs. harmonised "
            f"{_n3(_h['overall'].get('balanced_accuracy'))} (AUROC {_n3(_h['overall'].get('auroc_macro_ovr'))}). "
            "A true cross-site test needs the held-out hospital data listed in the next-steps section.")]
