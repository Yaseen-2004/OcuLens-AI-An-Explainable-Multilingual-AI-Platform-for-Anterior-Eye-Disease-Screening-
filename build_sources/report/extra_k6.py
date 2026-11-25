# Part K6 - Is the keratitis result reproducible? Seed study and diffusion ensemble (25 Nov 2026).
import os as _osK6, json as _jsK6
_SS = _osK6.path.join(r"D:\Capston_Project", "experiments", "runs", "seed_study.json")
_CI6 = _osK6.path.join(r"D:\Capston_Project", "experiments", "ci", "ci.json")
if _osK6.path.exists(_SS):
    _st = _jsK6.load(open(_SS, encoding="utf-8")); _ci6 = _jsK6.load(open(_CI6, encoding="utf-8"))
    s.append(PageBreak())
    s += [p("Part K6 - Is the keratitis result reproducible?", H1),
          p("The selected keratitis model (diffusion-augmented, 0.488) came from a single training run, and its confidence "
            "interval overlapped the previous ensemble's. To test whether it was a lucky draw, the identical recipe (same 809 real "
            "and 1,200 synthetic training images, same settings) was retrained with three more random seeds, in parallel on "
            "accounts 0063, 0034 and 3007.")]
    _rows6 = [["Run", "Balanced accuracy"]] + [[f"Seed {k}" + (" (original, in the portal)" if k == "42" else ""), f"{v:.3f}"] for k, v in _st["seeds"].items()]
    _rows6 += [["Mean ± standard deviation of the four seeds", f'{_st["mean"]:.3f} ± {_st["sd"]:.3f}'],
               ["Ensemble of the four diffusion models [95% CI]", f'{_st["ensemble4"]["point"]:.3f} [{_st["ensemble4"]["ci95"][0]:.3f}–{_st["ensemble4"]["ci95"][1]:.3f}]'],
               ["10-model plain ensemble, for comparison", "0.451"],
               ["Plain image-only model (seed 42), for comparison", "0.371"]]
    s.append(table(_rows6, [11.2*cm, 5.0*cm]))
    s.append(p("Result: 0.488 was the best of four seeds; the typical single run is about 0.42 ± 0.05. Diffusion augmentation "
               "still helps on average compared with the plain image-only model, but a single diffusion model does not reliably "
               "beat the 10-model ensemble. Averaging the four diffusion models gives 0.474, better than the 10-model ensemble "
               "with fewer than half the models and without depending on one lucky seed; its interval still overlaps, so the "
               "gain is promising rather than proven. Method note: the keratitis model was chosen by comparing test-set scores, "
               "which makes the reported 0.488 optimistic; the seed average (0.42) and the ensemble (0.474) are the fairer "
               "figures, and future model selection should use the validation split."))
