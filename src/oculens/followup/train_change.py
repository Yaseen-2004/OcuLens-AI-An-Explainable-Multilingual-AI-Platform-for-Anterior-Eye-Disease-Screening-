"""Train the Siamese change network on labelled scan pairs (Step 10).

Input: a CSV of pairs  prev_path,curr_path,label,group  with label in {progressed, stable, improved},
paths relative to the datasets root, and group = patient ID (used for a leakage-free split).
Clinicians label these pairs from longitudinal hospital data; public data has no such labels.

    python -m oculens.followup.train_change --pairs data/followup_pairs.csv --epochs 20
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
import timm
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset

from oculens.config import load_config, resolve
from oculens.data.splits import grouped_split
from oculens.followup.align import align_to
from oculens.models.classifier import local_weights
from oculens.followup.change import SiameseChange
from oculens.preprocessing.transforms import build_transforms

LABELS = ["progressed", "stable", "improved"]


class PairDataset(Dataset):
    def __init__(self, df, root, size, train, pcfg):
        self.df, self.root = df.reset_index(drop=True), root
        self.tf = build_transforms(train=False, image_size=size, cfg=pcfg)   # same geometry for both images
        self.train = train

    def __len__(self):
        return len(self.df)

    def __getitem__(self, i):
        r = self.df.iloc[i]
        prev = np.array(Image.open(self.root / r["prev_path"]).convert("RGB"))
        curr = np.array(Image.open(self.root / r["curr_path"]).convert("RGB"))
        curr, _ = align_to(prev, curr)                       # register before comparing
        a, b = self.tf(prev), self.tf(curr)
        if self.train and np.random.rand() < 0.5:
            a, b = a.flip(-1), b.flip(-1)
        return a, b, LABELS.index(r["label"])


def build_model(backbone: str = "efficientnet_b0") -> SiameseChange:
    w = local_weights(backbone)
    kw = {"pretrained": True, "pretrained_cfg_overlay": {"file": str(w)}} if w else {"pretrained": False}
    enc = timm.create_model(backbone, num_classes=0, **kw)
    return SiameseChange(enc, enc.num_features, len(LABELS))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--size", type=int, default=224)
    ap.add_argument("--out-dir", default=None, help="checkpoint folder (default models/checkpoints)")
    args = ap.parse_args(argv)
    cfg = load_config()
    df = pd.read_csv(resolve(args.pairs), dtype=str)
    df["split"] = grouped_split(df, seed=cfg["training"]["seed"])
    root = resolve(cfg["paths"]["datasets_root"])
    dl = {s: DataLoader(PairDataset(df[df["split"] == s], root, args.size, s == "train", cfg["preprocessing"]),
                        batch_size=8, shuffle=(s == "train")) for s in ("train", "val", "test")}
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = build_model(cfg["training"]["backbone"]).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    loss_fn = torch.nn.CrossEntropyLoss()
    best, ckpt = -1.0, (resolve(args.out_dir) if args.out_dir else resolve(cfg["paths"]["checkpoints_dir"])) / "siamese_change.pt"
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    for epoch in range(1, args.epochs + 1):
        model.train()
        for a, b, y in dl["train"]:
            opt.zero_grad()
            loss = loss_fn(model(a.to(device), b.to(device)), y.to(device))
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            correct = total = 0
            for a, b, y in dl["val"]:
                correct += (model(a.to(device), b.to(device)).argmax(1).cpu() == y).sum().item()
                total += len(y)
        acc = correct / max(1, total)
        print(json.dumps({"epoch": epoch, "val_accuracy": round(acc, 4)}), flush=True)
        if acc > best:
            best = acc
            torch.save({"state_dict": model.state_dict(), "labels": LABELS}, ckpt)
    print("best val accuracy", best, "saved", ckpt)


if __name__ == "__main__":
    main()
