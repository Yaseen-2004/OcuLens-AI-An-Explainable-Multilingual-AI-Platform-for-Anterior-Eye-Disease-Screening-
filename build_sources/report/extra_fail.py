# Part O - Failure analysis: where the models get it wrong (23 Nov 2026).
import os as _oO, json as _jO
from reportlab.platypus import Image as _RLImg, Table as _Tbl, TableStyle as _TS
from PIL import Image as _PImg

_FP = _oO.path.join(r"D:\Capston_Project", "experiments", "failures")
_IDX = _oO.path.join(_FP, "index.json")

_TASKN = {"keratitis": "Keratitis (ensemble)", "ulcer_pattern": "Ulcer pattern", "trachoma_tf": "Trachoma (TF)"}

if _oO.path.exists(_IDX):
    _items = _jO.load(open(_IDX, encoding="utf-8"))
    if _items:
        s.append(PageBreak())
        s += [p("Part O - Failure analysis", H1),
              p("Honest error review: the misclassified test cases below are shown most-confident-mistake first, with the "
                "Grad-CAM++ heat-map, so the failure modes are visible rather than hidden behind an average. Confident errors "
                "are the ones that matter for safety - and the reason the referral gate exists.")]
        _by = {}
        for _it in _items:
            _by.setdefault(_it["task"], []).append(_it)
        for _task, _lst in _by.items():
            s += [p(_TASKN.get(_task, _task), H2)]
            _imgs, _caps = [], []
            for _it in _lst[:6]:
                _fp = _oO.path.join(_FP, _it["file"])
                if not _oO.path.exists(_fp):
                    continue
                _w, _h = _PImg.open(_fp).size
                _iw = 5.0 * cm
                _imgs.append(_RLImg(_fp, width=_iw, height=_iw * _h / _w))
                _caps.append(p(f"true: <b>{_it['true']}</b><br/>pred: <b>{_it['pred']}</b> ({_it['conf']*100:.0f}%)"))
            # lay out 3 per row: image row then caption row
            for _i in range(0, len(_imgs), 3):
                _ri = _imgs[_i:_i + 3]
                _rc = _caps[_i:_i + 3]
                _t = _Tbl([_ri, _rc], colWidths=[5.4 * cm] * len(_ri))
                _t.setStyle(_TS([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                 ("BOTTOMPADDING", (0, 0), (-1, 0), 2), ("BOTTOMPADDING", (0, 1), (-1, 1), 10)]))
                s.append(_t)
        s.append(p("These are first baselines on public data; keratitis in particular shows the hard, visually-similar "
                   "infection types driving most errors - a target for the rare-class augmentation and multi-site data in the roadmap."))
