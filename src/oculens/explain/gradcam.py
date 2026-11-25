"""Grad-CAM and Grad-CAM++ for any CNN backbone (hooks on the last convolution by default)."""
from __future__ import annotations

import cv2
import numpy as np
import torch
from torch import nn


def last_conv_layer(model: nn.Module) -> nn.Module:
    last = None
    for m in model.modules():
        if isinstance(m, nn.Conv2d):
            last = m
    if last is None:
        raise ValueError("model has no Conv2d layer; use attention rollout for transformers")
    return last


class GradCAM:
    def __init__(self, model: nn.Module, target_layer: nn.Module | None = None, plus_plus: bool = False):
        self.model = model
        self.layer = target_layer or last_conv_layer(model)
        self.plus_plus = plus_plus
        self._acts = self._grads = None
        self._h1 = self.layer.register_forward_hook(self._save_acts)
        self._h2 = self.layer.register_full_backward_hook(self._save_grads)

    def _save_acts(self, _m, _i, out):
        self._acts = out.detach()

    def _save_grads(self, _m, _gi, go):
        self._grads = go[0].detach()

    def remove(self):
        self._h1.remove()
        self._h2.remove()

    def __call__(self, x: torch.Tensor, class_idx: int | None = None) -> tuple[np.ndarray, int]:
        """x: (1,3,H,W). Returns (heatmap HxW in [0,1], class index explained)."""
        self.model.eval()
        x = x.clone().requires_grad_(True)
        logits = self.model(x)
        idx = int(logits.argmax(1).item()) if class_idx is None else class_idx
        self.model.zero_grad()
        logits[0, idx].backward()
        a, g = self._acts[0], self._grads[0]               # (C,h,w)
        if self.plus_plus:
            g2, g3 = g ** 2, g ** 3
            denom = 2 * g2 + (a * g3).sum((1, 2), keepdim=True)
            alpha = g2 / torch.where(denom != 0, denom, torch.ones_like(denom))
            weights = (alpha * torch.relu(g)).sum((1, 2))
        else:
            weights = g.mean((1, 2))
        cam = torch.relu((weights[:, None, None] * a).sum(0)).cpu().numpy()
        cam = cv2.resize(cam, (x.shape[-1], x.shape[-2]), interpolation=cv2.INTER_LINEAR)
        cam = cam - cam.min()
        return (cam / cam.max() if cam.max() > 0 else cam), idx


def overlay(image_rgb: np.ndarray, cam: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    heat = cv2.applyColorMap((cv2.resize(cam, image_rgb.shape[1::-1]) * 255).astype(np.uint8), cv2.COLORMAP_JET)
    heat = cv2.cvtColor(heat, cv2.COLOR_BGR2RGB)
    return (alpha * heat + (1 - alpha) * image_rgb).astype(np.uint8)
