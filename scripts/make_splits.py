"""Create leakage-free split CSVs for every task in the config.

    python scripts/make_splits.py              # all tasks
    python scripts/make_splits.py keratitis    # one task
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from oculens.config import load_config, resolve  # noqa: E402
from oculens.data.splits import make_task_split  # noqa: E402


def main(tasks):
    cfg = load_config()
    manifest = pd.read_csv(resolve(cfg["paths"]["manifest"]), dtype=str, keep_default_na=False)
    out_dir = resolve(cfg["paths"]["splits_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in tasks or cfg["tasks"]:
        df = make_task_split(manifest, cfg["tasks"][name], seed=cfg["training"]["seed"])
        df.to_csv(out_dir / f"{name}.csv", index=False)
        table = pd.crosstab(df["label"], df["split"])
        print(f"\n== {name}: {len(df)} images, {df['group'].nunique()} groups (no group in two splits)")
        print(table.to_string())


if __name__ == "__main__":
    main(sys.argv[1:])
