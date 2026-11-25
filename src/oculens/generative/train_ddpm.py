"""Train the conditional DDPM on one task's TRAINING split, then write synthetic images.

    python -m oculens.generative.train_ddpm --task keratitis --size 64 --epochs 200
    python -m oculens.generative.train_ddpm --task keratitis --sample-only --per-class 200

Synthetic images are written to data/synthetic/<task>/<class>/ and listed in
data/synthetic/<task>.csv with split='train' only, so they can never reach validation or test.
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset

from oculens.config import load_config, resolve
from oculens.generative.ddpm import CondUNet, Diffusion


class TrainImages(Dataset):
    def __init__(self, df, root, cache, classes, size):
        self.df, self.root, self.cache, self.size = df.reset_index(drop=True), root, cache, size
        self.idx = {c: i for i, c in enumerate(classes)}

    def __len__(self):
        return len(self.df)

    def __getitem__(self, i):
        r = self.df.iloc[i]
        p = (self.cache / r["image_path"]).with_suffix(".jpg")
        img = Image.open(p if p.exists() else self.root / r["image_path"]).convert("RGB")
        w, h = img.size
        s = min(w, h)
        img = img.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2)).resize((self.size, self.size))
        if np.random.rand() < 0.5:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        x = torch.from_numpy(np.asarray(img, dtype=np.float32) / 127.5 - 1).permute(2, 0, 1)
        return x, self.idx[str(r["label"])]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--size", type=int, default=64)
    ap.add_argument("--epochs", type=int, default=200)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--per-class", type=int, default=100)
    ap.add_argument("--sample-steps", type=int, default=100)
    ap.add_argument("--sample-only", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out-dir", default=None, help="folder for checkpoint and images (default models/ and data/)")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args(argv)

    cfg = load_config()
    task = cfg["tasks"][args.task]
    classes = [str(c) for c in task["classes"]]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    out_base = resolve(args.out_dir) if args.out_dir else None
    ckpt = (out_base / "checkpoints" if out_base else resolve(cfg["paths"]["checkpoints_dir"])) / f"ddpm_{args.task}_{args.size}.pt"
    model = CondUNet(len(classes)).to(device)
    diff = Diffusion(model, device=device)

    if not args.sample_only:
        df = pd.read_csv(resolve(cfg["paths"]["splits_dir"]) / f"{args.task}.csv", dtype=str, keep_default_na=False)
        df = df[df["split"] == "train"]                       # never train the generator on val/test images
        if args.limit:
            df = df.head(args.limit)
        ds = TrainImages(df, resolve(cfg["paths"]["datasets_root"]), resolve(cfg["paths"]["cache_dir"]), classes, args.size)
        dl = DataLoader(ds, batch_size=args.batch_size, shuffle=True, drop_last=True,
                        num_workers=cfg["training"]["num_workers"] if args.workers is None else args.workers)
        opt = torch.optim.AdamW(model.parameters(), lr=2e-4)
        for epoch in range(1, args.epochs + 1):
            model.train()
            t0, tot = time.time(), 0.0
            for x, y in dl:
                loss = diff.loss(x.to(device), y.to(device))
                opt.zero_grad()
                loss.backward()
                opt.step()
                tot += loss.item()
            print(json.dumps({"epoch": epoch, "loss": round(tot / max(1, len(dl)), 5), "seconds": round(time.time() - t0, 1)}), flush=True)
        ckpt.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"state_dict": model.state_dict(), "classes": classes, "size": args.size}, ckpt)

    model.load_state_dict(torch.load(ckpt, map_location=device, weights_only=False)["state_dict"])
    syn_root = out_base / "synthetic" if out_base else resolve("data/synthetic")
    out_dir = syn_root / args.task
    rows = []
    for ci, c in enumerate(classes):
        (out_dir / c).mkdir(parents=True, exist_ok=True)
        done = 0
        while done < args.per_class:
            n = min(16, args.per_class - done)
            imgs = diff.sample(torch.full((n,), ci, device=device, dtype=torch.long), args.size, steps=args.sample_steps)
            for k, im in enumerate(((imgs + 1) * 127.5).clamp(0, 255).byte().permute(0, 2, 3, 1).cpu().numpy()):
                p = out_dir / c / f"syn_{done + k:05d}.png"
                Image.fromarray(im).save(p)
                rows.append({"image_path": str(p), "label": c, "split": "train", "synthetic": 1, "group": f"syn_{c}_{done + k}"})
            done += n
    pd.DataFrame(rows).to_csv(syn_root / f"{args.task}.csv", index=False)
    print(f"wrote {len(rows)} synthetic images to {out_dir} (training split only)")


if __name__ == "__main__":
    main()
