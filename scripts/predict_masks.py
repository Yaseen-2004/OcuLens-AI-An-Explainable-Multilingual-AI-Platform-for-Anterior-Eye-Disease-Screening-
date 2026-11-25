"""Write U-Net region masks for every image of a task to data/masks/ (needed by the mask_input and
region_crop variants for datasets that have no ground-truth masks, e.g. keratitis).

    python scripts/predict_masks.py keratitis
    python scripts/predict_masks.py keratitis --checkpoint models/checkpoints/unet_cornea.pt
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

from oculens.config import load_config, resolve  # noqa: E402
from oculens.models.segmenter import Segmenter  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task")
    ap.add_argument("--checkpoint", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()
    cfg = load_config()
    ckpt = args.checkpoint or resolve(cfg["paths"]["checkpoints_dir"]) / "unet_cornea.pt"
    if not Path(ckpt).exists():
        raise SystemExit(f"{ckpt} not found - train it first: python -m oculens.training.train_segmentation --target cornea")
    seg = Segmenter(ckpt)
    df = pd.read_csv(resolve(cfg["paths"]["splits_dir"]) / f"{args.task}.csv", dtype=str, keep_default_na=False)
    if args.limit:
        df = df.head(args.limit)
    root = resolve(cfg["paths"]["datasets_root"])
    cache = resolve(cfg["paths"]["cache_dir"])
    out_root = resolve(args.out_dir) if args.out_dir else resolve(cfg["paths"]["masks_dir"])
    n = 0
    for rel in df["image_path"]:
        src = (cache / rel).with_suffix(".jpg")
        img = np.array(Image.open(src if src.exists() else root / rel).convert("RGB"))
        dst = (out_root / rel).with_suffix(".png")
        dst.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(seg.predict(img) * 255).save(dst)
        n += 1
    print(f"wrote {n} {seg.target} masks to {out_root}")


if __name__ == "__main__":
    main()
