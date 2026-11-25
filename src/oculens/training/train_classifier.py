"""Train an image classifier for one task defined in configs/default.yaml.

Usage:
    python -m oculens.training.train_classifier --task keratitis
    python -m oculens.training.train_classifier --task keratitis --variant mask_input      # RQ1 option A
    python -m oculens.training.train_classifier --task keratitis --variant region_crop     # RQ1 option B
    python -m oculens.training.train_classifier --task ulcer_pattern --variant multitask   # RQ1 option C
    python -m oculens.training.train_classifier --task keratitis --synthetic               # add DDPM images (train only)
    python -m oculens.training.train_classifier --task keratitis --resume                  # continue an interrupted run
    python -m oculens.training.train_classifier --task keratitis --dry-run                 # 1 epoch, few images, separate folder

Model selection uses validation balanced accuracy (mean sensitivity). Training stops early when it
has not improved for `patience` epochs. The last state is saved every epoch so a crash can resume.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, WeightedRandomSampler

from oculens.config import load_config, resolve
from oculens.data.dataset import EyeImageDataset
from oculens.models.classifier import VARIANTS, MultiTaskNet, build_model, save_checkpoint
from oculens.training.losses import FocalLoss, class_weights
from oculens.training.metrics import classification_report
from oculens.uncertainty.calibration import fit_temperature
from oculens.uncertainty.conformal import fit_conformal_threshold


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


@torch.no_grad()
def predict_logits(model, loader, device) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    logits, ys = [], []
    for batch in loader:
        x, y = batch[0], batch[1]
        logits.append(model(x.to(device)).cpu())
        ys.append(y)
    return torch.cat(logits).numpy(), torch.cat(ys).numpy()


def softmax(z: np.ndarray, t: float = 1.0) -> np.ndarray:
    z = z / t
    z = z - z.max(1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(1, keepdims=True)


def load_synthetic(task: str, csv_path: str | None = None) -> pd.DataFrame:
    """Synthetic (DDPM) or harmonised (CycleGAN) images - training split only, by construction."""
    p = resolve(csv_path) if csv_path else resolve("data/synthetic") / f"{task}.csv"
    if not p.exists():
        raise SystemExit(f"{p} not found - run python -m oculens.generative.train_ddpm --task {task} first")
    syn = pd.read_csv(p, dtype=str, keep_default_na=False)
    syn = syn[syn["split"] == "train"].copy()
    for col, val in (("extra", "{}"), ("site", "synthetic"), ("dataset", "synthetic"), ("mask_path", "")):
        if col not in syn:
            syn[col] = val
    return syn


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--config", default=None)
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--backbone", default=None)
    ap.add_argument("--variant", choices=VARIANTS, default="image")
    ap.add_argument("--synthetic", action="store_true", help="add synthetic images to the training split")
    ap.add_argument("--synthetic-csv", default=None, help="other training-only image list, e.g. CycleGAN output CSV")
    ap.add_argument("--patience", type=int, default=None, help="early stopping patience in epochs (0 = off)")
    ap.add_argument("--resume", action="store_true", help="continue from the last saved epoch")
    ap.add_argument("--dry-run", action="store_true", help="1 epoch on a few images, outputs to experiments/dryrun")
    ap.add_argument("--limit", type=int, default=0, help="use at most N training images")
    ap.add_argument("--no-pretrained", action="store_true")
    ap.add_argument("--batch-size", type=int, default=None)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--image-size", type=int, default=None)
    ap.add_argument("--lr", type=float, default=None)
    ap.add_argument("--seed", type=int, default=None, help="different seeds -> deep-ensemble members")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    for key, val in (("batch_size", args.batch_size), ("num_workers", args.workers), ("lr", args.lr)):
        if val is not None:
            cfg["training"][key] = val
    if args.seed is not None:
        cfg["training"]["seed"] = args.seed
    if args.image_size:
        cfg["preprocessing"]["image_size"] = args.image_size
    if args.dry_run:
        args.limit = args.limit or 24
        args.epochs = args.epochs or 1
        cfg["training"]["batch_size"] = min(cfg["training"]["batch_size"], 8)
        cfg["training"]["num_workers"] = 0
        out = resolve("experiments/dryrun")
        cfg["paths"]["checkpoints_dir"], cfg["paths"]["runs_dir"] = str(out / "checkpoints"), str(out / "runs")
    tcfg, task = cfg["training"], cfg["tasks"][args.task]
    classes = [str(c) for c in task["classes"]]
    backbone = args.backbone or tcfg["backbone"]
    epochs = args.epochs or tcfg["epochs"]
    patience = tcfg.get("patience", 0) if args.patience is None else args.patience
    aux_label = task.get("aux_label") if args.variant == "multitask" else None
    aux_classes = [str(c) for c in task.get("aux_classes", [])] if aux_label else None
    if args.variant == "multitask" and not aux_label:
        raise SystemExit(f"task {args.task} has no aux_label in the config; multitask needs one (e.g. ulcer_pattern)")
    set_seed(tcfg["seed"])
    device = "cuda" if torch.cuda.is_available() else "cpu"

    split_csv = resolve(cfg["paths"]["splits_dir"]) / f"{args.task}.csv"
    if not split_csv.exists():
        raise SystemExit(f"{split_csv} not found - run scripts/make_splits.py first")
    df = pd.read_csv(split_csv, dtype=str, keep_default_na=False)
    tr, va, te = (df[df["split"] == s] for s in ("train", "val", "test"))
    n_syn = 0
    if args.synthetic:
        syn = load_synthetic(args.task, args.synthetic_csv)
        syn = syn[syn["label"].isin(classes)]
        n_syn = len(syn)
        tr = pd.concat([tr, syn[[c for c in tr.columns if c in syn.columns]]], ignore_index=True)
    if args.limit:
        tr = tr.sample(min(args.limit, len(tr)), random_state=tcfg["seed"])
        va = va.head(max(8, args.limit // 3))
        te = te.head(max(8, args.limit // 3))

    root = resolve(cfg["paths"]["datasets_root"])
    cache = resolve(cfg["paths"].get("cache_dir", "data/cache"))
    masks = resolve(cfg["paths"].get("masks_dir", "data/masks"))
    pcfg, size = cfg["preprocessing"], cfg["preprocessing"]["image_size"]
    kw_ds = dict(image_size=size, preprocess_cfg=pcfg, cache_root=cache if cache.exists() else None,
                 variant=args.variant, masks_root=masks if masks.exists() else None,
                 aux_label=aux_label, aux_classes=aux_classes)
    ds_tr = EyeImageDataset(tr, root, classes, train=True, **kw_ds)
    ds_va = EyeImageDataset(va, root, classes, train=False, **kw_ds)
    ds_te = EyeImageDataset(te, root, classes, train=False, **kw_ds)
    if args.variant in ("mask_input", "region_crop"):
        print(f"masks missing: train {ds_tr.missing_masks}/{len(ds_tr)}, val {ds_va.missing_masks}/{len(ds_va)}, "
              f"test {ds_te.missing_masks}/{len(ds_te)} (missing -> empty mask / full image)")

    counts = ds_tr.class_counts()
    # Balanced sampling so rare classes (e.g. fungal keratitis) are seen every epoch.
    sample_w = (1.0 / np.maximum(counts, 1))[ds_tr.df["label"].astype(str).map(ds_tr.class_to_idx).to_numpy()]
    sampler = WeightedRandomSampler(torch.tensor(sample_w, dtype=torch.double), num_samples=len(ds_tr), replacement=True)
    kw = dict(batch_size=tcfg["batch_size"], num_workers=tcfg["num_workers"])
    dl_tr = DataLoader(ds_tr, sampler=sampler, **kw)
    dl_va = DataLoader(ds_va, shuffle=False, **kw)
    dl_te = DataLoader(ds_te, shuffle=False, **kw)

    meta = {"backbone": backbone, "classes": classes, "task": args.task, "image_size": size, "dropout": tcfg["dropout"],
            "region": task["region"], "variant": args.variant, "synthetic_images": n_syn,
            "aux_label": aux_label, "aux_classes": aux_classes}
    model = build_model(meta, pretrained=tcfg["pretrained"] and not args.no_pretrained).to(device)
    w = class_weights(counts, device)
    loss_fn = FocalLoss(tcfg["focal_gamma"], w) if tcfg["loss"] == "focal" else torch.nn.CrossEntropyLoss(weight=w)
    aux_weight = float(tcfg.get("aux_weight", 0.5))
    opt = torch.optim.AdamW(model.parameters(), lr=tcfg["lr"], weight_decay=tcfg["weight_decay"])
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)

    name = f"{args.task}_{backbone}"
    name += "" if args.variant == "image" else f"_{args.variant}"
    name += "_syn" if args.synthetic else ""
    name += f"_s{args.seed}" if args.seed is not None else ""
    ckpt_dir = resolve(cfg["paths"]["checkpoints_dir"])
    ckpt_path, last_path = ckpt_dir / f"{name}.pt", ckpt_dir / f"{name}_last.pt"

    best, history, bad, start = -1.0, [], 0, 1
    if args.resume and last_path.exists():
        st = torch.load(last_path, map_location=device, weights_only=False)
        model.load_state_dict(st["model"])
        opt.load_state_dict(st["opt"])
        best, history, bad, start = st["best"], st["history"], st["bad"], st["epoch"] + 1
        if st["sched"].get("T_max") == epochs:
            sched.load_state_dict(st["sched"])
        else:
            # extending a finished run (e.g. 10 -> 50 epochs): re-plan the cosine schedule for the new length
            for _ in range(st["epoch"]):
                sched.step()
            bad = 0
            print(f"extending run from {st['sched'].get('T_max')} to {epochs} epochs (learning-rate schedule re-planned)")
        print(f"resumed from epoch {st['epoch']} (best val balanced acc {best:.4f})")
    elif args.resume:
        print("no saved state to resume from - starting fresh")

    run_dir = resolve(cfg["paths"]["runs_dir"]) / f"{name}_{time.strftime('%Y%m%d-%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"task={args.task} variant={args.variant} backbone={backbone} device={device} train={len(ds_tr)} "
          f"(synthetic {n_syn}) val={len(ds_va)} test={len(ds_te)} epochs={epochs} patience={patience}")
    print("train class counts:", dict(zip(classes, counts.tolist())))

    stopped_early = False
    for epoch in range(start, epochs + 1):
        model.train()
        t0, total = time.time(), 0.0
        for batch in dl_tr:
            x, y = batch[0].to(device), batch[1].to(device)
            opt.zero_grad()
            if isinstance(model, MultiTaskNet):
                main_out, aux_out = model.forward_both(x)
                loss = loss_fn(main_out, y)
                aux_t = batch[2].to(device)
                if (aux_t >= 0).any():
                    loss = loss + aux_weight * F.cross_entropy(aux_out, aux_t, ignore_index=-1)
            else:
                loss = loss_fn(model(x), y)
            loss.backward()
            opt.step()
            total += loss.item() * len(y)
        sched.step()
        lv, yv = predict_logits(model, dl_va, device)
        score = classification_report(softmax(lv), yv, classes)["balanced_accuracy"]
        history.append({"epoch": epoch, "train_loss": total / len(ds_tr), "val_balanced_acc": score,
                        "seconds": round(time.time() - t0, 1)})
        print(json.dumps(history[-1]), flush=True)
        if score > best:
            best, bad = score, 0
            save_checkpoint(ckpt_path, model, meta)
        else:
            bad += 1
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "sched": sched.state_dict(),
                    "epoch": epoch, "best": best, "history": history, "bad": bad}, last_path)
        if patience and bad >= patience:
            stopped_early = True
            print(f"early stop: no improvement for {patience} epochs (best {best:.4f})")
            break

    # Reload best weights, calibrate on validation, then evaluate once on test.
    model.load_state_dict(torch.load(ckpt_path, map_location=device, weights_only=False)["state_dict"])
    lv, yv = predict_logits(model, dl_va, device)
    temperature = fit_temperature(lv, yv)
    qhat = fit_conformal_threshold(softmax(lv, temperature), yv, alpha=cfg["uncertainty"]["conformal_alpha"])
    lt, yt = predict_logits(model, dl_te, device)
    test_rep = classification_report(softmax(lt, temperature), yt, classes)

    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    ckpt["meta"].update({"temperature": temperature, "conformal_qhat": qhat,
                         "conformal_alpha": cfg["uncertainty"]["conformal_alpha"]})
    torch.save(ckpt, ckpt_path)

    result = {"task": args.task, "variant": args.variant, "synthetic_images": n_syn, "backbone": backbone,
              "dry_run": args.dry_run, "best_val_balanced_acc": best, "stopped_early": stopped_early,
              "temperature": temperature, "conformal_qhat": qhat, "test": test_rep, "history": history,
              "checkpoint": str(ckpt_path)}
    (run_dir / "result.json").write_text(json.dumps(result, indent=2))
    print("test:", json.dumps({k: v for k, v in test_rep.items() if k not in ("per_class", "confusion_matrix")}))
    print("saved", ckpt_path, "and", run_dir / "result.json")
    return result


if __name__ == "__main__":
    main()
