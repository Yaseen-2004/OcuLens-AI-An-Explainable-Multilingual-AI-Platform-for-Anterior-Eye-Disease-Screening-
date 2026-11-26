"""Leakage-free train / validation / test splits.

Rules (from the project plan):
  * split by group (patient or eye), never by image;
  * the test set holds only real images (synthetic images may only ever be added to training);
  * keratitis can be split across hospitals to measure generalisation to a new site.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold


def grouped_split(df: pd.DataFrame, label_col: str = "label", group_col: str = "group",
                  val_frac: float = 0.15, test_frac: float = 0.15, seed: int = 42) -> pd.Series:
    """Return a Series of 'train' / 'val' / 'test', stratified by label and grouped by group."""
    split = pd.Series("train", index=df.index)
    y = df[label_col].astype(str).to_numpy()
    groups = df[group_col].astype(str).to_numpy()

    # Carve out the test set, then the validation set from what remains.
    n_test = max(2, round(1 / test_frac))
    test_idx = _one_fold(y, groups, n_test, seed)
    split.iloc[test_idx] = "test"

    rest = np.where(split.to_numpy() == "train")[0]
    n_val = max(2, round((1 - test_frac) / val_frac))
    val_local = _one_fold(y[rest], groups[rest], n_val, seed + 1)
    split.iloc[rest[val_local]] = "val"
    return split


def _one_fold(y: np.ndarray, groups: np.ndarray, n_splits: int, seed: int) -> np.ndarray:
    n_splits = max(2, min(n_splits, len(np.unique(groups))))
    skf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    _, held = next(skf.split(np.zeros(len(y)), y, groups))
    return held


def cross_site_split(df: pd.DataFrame, test_site: str, label_col: str = "label",
                     val_frac: float = 0.15, seed: int = 42) -> pd.Series:
    """Hold out one whole site as the test set; split the other sites into train/val by group."""
    split = pd.Series("train", index=df.index)
    is_test = df["site"].astype(str).eq(test_site).to_numpy()
    split[is_test] = "test"
    rest = np.where(~is_test)[0]
    if len(rest):
        y = df[label_col].astype(str).to_numpy()[rest]
        g = df["group"].astype(str).to_numpy()[rest]
        val_local = _one_fold(y, g, max(2, round(1 / val_frac)), seed)
        split.iloc[rest[val_local]] = "val"
    return split


def check_no_leakage(df: pd.DataFrame, split: pd.Series, group_col: str = "group") -> None:
    """Raise if any group appears in more than one split."""
    per_group = df.assign(split=split).groupby(group_col)["split"].nunique()
    leaked = per_group[per_group > 1]
    if len(leaked):
        raise ValueError(f"{len(leaked)} groups appear in more than one split, e.g. {list(leaked.index[:3])}")


def make_task_split(manifest: pd.DataFrame, task_cfg: dict, seed: int = 42) -> pd.DataFrame:
    """Select a task's rows from the manifest, attach a 'split' column and verify no leakage."""
    df = manifest[manifest["dataset"] == task_cfg["dataset"]].copy()
    label_col = "label"
    if task_cfg.get("label_column") and task_cfg["label_column"] not in ("label", "category"):
        # labels stored in the JSON 'extra' column (e.g. trachoma TF)
        import json

        key = task_cfg["label_column"]
        df["label"] = df["extra"].map(lambda s: str(json.loads(s).get(key, "")))
    df = df[df[label_col].astype(str).isin([str(c) for c in task_cfg["classes"]])]
    if task_cfg.get("split") == "cross_site":
        df["split"] = cross_site_split(df, task_cfg["test_site"], seed=seed)
    else:
        df["split"] = grouped_split(df, seed=seed)
    check_no_leakage(df, df["split"])
    return df
