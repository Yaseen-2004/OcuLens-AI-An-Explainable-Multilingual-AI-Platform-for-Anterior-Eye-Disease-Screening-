"""Screening metrics. Sensitivity is the primary metric: a missed case costs more than an extra referral."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (balanced_accuracy_score, cohen_kappa_score, confusion_matrix,
                             f1_score, roc_auc_score)


def per_class_sensitivity_specificity(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> dict:
    cm = confusion_matrix(y_true, y_pred, labels=list(range(n_classes)))
    out = {}
    for k in range(n_classes):
        tp = cm[k, k]
        fn = cm[k].sum() - tp
        fp = cm[:, k].sum() - tp
        tn = cm.sum() - tp - fn - fp
        out[k] = {
            "sensitivity": float(tp / (tp + fn)) if tp + fn else float("nan"),
            "specificity": float(tn / (tn + fp)) if tn + fp else float("nan"),
            "support": int(cm[k].sum()),
        }
    return out


def expected_calibration_error(probs: np.ndarray, y_true: np.ndarray, n_bins: int = 15) -> float:
    conf = probs.max(1)
    correct = (probs.argmax(1) == y_true).astype(float)
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            ece += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(ece)


def classification_report(probs: np.ndarray, y_true: np.ndarray, classes: list[str]) -> dict:
    n = len(classes)
    y_pred = probs.argmax(1)
    rep = {
        "n": int(len(y_true)),
        "accuracy": float((y_pred == y_true).mean()) if len(y_true) else float("nan"),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)) if len(y_true) else float("nan"),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", labels=list(range(n)), zero_division=0)),
        "kappa": float(cohen_kappa_score(y_true, y_pred)) if len(set(y_true)) > 1 else float("nan"),
        "ece": expected_calibration_error(probs, y_true),
        "per_class": {classes[k]: v for k, v in per_class_sensitivity_specificity(y_true, y_pred, n).items()},
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=list(range(n))).tolist(),
    }
    try:
        if n == 2:
            rep["auroc"] = float(roc_auc_score(y_true, probs[:, 1]))
        else:
            rep["auroc_macro_ovr"] = float(roc_auc_score(y_true, probs, multi_class="ovr", labels=list(range(n))))
    except ValueError:
        rep["auroc"] = float("nan")  # a class is missing from this split
    return rep
