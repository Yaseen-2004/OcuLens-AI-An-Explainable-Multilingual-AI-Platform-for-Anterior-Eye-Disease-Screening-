"""Scan datasets/ and write data/manifest.csv.

    python scripts/build_manifest.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oculens.config import load_config, resolve  # noqa: E402
from oculens.data.manifest import build_manifest, summarize  # noqa: E402


def main():
    cfg = load_config()
    root = resolve(cfg["paths"]["datasets_root"])
    out = resolve(cfg["paths"]["manifest"])
    df = build_manifest(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(summarize(df).to_string())
    print(f"\n{len(df)} images -> {out}")


if __name__ == "__main__":
    main()
