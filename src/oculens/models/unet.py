"""Small U-Net baseline for eye-layer segmentation (cornea, ulcer ...).

Kept dependency-free so it trains on a CPU; nnU-Net / TransUNet / MedSAM are the planned comparisons.
"""
from __future__ import annotations

import torch
from torch import nn
import torch.nn.functional as F


def _block(cin: int, cout: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(cin, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
        nn.Conv2d(cout, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
    )


class UNet(nn.Module):
    def __init__(self, in_ch: int = 3, num_classes: int = 1, base: int = 32):
        super().__init__()
        ch = [base, base * 2, base * 4, base * 8]
        self.downs = nn.ModuleList()
        prev = in_ch
        for c in ch:
            self.downs.append(_block(prev, c))
            prev = c
        self.bottleneck = _block(ch[-1], ch[-1] * 2)
        self.ups = nn.ModuleList()
        self.up_blocks = nn.ModuleList()
        prev = ch[-1] * 2
        for c in reversed(ch):
            self.ups.append(nn.ConvTranspose2d(prev, c, 2, stride=2))
            self.up_blocks.append(_block(c * 2, c))
            prev = c
        self.head = nn.Conv2d(ch[0], num_classes, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        skips = []
        for down in self.downs:
            x = down(x)
            skips.append(x)
            x = F.max_pool2d(x, 2)
        x = self.bottleneck(x)
        for up, block, skip in zip(self.ups, self.up_blocks, reversed(skips)):
            x = up(x)
            if x.shape[-2:] != skip.shape[-2:]:
                x = F.interpolate(x, size=skip.shape[-2:], mode="bilinear", align_corners=False)
            x = block(torch.cat([skip, x], dim=1))
        return self.head(x)


def dice_loss(logits: torch.Tensor, target: torch.Tensor, eps: float = 1.0) -> torch.Tensor:
    p = torch.sigmoid(logits)
    inter = (p * target).sum(dim=(1, 2, 3))
    union = p.sum(dim=(1, 2, 3)) + target.sum(dim=(1, 2, 3))
    return 1 - ((2 * inter + eps) / (union + eps)).mean()


def dice_bce_loss(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Dice + binary cross-entropy, as planned in Step 4."""
    return dice_loss(logits, target) + F.binary_cross_entropy_with_logits(logits, target)
