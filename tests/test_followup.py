from datetime import date

import cv2
import numpy as np

from oculens.followup.align import align_to
from oculens.followup.change import compare_scans, image_difference
from oculens.followup.schedule import next_scan, post_op_check, post_op_schedule, trend


def textured(seed=0, size=256):
    rng = np.random.default_rng(seed)
    img = rng.integers(0, 255, (size, size, 3), dtype=np.uint8)
    return cv2.GaussianBlur(img, (5, 5), 1)


def test_alignment_recovers_shift():
    ref = textured()
    m = np.float32([[1, 0, 12], [0, 1, -8]])
    moved = cv2.warpAffine(ref, m, (256, 256), borderMode=cv2.BORDER_REFLECT)
    aligned, info = align_to(ref, moved)
    assert info["aligned"]
    before = np.abs(ref.astype(int) - moved.astype(int)).mean()
    after = np.abs(ref[20:-20, 20:-20].astype(int) - aligned[20:-20, 20:-20].astype(int)).mean()
    assert after < before / 2


def test_change_classification():
    a = {"condition": "Cataract", "probability": 0.4, "date": "2026-01-01"}
    b = {"condition": "Cataract", "probability": 0.8, "date": "2026-04-01"}
    assert compare_scans(a, b)["status"] == "progressed"
    assert compare_scans(b, a)["status"] == "improved"
    assert compare_scans(a, {**a, "probability": 0.45})["status"] == "stable"


def test_identical_images_show_no_difference():
    img = textured(1)
    assert image_difference(img, img)["changed_fraction"] < 0.01


def test_schedule_and_post_op():
    d = date(2026, 11, 18)
    assert next_scan("urgent", d) == date(2026, 11, 19)
    assert next_scan("routine", d, progressed=True) < next_scan("routine", d)
    assert post_op_schedule(d)[-1] == date(2026, 12, 18)
    assert post_op_check({"pain": True})["alert_surgeon"]
    assert not post_op_check({})["alert_surgeon"]
    t = trend([{"date": "2026-02-01", "probability": 0.5}, {"date": "2026-01-01", "probability": 0.3}])
    assert t[1]["delta"] == 0.2
