"""Anatomically verified explanation: how much of the heatmap falls on the predicted region."""
from __future__ import annotations

import cv2
import numpy as np


def attention_in_region(cam: np.ndarray, region_mask: np.ndarray) -> float:
    """Share of total heatmap mass inside the mask (0..1)."""
    if region_mask.shape != cam.shape:
        region_mask = cv2.resize(region_mask.astype(np.uint8), cam.shape[::-1], interpolation=cv2.INTER_NEAREST)
    total = float(cam.sum())
    return float(cam[region_mask > 0].sum() / total) if total > 0 else 0.0


def pointing_game_hit(cam: np.ndarray, region_mask: np.ndarray) -> bool:
    """True if the single hottest pixel lies inside the region."""
    if region_mask.shape != cam.shape:
        region_mask = cv2.resize(region_mask.astype(np.uint8), cam.shape[::-1], interpolation=cv2.INTER_NEAREST)
    y, x = np.unravel_index(np.argmax(cam), cam.shape)
    return bool(region_mask[y, x] > 0)


def verify_explanation(cam: np.ndarray, region_mask: np.ndarray | None, min_ratio: float = 0.5) -> dict:
    if region_mask is None or not region_mask.any():
        return {"attention_in_region": None, "pointing_hit": None, "reliable": None,
                "note": "no region mask available - explanation not anatomy-checked"}
    ratio = attention_in_region(cam, region_mask)
    return {"attention_in_region": round(ratio, 3), "pointing_hit": pointing_game_hit(cam, region_mask),
            "reliable": ratio >= min_ratio}
