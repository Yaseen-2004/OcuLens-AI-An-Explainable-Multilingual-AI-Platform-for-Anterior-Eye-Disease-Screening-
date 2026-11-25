# Part K4 - Extending diffusion augmentation to the other tasks (24 Nov 2026, afternoon).
import os as _osK4, json as _jsK4

_EVF = _osK4.path.join(r"D:\Capston_Project", "experiments", "eval_final")
_RUN = _osK4.path.join(r"D:\Capston_Project", "experiments", "runs")


def _k4load(path, key):
    try:
        return _jsK4.load(open(path, encoding="utf-8"))[key]
    except Exception:
        return None


def _k4f(v):
    try:
        return f"{float(v):.3f}"
    except Exception:
        return "n/a"


_ui = _k4load(_osK4.path.join(_EVF, "eval_ulcer_image.json"), "overall")
_um = _k4load(_osK4.path.join(_EVF, "eval_ulcer_mask_input.json"), "overall")
_us = _k4load(_osK4.path.join(_RUN, "eval_ulcer_pattern_syn.json"), "test")

if _us:
    s.append(PageBreak())
    s += [p("Part K4 - Does diffusion augmentation help the other tasks?", H1),
          p("Diffusion augmentation was the keratitis winner (Part K3), so the same recipe - train a class-conditional "
            "DDPM on the training split only, generate synthetic images for each class, retrain the classifier - was "
            "run for the other two tasks, plus a scaled-up keratitis run with twice as many synthetic images. The three "
            "runs were started in parallel on the team DGX accounts 0034, 0063 and 3007.")]
    s += [p("K4.1 Ulcer pattern (completed, account 0063)", H2)]
    _rows = [["Ulcer model", "Bal. acc", "AUROC", "ECE"]]
    for _lab, _o in [("Image baseline", _ui), ("mask_input (anatomy, RQ1) - current best", _um),
                     ("Image + diffusion synthetic (900 images)", _us)]:
        if _o:
            _rows.append([_lab, _k4f(_o.get("balanced_accuracy")),
                          _k4f(_o.get("auroc_macro_ovr", _o.get("auroc"))), _k4f(_o.get("ece"))])
    s.append(table(_rows, [8.2*cm, 2.6*cm, 2.6*cm, 2.6*cm]))
    s.append(p("Result: diffusion augmentation lifts the plain-image ulcer model from 0.632 to 0.646 balanced accuracy "
               "and gives the highest ulcer AUROC seen (0.871) with better calibration, but it does <b>not</b> beat the "
               "anatomy-aware mask_input model (0.678). For ulcer pattern, telling the model where the cornea is matters "
               "more than extra synthetic data, so mask_input remains the best ulcer model (the portal currently runs the image-only ulcer model)."))
    _tr0 = _k4load(_osK4.path.join(_EVF, "eval_trachoma_image.json"), "overall")
    _trs = _k4load(_osK4.path.join(_RUN, "eval_trachoma_tf_syn.json"), "overall")
    _kx2 = _k4load(_osK4.path.join(_RUN, "eval_keratitis_syn_x2.json"), "overall")
    s += [p("K4.2 Trachoma and the larger keratitis run (completed 25 Nov)", H2),
          p("Both runs were stopped on 24 Nov when GPU access was lost and resumed on 25 Nov from their saved epoch "
            "(trachoma from epoch 51, keratitis from epoch 48), reusing the synthetic images already generated.")]
    _r2 = [["Model", "Bal. acc", "AUROC", "ECE"]]
    for _lab, _o in [("Trachoma baseline (in portal)", _tr0), ("Trachoma + 600 diffusion images", _trs),
                     ("Keratitis + 1,200 diffusion images (300 per class, in portal)", {"balanced_accuracy": 0.488, "auroc_macro_ovr": 0.771, "ece": 0.047}),
                     ("Keratitis + 2,400 diffusion images (600 per class)", _kx2)]:
        if _o:
            _r2.append([_lab, _k4f(_o.get("balanced_accuracy")), _k4f(_o.get("auroc_macro_ovr", _o.get("auroc"))), _k4f(_o.get("ece"))])
    s.append(table(_r2, [8.2*cm, 2.6*cm, 2.6*cm, 2.6*cm]))
    s.append(p("Result: diffusion images did not help trachoma, an already well-handled two-class task (0.808 vs 0.814, "
               "slightly worse calibration), so the baseline stays. Doubling the keratitis synthetic set made things worse "
               "(0.388 vs 0.488): with 2,400 rough 64-pixel images against 809 real ones, the synthetic data swamped the real "
               "data. Synthetic images help most where real data is scarce, and only in moderation."))
