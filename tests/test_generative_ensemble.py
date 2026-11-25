import numpy as np
import torch

from oculens.followup.change import SiameseChange
from oculens.generative.cyclegan import CycleGAN
from oculens.generative.ddpm import CondUNet, Diffusion
from oculens.generative.validate import frechet_distance, tstr
from oculens.models.classifier import create_classifier, save_checkpoint
from oculens.models.segmenter import Segmenter, model_input_mask
from oculens.models.unet import UNet
from oculens.training.evaluate import referral_effect
from oculens.uncertainty.ensemble import Ensemble


def test_ddpm_loss_and_sample_shapes():
    model = CondUNet(num_classes=3, base=16, mults=(1, 2))
    diff = Diffusion(model, timesteps=50)
    x = torch.rand(2, 3, 32, 32) * 2 - 1
    loss = diff.loss(x, torch.tensor([0, 2]))
    loss.backward()
    assert loss.item() > 0
    out = diff.sample(torch.tensor([1, 1]), size=32, steps=5)
    assert out.shape == (2, 3, 32, 32) and out.min() >= -1 and out.max() <= 1


def test_cyclegan_step_runs():
    gan = CycleGAN(base=8)
    losses = gan.train_step(torch.rand(1, 3, 64, 64) * 2 - 1, torch.rand(1, 3, 64, 64) * 2 - 1)
    assert losses["loss_g"] > 0 and losses["loss_d"] > 0


def test_fid_and_tstr():
    rng = np.random.default_rng(0)
    a = rng.normal(size=(300, 8))
    assert frechet_distance(a, a) < 1e-6
    assert frechet_distance(a, a + 3.0) > 50
    y = (a[:, 0] > 0).astype(int)
    assert tstr(a, y, a, y)["tstr_balanced_accuracy"] > 0.9


def test_ensemble_from_checkpoints(tmp_path):
    for s in (1, 2):
        torch.manual_seed(s)
        m = create_classifier("resnet18", 3, pretrained=False, dropout=0.0)
        save_checkpoint(tmp_path / f"t_resnet18_s{s}.pt", m, {"backbone": "resnet18", "classes": ["A", "B", "C"],
                                                              "temperature": 1.5, "dropout": 0.0})
    ens = Ensemble.from_task(tmp_path, "t", "resnet18")
    out = ens.predict(torch.randn(2, 3, 64, 64))
    assert out["probs"].shape == (2, 3)
    assert np.allclose(out["probs"].sum(1), 1, atol=1e-5)
    assert (out["mutual_information"] >= -1e-6).all()


def test_referral_reduces_missed_cases():
    # class 0 = normal. Two sick cases look normal but are uncertain -> referred instead of missed.
    probs = np.array([[0.55, 0.45], [0.52, 0.48], [0.95, 0.05], [0.05, 0.95]])
    y = np.array([1, 1, 0, 1])
    r = referral_effect(probs, y, qhat=0.6, normal_idx=0)
    assert r["missed_rate_with_referral"] < r["missed_rate_without_referral"]
    assert r["referral_rate"] == 0.5


def test_segmenter_and_mask_geometry(tmp_path):
    torch.save({"state_dict": UNet().state_dict(), "meta": {"size": 64, "target": "cornea"}}, tmp_path / "u.pt")
    seg = Segmenter(tmp_path / "u.pt")
    mask = seg.predict(np.zeros((120, 160, 3), np.uint8))
    assert mask.shape == (120, 160)
    assert model_input_mask(np.ones((120, 160), np.uint8), 96).shape == (96, 96)


def test_siamese_change_forward():
    enc = torch.nn.Sequential(torch.nn.Conv2d(3, 4, 3), torch.nn.AdaptiveAvgPool2d(1), torch.nn.Flatten())
    out = SiameseChange(enc, 4)(torch.randn(2, 3, 32, 32), torch.randn(2, 3, 32, 32))
    assert out.shape == (2, 3)
