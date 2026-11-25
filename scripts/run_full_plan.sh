#!/bin/bash
# Full experiment plan (start only when the team says so).
# Every job logs to experiments/logs/<job>.log; a one-line status per job goes to experiments/logs/full_plan_summary.log.
# Classifier jobs use --resume --patience $PATIENCE, so re-running this script after an interruption continues where it stopped.
# Jobs whose outputs already exist are skipped (delete the output to force a re-run).
#   bash scripts/run_full_plan.sh            # everything
#   EPOCHS=10 is the default for every job
#   ONLY=baseline bash scripts/run_full_plan.sh   # just one stage: seg | baseline | rq1 | ensemble | rq2 | explain | export
cd "$(dirname "$0")/.."
export PYTHONUNBUFFERED=1 PYTHONPATH=src${PYTHONPATH:+:$PYTHONPATH}
L=experiments/logs; C=models/checkpoints; mkdir -p "$L"
SUMMARY=$L/full_plan_summary.log
B=efficientnet_b0
EPOCHS=${EPOCHS:-10}          # epochs for every training job (override: EPOCHS=50 bash scripts/run_full_plan.sh)
PATIENCE=${PATIENCE:-6}       # early-stopping patience for classifiers (0 = train all epochs)
stage() { [ -z "$ONLY" ] || [[ " $ONLY " == *" $1 "* ]]; }
run() {
  name=$1; out=$2; shift 2
  # classifier, eval and explain jobs always run (classifiers resume); expensive generators are skipped when done
  if [ -n "$out" ] && [ -e "$out" ] && [[ "$name" != classifier_* && "$name" != eval_* && "$name" != explain_* ]]; then
    echo "$(date '+%F %T') SKIP  $name (exists: $out)" | tee -a "$SUMMARY"; return; fi
  t0=$(date +%s); echo "$(date '+%F %T') START $name" | tee -a "$SUMMARY"
  "$@" >> "$L/${name}.log" 2>&1; code=$?
  echo "$(date '+%F %T') END   $name exit=$code $(( ($(date +%s) - t0) / 60 )) min" | tee -a "$SUMMARY"
}

# 1. Segmentation (cornea masks for the anatomy check and the RQ1 variants)
if stage seg; then
  run unet_cornea      $C/unet_cornea.pt python -m oculens.training.train_segmentation --target cornea --epochs $EPOCHS
  run unet_ulcer       $C/unet_ulcer.pt  python -m oculens.training.train_segmentation --target ulcer --epochs $EPOCHS
  run masks_keratitis  data/masks/infectious_keratitis_figshare python scripts/predict_masks.py keratitis
fi

# 2. Baselines (image only) + test evaluation
if stage baseline; then
  for T in keratitis ulcer_pattern trachoma_tf; do
    run classifier_${T}_image "" python scripts/train.py --task $T --epochs $EPOCHS --resume --patience $PATIENCE
    run eval_${T}_image experiments/runs/eval_${T}_image.json python -m oculens.training.evaluate --task $T \
        --checkpoint $C/${T}_$B.pt --out experiments/runs/eval_${T}_image.json
  done
fi

# 3. RQ1: does anatomy help? (mask as input, region crop, multitask)
if stage rq1; then
  for V in mask_input region_crop; do
    for T in keratitis ulcer_pattern; do
      run classifier_${T}_$V "" python scripts/train.py --task $T --variant $V --epochs $EPOCHS --resume --patience $PATIENCE
      run eval_${T}_$V experiments/runs/eval_${T}_$V.json python -m oculens.training.evaluate --task $T \
          --checkpoint $C/${T}_${B}_$V.pt --out experiments/runs/eval_${T}_$V.json
    done
  done
  run classifier_ulcer_pattern_multitask "" python scripts/train.py --task ulcer_pattern --variant multitask --epochs $EPOCHS --resume --patience $PATIENCE
  run eval_ulcer_pattern_multitask experiments/runs/eval_ulcer_pattern_multitask.json python -m oculens.training.evaluate \
      --task ulcer_pattern --checkpoint $C/ulcer_pattern_${B}_multitask.pt --out experiments/runs/eval_ulcer_pattern_multitask.json
fi

# 4. RQ3 support: deep ensemble of 5 keratitis models
if stage ensemble; then
  for S in 1 2 3 4 5; do
    run classifier_keratitis_seed$S "" python scripts/train.py --task keratitis --seed $S --epochs $EPOCHS --resume --patience $PATIENCE
  done
fi

# 5. RQ2: synthetic rare-class images and cross-hospital harmonisation
if stage rq2; then
  run ddpm_keratitis data/synthetic/keratitis.csv python -m oculens.generative.train_ddpm --task keratitis --size 64 --epochs $EPOCHS --per-class 200
  run classifier_keratitis_synthetic "" python scripts/train.py --task keratitis --synthetic --epochs $EPOCHS --resume --patience $PATIENCE
  run eval_keratitis_synthetic experiments/runs/eval_keratitis_synthetic.json python -m oculens.training.evaluate --task keratitis \
      --checkpoint $C/keratitis_${B}_syn.pt --out experiments/runs/eval_keratitis_synthetic.json
  # declared: uses AGEH (the test site) images WITHOUT labels as the target style
  run cyclegan_zeh_to_ageh data/harmonized/keratitis_ZEH_to_AGEH.csv python -m oculens.generative.train_cyclegan --task keratitis \
      --domain-a ZEH --domain-b AGEH --allow-test-domain --size 128 --epochs $EPOCHS
  run classifier_keratitis_harmonized "" python scripts/train.py --task keratitis --synthetic \
      --synthetic-csv data/harmonized/keratitis_ZEH_to_AGEH.csv --epochs $EPOCHS --resume --patience $PATIENCE --seed 101
fi

# 6. RQ4: explanation quality
if stage explain; then
  for M in cornea ulcer; do
    run explain_ulcer_image_$M experiments/runs/explain_ulcer_image_$M.json python -m oculens.explain.evaluate --task ulcer_pattern \
        --mask $M --checkpoint $C/ulcer_pattern_$B.pt --out experiments/runs/explain_ulcer_image_$M.json
    run explain_ulcer_maskinput_$M experiments/runs/explain_ulcer_maskinput_$M.json python -m oculens.explain.evaluate --task ulcer_pattern \
        --mask $M --checkpoint $C/ulcer_pattern_${B}_mask_input.pt --out experiments/runs/explain_ulcer_maskinput_$M.json
  done
fi

# 7. Deployment check
if stage export; then
  run export_onnx_keratitis models/exported/keratitis_$B.onnx python scripts/export_onnx.py --task keratitis
fi
echo "$(date '+%F %T') plan finished" | tee -a "$SUMMARY"
