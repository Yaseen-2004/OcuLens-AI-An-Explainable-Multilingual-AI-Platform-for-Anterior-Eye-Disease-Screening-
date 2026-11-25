"""Train the U-Net baseline on SUSTech-SYSU cornea masks (Step 4).

Usage:
    python -m oculens.training.train_segmentation --epochs 10
    python -m oculens.training.train_segmentation --target ulcer --epochs 10
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset

from oculens.config import load_config, resolve
from oculens.data.splits import grouped_split
from oculens.models.unet import UNet, dice_bce_loss


class MaskDataset(Dataset):
    def __init__(self, rows: pd.DataFrame, root: Path, size: int, flip: bool, invert: bool = False):
        self.rows, self.root, self.size, self.flip = rows.reset_index(drop=True), root, size, flip
        self.invert = invert  # True for SUSTech ulcer labels, which mark the lesion in black on white

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        r = self.rows.iloc[i]
        img = Image.open(self.root / r["image_path"]).convert("RGB").resize((self.size, self.size))
        msk = Image.open(self.root / r["mask"]).convert("L").resize((self.size, self.size), Image.NEAREST)
        x = torch.from_numpy(np.asarray(img, dtype=np.float32) / 255.0).permute(2, 0, 1)
        fg = np.asarray(msk) <= 127 if self.invert else np.asarray(msk) > 127
        y = torch.from_numpy(fg.astype(np.float32))[None]
        if self.flip and torch.rand(1).item() < 0.5:
            x, y = x.flip(-1), y.flip(-1)
        return x, y


def dice_iou(logits: torch.Tensor, y: torch.Tensor) -> tuple[float, float]:
    p = (torch.sigmoid(logits) > 0.5).float()
    inter = (p * y).sum((1, 2, 3))
    union = p.sum((1, 2, 3)) + y.sum((1, 2, 3))
    dice = ((2 * inter + 1) / (union + 1)).mean().item()
    iou = ((inter + 1) / (union - inter + 1)).mean().item()
    return dice, iou


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["cornea", "ulcer"], default="cornea")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out-dir", default=None, help="checkpoint folder (default models/checkpoints)")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args(argv)

    cfg = load_config()
    root = resolve(cfg["paths"]["datasets_root"])
    man = pd.read_csv(resolve(cfg["paths"]["manifest"]), dtype=str, keep_default_na=False)
    df = man[man["dataset"] == "sustech_sysu"].copy()
    if args.target == "cornea":
        df["mask"] = df["extra"].map(lambda s: json.loads(s).get("cornea_mask", ""))
    else:
        df["mask"] = df["mask_path"]
    df = df[df["mask"] != ""]
    df["split"] = grouped_split(df.assign(label="x"), seed=cfg["training"]["seed"])
    if args.limit:
        df = df.groupby("split").head(args.limit)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dl = {s: DataLoader(MaskDataset(df[df["split"] == s], root, args.size, flip=(s == "train"), invert=(args.target == "ulcer")),
                        batch_size=8, shuffle=(s == "train"), num_workers=cfg["training"]["num_workers"] if args.workers is None else args.workers)
          for s in ("train", "val", "test")}
    model = UNet().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
    best = -1.0
    ckpt = (resolve(args.out_dir) if args.out_dir else resolve(cfg["paths"]["checkpoints_dir"])) / f"unet_{args.target}.pt"
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    for epoch in range(1, args.epochs + 1):
        model.train()
        t0 = time.time()
        for x, y in dl["train"]:
            opt.zero_grad()
            loss = dice_bce_loss(model(x.to(device)), y.to(device))
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            scores = [dice_iou(model(x.to(device)), y.to(device)) for x, y in dl["val"]]
        dice = float(np.mean([s[0] for s in scores])) if scores else float("nan")
        print(json.dumps({"epoch": epoch, "val_dice": round(dice, 4), "seconds": round(time.time() - t0, 1)}), flush=True)
        if dice > best:
            best = dice
            torch.save({"state_dict": model.state_dict(), "meta": {"target": args.target, "size": args.size}}, ckpt)
    model.load_state_dict(torch.load(ckpt, map_location=device, weights_only=False)["state_dict"])
    model.eval()
    with torch.no_grad():
        scores = [dice_iou(model(x.to(device)), y.to(device)) for x, y in dl["test"]]
    print(json.dumps({"test_dice": float(np.mean([s[0] for s in scores])),
                      "test_iou": float(np.mean([s[1] for s in scores])), "checkpoint": str(ckpt)}))


if __name__ == "__main__":
    main()
