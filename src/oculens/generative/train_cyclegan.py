"""Train the CycleGAN harmoniser between two sites, then translate site-A training images into
site-B style (revised RQ2: does harmonisation help a model trained at one hospital work at another?).

    python -m oculens.generative.train_cyclegan --task keratitis --domain-a ZEH --domain-b AGEH --epochs 50

By default only non-test images are used from either site. For the keratitis cross-site split the
whole AGEH site is the test set, so using it as domain B is unsupervised domain adaptation on the test
site (labels are never read). That must be declared explicitly with --allow-test-domain and reported.
Translated images are written as a training-only CSV, like the DDPM output.
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
from oculens.generative.cyclegan import CycleGAN


class Imgs(Dataset):
    def __init__(self, paths, root, cache, size, augment=True):
        self.paths, self.root, self.cache, self.size, self.augment = list(paths), root, cache, size, augment

    def __len__(self):
        return len(self.paths)

    def load(self, rel):
        p = (self.cache / rel).with_suffix(".jpg")
        img = Image.open(p if p.exists() else self.root / rel).convert("RGB")
        w, h = img.size
        s = min(w, h)
        return img.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2)).resize((self.size, self.size))

    def __getitem__(self, i):
        img = self.load(self.paths[i])
        if self.augment and np.random.rand() < 0.5:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        return torch.from_numpy(np.asarray(img, dtype=np.float32) / 127.5 - 1).permute(2, 0, 1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="keratitis")
    ap.add_argument("--domain-a", required=True, help="site whose training images are translated")
    ap.add_argument("--domain-b", required=True, help="target style site")
    ap.add_argument("--allow-test-domain", action="store_true")
    ap.add_argument("--size", type=int, default=128)
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out-dir", default=None, help="where checkpoints and images go (default models/ and data/)")
    args = ap.parse_args(argv)

    cfg = load_config()
    df = pd.read_csv(resolve(cfg["paths"]["splits_dir"]) / f"{args.task}.csv", dtype=str, keep_default_na=False)
    a = df[(df["site"] == args.domain_a) & (df["split"] == "train")]
    b = df[df["site"] == args.domain_b]
    if not args.allow_test_domain:
        b = b[b["split"] != "test"]
    if b.empty:
        raise SystemExit(f"no usable images for domain {args.domain_b}; it may be the test site - see --allow-test-domain")
    if args.limit:
        a, b = a.head(args.limit), b.head(args.limit)
    root, cache = resolve(cfg["paths"]["datasets_root"]), resolve(cfg["paths"]["cache_dir"])
    da, db = Imgs(a["image_path"], root, cache, args.size), Imgs(b["image_path"], root, cache, args.size)
    la = DataLoader(da, batch_size=args.batch_size, shuffle=True, drop_last=True)
    lb = DataLoader(db, batch_size=args.batch_size, shuffle=True, drop_last=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    gan = CycleGAN(device=device)
    out_base = resolve(args.out_dir) if args.out_dir else None
    ckpt = (out_base / "checkpoints" if out_base else resolve(cfg["paths"]["checkpoints_dir"])) / \
        f"cyclegan_{args.task}_{args.domain_a}_to_{args.domain_b}.pt"
    print(f"domain A {args.domain_a}: {len(da)} train images; domain B {args.domain_b}: {len(db)} images "
          f"(test-site images used: {args.allow_test_domain})")
    for epoch in range(1, args.epochs + 1):
        t0, logs = time.time(), []
        for xa, xb in zip(la, lb):
            logs.append(gan.train_step(xa.to(device), xb.to(device)))
        print(json.dumps({"epoch": epoch, "loss_g": round(float(np.mean([l["loss_g"] for l in logs] or [0])), 4),
                          "loss_d": round(float(np.mean([l["loss_d"] for l in logs] or [0])), 4),
                          "seconds": round(time.time() - t0, 1)}), flush=True)
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"G_ab": gan.G_ab.state_dict(), "G_ba": gan.G_ba.state_dict(), "size": args.size,
                "domain_a": args.domain_a, "domain_b": args.domain_b, "used_test_domain": args.allow_test_domain}, ckpt)

    # Translate domain-A TRAINING images; keep their labels; mark them training-only.
    out_dir = (out_base / "harmonized" if out_base else resolve("data/harmonized")) / f"{args.task}_{args.domain_a}_to_{args.domain_b}"
    gan.G_ab.eval()
    rows = []
    with torch.no_grad():
        for (_, r), rel in zip(a.iterrows(), a["image_path"]):
            x = torch.from_numpy(np.asarray(da.load(rel), dtype=np.float32) / 127.5 - 1).permute(2, 0, 1)[None].to(device)
            y = ((gan.G_ab(x)[0] + 1) * 127.5).clamp(0, 255).byte().permute(1, 2, 0).cpu().numpy()
            dst = out_dir / r["label"] / (rel.replace("/", "__").rsplit(".", 1)[0] + ".png")
            dst.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(y).save(dst)
            rows.append({"image_path": str(dst), "label": r["label"], "split": "train", "synthetic": 1,
                         "group": r["group"], "site": f"{args.domain_a}->{args.domain_b}"})
    pd.DataFrame(rows).to_csv(out_dir.parent / f"{out_dir.name}.csv", index=False)
    print(f"saved {ckpt}; translated {len(rows)} training images to {out_dir}")


if __name__ == "__main__":
    main()
