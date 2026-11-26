"""Build one manifest CSV that describes every image in the downloaded datasets.

Each row is one image with:
  image_path    path relative to the datasets root
  dataset       short dataset name
  region        anatomical region the label refers to
  label         main class label ("" when the dataset has no label for this image)
  extra         JSON with dataset-specific fields (grades, eye side, illumination mode ...)
  group         ID used for leakage-free splitting (patient or eye where known)
  site          hospital / source
  quality_tier  clinical | field | web
  mask_path     segmentation mask path relative to the datasets root, if any

Splitting must use `group`, never single images, so one patient never appears in both
training and test data.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

import pandas as pd

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
COLUMNS = ["image_path", "dataset", "region", "label", "extra", "group", "site", "quality_tier", "mask_path"]


def _images(folder: Path):
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXT)


def _row(root: Path, img: Path, **kw) -> dict:
    row = {c: "" for c in COLUMNS}
    row["image_path"] = img.relative_to(root).as_posix()
    extra = kw.pop("extra", None)
    row["extra"] = json.dumps(extra or {}, sort_keys=True)
    row.update(kw)
    return row


def _sha1(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- per-dataset readers

def read_sustech(root: Path) -> list[dict]:
    """SUSTech-SYSU corneal ulcer: labels from 'Category information.xlsx', cornea and ulcer masks."""
    base = root / "sustech_sysu_corneal_ulcer" / "raw"
    if not base.exists():
        return []
    labels: dict[str, dict] = {}
    xlsx = base / "Category information.xlsx"
    if xlsx.exists():
        import openpyxl

        ws = openpyxl.load_workbook(xlsx, read_only=True).worksheets[0]
        for name, category, typ, grade in list(ws.iter_rows(values_only=True))[1:]:
            if name:
                labels[str(name)] = {"category": category, "type": typ, "grade": grade}
    rows = []
    for img in _images(base / "rawImages"):
        stem = img.stem
        lab = labels.get(img.name, {})
        ulcer = base / "ulcerLabels" / f"{stem}.png"
        cornea = base / "corneaLabels" / f"{stem}.png"
        rows.append(_row(
            root, img, dataset="sustech_sysu", region="cornea",
            label="" if lab.get("category") is None else str(lab["category"]),
            extra={**lab, "cornea_mask": cornea.relative_to(root).as_posix() if cornea.exists() else ""},
            group=f"sustech_{stem}",  # no patient IDs are published; each image is its own group
            site="ZOC", quality_tier="clinical",
            mask_path=ulcer.relative_to(root).as_posix() if ulcer.exists() else "",
        ))
    return rows


_KERATITIS_NAME = re.compile(r"^(?P<cls>[A-Za-z]+)_(?P<pid>\d+)_(?P<visit>\d+)(?P<eye>[LR])", re.I)


def read_keratitis(root: Path) -> list[dict]:
    """Infectious keratitis (Figshare): <site>/<class>/<illumination mode 1|2|3>/<CLASS>_<patient>_<nn><L|R>.jpg."""
    base = root / "infectious_keratitis_figshare" / "raw"
    rows = []
    for site_dir in sorted(base.glob("*_Dataset")) if base.exists() else []:
        site = site_dir.name.replace("_Dataset", "")
        inner = site_dir / site_dir.name
        inner = inner if inner.exists() else site_dir
        for class_dir in sorted(d for d in inner.iterdir() if d.is_dir()):
            for img in _images(class_dir):
                mode = img.parent.name if img.parent != class_dir else ""
                m = _KERATITIS_NAME.match(img.stem)
                pid = m.group("pid") if m else img.stem
                eye = m.group("eye").upper() if m else ""
                rows.append(_row(
                    root, img, dataset="infectious_keratitis", region="cornea", label=class_dir.name,
                    extra={"illumination_mode": mode, "eye": eye, "visit": m.group("visit") if m else ""},
                    group=f"ker_{site}_{class_dir.name}_{pid}", site=site, quality_tier="clinical",
                ))
    return rows


def read_eye_disease_web(root: Path) -> list[dict]:
    """Web-sourced eye disease classification set. Exact duplicates share a group."""
    base = root / "eye_disease_classification_mendeley" / "raw"
    rows = []
    for top in sorted(base.iterdir()) if base.exists() else []:
        if not top.is_dir():
            continue
        for class_dir in sorted(d for d in top.iterdir() if d.is_dir()):
            for img in _images(class_dir):
                rows.append(_row(
                    root, img, dataset="eye_disease_web", region="whole_eye", label=class_dir.name,
                    group=f"web_{_sha1(img)[:16]}", site="web", quality_tier="web",
                ))
    return rows


def read_trachoma(root: Path) -> list[dict]:
    """Trachoma conjunctival photos with TF / TI labels from tfti.csv."""
    base = root / "trachoma_conjunctiva_figshare" / "raw" / "m"
    if not base.exists():
        return []
    labels = {}
    csv_path = base / "tfti.csv"
    if csv_path.exists():
        with open(csv_path, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                labels[r["key"]] = {"TF": r["TF"], "TI": r["TI"]}
    rows = []
    for img in _images(base):
        key = img.stem.replace("image", "")
        lab = labels.get(key, {})
        rows.append(_row(
            root, img, dataset="trachoma", region="conjunctiva", label=lab.get("TF", ""),
            extra=lab, group=f"tra_{key}", site="Niger_Ethiopia", quality_tier="field",
        ))
    return rows


def read_nuclear_cataract(root: Path) -> list[dict]:
    """Nuclear cataract slit-lamp images. NOTE: the public download has no LOCS III grades."""
    base = root / "nuclear_cataract_mendeley" / "raw"
    rows = []
    for ds in base.rglob("Nuclear Cataract Dataset") if base.exists() else []:
        for pdir in sorted(d for d in ds.iterdir() if d.is_dir()):
            for img in _images(pdir):
                eye = {"DER": "R", "IZQ": "L"}.get(img.parent.name, "")
                rows.append(_row(
                    root, img, dataset="nuclear_cataract", region="lens", label="",
                    extra={"eye": eye}, group=f"nuc_{pdir.name}", site="Conde_Valenciana", quality_tier="clinical",
                ))
    return rows


def read_temporal(root: Path) -> list[dict]:
    """Slit-lamp time series: S1_file/<patient>/<patient>_<t>_<tag>.jpg."""
    base = root / "slitlamp_cataract_temporal_figshare" / "raw"
    rows = []
    for img in _images(base) if base.exists() else []:
        parts = img.stem.split("_")
        rows.append(_row(
            root, img, dataset="slitlamp_temporal", region="lens", label="",
            extra={"timepoint": parts[1] if len(parts) > 1 else "", "tag": parts[2] if len(parts) > 2 else ""},
            group=f"tmp_{img.parent.name}", site="PLOS_ONE_2018", quality_tier="clinical",
        ))
    return rows


READERS = [read_sustech, read_keratitis, read_eye_disease_web, read_trachoma, read_nuclear_cataract, read_temporal]


def build_manifest(datasets_root: str | Path) -> pd.DataFrame:
    root = Path(datasets_root)
    rows: list[dict] = []
    for reader in READERS:
        rows.extend(reader(root))
    return pd.DataFrame(rows, columns=COLUMNS)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """Images, groups and labeled images per dataset."""
    return (df.assign(labeled=df["label"].astype(str).ne(""))
              .groupby("dataset")
              .agg(images=("image_path", "size"), groups=("group", "nunique"), labeled=("labeled", "sum")))
