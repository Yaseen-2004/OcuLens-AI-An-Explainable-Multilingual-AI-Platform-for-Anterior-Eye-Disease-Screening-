"""Train the normal-eye check (healthy vs diseased front-of-eye photo).

    python scripts/train_normal_gate.py

Data (data/manifest.csv): healthy = eye_disease_web "Normal" (649); diseased = eye_disease_web Conjunctivitis,
Uveitis, Cataract, Eyelid (1,649), infectious keratitis (1,373), SUSTech corneal ulcer (712) and a sample of
slit-lamp cataract images. Trachoma photos (the inside of the eyelid) are a different view and are left out.

Leakage control: images are grouped by patient where the dataset has patients, and the web photos are grouped by
near-duplicates (feature cosine >= 0.97) because that dataset contains augmented copies. Groups are split
60/20/20 into train / validation / test within each source and label.

Outputs: models/checkpoints/normal_gate.npz (head + threshold) and experiments/normal_gate/metrics.json.
"""
from __future__ import annotations

import csv
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from oculens.config import load_config  # noqa: E402
from oculens.models.classifier import load_checkpoint  # noqa: E402
from oculens.quality.normal_gate import THUMB_SIDE, features, p_normal, thumbnail  # noqa: E402

DATASETS = ROOT / "datasets"
OUT = ROOT / "models" / "checkpoints" / "normal_gate.npz"
METRICS = ROOT / "experiments" / "normal_gate" / "metrics.json"
MAX_FALSE_NORMAL = 0.005         # at most 0.5% of the hardest diseased eyes may be called normal
SEED = 7


def load_rows():
    rows = list(csv.DictReader(open(ROOT / "data" / "manifest.csv", encoding="utf-8")))
    random.seed(SEED)
    out = []
    cat = [r for r in rows if r["dataset"] == "nuclear_cataract"]
    keep_cat = set(id(r) for r in random.sample(cat, 300))
    for r in rows:
        d = r["dataset"]
        if d == "trachoma" or (d == "nuclear_cataract" and id(r) not in keep_cat):
            continue
        y = 1 if (d == "eye_disease_web" and r["label"] == "Normal") else 0
        src = "web_" + r["label"].lower() if d == "eye_disease_web" else d
        out.append({"path": DATASETS / r["image_path"], "y": y, "src": src, "group": r["group"] or r["image_path"]})
    return out


def load_thumb(p: Path) -> np.ndarray:
    im = Image.open(p)
    im.draft("RGB", (THUMB_SIDE * 4, THUMB_SIDE * 4))    # fast JPEG decode at reduced size
    return thumbnail(im)


def near_dup_groups(rows, feats, thr=0.97):
    """Union-find over the web photos: near-identical images share a group."""
    idx = [i for i, r in enumerate(rows) if r["src"].startswith("web_")]
    parent = {i: i for i in idx}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    F = feats[idx]
    S = F @ F.T
    n_pairs = 0
    for a in range(len(idx)):
        for b in np.nonzero(S[a, a + 1:] >= thr)[0] + a + 1:
            ra, rb = find(idx[a]), find(idx[b])
            if ra != rb:
                parent[ra] = rb
                n_pairs += 1
    for i in idx:
        rows[i]["group"] = "web_dup_" + str(find(i))
    return n_pairs


def split_groups(rows):
    by = defaultdict(lambda: defaultdict(list))
    for i, r in enumerate(rows):
        by[(r["src"], r["y"])][r["group"]].append(i)
    split = {}
    rng = random.Random(SEED)
    for key, groups in by.items():
        g = list(groups)
        rng.shuffle(g)
        n = len(g)
        for k, gid in enumerate(g):
            s = "train" if k < 0.6 * n else ("val" if k < 0.8 * n else "test")
            for i in groups[gid]:
                split[i] = s
    return [split[i] for i in range(len(rows))]


def main():
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    cfg = load_config()
    rows = load_rows()
    print(f"{len(rows)} images ({sum(r['y'] for r in rows)} healthy)", flush=True)
    model, meta = load_checkpoint(ROOT / "models" / "checkpoints" / "keratitis_efficientnet_b0_syn.pt")
    t0 = time.time()
    thumbs, ok = [], []
    for i, r in enumerate(rows):
        try:
            thumbs.append(load_thumb(r["path"]))
            ok.append(i)
        except Exception as e:  # noqa: BLE001
            print("skip", r["path"].name, e)
    rows = [rows[i] for i in ok]
    print(f"loaded {len(rows)} thumbnails in {time.time() - t0:.0f}s", flush=True)
    feats = features(model, thumbs, cfg["preprocessing"], meta.get("image_size", 224))
    print(f"features {feats.shape} in {time.time() - t0:.0f}s", flush=True)
    merged = near_dup_groups(rows, feats)
    print(f"near-duplicate merges among web photos: {merged}", flush=True)
    sp = np.array(split_groups(rows))
    y = np.array([r["y"] for r in rows])
    src = np.array([r["src"] for r in rows])
    import os
    if os.environ.get("NORMAL_GATE_CACHE"):          # optional: keep features for threshold analysis
        np.savez(os.environ["NORMAL_GATE_CACHE"], feats=feats, y=y, src=src, sp=sp)
    tr, va, te = sp == "train", sp == "val", sp == "test"
    dev = tr | va
    best = None
    for C in (0.1, 0.3, 1.0, 3.0, 10.0):                 # choose regularisation on validation
        clf = LogisticRegression(C=C, class_weight="balanced", max_iter=5000).fit(feats[tr], y[tr])
        auc = roc_auc_score(y[va], clf.predict_proba(feats[va])[:, 1])
        print(f"C={C}: val AUROC {auc:.4f}")
        if best is None or auc > best[0]:
            best = (auc, C)
    C = best[1]
    # Threshold from out-of-fold scores on train+val (5 folds), set on the hardest negatives: diseased photos from
    # the same web source as the healthy ones (clinical slit-lamp photos are far easier). At most 0.5% of them pass.
    from sklearn.model_selection import StratifiedKFold
    idx = np.nonzero(dev)[0]
    oof = np.zeros(len(y))
    strat = np.array([f"{a}_{b}" for a, b in zip(src[idx], y[idx])])
    for a, b in StratifiedKFold(5, shuffle=True, random_state=SEED).split(idx, strat):
        m = LogisticRegression(C=C, class_weight="balanced", max_iter=5000).fit(feats[idx[a]], y[idx[a]])
        oof[idx[b]] = m.predict_proba(feats[idx[b]])[:, 1]
    hard = dev & (y == 0) & np.char.startswith(src, "web_")
    thr = float(np.quantile(oof[hard], 1 - MAX_FALSE_NORMAL))
    clf = LogisticRegression(C=C, class_weight="balanced", max_iter=5000).fit(feats[dev], y[dev])   # final head
    gate = {"coef": clf.coef_.astype("float32"), "intercept": clf.intercept_.astype("float32")}
    pt = p_normal(gate, feats[te])
    yt, st = y[te], src[te]
    res = {
        "C": C, "threshold": thr, "thumb_side": THUMB_SIDE, "max_false_normal_hard": MAX_FALSE_NORMAL,
        "hard_negatives_for_threshold": int(hard.sum()),
        "n": {"train": int(tr.sum()), "val": int(va.sum()), "test": int(te.sum()),
              "healthy_test": int((yt == 1).sum()), "diseased_test": int((yt == 0).sum())},
        "test_auroc": float(roc_auc_score(yt, pt)),
        "test_auroc_same_source": float(roc_auc_score(yt[np.char.startswith(st, "web_")],
                                                      pt[np.char.startswith(st, "web_")])),
        "healthy_called_normal": float((pt[yt == 1] >= thr).mean()),
        "diseased_called_normal": float((pt[yt == 0] >= thr).mean()),
        "diseased_called_normal_by_source": {
            s: {"n": int(((st == s) & (yt == 0)).sum()), "rate": float((pt[(st == s) & (yt == 0)] >= thr).mean())}
            for s in sorted(set(st[yt == 0]))},
    }
    print(json.dumps(res, indent=1))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez(OUT, coef=gate["coef"], intercept=gate["intercept"], threshold=np.float32(thr),
             thumb_side=np.int32(THUMB_SIDE), image_size=np.int32(meta.get("image_size", 224)))
    METRICS.parent.mkdir(parents=True, exist_ok=True)
    METRICS.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("saved", OUT, "and", METRICS)


if __name__ == "__main__":
    main()
