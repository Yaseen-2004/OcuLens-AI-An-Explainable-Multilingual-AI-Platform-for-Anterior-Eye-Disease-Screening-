"""Monte Carlo dropout: keep dropout active at inference and average several passes."""
from __future__ import annotations

import torch
from torch import nn


def enable_dropout(model: nn.Module) -> None:
    for m in model.modules():
        if isinstance(m, nn.Dropout) or m.__class__.__name__.lower().startswith("dropout"):
            m.train()


@torch.no_grad()
def mc_dropout_predict(model: nn.Module, x: torch.Tensor, passes: int = 10, temperature: float = 1.0):
    """Returns (mean probabilities, predictive entropy) for a batch."""
    model.eval()
    enable_dropout(model)
    probs = torch.stack([torch.softmax(model(x) / temperature, dim=1) for _ in range(passes)])
    model.eval()
    mean = probs.mean(0)
    entropy = -(mean * mean.clamp_min(1e-12).log()).sum(1)
    return mean, entropy
