"""Align a follow-up image to the previous one (ORB features + RANSAC similarity transform)."""
from __future__ import annotations

import cv2
import numpy as np


def align_to(reference_rgb: np.ndarray, moving_rgb: np.ndarray, max_features: int = 2000) -> tuple[np.ndarray, dict]:
    """Warp `moving` onto `reference`. Returns (aligned image, info). Falls back to a plain resize."""
    h, w = reference_rgb.shape[:2]
    ref = cv2.cvtColor(reference_rgb, cv2.COLOR_RGB2GRAY)
    mov = cv2.cvtColor(cv2.resize(moving_rgb, (w, h)), cv2.COLOR_RGB2GRAY)
    resized = cv2.resize(moving_rgb, (w, h))
    orb = cv2.ORB_create(max_features)
    k1, d1 = orb.detectAndCompute(ref, None)
    k2, d2 = orb.detectAndCompute(mov, None)
    if d1 is None or d2 is None or len(k1) < 10 or len(k2) < 10:
        return resized, {"aligned": False, "reason": "too few features", "inliers": 0}
    matches = sorted(cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d2, d1), key=lambda m: m.distance)
    matches = matches[: max(10, len(matches) // 2)]
    src = np.float32([k2[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst = np.float32([k1[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
    m, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=4.0)
    n_in = int(inl.sum()) if inl is not None else 0
    if m is None or n_in < 8:
        return resized, {"aligned": False, "reason": "no stable transform", "inliers": n_in}
    aligned = cv2.warpAffine(resized, m, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    scale = float(np.sqrt(abs(np.linalg.det(m[:, :2]))))
    return aligned, {"aligned": True, "inliers": n_in, "scale": round(scale, 3)}
