"""End-to-end screening of one image:

quality check -> enhancement -> classification (calibrated) -> conformal set / referral
-> Grad-CAM (+ anatomy check when a region mask is available) -> triage -> structured report.
"""
from __future__ import annotations

import base64
import uuid
from pathlib import Path

import cv2
import numpy as np
import torch

from oculens.assistant.schema import Finding, ScreeningReport, Symptoms, Triage
from oculens.config import load_config, resolve
from oculens.explain.gradcam import GradCAM, overlay
from oculens.explain.region_check import verify_explanation
from oculens.models.classifier import load_checkpoint
from oculens.models.segmenter import Segmenter, model_input_mask
from oculens.preprocessing.joint import prepare_input, prepare_mask
from oculens.preprocessing.transforms import build_transforms
from oculens.quality.checks import assess_quality
from oculens.triage.engine import TriageEngine
from oculens.uncertainty.conformal import prediction_set, should_refer


class ScreeningPipeline:
    def __init__(self, checkpoint: str | Path | None = None, config: dict | None = None,
                 segmenter_checkpoint: str | Path | None = None):
        self.cfg = config or load_config()
        self.triage = TriageEngine()
        self.model = self.meta = None
        self.segmenter = Segmenter(segmenter_checkpoint) if segmenter_checkpoint and Path(segmenter_checkpoint).exists() else None
        if checkpoint and Path(checkpoint).exists():
            self.model, self.meta = load_checkpoint(checkpoint)
            self.tf = build_transforms(train=False, image_size=self.meta.get("image_size", 224),
                                       cfg=self.cfg["preprocessing"])

    @classmethod
    def from_task(cls, task: str, backbone: str | None = None) -> "ScreeningPipeline":
        cfg = load_config()
        bb = backbone or cfg["training"]["backbone"]
        ck = resolve(cfg["paths"]["checkpoints_dir"])
        return cls(ck / f"{task}_{bb}.pt", cfg, segmenter_checkpoint=ck / "unet_cornea.pt")

    @property
    def has_model(self) -> bool:
        return self.model is not None

    def run(self, image_rgb: np.ndarray, symptoms: dict | None = None, region_mask: np.ndarray | None = None,
            eye: str | None = None, return_overlay: bool = True) -> dict:
        symptoms_model = Symptoms(**(symptoms or {}))
        quality = assess_quality(image_rgb, self.cfg["quality"])
        findings: list[Finding] = []
        overlay_b64 = None

        if quality.ok and self.has_model:
            classes = self.meta["classes"]
            variant = self.meta.get("variant", "image")
            if region_mask is None and self.segmenter is not None and (
                    variant in ("mask_input", "region_crop") or self.meta.get("region") == self.segmenter.target):
                region_mask = self.segmenter.predict(image_rgb)          # U-Net mask: model input and anatomy check
            size = self.meta.get("image_size", 224)
            if variant in ("mask_input", "region_crop"):
                x = prepare_input(image_rgb, region_mask, variant, size, self.cfg["preprocessing"]).unsqueeze(0)
            else:
                x = self.tf(image_rgb).unsqueeze(0)
            with torch.no_grad():
                logits = self.model(x)[0].numpy()
            t = self.meta.get("temperature", 1.0)
            z = logits / t
            probs = np.exp(z - z.max())
            probs = probs / probs.sum()
            top = int(np.argmax(probs))
            pset = prediction_set(probs, self.meta.get("conformal_qhat", 1.0), classes)
            refer = should_refer(pset, self.cfg["uncertainty"]["refer_if_set_size_over"])

            cam_engine = GradCAM(self.model, plus_plus=True)
            try:
                cam, _ = cam_engine(x, top)
            finally:
                cam_engine.remove()
            check_mask = None
            if region_mask is not None:
                if variant in ("mask_input", "region_crop"):
                    check_mask = prepare_mask(image_rgb, region_mask.astype(np.uint8), variant, cam.shape[0], self.cfg["preprocessing"])
                else:
                    check_mask = model_input_mask(region_mask.astype(np.uint8), cam.shape[0])
            check = verify_explanation(cam, check_mask, self.cfg["explain"]["attention_in_region_min"])
            findings.append(Finding(
                region=self.meta.get("region", "unknown"), condition=classes[top], probability=float(probs[top]),
                prediction_set=pset, uncertainty="high" if refer else "low", refer=refer,
                attention_in_region=check["attention_in_region"], explanation_reliable=check["reliable"],
            ))
            if return_overlay:
                base = cv2.resize(image_rgb, (cam.shape[1], cam.shape[0]))
                ok, buf = cv2.imencode(".png", cv2.cvtColor(overlay(base, cam), cv2.COLOR_RGB2BGR))
                overlay_b64 = base64.b64encode(buf.tobytes()).decode() if ok else None

        if not quality.ok:
            tri = Triage(level="refer", advice="Image quality too low - please recapture.",
                         reasons=quality.prompts)
        else:
            tri = Triage(**self.triage.decide([f.model_dump() for f in findings], symptoms_model.model_dump()).to_dict())
            if not self.has_model:
                tri.reasons.append("no trained model loaded - symptoms-only triage")

        report = ScreeningReport(
            scan_id=uuid.uuid4().hex[:12], eye=eye, quality=quality.to_dict(), findings=findings,
            symptoms=symptoms_model, triage=tri,
            model_info={k: self.meta[k] for k in ("task", "backbone", "classes")} if self.meta else {},
        )
        return {"report": report, "overlay_png_base64": overlay_b64}
