"""Evaluate a saved classifier on its test split: overall metrics, conformal coverage, referral
effect (RQ3) and subgroup metrics (fairness by site, eye side, illumination mode).

    python -m oculens.training.evaluate --task keratitis
    python -m oculens.training.evaluate --task keratitis --split val
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from oculens.config import load_config, resolve
from oculens.data.dataset import EyeImageDataset
from oculens.models.classifier import load_checkpoint
from oculens.training.metrics import classification_report
from oculens.uncertainty.conformal import empirical_coverage


@torch.no_grad()
def predict_probs(model, loader, temperature: float, device: str = "cpu") -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    ps, ys = [], []
    for batch in loader:
        ps.append(torch.softmax(model(batch[0].to(device)) / temperature, 1).cpu())
        ys.append(batch[1])
    return torch.cat(ps).numpy(), torch.cat(ys).numpy()


def referral_effect(probs: np.ndarray, y: np.ndarray, qhat: float, normal_idx: int | None = None) -> dict:
    """Accuracy and missed-case rate on cases kept vs. the referral rate (RQ3)."""
    in_set = (1.0 - probs) <= qhat
    refer = in_set.sum(1) > 1
    kept = ~refer
    pred = probs.argmax(1)
    out = {"referral_rate": float(refer.mean()),
           "accuracy_all": float((pred == y).mean()),
           "accuracy_kept": float((pred[kept] == y[kept]).mean()) if kept.any() else float("nan")}
    if normal_idx is not None:
        sick = y != normal_idx
        missed_all = (sick & (pred == normal_idx)).sum() / max(1, sick.sum())
        missed_kept = (sick & kept & (pred == normal_idx)).sum() / max(1, sick.sum())
        out.update(missed_rate_without_referral=float(missed_all), missed_rate_with_referral=float(missed_kept))
    return out


def subgroup_reports(df: pd.DataFrame, probs: np.ndarray, y: np.ndarray, classes: list[str]) -> dict:
    extra = df["extra"].map(lambda s: json.loads(s) if s else {})
    groups = {"site": df["site"].to_numpy(),
              "eye": extra.map(lambda e: e.get("eye", "")).to_numpy(),
              "illumination_mode": extra.map(lambda e: str(e.get("illumination_mode", ""))).to_numpy()}
    out = {}
    for name, values in groups.items():
        vals = [v for v in np.unique(values) if v not in ("", "nan")]
        if len(vals) < 2:
            continue
        out[name] = {}
        for v in vals:
            m = values == v
            if m.sum() >= 10:
                r = classification_report(probs[m], y[m], classes)
                out[name][str(v)] = {k: r[k] for k in ("n", "accuracy", "balanced_accuracy", "macro_f1")}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--checkpoint", default=None)
    ap.add_argument("--split", default="test")
    ap.add_argument("--out", default=None, help="output JSON path")
    args = ap.parse_args(argv)

    cfg = load_config()
    ckpt = args.checkpoint or resolve(cfg["paths"]["checkpoints_dir"]) / f"{args.task}_{cfg['training']['backbone']}.pt"
    model, meta = load_checkpoint(ckpt)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    classes = meta["classes"]
    df = pd.read_csv(resolve(cfg["paths"]["splits_dir"]) / f"{args.task}.csv", dtype=str, keep_default_na=False)
    df = df[df["split"] == args.split].reset_index(drop=True)
    cache = resolve(cfg["paths"]["cache_dir"])
    masks = resolve(cfg["paths"].get("masks_dir", "data/masks"))
    ds = EyeImageDataset(df, resolve(cfg["paths"]["datasets_root"]), classes, train=False,
                         image_size=meta.get("image_size", 224), preprocess_cfg=cfg["preprocessing"],
                         cache_root=cache if cache.exists() else None, variant=meta.get("variant", "image"),
                         masks_root=masks if masks.exists() else None)
    probs, y = predict_probs(model, DataLoader(ds, batch_size=32, num_workers=cfg["training"]["num_workers"]),
                             meta.get("temperature", 1.0), device)
    qhat = meta.get("conformal_qhat", 1.0)
    cov, size = empirical_coverage(probs, y, qhat)
    normal = next((i for i, c in enumerate(classes) if c in ("Normal", "normal", "0")), None)
    result = {"task": args.task, "checkpoint": str(ckpt), "split": args.split,
              "overall": classification_report(probs, y, classes),
              "conformal": {"target_coverage": 1 - meta.get("conformal_alpha", 0.05), "coverage": cov, "mean_set_size": size},
              "referral": referral_effect(probs, y, qhat, normal),
              "subgroups": subgroup_reports(df, probs, y, classes)}
    out = resolve(args.out) if args.out else resolve(cfg["paths"]["runs_dir"]) / f"eval_{args.task}_{args.split}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ("conformal", "referral")}, indent=2))
    print("saved", out)


if __name__ == "__main__":
    main()
