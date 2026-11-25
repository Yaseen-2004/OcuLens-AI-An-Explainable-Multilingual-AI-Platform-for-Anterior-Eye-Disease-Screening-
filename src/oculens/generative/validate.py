"""Synthetic-data validation: FID on backbone features, and TSTR (train on synthetic, test on real).

FID here uses features from a frozen ImageNet backbone (timm), so it runs offline with the weights
in models/pretrained. Report which backbone was used: values are only comparable within one backbone.
"""
from __future__ import annotations

import numpy as np
import torch
from scipy import linalg


@torch.no_grad()
def extract_features(model: torch.nn.Module, images: torch.Tensor, batch: int = 32) -> np.ndarray:
    """images: (N,3,H,W) normalised for the backbone. Model must return pooled features (num_classes=0)."""
    model.eval()
    return torch.cat([model(images[i:i + batch]) for i in range(0, len(images), batch)]).cpu().numpy()


def frechet_distance(feat_real: np.ndarray, feat_fake: np.ndarray, eps: float = 1e-6) -> float:
    mu1, mu2 = feat_real.mean(0), feat_fake.mean(0)
    s1, s2 = np.cov(feat_real, rowvar=False), np.cov(feat_fake, rowvar=False)
    covmean = linalg.sqrtm(s1.dot(s2))
    covmean = covmean[0] if isinstance(covmean, tuple) else covmean
    if not np.isfinite(covmean).all():
        off = np.eye(s1.shape[0]) * eps
        covmean = linalg.sqrtm((s1 + off).dot(s2 + off))
        covmean = covmean[0] if isinstance(covmean, tuple) else covmean
    covmean = covmean.real
    return float(((mu1 - mu2) ** 2).sum() + np.trace(s1) + np.trace(s2) - 2 * np.trace(covmean))


def tstr(train_feats_synth: np.ndarray, y_synth: np.ndarray, test_feats_real: np.ndarray, y_real: np.ndarray) -> dict:
    """Fit a linear probe on synthetic-image features, score it on real images (balanced accuracy).

    A useful generator gives TSTR close to TRTR (train-real, test-real) on the same probe.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score

    clf = LogisticRegression(max_iter=2000, class_weight="balanced").fit(train_feats_synth, y_synth)
    return {"tstr_balanced_accuracy": float(balanced_accuracy_score(y_real, clf.predict(test_feats_real)))}
