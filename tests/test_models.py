import numpy as np
import torch

from oculens.explain.gradcam import GradCAM
from oculens.explain.region_check import verify_explanation
from oculens.models.classifier import create_classifier
from oculens.models.unet import UNet, dice_bce_loss
from oculens.pipeline import ScreeningPipeline


def test_classifier_and_gradcam_shapes():
    model = create_classifier("resnet18", num_classes=3, pretrained=False)
    cam, idx = GradCAM(model, plus_plus=True)(torch.randn(1, 3, 128, 128))
    assert cam.shape == (128, 128) and 0 <= idx < 3
    assert 0.0 <= cam.min() and cam.max() <= 1.0


def test_region_check():
    cam = np.zeros((10, 10)); cam[2:5, 2:5] = 1.0
    mask = np.zeros((10, 10), np.uint8); mask[0:6, 0:6] = 1
    r = verify_explanation(cam, mask, 0.5)
    assert r["reliable"] and r["attention_in_region"] == 1.0


def test_unet_forward_and_loss():
    m = UNet(base=8)
    x = torch.randn(2, 3, 64, 64)
    y = (torch.rand(2, 1, 64, 64) > 0.5).float()
    out = m(x)
    assert out.shape == (2, 1, 64, 64)
    assert dice_bce_loss(out, y).item() > 0


def test_pipeline_without_model_still_triages():
    rng = np.random.default_rng(0)
    img = rng.integers(40, 200, (256, 256, 3), dtype=np.uint8)
    out = ScreeningPipeline(checkpoint=None).run(img, symptoms={"pain": True, "sudden_vision_loss": True})
    assert out["report"].triage.level == "urgent"
