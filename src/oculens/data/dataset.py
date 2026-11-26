"""PyTorch dataset over a split CSV produced by make_task_split."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image
from torch.utils.data import Dataset

from oculens.preprocessing.joint import prepare_input
from oculens.preprocessing.transforms import build_transforms


def find_mask(row: pd.Series, datasets_root: Path, masks_root: Path | None) -> Path | None:
    """Region mask for one image: the dataset's own cornea mask if it has one, otherwise a mask
    predicted by the trained U-Net (scripts/predict_masks.py writes them to data/masks/)."""
    try:
        extra = json.loads(row.get("extra", "") or "{}")
    except (TypeError, ValueError):
        extra = {}
    if extra.get("cornea_mask"):
        p = datasets_root / extra["cornea_mask"]
        if p.exists():
            return p
    if masks_root is not None:
        p = (masks_root / row["image_path"]).with_suffix(".png")
        if p.exists():
            return p
    return None


class EyeImageDataset(Dataset):
    def __init__(self, df: pd.DataFrame, datasets_root: str | Path, classes: list[str],
                 train: bool, image_size: int = 224, preprocess_cfg: dict | None = None,
                 cache_root: str | Path | None = None, variant: str = "image",
                 masks_root: str | Path | None = None, aux_label: str | None = None,
                 aux_classes: list[str] | None = None):
        self.df = df.reset_index(drop=True)
        self.root = Path(datasets_root)
        self.cache = Path(cache_root) if cache_root else None
        self.class_to_idx = {str(c): i for i, c in enumerate(classes)}
        self.train, self.size, self.cfg = train, image_size, preprocess_cfg or {}
        self.variant = variant
        self.masks_root = Path(masks_root) if masks_root else None
        self.aux_label = aux_label
        self.aux_to_idx = {str(c): i for i, c in enumerate(aux_classes or [])}
        self.tf = build_transforms(train=train, image_size=image_size, cfg=self.cfg)
        self.rng = np.random.default_rng()
        if variant in ("mask_input", "region_crop"):
            self.mask_paths = [find_mask(r, self.root, self.masks_root) for _, r in self.df.iterrows()]
            self.missing_masks = sum(m is None for m in self.mask_paths)
        else:
            self.mask_paths, self.missing_masks = None, 0

    def __len__(self) -> int:
        return len(self.df)

    def _image_path(self, rel: str) -> Path:
        path = self.root / rel                       # absolute paths (synthetic images) stay absolute
        if self.cache is not None and not Path(rel).is_absolute():
            cached = (self.cache / rel).with_suffix(".jpg")
            if cached.exists():
                path = cached
        return path

    def __getitem__(self, i: int):
        row = self.df.iloc[i]
        img = np.array(Image.open(self._image_path(row["image_path"])).convert("RGB"))
        if self.variant in ("mask_input", "region_crop"):
            mp = self.mask_paths[i]
            mask = np.array(Image.open(mp).convert("L")) if mp is not None else None
            x = prepare_input(img, mask, self.variant, self.size, self.cfg, train=self.train, rng=self.rng)
        else:
            x = self.tf(img)
        y = torch.tensor(self.class_to_idx[str(row["label"])], dtype=torch.long)
        if self.aux_label:
            try:
                aux_val = str(json.loads(row.get("extra", "") or "{}").get(self.aux_label, ""))
            except (TypeError, ValueError):
                aux_val = ""
            aux = self.aux_to_idx.get(aux_val, -1)       # -1 = no severity label (ignored in the loss)
            return x, y, torch.tensor(aux, dtype=torch.long)
        return x, y

    def class_counts(self) -> np.ndarray:
        idx = self.df["label"].astype(str).map(self.class_to_idx)
        return np.bincount(idx, minlength=len(self.class_to_idx))
