"""Explanation quality metrics over a test set (RQ4).

  attention-in-region  share of heatmap mass on the expected anatomical region (mask)
  pointing game        is the hottest pixel inside the region?
  deletion AUC         remove the most-attended pixels step by step; a faithful map makes the
                       predicted-class probability fall fast (lower AUC = more faithful)

Usage:
    python -m oculens.explain.evaluate --task ulcer_pattern --mask cornea --method gradcam++
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
import torch
from PIL import Image

from oculens.config import load_config, resolve
from oculens.explain.gradcam import GradCAM
from oculens.explain.region_check import attention_in_region, pointing_game_hit
from oculens.models.classifier import load_checkpoint
from oculens.preprocessing.joint import prepare_input, prepare_mask
from oculens.preprocessing.transforms import build_transforms


@torch.no_grad()
def deletion_auc(model, x: torch.Tensor, cam: np.ndarray, cls: int, steps: int = 10) -> float:
    order = np.argsort(-cam.ravel())
    n = len(order)
    probs = []
    for k in range(steps + 1):
        xk = x.clone()
        if k:
            idx = order[: int(n * k / steps)]
            m = torch.ones(n, device=x.device)
            m[torch.as_tensor(idx, device=x.device)] = 0
            xk = xk * m.view(1, 1, *cam.shape)
        probs.append(torch.softmax(model(xk), 1)[0, cls].item())
    trapezoid = getattr(np, "trapezoid", None) or np.trapz  # numpy 2 renamed trapz
    return float(trapezoid(probs, dx=1.0 / steps))


def evaluate(task: str, mask_key: str = "cornea", plus_plus: bool = True, limit: int = 0, checkpoint: str | None = None) -> dict:
    cfg = load_config()
    model, meta = load_checkpoint(checkpoint or resolve(cfg["paths"]["checkpoints_dir"]) / f"{task}_{cfg['training']['backbone']}.pt")
    variant = meta.get("variant", "image")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    df = pd.read_csv(resolve(cfg["paths"]["splits_dir"]) / f"{task}.csv", dtype=str, keep_default_na=False)
    df = df[df["split"] == "test"]
    df["mask"] = df["extra"].map(lambda s: json.loads(s).get("cornea_mask", "")) if mask_key == "cornea" else df["mask_path"]
    df = df[df["mask"] != ""]
    if limit:
        df = df.head(limit)
    root = resolve(cfg["paths"]["datasets_root"])
    size = meta.get("image_size", 224)
    tf = build_transforms(train=False, image_size=size, cfg=cfg["preprocessing"])
    cam_engine = GradCAM(model, plus_plus=plus_plus)
    rows = []
    try:
        for _, r in df.iterrows():
            img = np.array(Image.open(root / r["image_path"]).convert("RGB"))
            m_arr = np.array(Image.open(root / r["mask"]).convert("L").resize(img.shape[1::-1], Image.NEAREST))
            if mask_key == "ulcer":
                m_arr = 255 - m_arr  # SUSTech ulcer labels mark the lesion in black on white
            if variant in ("mask_input", "region_crop"):
                # the region the model is asked about; for these variants the input mask is the cornea
                cornea_rel = json.loads(r["extra"]).get("cornea_mask", "")
                cm = np.array(Image.open(root / cornea_rel).convert("L").resize(img.shape[1::-1], Image.NEAREST)) if cornea_rel else None
                x = prepare_input(img, cm, variant, size, cfg["preprocessing"]).unsqueeze(0)
                mask = prepare_mask(img, (m_arr > 127).astype(np.uint8), variant, size, cfg["preprocessing"])
            else:
                x = tf(img).unsqueeze(0)
                # Apply the same resize + centre crop to the mask as to the image.
                h, w = m_arr.shape
                s = size / min(h, w)
                m_res = np.array(Image.fromarray(m_arr).resize((round(w * s), round(h * s)), Image.NEAREST))
                top, left = (m_res.shape[0] - size) // 2, (m_res.shape[1] - size) // 2
                mask = (m_res[top: top + size, left: left + size] > 127).astype(np.uint8)
            x = x.to(device)
            cam, cls = cam_engine(x)
            rows.append({"image": r["image_path"], "ratio": attention_in_region(cam, mask),
                         "pointing_hit": pointing_game_hit(cam, mask), "mask_area": float(mask.mean()),
                         "deletion_auc": deletion_auc(model, x, cam, cls)})
    finally:
        cam_engine.remove()
    res = pd.DataFrame(rows)
    min_ratio = cfg["explain"]["attention_in_region_min"]
    summary = {
        "task": task, "mask": mask_key, "method": "Grad-CAM++" if plus_plus else "Grad-CAM", "n": len(res),
        "mean_attention_in_region": round(float(res["ratio"].mean()), 3),
        "mean_mask_area": round(float(res["mask_area"].mean()), 3),
        "share_reliable": round(float((res["ratio"] >= min_ratio).mean()), 3),
        "pointing_game": round(float(res["pointing_hit"].mean()), 3),
        "mean_deletion_auc": round(float(res["deletion_auc"].mean()), 3),
    }
    return {"summary": summary, "per_image": rows}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="ulcer_pattern")
    ap.add_argument("--mask", choices=["cornea", "ulcer"], default="cornea")
    ap.add_argument("--method", choices=["gradcam", "gradcam++"], default="gradcam++")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--checkpoint", default=None)
    ap.add_argument("--out", default=None, help="output JSON path (default experiments/runs/explain_*.json)")
    args = ap.parse_args(argv)
    out = evaluate(args.task, args.mask, args.method == "gradcam++", args.limit, args.checkpoint)
    cfg = load_config()
    dest = resolve(args.out) if args.out else resolve(cfg["paths"]["runs_dir"]) / f"explain_{args.task}_{args.mask}_{args.method}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(json.dumps(out["summary"], indent=2))
    print("saved", dest)


if __name__ == "__main__":
    main()
