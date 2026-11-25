"""Change detection between two scans of the same eye.

Two complementary signals:
  1. model-based: change in the classifier's probability for the tracked condition;
  2. image-based: structural difference after alignment (a learned Siamese network replaces
     this once enough longitudinal pairs are labelled).
"""
from __future__ import annotations

import cv2
import numpy as np
import torch
from torch import nn

from oculens.followup.align import align_to


def image_difference(prev_rgb: np.ndarray, curr_rgb: np.ndarray, size: int = 256) -> dict:
    prev = cv2.resize(prev_rgb, (size, size))
    aligned, info = align_to(prev, curr_rgb)
    a = cv2.cvtColor(prev, cv2.COLOR_RGB2LAB).astype(np.float32)
    b = cv2.cvtColor(aligned, cv2.COLOR_RGB2LAB).astype(np.float32)
    diff = np.abs(a - b).mean(axis=2)
    return {"alignment": info, "mean_abs_diff": round(float(diff.mean()), 3),
            "changed_fraction": round(float((diff > 20).mean()), 4)}


def classify_change(prev_prob: float, curr_prob: float, threshold: float = 0.15) -> str:
    """Probability of the tracked abnormal condition: up -> progressed, down -> improved."""
    delta = curr_prob - prev_prob
    if delta > threshold:
        return "progressed"
    if delta < -threshold:
        return "improved"
    return "stable"


def compare_scans(prev: dict, curr: dict, prev_rgb: np.ndarray | None = None,
                  curr_rgb: np.ndarray | None = None, threshold: float = 0.15) -> dict:
    """prev / curr: {'condition': str, 'probability': float, 'date': str}."""
    if prev.get("condition") == curr.get("condition"):
        status = classify_change(prev["probability"], curr["probability"], threshold)
    else:
        status = "changed_condition"
    out = {"status": status, "from": prev, "to": curr}
    if prev_rgb is not None and curr_rgb is not None:
        out["image"] = image_difference(prev_rgb, curr_rgb)
    return out


class SiameseChange(nn.Module):
    """Shared encoder on both images; head classifies progressed / stable / improved."""

    def __init__(self, encoder: nn.Module, feat_dim: int, n_classes: int = 3):
        super().__init__()
        self.encoder = encoder
        self.head = nn.Sequential(nn.Linear(feat_dim * 3, 256), nn.ReLU(), nn.Dropout(0.3), nn.Linear(256, n_classes))

    def forward(self, prev: torch.Tensor, curr: torch.Tensor) -> torch.Tensor:
        a, b = self.encoder(prev), self.encoder(curr)
        return self.head(torch.cat([a, b, b - a], dim=1))
