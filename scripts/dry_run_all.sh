#!/bin/bash
# Dry run of every training / evaluation path: 1 epoch on a few real images each.
# Purpose: prove the code runs end to end before real training. Results are NOT meaningful.
# All outputs go to experiments/dryrun; real checkpoints in models/checkpoints are never touched.
# Logs: experiments/logs/dryrun_<step>.log and experiments/logs/dryrun_summary.log
cd "$(dirname "$0")/.."
export PYTHONUNBUFFERED=1 PYTHONPATH=src${PYTHONPATH:+:$PYTHONPATH} OCULENS_ASSISTANT=template
D=experiments/dryrun
L=experiments/logs
mkdir -p "$D" "$L"
SUMMARY=$L/dryrun_summary.log
echo "# dry run started $(date '+%Y-%m-%d %H:%M:%S')" > "$SUMMARY"
run() {
  name=$1; shift
  t0=$(date +%s)
  "$@" > "$L/dryrun_${name}.log" 2>&1
  code=$?
  printf "%-28s exit=%d  %4ds\n" "$name" "$code" "$(( $(date +%s) - t0 ))" | tee -a "$SUMMARY"
}

# --- classifiers (RQ1 variants), early stopping / resume, synthetic merge
run classifier_image        python scripts/train.py --task keratitis --dry-run
run classifier_resume       python scripts/train.py --task keratitis --dry-run --epochs 2 --resume
run classifier_mask_input   python scripts/train.py --task ulcer_pattern --variant mask_input --dry-run
run classifier_region_crop  python scripts/train.py --task ulcer_pattern --variant region_crop --dry-run
run classifier_multitask    python scripts/train.py --task ulcer_pattern --variant multitask --dry-run
run classifier_ensemble_s1  python scripts/train.py --task trachoma_tf --dry-run --seed 1

# --- evaluation and explainability on dry-run checkpoints
run evaluate_keratitis      python -m oculens.training.evaluate --task keratitis \
                              --checkpoint $D/checkpoints/keratitis_efficientnet_b0.pt --out $D/eval_keratitis.json
run explain_mask_input      python -m oculens.explain.evaluate --task ulcer_pattern --mask ulcer --limit 4 \
                              --checkpoint $D/checkpoints/ulcer_pattern_efficientnet_b0_mask_input.pt --out $D/explain_ulcer.json

# --- segmentation and predicted masks
run unet_cornea             python -m oculens.training.train_segmentation --target cornea --epochs 1 --limit 8 \
                              --size 128 --workers 0 --out-dir $D/checkpoints
run predict_masks           python scripts/predict_masks.py keratitis --limit 4 \
                              --checkpoint $D/checkpoints/unet_cornea.pt --out-dir $D/masks

# --- generative models (Step 3) and training with their output
run ddpm                    python -m oculens.generative.train_ddpm --task keratitis --size 32 --epochs 1 --limit 16 \
                              --batch-size 8 --per-class 2 --sample-steps 5 --workers 0 --out-dir $D
run classifier_synthetic    python scripts/train.py --task keratitis --dry-run --synthetic \
                              --synthetic-csv $D/synthetic/keratitis.csv
run cyclegan                python -m oculens.generative.train_cyclegan --task keratitis --domain-a ZEH --domain-b AGEH \
                              --allow-test-domain --size 64 --epochs 1 --limit 4 --batch-size 2 --out-dir $D

# --- follow-up Siamese model (pairs built from the time-series set; labels are FAKE, code check only)
run make_dry_pairs          python - <<'PY'
import glob, os, pandas as pd
rows, labels = [], ["progressed", "stable", "improved"]
for pid in sorted(glob.glob("datasets/slitlamp_cataract_temporal_figshare/raw/S1_file/*")):
    imgs = sorted(glob.glob(os.path.join(pid, "*.jpg")))
    for i in range(len(imgs) - 1):
        rel = lambda p: os.path.relpath(p, "datasets").replace("\\", "/")
        rows.append({"prev_path": rel(imgs[i]), "curr_path": rel(imgs[i + 1]),
                     "label": labels[(i + len(rows)) % 3], "group": os.path.basename(pid)})
pd.DataFrame(rows).to_csv("experiments/dryrun/followup_pairs_FAKE_LABELS.csv", index=False)
print(len(rows), "pairs (fake labels, dry run only)")
PY
run siamese_change          python -m oculens.followup.train_change --pairs $D/followup_pairs_FAKE_LABELS.csv \
                              --epochs 1 --size 128 --out-dir $D/checkpoints

# --- export and the end-to-end app pipeline with dry-run models
run export_onnx             python scripts/export_onnx.py --task keratitis --checkpoint $D/checkpoints/keratitis_efficientnet_b0.pt \n                              --out-dir $D/exported
run pipeline_end_to_end     python - <<'PY'
import glob, numpy as np
from PIL import Image
from oculens.pipeline import ScreeningPipeline
D = "experiments/dryrun/checkpoints"
img = np.array(Image.open(sorted(glob.glob("datasets/infectious_keratitis_figshare/raw/ZEH_Dataset/ZEH_Dataset/HSK/2/*.jpg"))[0]).convert("RGB"))
for ck in ("keratitis_efficientnet_b0.pt", "ulcer_pattern_efficientnet_b0_mask_input.pt", "ulcer_pattern_efficientnet_b0_multitask.pt"):
    out = ScreeningPipeline(checkpoint=f"{D}/{ck}", segmenter_checkpoint=f"{D}/unet_cornea.pt").run(img, symptoms={"pain": True})
    r = out["report"]
    f = r.findings[0] if r.findings else None
    print(ck, "| triage:", r.triage.level, "| finding:", f and (f.condition, round(f.probability, 3), f.prediction_set,
          f.attention_in_region), "| overlay:", out["overlay_png_base64"] is not None)
PY

echo "# dry run finished $(date '+%Y-%m-%d %H:%M:%S')" >> "$SUMMARY"
