"""Normal-eye check: resolution equalisation and the logistic head (no model weights needed)."""
import numpy as np

from oculens.quality.normal_gate import THUMB_SIDE, p_normal, thumbnail


def test_thumbnail_equalises_resolution_and_never_enlarges():
    big = np.zeros((2620, 3930, 3), np.uint8)
    small = np.zeros((40, 50, 3), np.uint8)
    t = thumbnail(big)
    assert min(t.shape[:2]) == THUMB_SIDE and abs(t.shape[1] / t.shape[0] - 1.5) < 0.05   # aspect kept
    assert thumbnail(small).shape == small.shape                                         # tiny photos unchanged


def test_p_normal_is_a_logistic_head():
    gate = {"coef": np.array([[2.0, -1.0]], np.float32), "intercept": np.array([0.5], np.float32)}
    f = np.array([[1.0, 0.0], [0.0, 1.0]], np.float32)
    p = p_normal(gate, f)
    assert np.allclose(p, 1 / (1 + np.exp(-np.array([2.5, -0.5]))))
