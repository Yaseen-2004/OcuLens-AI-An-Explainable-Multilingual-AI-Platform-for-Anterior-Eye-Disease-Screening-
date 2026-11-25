import numpy as np

from oculens.uncertainty.calibration import fit_temperature
from oculens.uncertainty.conformal import (empirical_coverage, fit_conformal_threshold,
                                           prediction_set, should_refer)


def synthetic(n, k=4, seed=0):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, k, n)
    logits = rng.normal(0, 1, (n, k))
    logits[np.arange(n), y] += 2.0
    p = np.exp(logits)
    return p / p.sum(1, keepdims=True), y, logits


def test_conformal_coverage_close_to_target():
    p_cal, y_cal, _ = synthetic(2000, seed=1)
    p_test, y_test, _ = synthetic(2000, seed=2)
    qhat = fit_conformal_threshold(p_cal, y_cal, alpha=0.1)
    cov, size = empirical_coverage(p_test, y_test, qhat)
    assert cov >= 0.87          # target 0.90, small finite-sample slack
    assert 1.0 <= size <= 4.0


def test_prediction_set_never_empty_and_referral():
    s = prediction_set(np.array([0.4, 0.35, 0.15, 0.1]), qhat=0.7, classes=list("ABCD"))
    assert s == ["A", "B"]
    assert should_refer(s, max_set_size=1)
    assert prediction_set(np.array([0.25] * 4), qhat=0.0, classes=list("ABCD")) == ["A"]


def test_temperature_reduces_overconfidence():
    _, y, logits = synthetic(1000, seed=3)
    t = fit_temperature(logits * 4.0, y)     # artificially overconfident logits
    assert t > 1.5
