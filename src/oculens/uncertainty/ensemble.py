"""Deep ensemble: average the calibrated probabilities of several independently trained models.

Train members with different seeds:
    python scripts/train.py --task keratitis --seed 1   (... seeds 1-5)
Members are found as models/checkpoints/<task>_<backbone>_s*.pt.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from oculens.models.classifier import load_checkpoint


class Ensemble:
    def __init__(self, checkpoints: list[str | Path]):
        if not checkpoints:
            raise ValueError("no ensemble members")
        loaded = [load_checkpoint(p) for p in checkpoints]
        self.models = [m for m, _ in loaded]
        self.metas = [meta for _, meta in loaded]
        classes = {tuple(m["classes"]) for m in self.metas}
        if len(classes) != 1:
            raise ValueError("ensemble members disagree on classes")
        self.classes = list(self.metas[0]["classes"])

    @classmethod
    def from_task(cls, checkpoints_dir: str | Path, task: str, backbone: str) -> "Ensemble":
        return cls(sorted(Path(checkpoints_dir).glob(f"{task}_{backbone}_s*.pt")))

    @torch.no_grad()
    def predict(self, x: torch.Tensor) -> dict:
        """x: (B,3,H,W). Returns mean probs, member spread, total entropy and mutual information."""
        probs = []
        for m, meta in zip(self.models, self.metas):
            m.eval()
            probs.append(torch.softmax(m(x) / meta.get("temperature", 1.0), dim=1))
        p = torch.stack(probs)                       # (M,B,C)
        mean = p.mean(0)
        total = -(mean * mean.clamp_min(1e-12).log()).sum(1)
        expected = -(p * p.clamp_min(1e-12).log()).sum(2).mean(0)
        return {"probs": mean.numpy(), "std": p.std(0).numpy(), "entropy": total.numpy(),
                "mutual_information": (total - expected).numpy()}   # disagreement = epistemic uncertainty


def ensemble_uncertainty_flag(mutual_information: np.ndarray, threshold: float) -> np.ndarray:
    """True where members disagree enough to refer the case."""
    return mutual_information > threshold
