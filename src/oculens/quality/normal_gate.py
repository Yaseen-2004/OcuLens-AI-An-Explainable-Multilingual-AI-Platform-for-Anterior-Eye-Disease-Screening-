"""Normal-eye check: does a front-of-eye photo look healthy?

A logistic-regression head on the pooled features of the deployed keratitis EfficientNet-B0 (the same features
as the eye check), trained on healthy eyes against diseased ones (conjunctivitis, uveitis, cataract, eyelid
disease, infectious keratitis, corneal ulcer).

Resolution is equalised on purpose. The only healthy-eye photos available are ~55 px web thumbnails while the
diseased photos are 150-2600 px, so a model could learn "small and blurry = healthy". Every image is therefore
shrunk to the same thumbnail size (short side 56 px) before features are taken, in training and in the portal.

The decision threshold is set on validation images so that at most ~2% of diseased eyes are called normal. Below
the threshold nothing changes: the disease models and the referral gate decide as before. A low disease-model
confidence alone is never reported as normal.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

THUMB_SIDE = 56


def thumbnail(img: np.ndarray | Image.Image, side: int = THUMB_SIDE) -> np.ndarray:
    """Shrink so the short side is `side` px (never enlarges), keeping the aspect ratio."""
    im = img if isinstance(img, Image.Image) else Image.fromarray(img)
    im = im.convert("RGB")
    w, h = im.size
    s = side / min(w, h)
    if s < 1:
        im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
    return np.asarray(im)


def features(model, imgs, cfg: dict | None, image_size: int = 224, batch: int = 64) -> np.ndarray:
    """L2-normalised pooled backbone features for a list of RGB arrays (thumbnails)."""
    import torch
    from oculens.preprocessing.transforms import build_transforms
    tf = build_transforms(train=False, image_size=image_size, cfg=cfg)
    out = []
    model.eval()
    with torch.no_grad():
        for i in range(0, len(imgs), batch):
            x = torch.stack([tf(a) for a in imgs[i:i + batch]])
            f = model.forward_features(x)
            v = torch.nn.functional.adaptive_avg_pool2d(f, 1).flatten(1)
            out.append(torch.nn.functional.normalize(v, dim=1).numpy())
    return np.concatenate(out, 0).astype("float32")


def p_normal(gate: dict, feats: np.ndarray) -> np.ndarray:
    """Probability that each image shows a healthy eye."""
    z = feats @ gate["coef"].T + gate["intercept"]
    return 1.0 / (1.0 + np.exp(-z.ravel()))
