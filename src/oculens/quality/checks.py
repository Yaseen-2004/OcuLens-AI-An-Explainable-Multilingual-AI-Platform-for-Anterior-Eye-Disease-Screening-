"""Rule-based image quality gate (Step 2 of the method).

Rejects blurred, too dark / too bright, low-contrast and glare-heavy images and returns
a short prompt for the technician so they can recapture. A small learned quality CNN can
later be added on top of these rules.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import cv2
import numpy as np

DEFAULTS = {
    "blur_min_laplacian_var": 60.0,
    "brightness_min": 40.0,
    "brightness_max": 225.0,
    "glare_max_fraction": 0.08,
    "contrast_min_std": 18.0,
}

PROMPTS = {
    "blurred": "Image is blurred - refocus and recapture.",
    "too_dark": "Image is too dark - increase illumination.",
    "too_bright": "Image is overexposed - reduce illumination.",
    "glare": "Strong reflection on the eye - change the light angle and recapture.",
    "low_contrast": "Low contrast - check focus and lighting.",
}


@dataclass
class QualityResult:
    ok: bool
    reasons: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def prompts(self) -> list[str]:
        return [PROMPTS[r] for r in self.reasons]

    def to_dict(self) -> dict:
        return {**asdict(self), "prompts": self.prompts}


def _gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)


def assess_quality(image_rgb: np.ndarray, cfg: dict | None = None) -> QualityResult:
    """Assess an RGB uint8 image. Returns ok=False with reasons when it should be retaken."""
    c = {**DEFAULTS, **(cfg or {})}
    gray = _gray(image_rgb)
    # Work at a fixed scale so thresholds do not depend on camera resolution.
    scale = 512 / max(gray.shape)
    if scale < 1:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    contrast = float(gray.std())
    glare = float((gray >= 250).mean())

    reasons = []
    if lap_var < c["blur_min_laplacian_var"]:
        reasons.append("blurred")
    if brightness < c["brightness_min"]:
        reasons.append("too_dark")
    if brightness > c["brightness_max"]:
        reasons.append("too_bright")
    if glare > c["glare_max_fraction"]:
        reasons.append("glare")
    if contrast < c["contrast_min_std"]:
        reasons.append("low_contrast")

    metrics = {"laplacian_var": round(lap_var, 2), "brightness": round(brightness, 2),
               "contrast_std": round(contrast, 2), "glare_fraction": round(glare, 4)}
    return QualityResult(ok=not reasons, reasons=reasons, metrics=metrics)
