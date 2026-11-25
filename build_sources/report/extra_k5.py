# Part K5 - Correction: ulcer label polarity, real U-Net scores, corrected explanation check (25 Nov 2026).
import os as _osK5, json as _jsK5
_SEG = _osK5.path.join(r"D:\Capston_Project", "experiments", "seg", "unet_eval.json")
_RN5 = _osK5.path.join(r"D:\Capston_Project", "experiments", "runs")
if _osK5.path.exists(_SEG):
    _sg = _jsK5.load(open(_SEG, encoding="utf-8"))
    s.append(PageBreak())
    s += [p("Part K5 - Correction: ulcer labels were read inverted", H1),
          p("While scoring the U-Nets on their held-out test images (25 Nov) we found that the SUSTech-SYSU ulcer label files "
            "mark the ulcer in black on a white background, while our code treated white as the ulcer. The ulcer U-Net had "
            "therefore learned the background: its apparent Dice of 0.989 measured the background, and its true lesion Dice was "
            "0.389. The explanation check against the ulcer region (Part K2.4, ulcer-mask rows) was inverted in the same way. "
            "Classifier results are not affected: the anatomy variants use the cornea labels, which are stored the right way round. "
            "Both readers now flip the ulcer labels (an ulcer covers about 4% of the image instead of 96%); all 48 unit tests pass, "
            "and the ulcer U-Net was retrained for 50 epochs on the DGX (account 0034).")]
    _rows5 = [["U-Net", "Test images", "Dice", "IoU"],
              ["Cornea (used by the portal)", str(_sg["cornea"]["test_images"]), f'{_sg["cornea"]["dice"]:.3f}', f'{_sg["cornea"]["iou"]:.3f}'],
              ["Ulcer, before the fix (true lesion Dice)", str(_sg["ulcer"]["test_images"]), "0.389", "n/a"],
              ["Ulcer, retrained with correct labels", str(_sg["ulcer"]["test_images"]), f'{_sg["ulcer"]["dice"]:.3f}', f'{_sg["ulcer"]["iou"]:.3f}']]
    s.append(table(_rows5, [7.4*cm, 2.6*cm, 2.6*cm, 2.6*cm]))
    _ex = []
    for _f, _lab in [("explain_ulcer_image_ulcer_fixed.json", "image model"), ("explain_ulcer_maskinput_ulcer_fixed.json", "mask-input model")]:
        _fp = _osK5.path.join(_RN5, _f)
        if _osK5.path.exists(_fp):
            _sm = _jsK5.load(open(_fp, encoding="utf-8"))["summary"]
            _ex.append([f"Ulcer {_lab} vs the real ulcer region", str(_sm["n"]), str(_sm["mean_attention_in_region"]), str(_sm["mean_mask_area"]), str(_sm["pointing_game"])])
    if _ex:
        s += [p("K5.1 Corrected explanation check (RQ4)", H2)]
        s.append(table([["Model / region", "Imgs", "Attn in region", "Region area", "Pointing"]] + _ex, [7.0*cm, 1.4*cm, 2.8*cm, 2.6*cm, 2.2*cm]))
        s.append(p("Corrected reading: the Grad-CAM++ heat-maps place about 2% of their weight on the ulcer lesion, which itself "
                   "covers about 4% of the image, and the hottest point never lands on it. The models read the cornea "
                   "(Part K2.4, cornea rows: 67% of the heat-map inside a cornea covering 56%), but they do not point at the "
                   "lesion. This replaces the ulcer-mask rows of Part K2.4, which came from the inverted labels."))
