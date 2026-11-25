"""Image + mask transforms that keep the two aligned (used by the mask_input and region_crop variants).

The same function prepares inputs in training (random geometry) and in the app (fixed geometry),
so the model always sees identical preprocessing.
"""
from __future__ import annotations

import cv2
import numpy as np
import torch

from oculens.preprocessing.enhance import crop_eye_region, enhance
from oculens.preprocessing.transforms import IMAGENET_MEAN, IMAGENET_STD


def _shrink(img: np.ndarray, mask: np.ndarray | None, work: int):
    h, w = img.shape[:2]
    if max(h, w) > work:
        s = work / max(h, w)
        img = cv2.resize(img, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
    if mask is not None and mask.shape[:2] != img.shape[:2]:
        mask = cv2.resize(mask, img.shape[1::-1], interpolation=cv2.INTER_NEAREST)
    return img, mask


def _random_geometry(img, mask, size, rng):
    h, w = img.shape[:2]
    # random resized crop (scale 0.75-1 of the area, aspect 3/4-4/3)
    area = h * w * rng.uniform(0.75, 1.0)
    ar = np.exp(rng.uniform(np.log(3 / 4), np.log(4 / 3)))
    cw, ch = min(w, int(round(np.sqrt(area * ar)))), min(h, int(round(np.sqrt(area / ar))))
    x0, y0 = rng.integers(0, w - cw + 1), rng.integers(0, h - ch + 1)
    img, mask = img[y0:y0 + ch, x0:x0 + cw], mask[y0:y0 + ch, x0:x0 + cw]
    if rng.random() < 0.5:
        img, mask = img[:, ::-1], mask[:, ::-1]
    angle = rng.uniform(-15, 15)
    m = cv2.getRotationMatrix2D((cw / 2, ch / 2), angle, 1.0)
    img = cv2.warpAffine(np.ascontiguousarray(img), m, (cw, ch), borderMode=cv2.BORDER_REFLECT)
    mask = cv2.warpAffine(np.ascontiguousarray(mask), m, (cw, ch), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT)
    img = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
    mask = cv2.resize(mask, (size, size), interpolation=cv2.INTER_NEAREST)
    # photometric jitter on the image only
    img = np.clip(img.astype(np.float32) * rng.uniform(0.8, 1.2) + rng.uniform(-20, 20), 0, 255).astype(np.uint8)
    return img, mask


def _center_geometry(img, mask, size):
    h, w = img.shape[:2]
    s = size / min(h, w)
    img = cv2.resize(img, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
    mask = cv2.resize(mask, img.shape[1::-1], interpolation=cv2.INTER_NEAREST)
    top, left = (img.shape[0] - size) // 2, (img.shape[1] - size) // 2
    return img[top:top + size, left:left + size], mask[top:top + size, left:left + size]


def prepare_input(image_rgb: np.ndarray, mask: np.ndarray | None, variant: str, size: int, cfg: dict,
                  train: bool = False, rng: np.random.Generator | None = None) -> torch.Tensor:
    """Return the model input tensor: (3,H,W) for region_crop, (4,H,W) for mask_input."""
    img, mask = _shrink(image_rgb, mask, int(cfg.get("work_size", 512)))
    mask = np.zeros(img.shape[:2], np.uint8) if mask is None else (mask > 0).astype(np.uint8)
    if variant == "region_crop" and mask.any():
        ys, xs = np.where(mask > 0)
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        my, mx = int((y1 - y0) * 0.1), int((x1 - x0) * 0.1)
        sl = (slice(max(0, y0 - my), y1 + my + 1), slice(max(0, x0 - mx), x1 + mx + 1))
        img, mask = img[sl], mask[sl]
    img = enhance(np.ascontiguousarray(img), cfg)
    img, mask = (_random_geometry(img, mask, size, rng or np.random.default_rng()) if train
                 else _center_geometry(img, mask, size))
    x = torch.from_numpy(img.astype(np.float32) / 255.0).permute(2, 0, 1)
    x = (x - torch.tensor(IMAGENET_MEAN).view(3, 1, 1)) / torch.tensor(IMAGENET_STD).view(3, 1, 1)
    if variant == "mask_input":
        x = torch.cat([x, torch.from_numpy(mask.astype(np.float32))[None]], 0)
    return x


def prepare_mask(image_rgb: np.ndarray, mask: np.ndarray, variant: str, size: int, cfg: dict) -> np.ndarray:
    """The region mask in the model's input geometry (eval mode), for the anatomy check."""
    img, m = _shrink(image_rgb, mask, int(cfg.get("work_size", 512)))
    m = (m > 0).astype(np.uint8)
    if variant == "region_crop" and m.any():
        ys, xs = np.where(m > 0)
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        my, mx = int((y1 - y0) * 0.1), int((x1 - x0) * 0.1)
        sl = (slice(max(0, y0 - my), y1 + my + 1), slice(max(0, x0 - mx), x1 + mx + 1))
        img, m = img[sl], m[sl]
    return _center_geometry(img, m, size)[1]


__all__ = ["prepare_input", "prepare_mask", "crop_eye_region"]
