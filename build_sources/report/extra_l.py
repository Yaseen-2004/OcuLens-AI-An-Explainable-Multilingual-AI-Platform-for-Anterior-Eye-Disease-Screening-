import json as _json
import os as _os
import re as _re

from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.widgets.markers import makeMarker

_P = r"D:\Capston_Project"
_LOGS = _os.path.join(_P, "experiments", "logs")


def _epochs(path):
    rows = []
    if _os.path.exists(path):
        for line in open(path, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line.startswith('{"epoch"'):
                rows.append(_json.loads(line))
    return rows


s.append(PageBreak())
s += [p("Part L - Run logs", H1),
      p("Written 20 Nov 2026. This part copies the actual logs of every test, data-check and training run so far. "
        "The raw log files are kept in D:\\Capston_Project\\experiments\\logs and the run folders under experiments\\runs. "
        "No new runs were started to write this section.")]

# ------------------------------------------------------------------ L1 tests
s += [p("L1. Unit test runs", H2)]
s.append(table([
    ["Date", "Tests", "Result", "What changed"],
    ["18 Nov", "24", "24 passed", "First build of the package (quality, splits, triage, uncertainty, assistant, models)"],
    ["18 Nov", "30", "30 passed", "Follow-up module and doctor dashboard / API tests added"],
    ["19 Nov", "30", "30 passed", "Re-checked before starting the PC training queue"],
    ["20 Nov", "37", "37 passed", "Diffusion, CycleGAN, FID/TSTR, ensemble, referral, segmenter and Siamese tests added; two library warnings fixed"],
    ["22 Nov", "48", "48 passed", "RQ1 variants, aligned image+mask transforms, model rebuild per variant, dataset masks / severity labels / synthetic paths"],
], [1.8*cm, 1.5*cm, 2.4*cm, 11.3*cm]))
_pt = _os.path.join(_LOGS, "pytest_2026-11-20.log")
if _os.path.exists(_pt):
    s.append(p(f"Last recorded pytest output (experiments/logs/pytest_2026-11-20.log): <b>{open(_pt).read().strip()}</b>"))

# ------------------------------------------------------------------ L2 data checks
s += [p("L2. Data verification logs", H2)]
_rows = [["Archive / dataset", "Bytes", "Check", "Files extracted"]]
for _f in ("_verify_report.json", "_verify_report_round2.json"):
    _fp = _os.path.join(_P, "datasets", _f)
    if not _os.path.exists(_fp):
        continue
    for _k, _v in _json.load(open(_fp)).items():
        if _k == "keratitis_summary":
            continue
        _chk = []
        if "md5_ok" in _v:
            _chk.append("MD5 " + ("ok" if _v["md5_ok"] else "FAILED"))
        if "sha256_all_match" in _v:
            _chk.append("SHA-256 all files " + ("ok" if _v["sha256_all_match"] else "FAILED"))
        _chk.append("zip CRC " + ("ok" if not _v.get("zip_crc_bad_member") and not _v.get("crc_bad_member") else "FAILED"))
        _n = _v.get("extracted_files", _v.get("members_extracted", _v.get("files", "")))
        _rows.append([_k, f"{_v.get('zip_bytes', _v.get('bytes', 0)):,}", "; ".join(_chk), str(_n)])
_rows.append(["trachoma m.tar (round 3)", "3,537,444,864", "MD5 ok (checked in session)", "1,657"])
_rows.append(["slit-lamp time series zip (round 3)", "361,538", "MD5 ok (checked in session)", "60"])
s.append(table(_rows, [5.6*cm, 3.0*cm, 5.4*cm, 3.0*cm]))
s.append(p("Earlier failed attempts are not in these files: the first SUSTech-SYSU and Nuclear Cataract downloads were corrupted by an interrupted resume and were deleted (Part G4)."))

# ------------------------------------------------------------------ L3 training runs overview
s += [p("L3. Training runs", H2)]
_cpu = _epochs(_os.path.join(_LOGS, "cpu_keratitis_2026-11-19.log"))
_best = max(_cpu, key=lambda r: r["val_balanced_acc"]) if _cpu else None
s.append(table([
    ["Run", "Where", "Data", "Epochs", "Outcome"],
    ["18 Nov 11:39 smoke run", "PC CPU", "48 train / 12 val / 12 test images", "1 of 1", "Code check only: loop trained, calibrated, tested and saved (test n = 12, not a result)"],
    ["18 Nov DGX attempt 1", "H200 MIG slice", "809 / 135 / 429", "0", "Crashed: shared memory (/dev/shm) full; fixed"],
    ["18 Nov DGX attempt 2", "H200 MIG slice", "809 / 135 / 429", "1 of 30", "186 s per epoch; stopped to apply the speed fix"],
    ["18 Nov DGX attempt 3", "H200 MIG slice", "809 / 135 / 429", "3 of 30", "85-89 s per epoch; stopped for the 100-epoch restart; connection then lost"],
    ["18 Nov DGX 100-epoch run (found 23 Nov)", "H200 MIG slice", "809 / 135 / 429", "100 of 100", "Started despite the lost connection and finished at 14:26. Best validation balanced accuracy 0.586 at epoch 35; calibrated and tested: test balanced accuracy 0.422, AUROC 0.726 (details in Part K and L5b)"],
    ["18 Nov 20:16 PC run", "PC CPU", "809 / 135 / 429", "about 1 of 15", "About 6.5 min per epoch; stopped at your request"],
    ["19 Nov 14:26 PC queue", "PC CPU", "809 / 135 / 429",
     f"{len(_cpu)} of 15" if _cpu else "-",
     (f"Ended with the session before finishing. Best validation balanced accuracy {_best['val_balanced_acc']:.3f} at epoch {_best['epoch']} "
      "(checkpoint saved); test evaluation not run. Later queue jobs (ulcer, explainability, trachoma) never started.") if _best else "-"],
], [3.3*cm, 2.4*cm, 3.2*cm, 1.8*cm, 6.3*cm]))

# ------------------------------------------------------------------ L4 epoch-by-epoch, CPU run
if _cpu:
    s += [p("L4. Keratitis run on the PC, 19 Nov (epoch log)", H2)]
    s.append(table([["Epoch", "Train loss", "Val balanced acc.", "Seconds"]] +
                   [[str(r["epoch"]), f"{r['train_loss']:.3f}", f"{r['val_balanced_acc']:.3f}", f"{r['seconds']:.0f}"] for r in _cpu],
                   [2.5*cm, 3.5*cm, 4.0*cm, 3.0*cm]))
    s.append(Spacer(1, 6))
    _d = Drawing(480, 210)
    _lp = LinePlot()
    _lp.x, _lp.y, _lp.width, _lp.height = 45, 35, 330, 150
    _lp.data = [[(r["epoch"], r["val_balanced_acc"]) for r in _cpu], [(r["epoch"], min(r["train_loss"], 1.0)) for r in _cpu]]
    _lp.lines[0].strokeColor, _lp.lines[0].strokeWidth = colors.HexColor("#0F7C80"), 2
    _lp.lines[1].strokeColor, _lp.lines[1].strokeWidth = colors.HexColor("#E8A33D"), 2
    _lp.lines[0].symbol = makeMarker("FilledCircle")
    _lp.lines[1].symbol = makeMarker("FilledSquare")
    _lp.xValueAxis.valueMin, _lp.xValueAxis.valueMax, _lp.xValueAxis.valueStep = 1, len(_cpu), 1
    _lp.yValueAxis.valueMin, _lp.yValueAxis.valueMax, _lp.yValueAxis.valueStep = 0, 1.0, 0.2
    _lp.xValueAxis.labels.fontSize = _lp.yValueAxis.labels.fontSize = 7
    _d.add(_lp)
    _lg = Legend()
    _lg.x, _lg.y, _lg.fontSize, _lg.alignment = 385, 160, 7, "right"
    _lg.colorNamePairs = [(colors.HexColor("#0F7C80"), "val balanced accuracy"), (colors.HexColor("#E8A33D"), "train loss (capped at 1.0)")]
    _d.add(_lg)
    _d.add(String(210, 10, "epoch", fontSize=8, textAnchor="middle"))
    s.append(_d)
    s.append(p("<b>Reading the log:</b> training loss falls steadily (2.16 to 0.12), while validation balanced accuracy peaks early "
               f"({_best['val_balanced_acc']:.3f} at epoch {_best['epoch']}) and then drifts down - the model starts to overfit the 809 training images. "
               "Validation has only 135 images (9 fungal), so single-epoch values are noisy. Epoch 4 was slow (660 s) because the PC was busy. "
               "Next steps when training is allowed: stronger augmentation or early stopping, and the test-set evaluation with "
               "python -m oculens.training.evaluate --task keratitis on the saved checkpoint."))

# ------------------------------------------------------------------ L5 DGX epoch log
_dg = _os.path.join(_LOGS, "dgx_training_2026-11-18.log")
if _os.path.exists(_dg):
    s += [p("L5. NVIDIA DGX log, 18 Nov", H2),
          Preformatted(open(_dg, encoding="utf-8").read().strip(), ParagraphStyle("dgxlog", fontName="Courier", fontSize=6.2, leading=7.6))]

# ------------------------------------------------------------------ L5b DGX 100-epoch run
_dgx = _epochs(_os.path.join(_LOGS, "dgx_trainkerat_100ep_2026-11-18.log"))
if _dgx:
    _bd = max(_dgx, key=lambda r: r["val_balanced_acc"])
    s += [p("L5b. NVIDIA DGX 100-epoch keratitis run, 18 Nov", H2),
          p("This run was thought lost when the SSH connection dropped during the restart. On 23 Nov the server was reachable "
            "again and the log showed it had run all 100 epochs (about 85 s each, roughly 2.4 hours). The log, result file and "
            "checkpoint were downloaded to the PC (experiments/logs/dgx_trainkerat_100ep_2026-11-18.log, "
            "models/checkpoints/dgx/keratitis_efficientnet_b0_100ep.pt).")]
    _d2 = Drawing(480, 200)
    _lp2 = LinePlot()
    _lp2.x, _lp2.y, _lp2.width, _lp2.height = 45, 30, 330, 150
    _lp2.data = [[(r["epoch"], r["val_balanced_acc"]) for r in _dgx], [(r["epoch"], min(r["train_loss"], 1.0)) for r in _dgx]]
    _lp2.lines[0].strokeColor, _lp2.lines[0].strokeWidth = colors.HexColor("#0F7C80"), 1.5
    _lp2.lines[1].strokeColor, _lp2.lines[1].strokeWidth = colors.HexColor("#E8A33D"), 1.5
    _lp2.xValueAxis.valueMin, _lp2.xValueAxis.valueMax, _lp2.xValueAxis.valueStep = 0, 100, 10
    _lp2.yValueAxis.valueMin, _lp2.yValueAxis.valueMax, _lp2.yValueAxis.valueStep = 0, 1.0, 0.2
    _lp2.xValueAxis.labels.fontSize = _lp2.yValueAxis.labels.fontSize = 7
    _d2.add(_lp2)
    _lg2 = Legend()
    _lg2.x, _lg2.y, _lg2.fontSize, _lg2.alignment = 385, 150, 7, "right"
    _lg2.colorNamePairs = [(colors.HexColor("#0F7C80"), "val balanced accuracy"), (colors.HexColor("#E8A33D"), "train loss (capped at 1.0)")]
    _d2.add(_lg2)
    _d2.add(String(210, 8, "epoch", fontSize=8, textAnchor="middle"))
    s.append(_d2)
    s.append(p(f"<b>Reading the log:</b> training loss falls to almost zero, but validation balanced accuracy peaks at "
               f"{_bd['val_balanced_acc']:.3f} (epoch {_bd['epoch']}) and then hovers around 0.49: after about 35 epochs the model only "
               "memorises the 809 training images. This is why early stopping (patience 6) is now on by default. "
               "On the other hospital's test images, fungal keratitis was almost never recognised (1 of 20) and herpes keratitis "
               "only about one in three - the main weaknesses to work on (more fungal examples, synthetic rare-class images, "
               "cross-hospital harmonisation)."))

# ------------------------------------------------------------------ L6 dry run of every training path
_dr = _os.path.join(_LOGS, "dryrun_summary.log")
if _os.path.exists(_dr):
    _lines = [l.rstrip() for l in open(_dr, encoding="utf-8") if l.strip()]
    _steps = [l for l in _lines if not l.startswith("#")]
    _ok = sum(1 for l in _steps if "exit=0" in l)
    s += [p("L6. Dry run of every training path, 22 Nov", H2),
          p(f"Each training and evaluation script ran once for 1 epoch on a few real images (scripts/dry_run_all.sh), "
            f"to prove the code works end to end before real training. <b>{_ok} of {len(_steps)} steps passed</b>, one of them (ONNX export) only after a fix. "
            "The numbers these runs produce are meaningless (24 training images, 1 epoch). All outputs went to "
            "experiments/dryrun; the real checkpoint and data folders were checked afterwards and are unchanged."),
          Preformatted("\n".join(_lines), ParagraphStyle("drlog", fontName="Courier", fontSize=7, leading=8.6))]
    s.append(table([
        ["Step", "What it proved"],
        ["classifier_image / classifier_resume", "Baseline training, calibration and test; --resume continued at epoch 2 from the saved state"],
        ["classifier_mask_input / region_crop / multitask", "All three RQ1 variants train; SUSTech cornea masks found for every image (0 missing)"],
        ["classifier_ensemble_s1", "Seeded ensemble member (trachoma task) trains and saves under its own name"],
        ["evaluate_keratitis", "Test evaluation with conformal coverage, referral effect and subgroups (429 test images)"],
        ["explain_mask_input", "Explanation metrics on a 4-channel model with ulcer masks"],
        ["unet_cornea / predict_masks", "U-Net trains on cornea masks; predicted masks are written for keratitis images"],
        ["ddpm / classifier_synthetic", "Diffusion model trains and samples; 8 synthetic images joined the training split only"],
        ["cyclegan", "Harmoniser trains ZEH to AGEH, records that test-site images were used, translates training images"],
        ["make_dry_pairs / siamese_change", "Siamese change model trains on scan pairs (labels were fake, code check only)"],
        ["export_onnx", "First attempt failed (new PyTorch exporter needs onnxscript); fixed by using the classic exporter. ONNX Runtime about 19-27 ms per image vs 96-124 ms in PyTorch on this CPU; outputs match (difference under 1e-5)"],
        ["pipeline_end_to_end", "The app pipeline runs with image-only, mask-input and multitask models plus the U-Net, giving triage, prediction sets and heatmaps"],
    ], [5.4*cm, 11.6*cm]))

# ------------------------------------------------------------------ L7 files
s += [p("L7. Where the logs are", H2)]
s.append(table([
    ["File", "Contents"],
    ["experiments/logs/cpu_keratitis_2026-11-19.log", "Epoch log of the 19 Nov PC keratitis run (13 epochs)"],
    ["experiments/logs/dgx_training_2026-11-18.log", "DGX attempts 1-3, copied from the session output"],
    ["experiments/logs/pytest_2026-11-20.log", "Latest unit-test summary"],
    ["experiments/runs/keratitis_efficientnet_b0_20261118-113951/result.json", "Smoke run result (48 images)"],
    ["models/checkpoints/keratitis_efficientnet_b0.pt", "Best checkpoint of the 19 Nov run (epoch 5); not yet calibrated or tested"],
    ["datasets/_verify_report.json, _verify_report_round2.json", "Hash and integrity results for the downloaded datasets"],
    ["experiments/logs/dryrun_*.log, dryrun_summary.log", "One log per dry-run step and the summary table in L6"],
    ["experiments/logs/full_plan_summary.log (after start)", "One status line per job of scripts/run_full_plan.sh once real training starts"],
], [8.5*cm, 8.5*cm]))
