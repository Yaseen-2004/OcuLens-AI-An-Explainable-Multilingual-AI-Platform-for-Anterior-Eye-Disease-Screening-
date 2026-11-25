import glob as _glob
import json as _json
import os as _os

_PROJ = r"D:\Capston_Project"

s.append(PageBreak())
s += [p("Part J - Project build (code, tests, server setup)", H1),
      p("Written 18 Nov 2026. This part records what was built on 18 Nov, where it lives, and how it was checked. "
        "All code is in D:\\Capston_Project. It follows the design in Part E, adapted to clinical images and a web app.")]

s += [p("J1. What was built, by method step", H2)]
s.append(table([
    ["Step", "Code", "What it does", "Status"],
    ["1 Data", "src/oculens/data/manifest.py, splits.py, dataset.py", "Indexes all 7,419 images with labels, patient groups, sites and masks; makes leakage-free splits (cross-hospital for keratitis); loads images (with a 512 px cache).", "Working; tested"],
    ["2 Quality + preprocessing", "quality/checks.py, preprocessing/enhance.py, transforms.py", "Rejects blurred, dark, overexposed, low-contrast and glare-heavy images with a recapture prompt; removes reflections; CLAHE; same transforms in training and app.", "Working; tested"],
    ["3 GAN / diffusion", "generative/ddpm.py, cyclegan.py, validate.py, train_ddpm.py", "Class-conditional diffusion with classifier-free guidance for rare classes (training split only); CycleGAN harmoniser with its own training script; FID on backbone features and TSTR; outputs can be added to classifier training.", "Code ready; dry-run passed"],
    ["4 Segmentation", "models/unet.py, segmenter.py, training/train_segmentation.py", "U-Net with Dice + BCE loss on SUSTech cornea or ulcer masks; Dice and IoU; once trained, the pipeline uses its cornea mask for the anatomy check.", "Code ready; not yet trained"],
    ["5 Classification", "models/classifier.py, training/train_classifier.py, evaluate.py, losses.py, metrics.py", "Any timm backbone; RQ1 variants (mask as input, region crop, multitask severity head); focal loss, balanced sampling; early stopping and resume; per-class sensitivity, specificity, AUROC, kappa, ECE; evaluation with subgroup metrics.", "Working; dry-run passed; see Parts K-L"],
    ["6 Uncertainty", "uncertainty/calibration.py, conformal.py, mc_dropout.py, ensemble.py", "Temperature scaling; split-conformal prediction sets (95 % target); referral when more than one label stays plausible; MC dropout; deep ensembles (seeded members, mutual information); referral-effect measurement for RQ3.", "Working; tested"],
    ["7 Explainability", "explain/gradcam.py, region_check.py, evaluate.py", "Grad-CAM and Grad-CAM++; attention-in-region, pointing game, deletion AUC; unreliable flag.", "Working; tested"],
    ["8 Decision engine", "triage/engine.py, configs/triage_rules.yaml", "Safety overrides first, then uncertainty -> refer, then findings, then symptoms; routine / soon / refer / urgent.", "Working; rules need clinician sign-off"],
    ["9 Assistant", "assistant/schema.py, guardrails.py, llm.py, report.py", "Structured findings only; Anthropic API (claude-opus-5-5) when a key is set, offline template otherwise; guardrails remove doses and diagnostic wording, add urgent line and disclaimer; doctor report.", "Working; API path not yet tried with a key"],
    ["10 Follow-up", "followup/align.py, change.py, schedule.py, train_change.py", "Image alignment, change detection, Siamese network and its training script (needs clinician-labelled pairs), rescan schedule, post-surgery warning check.", "Working; tested; Siamese not trained"],
    ["11 Dashboard", "backend/app/store.py, static/dashboard.html", "Scan store, review queue, confirm / correct, audit log, corrections export for active learning.", "Working; tested"],
    ["12 App", "src/oculens/pipeline.py, backend/app/main.py, static/index.html, scripts/export_onnx.py", "End-to-end screening of one image; FastAPI service; screening page with heatmap and patient explanation; ONNX export with CPU latency benchmark.", "Working with or without a trained model"],
], [2.6*cm, 4.4*cm, 7.0*cm, 3.0*cm]))

s += [p("J2. Tests", H2),
      p("48 unit tests, all passing on 22 Nov (pytest, about 30 s on the PC). They need no dataset and train nothing: quality gate (4), splits and leakage check (3), "
        "triage rules (8), conformal coverage and temperature scaling (3), guardrails and template (2), classifier, Grad-CAM, U-Net and no-model pipeline (4), "
        "follow-up alignment, change and schedule (4), API with store and dashboard review (2), diffusion, CycleGAN, FID/TSTR, ensemble, referral effect, segmenter and Siamese model (7), model variants, aligned transforms and dataset handling (11). Tests never call the paid LLM API.")]

s += [p("J3. How to run", H2),
      Preformatted(r"""pip install -r requirements.txt
pytest                                           # 48 tests
bash scripts/dry_run_all.sh                      # 1-epoch check of every training path (~8 min)
bash scripts/run_full_plan.sh                    # all experiments, 10 epochs each, logged; start only when told
python scripts/build_manifest.py                 # data/manifest.csv (7,419 images)
python scripts/make_splits.py                    # data/splits/<task>.csv
python scripts/cache_images.py keratitis         # 512 px cache (much faster training)
python scripts/download_weights.py               # ImageNet weights into models/pretrained
python scripts/train.py --task keratitis --epochs 15
python -m oculens.explain.evaluate --task ulcer_pattern --mask cornea
uvicorn backend.app.main:app                     # screening page /  and  doctor dashboard /dashboard
""", ParagraphStyle("run", fontName="Courier", fontSize=7.2, leading=8.8))]

s += [p("J4. NVIDIA server workflow and problems met", H2)]
s.append(table([
    ["Topic", "What we found", "What we did"],
    ["Access", "Head node only; GPUs through Kubernetes pods; quota 8 CPU, 16 GiB, one H200 MIG 1g.18gb slice.", "Pod helper scripts_k8s/runpod.sh mounts ~/oculens-ai at /workspace."],
    ["Cluster policy", "Pods without a GPU request are rejected.", "Even data preparation borrows the GPU slice briefly."],
    ["Downloads", "The server cannot reach Amazon S3, so Figshare, Mendeley and Hugging Face files fail.", "Upload verified archives and weights from the PC by SFTP (about 11 MB/s)."],
    ["Missing package", "timm is not in the NVIDIA container.", "Install the timm wheel into /tmp at pod start."],
    ["Shared memory", "Loader workers crashed: /dev/shm full.", "In-memory /dev/shm volume on every pod."],
    ["Speed", "186 s per epoch: full-size photos processed before shrinking.", "Shrink to 512 px first: 85 s per epoch."],
    ["Outages", "Twice the server stopped answering SSH after bursts of logins; the second cut interrupted the 100-epoch restart.", "Fewer, batched connections; training continued on the PC meanwhile."],
], [2.6*cm, 7.0*cm, 7.4*cm]))

# ------------------------------------------------------------------ Part K: results from result files
s.append(PageBreak())
s += [p("Part K - Training and evaluation results", H1),
      p("Numbers below are read directly from the result files written by the training and evaluation scripts "
        "(experiments/runs/*/result.json and explain_*.json). Only completed runs are listed. "
        "These are first baselines on public data (trained on the PC CPU or the DGX GPU slice, as stated per run); they are not clinical performance claims.")]

_runs = {}
for _f in sorted(_glob.glob(_os.path.join(_PROJ, "experiments", "runs", "*", "result.json"))):
    try:
        _r = _json.load(open(_f))
    except Exception:
        continue
    if _r.get("test", {}).get("n", 0) >= 50:          # skip smoke runs
        _runs[_r["task"]] = (_f, _r)                    # latest full run per task wins (sorted by time)

if not _runs:
    s.append(p("<i>No full training run has finished yet. This section fills in automatically when one does.</i>"))
for _task, (_f, _r) in _runs.items():
    _t = _r["test"]
    _auc = _t.get("auroc", _t.get("auroc_macro_ovr"))
    s += [p(f"K. {_task} ({_r['backbone']})", H2),
          p(f"Run folder: {_os.path.basename(_os.path.dirname(_f))}. Epochs: {len(_r['history'])}. "
            f"Best validation balanced accuracy: {_r['best_val_balanced_acc']:.3f}. Temperature: {_r['temperature']:.2f}. "
            f"Conformal threshold (alpha {0.05}): {_r['conformal_qhat']:.3f}.")]
    s.append(table([
        ["Test images", "Accuracy", "Balanced acc.", "Macro F1", "AUROC", "Kappa", "ECE"],
        [str(_t["n"]), f"{_t['accuracy']:.3f}", f"{_t['balanced_accuracy']:.3f}", f"{_t['macro_f1']:.3f}",
         "n/a" if _auc is None or _auc != _auc else f"{_auc:.3f}",
         "n/a" if _t["kappa"] != _t["kappa"] else f"{_t['kappa']:.3f}", f"{_t['ece']:.3f}"],
    ], [2.4*cm, 2.2*cm, 2.6*cm, 2.2*cm, 2.2*cm, 2.2*cm, 2.2*cm]))
    s.append(Spacer(1, 4))
    s.append(table([["Class", "Sensitivity", "Specificity", "Test support"]] +
                   [[c, f"{v['sensitivity']:.3f}" if v['sensitivity'] == v['sensitivity'] else "n/a",
                     f"{v['specificity']:.3f}" if v['specificity'] == v['specificity'] else "n/a", str(v["support"])]
                    for c, v in _t["per_class"].items()],
                   [6.0*cm, 3.6*cm, 3.6*cm, 3.6*cm]))

_ex = sorted(_glob.glob(_os.path.join(_PROJ, "experiments", "runs", "explain_*.json")))
if _ex:
    s += [p("K. Explanation quality (RQ4)", H2)]
    _rows = [["Task / mask / method", "Images", "Attention in region", "Mask area", "Share reliable", "Pointing game", "Deletion AUC"]]
    for _f in _ex:
        _sm = _json.load(open(_f))["summary"]
        _rows.append([f"{_sm['task']} / {_sm['mask']} / {_sm['method']}", str(_sm["n"]), str(_sm["mean_attention_in_region"]),
                      str(_sm["mean_mask_area"]), str(_sm["share_reliable"]), str(_sm["pointing_game"]), str(_sm["mean_deletion_auc"])])
    s.append(table(_rows, [4.6*cm, 1.6*cm, 2.2*cm, 1.8*cm, 2.0*cm, 2.2*cm, 2.6*cm]))
    s.append(p("Attention in region should be read against the mask area: a map spread evenly would score about the mask area by chance."))
