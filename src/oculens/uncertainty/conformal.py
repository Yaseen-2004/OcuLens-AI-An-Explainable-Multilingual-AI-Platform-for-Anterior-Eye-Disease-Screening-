"""Split conformal prediction (LAC score) and the referral rule.

With a calibration set of n examples, the threshold qhat guarantees that the prediction set
contains the true label with probability >= 1 - alpha on new exchangeable data.
"""
from __future__ import annotations

import math

import numpy as np


def fit_conformal_threshold(probs: np.ndarray, labels: np.ndarray, alpha: float = 0.05) -> float:
    n = len(labels)
    if n == 0:
        return 1.0
    scores = 1.0 - probs[np.arange(n), labels]
    level = min(1.0, math.ceil((n + 1) * (1 - alpha)) / n)
    return float(np.quantile(scores, level, method="higher"))


def prediction_set(probs: np.ndarray, qhat: float, classes: list[str]) -> list[str]:
    """All labels whose score 1 - p is within the threshold. Never empty: falls back to the top label."""
    keep = [classes[i] for i in np.where(1.0 - probs <= qhat)[0]]
    return keep or [classes[int(np.argmax(probs))]]


def should_refer(pred_set: list[str], max_set_size: int = 1, top_prob: float | None = None,
                 min_top_prob: float = 0.0) -> bool:
    """Refer instead of guessing when several labels remain plausible or confidence is low."""
    if len(pred_set) > max_set_size:
        return True
    return top_prob is not None and top_prob < min_top_prob


def empirical_coverage(probs: np.ndarray, labels: np.ndarray, qhat: float) -> tuple[float, float]:
    """(coverage, mean set size) on a held-out set - used to check the guarantee holds."""
    in_set = (1.0 - probs) <= qhat
    covered = in_set[np.arange(len(labels)), labels].mean() if len(labels) else float("nan")
    return float(covered), float(np.maximum(in_set.sum(1), 1).mean())
