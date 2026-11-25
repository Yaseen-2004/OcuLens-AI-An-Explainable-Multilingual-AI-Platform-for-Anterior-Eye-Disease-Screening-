"""Image classifiers built on a timm backbone (EfficientNet, ConvNeXt, ViT, Swin ...).

Variants (RQ1 ablation, report Step 5):
  image        RGB image only (baseline)
  mask_input   RGB + region mask as a 4th input channel           (option A)
  region_crop  RGB cropped to the segmented region                (option B)
  multitask    shared backbone, condition head + severity head    (option C)
"""
from __future__ import annotations

from pathlib import Path

import timm
import torch
from torch import nn

PRETRAINED_DIR = Path(__file__).resolve().parents[3] / "models" / "pretrained"
VARIANTS = ("image", "mask_input", "region_crop", "multitask")


def local_weights(backbone: str) -> Path | None:
    """ImageNet weights saved by scripts/download_weights.py (works offline and behind firewalls)."""
    hits = sorted(PRETRAINED_DIR.glob(f"{backbone}*.safetensors")) if PRETRAINED_DIR.exists() else []
    return hits[0] if hits else None


def _timm(backbone: str, num_classes: int, pretrained: bool, dropout: float, in_chans: int = 3) -> nn.Module:
    kw = dict(num_classes=num_classes, drop_rate=dropout, in_chans=in_chans)
    if pretrained and (w := local_weights(backbone)):
        # timm adapts the first convolution when in_chans != 3 (extra channel initialised from RGB weights)
        return timm.create_model(backbone, pretrained=True, pretrained_cfg_overlay={"file": str(w)}, **kw)
    return timm.create_model(backbone, pretrained=pretrained, **kw)


def create_classifier(backbone: str, num_classes: int, pretrained: bool = True, dropout: float = 0.3,
                      in_chans: int = 3) -> nn.Module:
    return _timm(backbone, num_classes, pretrained, dropout, in_chans)


class MultiTaskNet(nn.Module):
    """Shared backbone with a main (condition) head and an auxiliary (severity) head.

    forward() returns the main logits only, so Grad-CAM, calibration and the app treat it like
    any classifier; forward_both() is used in training.
    """

    def __init__(self, backbone: str, num_classes: int, num_aux: int, pretrained: bool = True, dropout: float = 0.3):
        super().__init__()
        self.encoder = _timm(backbone, 0, pretrained, dropout)
        f = self.encoder.num_features
        self.drop = nn.Dropout(dropout)
        self.head = nn.Linear(f, num_classes)
        self.aux_head = nn.Linear(f, num_aux)

    def forward_both(self, x):
        z = self.drop(self.encoder(x))
        return self.head(z), self.aux_head(z)

    def forward(self, x):
        return self.forward_both(x)[0]


def build_model(meta: dict, pretrained: bool = False) -> nn.Module:
    """Rebuild a model from checkpoint metadata (or from training settings)."""
    variant = meta.get("variant", "image")
    n = len(meta["classes"])
    if variant == "multitask":
        return MultiTaskNet(meta["backbone"], n, len(meta["aux_classes"]), pretrained, meta.get("dropout", 0.0))
    return create_classifier(meta["backbone"], n, pretrained, meta.get("dropout", 0.0),
                             in_chans=4 if variant == "mask_input" else 3)


def save_checkpoint(path: str | Path, model: nn.Module, meta: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "meta": meta}, path)


def load_checkpoint(path: str | Path, map_location: str = "cpu") -> tuple[nn.Module, dict]:
    """Rebuild the model from the metadata stored with the weights."""
    ckpt = torch.load(path, map_location=map_location, weights_only=False)
    meta = ckpt["meta"]
    model = build_model(meta, pretrained=False)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model, meta
