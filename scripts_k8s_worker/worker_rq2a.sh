# RQ2a: diffusion synthetic images, then retrain keratitis with them
cd /workspace
mkdir -p experiments/logs
pip install -q --no-index --no-deps --target /tmp/pylibs /workspace/wheels/timm-*.whl
export PYTHONPATH=/tmp/pylibs:/workspace/src OCULENS_ASSISTANT=template
nvidia-smi -L
exec > >(tee -a experiments/logs/worker_rq2a.out) 2>&1; echo "== start $(date)"
python -m oculens.generative.train_ddpm --task keratitis --size 64 --epochs 50 --per-class 200
python scripts/train.py --task keratitis --synthetic --epochs 50 --patience 0 --resume
python -m oculens.training.evaluate --task keratitis --checkpoint models/checkpoints/keratitis_efficientnet_b0_syn.pt --out experiments/runs/eval_keratitis_synthetic.json
echo "== done $(date)"
