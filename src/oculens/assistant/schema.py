"""Structured findings: the only input the language model ever sees (it never sees the image)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Finding(BaseModel):
    region: str
    condition: str
    severity: Optional[str] = None
    probability: float = Field(ge=0, le=1)
    prediction_set: list[str] = []
    uncertainty: Literal["low", "high"] = "low"
    refer: bool = False
    attention_in_region: Optional[float] = None
    explanation_reliable: Optional[bool] = None


class Symptoms(BaseModel):
    pain: bool = False
    blurred_vision: bool = False
    sudden_vision_loss: bool = False
    vision_drop: bool = False
    redness: bool = False
    discharge: bool = False
    diabetes: bool = False
    recent_eye_surgery: bool = False
    eye_injury: bool = False
    chemical_exposure: bool = False


class Triage(BaseModel):
    level: Literal["routine", "soon", "refer", "urgent"]
    advice: str
    reasons: list[str] = []


class ScreeningReport(BaseModel):
    scan_id: str
    eye: Optional[Literal["left", "right"]] = None
    image_source: str = "slit_lamp"
    quality: dict
    findings: list[Finding] = []
    symptoms: Symptoms = Symptoms()
    triage: Triage
    model_info: dict = {}
    language: str = "en"
