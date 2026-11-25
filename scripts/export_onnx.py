"""Export a trained classifier to ONNX and benchmark CPU latency (Step 12).

    python scripts/export_onnx.py --task keratitis
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402
import torch  # noqa: E402

from oculens.config import load_config, resolve  # noqa: E402
from oculens.models.classifier import load_checkpoint  # noqa: E402


def benchmark(fn, x, runs: int = 20) -> float:
    fn(x)                                   # warm-up
    t0 = time.perf_counter()
    for _ in range(runs):
        fn(x)
    return (time.perf_counter() - t0) / runs * 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--checkpoint", default=None)
    ap.add_argument("--out-dir", default="models/exported")
    args = ap.parse_args()
    cfg = load_config()
    ckpt = args.checkpoint or resolve(cfg["paths"]["checkpoints_dir"]) / f"{args.task}_{cfg['training']['backbone']}.pt"
    model, meta = load_checkpoint(ckpt)
    size = meta.get("image_size", 224)
    x = torch.randn(1, 4 if meta.get("variant") == "mask_input" else 3, size, size)
    out = resolve(args.out_dir) / f"{Path(ckpt).stem}.onnx"
    out.parent.mkdir(parents=True, exist_ok=True)
    kw = dict(input_names=["image"], output_names=["logits"],
              dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}}, opset_version=17)
    try:
        torch.onnx.export(model, x, str(out), dynamo=False, **kw)      # classic exporter, no onnxscript needed
    except TypeError:                                                   # older PyTorch without the dynamo flag
        torch.onnx.export(model, x, str(out), **kw)
    print("exported", out, f"{out.stat().st_size / 1e6:.1f} MB")
    with torch.no_grad():
        print(f"PyTorch CPU: {benchmark(lambda t: model(t), x):.1f} ms / image")
    try:
        import onnxruntime as ort

        sess = ort.InferenceSession(str(out), providers=["CPUExecutionProvider"])
        xn = x.numpy()
        ref = model(x).detach().numpy()
        got = sess.run(None, {"image": xn})[0]
        print(f"ONNX Runtime CPU: {benchmark(lambda t: sess.run(None, {'image': t}), xn):.1f} ms / image; "
              f"max |diff| vs PyTorch = {np.abs(ref - got).max():.2e}")
    except ImportError:
        print("onnxruntime not installed - skipped ONNX benchmark (pip install onnxruntime)")


if __name__ == "__main__":
    main()
