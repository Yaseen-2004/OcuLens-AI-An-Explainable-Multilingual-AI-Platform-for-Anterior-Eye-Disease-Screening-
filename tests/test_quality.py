import cv2
import numpy as np

from oculens.quality.checks import assess_quality


def sharp_image(seed=0):
    rng = np.random.default_rng(seed)
    img = rng.integers(40, 200, (256, 256, 3), dtype=np.uint8)
    cv2.circle(img, (128, 128), 60, (90, 60, 40), -1)
    return img


def test_sharp_image_passes():
    r = assess_quality(sharp_image())
    assert r.ok, r.reasons


def test_blurred_image_rejected():
    img = cv2.GaussianBlur(sharp_image(), (31, 31), 12)
    r = assess_quality(img)
    assert "blurred" in r.reasons
    assert r.prompts


def test_dark_image_rejected():
    r = assess_quality((sharp_image() * 0.1).astype(np.uint8))
    assert "too_dark" in r.reasons


def test_glare_rejected():
    img = sharp_image()
    img[:80, :120] = 255
    assert "glare" in assess_quality(img).reasons
