"""Losses for imbalanced medical classes."""
from __future__ import annotations

import torch
from torch import nn
import torch.nn.functional as F


class FocalLoss(nn.Module):
    """Multi-class focal loss with optional per-class weights (alpha)."""

    def __init__(self, gamma: float = 2.0, weight: torch.Tensor | None = None):
        super().__init__()
        self.gamma = gamma
        self.register_buffer("weight", weight if weight is not None else None)

    def forward(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        logp = F.log_softmax(logits, dim=1)
        ce = F.nll_loss(logp, target, weight=self.weight, reduction="none")
        pt = logp.gather(1, target.unsqueeze(1)).squeeze(1).exp()
        return ((1 - pt) ** self.gamma * ce).mean()


def class_weights(counts, device="cpu") -> torch.Tensor:
    """Inverse-frequency weights normalised to mean 1. Empty classes get weight 0."""
    c = torch.tensor(counts, dtype=torch.float32)
    w = torch.where(c > 0, c.sum() / (len(c) * c.clamp(min=1)), torch.zeros_like(c))
    return (w / w[w > 0].mean()).to(device)
