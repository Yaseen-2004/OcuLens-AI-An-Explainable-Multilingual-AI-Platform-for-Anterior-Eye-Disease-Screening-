# Part K2 - Full 50-epoch parallel run across the 4-person team's own GPU accounts (23 Nov 2026).
# Reads the eval_*.json files collected into experiments/runs_50ep_parallel/.
import os as _os2, json as _json2, math as _math2

_K2 = _os2.path.join(r"D:\Capston_Project", "experiments", "runs_50ep_parallel")

def _f3(v):
    try:
        if v is None or (isinstance(v, float) and _math2.isnan(v)):
            return "n/a"
        return f"{float(v):.3f}"
    except Exception:
        return "n/a"

def _load(name):
    fp = _os2.path.join(_K2, name)
    if not _os2.path.exists(fp):
        return None
    try:
        return _json2.load(open(fp, encoding="utf-8"))
    except Exception:
        return None

s.append(PageBreak())
s += [p("Part K2 - Full 50-epoch run (parallel, 4 team accounts)", H1),
      p("On 23 Nov 2026 the full experiment plan was trained for 50 epochs. To finish quickly, the work was "
        "split across the four team members' own DGX accounts and run at the same time, one GPU slice each. "
        "Every number below is read straight from the eval_*.json file each run wrote; these are first baselines "
        "on public data, not clinical performance claims.")]

# --- account -> job map
s += [p("K2.1 Which account ran which job", H2)]
s.append(table([
    ["Account", "Jobs it ran (50 epochs)"],
    ["0034 (owner)", "Cornea + ulcer U-Nets, mask prediction; baselines (keratitis, ulcer, trachoma); "
                     "keratitis mask_input + region_crop; explanation-quality checks; ONNX export; harmonized eval"],
    ["0001", "5-model keratitis ensemble (seeds 1-5); multitask ulcer; ensemble evaluation"],
    ["0063", "Diffusion (DDPM) synthetic keratitis images + retrain (RQ2a); region_crop ulcer"],
    ["3007", "CycleGAN ZEH->AGEH harmonisation + retrain (RQ2b)"],
], [3.2*cm, 13.6*cm]))
s.append(p("The two ulcer variants (region_crop, multitask) were moved onto separate accounts so they trained "
           "at the same time instead of one after the other; this cut the final stretch from about two hours to about 35 minutes."))

# --- main results table
_MAP = [
    ("eval_keratitis_image.json",        "keratitis",    "image (baseline)",            "0034"),
    ("eval_keratitis_mask_input.json",   "keratitis",    "mask_input (RQ1)",            "0034"),
    ("eval_keratitis_region_crop.json",  "keratitis",    "region_crop (RQ1)",           "0034"),
    ("eval_keratitis_synthetic.json",    "keratitis",    "+ diffusion synth (RQ2a)",    "0063"),
    ("eval_keratitis_harmonized.json",   "keratitis",    "+ CycleGAN harmonise (RQ2b)", "3007"),
    ("eval_keratitis_ensemble.json",     "keratitis",    "5-model ensemble (RQ3)",      "0001"),
    ("eval_ulcer_pattern_image.json",    "ulcer_pattern","image (baseline)",            "0034"),
    ("eval_ulcer_pattern_mask_input.json","ulcer_pattern","mask_input (RQ1)",           "0034"),
    ("eval_ulcer_pattern_region_crop.json","ulcer_pattern","region_crop (RQ1)",         "0063"),
    ("eval_ulcer_pattern_multitask.json","ulcer_pattern","multitask (RQ1)",             "0001"),
    ("eval_trachoma_tf_image.json",      "trachoma_tf",  "image (baseline)",            "0034"),
]
s += [p("K2.2 Test-set results, every task and variant", H2)]
_rows = [["Task", "Variant", "Acct", "n", "Acc", "Bal.acc", "F1", "AUROC", "Kappa", "ECE"]]
for _name, _task, _variant, _acct in _MAP:
    _d = _load(_name)
    if not _d:
        continue
    _o = _d.get("overall", {})
    _rows.append([_task, _variant, _acct, str(_o.get("n", "")),
                  _f3(_o.get("accuracy")), _f3(_o.get("balanced_accuracy")), _f3(_o.get("macro_f1")),
                  _f3(_o.get("auroc_macro_ovr", _o.get("auroc"))), _f3(_o.get("kappa")), _f3(_o.get("ece"))])
s.append(table(_rows, [2.5*cm, 3.9*cm, 1.3*cm, 0.9*cm, 1.2*cm, 1.4*cm, 1.1*cm, 1.4*cm, 1.4*cm, 1.2*cm]))
s.append(p("Variant meaning (RQ1 - does telling the model where the cornea is help?): <b>image</b> = photo only; "
           "<b>mask_input</b> = cornea mask added as a 4th input channel; <b>region_crop</b> = image cropped to the cornea; "
           "<b>multitask</b> = a second head also predicts ulcer severity grade. RQ2a adds diffusion-generated rare-class "
           "images to training; RQ2b restyles training images toward the test hospital with CycleGAN; RQ3 averages five "
           "independently seeded models."))

# --- RQ1 read-off per task
for _task, _label in [("ulcer_pattern", "ulcer pattern"), ("keratitis", "keratitis")]:
    _variants = [(v, n) for (n, t, v, a) in _MAP if t == _task and ("baseline" in v or "RQ1" in v)]
    _br = [["Variant", "Balanced acc.", "Macro F1", "ECE"]]
    for _v, _n in _variants:
        _d = _load(_n)
        if not _d:
            continue
        _o = _d["overall"]
        _br.append([_v, _f3(_o.get("balanced_accuracy")), _f3(_o.get("macro_f1")), _f3(_o.get("ece"))])
    if len(_br) > 1:
        s += [p(f"K2.3 RQ1 read-off - {_label}", H2)]
        s.append(table(_br, [7.0*cm, 3.6*cm, 3.2*cm, 3.0*cm]))

# --- explanation quality (RQ4) from the 50-epoch explain files
_EX = ["explain_ulcer_image_cornea.json", "explain_ulcer_image_ulcer.json",
       "explain_ulcer_maskinput_cornea.json", "explain_ulcer_maskinput_ulcer.json"]
_exrows = [["Model / mask / method", "Imgs", "Attn in region", "Mask area", "Reliable", "Pointing", "Del.AUC"]]
for _n in _EX:
    _d = _load(_n)
    if not _d:
        continue
    _sm = _d["summary"]
    _mdl = "image" if "image" in _n else "mask_input"
    _exrows.append([f"ulcer {_mdl} / {_sm['mask']} / {_sm['method']}", str(_sm["n"]),
                    str(_sm["mean_attention_in_region"]), str(_sm["mean_mask_area"]),
                    str(_sm["share_reliable"]), str(_sm["pointing_game"]), str(_sm["mean_deletion_auc"])])
if len(_exrows) > 1:
    s += [p("K2.4 Explanation quality (RQ4, Grad-CAM++)", H2)]
    s.append(table(_exrows, [5.6*cm, 1.3*cm, 2.3*cm, 1.8*cm, 1.7*cm, 1.7*cm, 1.8*cm]))
    s.append(p("<b>Correction (25 Nov):</b> the two ulcer-mask rows above used inverted ulcer labels and are not valid; "
               "see Part K5 for the corrected figures. The cornea-mask rows are unaffected."))
    s.append(p("Attention-in-region is the share of heat-map mass inside the cornea/ulcer mask; read it against the "
               "mask area (a map spread evenly scores about the mask area by chance). Higher attention-in-region, "
               "pointing-game and lower deletion-AUC mean a more faithful, better-localised explanation."))

# --- ensemble extra detail
_ens = _load("eval_keratitis_ensemble.json")
if _ens:
    s += [p("K2.5 Ensemble uncertainty (RQ3)", H2),
          p(f"The {_ens.get('members','?')}-model deep ensemble reaches balanced accuracy "
            f"{_f3(_ens['overall'].get('balanced_accuracy'))} on the keratitis test set. Mean mutual information "
            f"(member disagreement, used as an epistemic-uncertainty / referral signal) is "
            f"{_f3(_ens.get('mean_mutual_information'))}.")]
