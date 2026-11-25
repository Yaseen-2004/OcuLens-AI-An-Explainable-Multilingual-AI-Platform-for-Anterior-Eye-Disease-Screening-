"""Write downscaled copies of every manifest image to data/cache/ (long side = preprocessing.work_size).

Decoding 12-megapixel JPEGs dominates training time, especially on a CPU. The cache keeps the
same relative paths, and EyeImageDataset reads from it automatically when a cached copy exists.

    python scripts/cache_images.py              # all datasets
    python scripts/cache_images.py keratitis    # only images used by one task's split file
"""
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

from oculens.config import load_config, resolve  # noqa: E402


def cache_one(src: Path, dst: Path, size: int) -> int:
    if dst.exists():
        return 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(src).convert("RGB")
    img.thumbnail((size, size), Image.Resampling.LANCZOS)
    img.save(dst.with_suffix(".jpg"), quality=95)
    return 1


def main(tasks):
    cfg = load_config()
    root = resolve(cfg["paths"]["datasets_root"])
    cache = resolve(cfg["paths"].get("cache_dir", "data/cache"))
    size = int(cfg["preprocessing"].get("work_size", 512))
    if tasks:
        paths = pd.concat([pd.read_csv(resolve(cfg["paths"]["splits_dir"]) / f"{t}.csv", dtype=str) for t in tasks])
    else:
        paths = pd.read_csv(resolve(cfg["paths"]["manifest"]), dtype=str)
    rels = sorted(set(paths["image_path"]))
    with ThreadPoolExecutor(max_workers=6) as ex:
        n = sum(ex.map(lambda r: cache_one(root / r, (cache / r).with_suffix(".jpg"), size), rels))
    print(f"{n} new cached images ({len(rels)} total) in {cache}")


if __name__ == "__main__":
    main(sys.argv[1:])
