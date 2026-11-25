"""Model input transforms. The same `enhance` step runs in training and in the deployed service."""
from __future__ import annotations

import cv2
import numpy as np
import torch
from torchvision import transforms as T

from oculens.preprocessing.enhance import enhance

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


class Enhance:
    """Downscale large photos first (enhancing a 12 MP image is slow and adds nothing at 224 px), then enhance."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.work_size = int(cfg.get("work_size", 512))

    def __call__(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        if max(h, w) > self.work_size:
            s = self.work_size / max(h, w)
            img = cv2.resize(img, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
        return enhance(img, self.cfg)


def build_transforms(train: bool, image_size: int = 224, cfg: dict | None = None):
    steps = [Enhance(cfg or {}), T.ToPILImage()]
    if train:
        steps += [
            T.RandomResizedCrop(image_size, scale=(0.75, 1.0)),
            T.RandomHorizontalFlip(),          # left and right eyes are mirror images
            T.RandomRotation(15),
            T.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1),
            T.RandomApply([T.GaussianBlur(5, sigma=(0.1, 1.5))], p=0.2),
        ]
    else:
        steps += [T.Resize(image_size), T.CenterCrop(image_size)]
    steps += [T.ToTensor(), T.Normalize(IMAGENET_MEAN, IMAGENET_STD)]
    return T.Compose(steps)


def denormalize(x: torch.Tensor) -> np.ndarray:
    """Tensor (3,H,W) normalised -> uint8 RGB image, for overlays."""
    mean = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
    std = torch.tensor(IMAGENET_STD).view(3, 1, 1)
    img = (x.cpu() * std + mean).clamp(0, 1).permute(1, 2, 0).numpy()
    return (img * 255).astype(np.uint8)
