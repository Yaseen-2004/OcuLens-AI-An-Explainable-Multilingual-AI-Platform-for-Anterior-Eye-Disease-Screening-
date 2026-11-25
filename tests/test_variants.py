import json

import numpy as np
import pandas as pd
import pytest
import torch
from PIL import Image

from oculens.data.dataset import EyeImageDataset
from oculens.models.classifier import MultiTaskNet, build_model, load_checkpoint, save_checkpoint
from oculens.preprocessing.joint import prepare_input, prepare_mask

CFG = {"work_size": 256, "remove_glare": True, "clahe_clip_limit": 2.0, "clahe_tile_grid": 8}


def img_and_mask(h=300, w=400):
    rng = np.random.default_rng(0)
    img = rng.integers(30, 220, (h, w, 3), dtype=np.uint8)
    mask = np.zeros((h, w), np.uint8)
    mask[100:220, 150:300] = 1
    return img, mask


@pytest.mark.parametrize("variant,ch", [("mask_input", 4), ("region_crop", 3)])
@pytest.mark.parametrize("train", [True, False])
def test_prepare_input_shapes(variant, ch, train):
    img, mask = img_and_mask()
    x = prepare_input(img, mask, variant, 64, CFG, train=train, rng=np.random.default_rng(1))
    assert x.shape == (ch, 64, 64)
    if variant == "mask_input":
        assert set(torch.unique(x[3]).tolist()) <= {0.0, 1.0}


def test_mask_input_keeps_mask_aligned_in_eval():
    img, mask = img_and_mask()
    x = prepare_input(img, mask, "mask_input", 64, CFG, train=False)
    assert np.array_equal(x[3].numpy().astype(np.uint8), prepare_mask(img, mask, "mask_input", 64, CFG))


def test_region_crop_zooms_into_mask():
    img, mask = img_and_mask()
    m = prepare_mask(img, mask, "region_crop", 64, CFG)
    assert m.mean() > 0.5          # after cropping, the region fills most of the input


@pytest.mark.parametrize("variant", ["image", "mask_input", "region_crop", "multitask"])
def test_build_model_variants_and_reload(tmp_path, variant):
    meta = {"backbone": "resnet18", "classes": ["A", "B", "C"], "variant": variant, "dropout": 0.0,
            "aux_classes": ["0", "1", "2", "3", "4"] if variant == "multitask" else None}
    m = build_model(meta)
    x = torch.randn(2, 4 if variant == "mask_input" else 3, 64, 64)
    assert m(x).shape == (2, 3)
    if variant == "multitask":
        main, aux = m.forward_both(torch.randn(2, 3, 64, 64))
        assert isinstance(m, MultiTaskNet) and aux.shape == (2, 5)
    save_checkpoint(tmp_path / "m.pt", m, meta)
    m2, meta2 = load_checkpoint(tmp_path / "m.pt")
    assert meta2["variant"] == variant and m2(x).shape == (2, 3)


def test_dataset_masks_aux_and_absolute_paths(tmp_path):
    img, mask = img_and_mask()
    (tmp_path / "ds").mkdir()
    Image.fromarray(img).save(tmp_path / "ds" / "a.jpg")
    Image.fromarray(mask * 255).save(tmp_path / "ds" / "a_mask.png")
    syn = tmp_path / "syn.png"
    Image.fromarray(img).save(syn)
    df = pd.DataFrame([
        {"image_path": "a.jpg", "label": "1", "extra": json.dumps({"cornea_mask": "a_mask.png", "grade": 3})},
        {"image_path": str(syn), "label": "0", "extra": "{}"},             # synthetic: absolute path, no mask, no grade
    ])
    ds = EyeImageDataset(df, tmp_path / "ds", ["0", "1"], train=True, image_size=64, preprocess_cfg=CFG,
                         variant="mask_input", aux_label="grade", aux_classes=["0", "1", "2", "3", "4"])
    assert ds.missing_masks == 1
    x, y, aux = ds[0]
    assert x.shape == (4, 64, 64) and int(y) == 1 and int(aux) == 3
    x, y, aux = ds[1]
    assert x[3].sum() == 0 and int(aux) == -1
