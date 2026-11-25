# ensemble: 5 keratitis models (seeds 1-5), 50 epochs each
cd /workspace
mkdir -p experiments/logs
pip install -q --no-index --no-deps --target /tmp/pylibs /workspace/wheels/timm-*.whl
export PYTHONPATH=/tmp/pylibs:/workspace/src OCULENS_ASSISTANT=template
nvidia-smi -L
exec > >(tee -a experiments/logs/worker_ensemble.out) 2>&1; echo "== start $(date)"
for S in 1 2 3 4 5; do python scripts/train.py --task keratitis --seed $S --epochs 50 --patience 0 --resume; done
echo "== done $(date)"
