"""Load a trained U-Net and predict a binary region mask (e.g. cornea) for an RGB image."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import torch

from oculens.models.unet import UNet


class Segmenter:
    def __init__(self, checkpoint: str | Path, threshold: float = 0.5, device: str | None = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        ckpt = torch.load(checkpoint, map_location="cpu", weights_only=False)
        self.model = UNet()
        self.model.load_state_dict(ckpt["state_dict"])
        self.model.to(self.device).eval()
        self.size = ckpt["meta"].get("size", 256)
        self.target = ckpt["meta"].get("target", "cornea")
        self.threshold = threshold

    @torch.no_grad()
    def predict(self, image_rgb: np.ndarray) -> np.ndarray:
        """Returns a uint8 mask (0/1) at the input image's resolution."""
        h, w = image_rgb.shape[:2]
        x = cv2.resize(image_rgb, (self.size, self.size)).astype(np.float32) / 255.0
        logits = self.model(torch.from_numpy(x).permute(2, 0, 1)[None].to(self.device))[0, 0].cpu().numpy()
        mask = (1 / (1 + np.exp(-logits)) > self.threshold).astype(np.uint8)
        return cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)


def model_input_mask(mask: np.ndarray, image_size: int) -> np.ndarray:
    """Apply the classifier's eval geometry (resize shorter side + centre crop) to a mask."""
    h, w = mask.shape
    s = image_size / min(h, w)
    m = cv2.resize(mask, (round(w * s), round(h * s)), interpolation=cv2.INTER_NEAREST)
    top, left = (m.shape[0] - image_size) // 2, (m.shape[1] - image_size) // 2
    return m[top: top + image_size, left: left + image_size]
