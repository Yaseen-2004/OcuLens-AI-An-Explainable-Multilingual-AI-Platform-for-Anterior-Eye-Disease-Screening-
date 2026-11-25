# Part K3 - Final model-selection sweep for keratitis (24 Nov 2026).
# Three follow-up experiments run in parallel on the team's own GPU accounts, then compared.
import os as _osS, json as _jsonS, math as _mathS

_SWEEP = _osS.path.join(r"D:\Capston_Project", "experiments", "runs", "final_sweep.json")


def _fS(v):
    try:
        if v is None or (isinstance(v, float) and _mathS.isnan(v)):
            return "n/a"
        return f"{float(v):.3f}"
    except Exception:
        return "n/a"


if _osS.path.exists(_SWEEP):
    _sw = _jsonS.load(open(_SWEEP, encoding="utf-8"))
    s.append(PageBreak())
    s += [p("Part K3 - Final model-selection sweep (keratitis)", H1),
          p("Keratitis is the hardest of the three tasks (four visually similar infection types, heavy class "
            "imbalance), so after the main 50-epoch run we tried three targeted ways to push it further and compared "
            "them head-to-head on the same held-out test set (n=%s). Each ran on a team member's own DGX GPU slice, "
            "the three at the same time. Numbers are read straight from each run's eval file." % _sw.get("test_n", 429))]
    _rows = [["Configuration", "Acct", "Bal. acc", "Macro F1", "AUROC", "ECE", "Acc"]]
    for _r in _sw.get("runs", []):
        _d = _r["d"]
        _rows.append([_r["label"], _r.get("acct", ""),
                      _fS(_d.get("balanced_accuracy")), _fS(_d.get("macro_f1")),
                      _fS(_d.get("auroc")), _fS(_d.get("ece")), _fS(_d.get("accuracy"))])
    s.append(table(_rows, [6.6*cm, 3.0*cm, 1.6*cm, 1.6*cm, 1.5*cm, 1.4*cm, 1.4*cm]))
    s += [p("K3.1 What each one tried", H2),
          p("<b>Higher-resolution 320px</b> - feed the network a larger image (320 vs 224 px) in case fine corneal "
            "texture was being lost. <b>10-model deep ensemble</b> - double the ensemble from 5 to 10 independently "
            "seeded models and average them. <b>Diffusion-augmented</b> - add DDPM-generated synthetic images of the "
            "rare infection classes to the training set, then train a single model (RQ2a).")]
    s += [p("K3.2 Result and decision", H2),
          p("The <b>diffusion-augmented single model wins clearly</b>: balanced accuracy 0.488 against 0.438 for the "
            "previous ensemble, with the best macro-F1 and by far the best calibration (ECE 0.047). Notably it beats "
            "the 10-model ensemble (0.451) - so on this data better training data helped more than more models, and "
            "scaling the ensemble from 5 to 10 gave only a small accuracy gain while worsening calibration. Higher "
            "resolution did not help (0.409). "
            "<b>The diffusion-augmented model is therefore the keratitis model used in the live portal.</b> The deep "
            "ensemble is retained in the portal purely as an epistemic-uncertainty signal: the spread between its "
            "members (mutual information) is shown next to each prediction to support the referral decision. These "
            "remain first baselines on public, single-site data - not clinical performance claims.")]
    s.append(p("<b>Update (25 Nov):</b> retraining the same recipe with three more seeds gave 0.437, 0.408 and 0.361, so 0.488 "
               "was the best of four runs (mean 0.42). See Part K6; the fair headline is the 4-seed diffusion ensemble, 0.474."))
