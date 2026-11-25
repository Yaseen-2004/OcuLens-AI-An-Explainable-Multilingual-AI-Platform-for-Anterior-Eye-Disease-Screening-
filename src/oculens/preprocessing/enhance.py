"""Image enhancement: CLAHE, specular reflection removal, eye-region crop."""
from __future__ import annotations

import cv2
import numpy as np


def apply_clahe(image_rgb: np.ndarray, clip_limit: float = 2.0, tile_grid: int = 8) -> np.ndarray:
    """Local contrast enhancement on the lightness channel only (keeps colour)."""
    lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid, tile_grid))
    return cv2.cvtColor(cv2.merge((clahe.apply(l), a, b)), cv2.COLOR_LAB2RGB)


def remove_specular_reflections(image_rgb: np.ndarray, threshold: int = 245, dilate: int = 3) -> np.ndarray:
    """Inpaint small near-white highlights. A light spot on the cornea can look like a cataract."""
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
    mask = (gray >= threshold).astype(np.uint8) * 255
    if not mask.any():
        return image_rgb
    mask = cv2.dilate(mask, np.ones((dilate, dilate), np.uint8))
    return cv2.inpaint(image_rgb, mask, 3, cv2.INPAINT_TELEA)


def crop_eye_region(image_rgb: np.ndarray, mask: np.ndarray | None = None, margin: float = 0.1) -> np.ndarray:
    """Crop to the bounding box of a segmentation mask (e.g. cornea). Without a mask, return a centre square."""
    h, w = image_rgb.shape[:2]
    if mask is not None and mask.any():
        ys, xs = np.where(mask > 0)
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    else:
        s = min(h, w)
        y0, x0 = (h - s) // 2, (w - s) // 2
        y1, x1 = y0 + s - 1, x0 + s - 1
    my, mx = int((y1 - y0) * margin), int((x1 - x0) * margin)
    return image_rgb[max(0, y0 - my): min(h, y1 + my + 1), max(0, x0 - mx): min(w, x1 + mx + 1)]


def enhance(image_rgb: np.ndarray, cfg: dict | None = None) -> np.ndarray:
    cfg = cfg or {}
    out = image_rgb
    if cfg.get("remove_glare", True):
        out = remove_specular_reflections(out)
    return apply_clahe(out, cfg.get("clahe_clip_limit", 2.0), cfg.get("clahe_tile_grid", 8))
