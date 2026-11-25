#!/bin/bash
# Run training / evaluation jobs one after another on this machine, logging each to experiments/.
cd "$(dirname "$0")/.."
export PYTHONUNBUFFERED=1 PYTHONPATH=src
run() { name=$1; shift; echo "== $(date +%H:%M:%S) start $name"; "$@" > "experiments/${name}.log" 2>&1; echo "== $(date +%H:%M:%S) end $name (exit $?)"; }
run cpu_keratitis      python scripts/train.py --task keratitis --epochs 15 --batch-size 16 --workers 4
run cpu_ulcer_pattern   python scripts/train.py --task ulcer_pattern --epochs 15 --batch-size 16 --workers 4
run explain_ulcer_cornea python -m oculens.explain.evaluate --task ulcer_pattern --mask cornea --method gradcam++
run explain_ulcer_ulcer  python -m oculens.explain.evaluate --task ulcer_pattern --mask ulcer --method gradcam++
run cpu_trachoma_tf     python scripts/train.py --task trachoma_tf --epochs 10 --batch-size 16 --workers 4
