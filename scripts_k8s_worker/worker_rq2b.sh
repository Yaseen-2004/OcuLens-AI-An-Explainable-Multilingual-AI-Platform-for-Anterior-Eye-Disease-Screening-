# RQ2b: CycleGAN harmonisation ZEH->AGEH, then retrain keratitis with harmonised images
cd /workspace
mkdir -p experiments/logs
pip install -q --no-index --no-deps --target /tmp/pylibs /workspace/wheels/timm-*.whl
export PYTHONPATH=/tmp/pylibs:/workspace/src OCULENS_ASSISTANT=template
nvidia-smi -L
exec > >(tee -a experiments/logs/worker_rq2b.out) 2>&1; echo "== start $(date)"
python -m oculens.generative.train_cyclegan --task keratitis --domain-a ZEH --domain-b AGEH --allow-test-domain --size 128 --epochs 50
python scripts/train.py --task keratitis --synthetic --synthetic-csv data/harmonized/keratitis_ZEH_to_AGEH.csv --epochs 50 --patience 0 --resume --seed 101
echo "== done $(date)"
