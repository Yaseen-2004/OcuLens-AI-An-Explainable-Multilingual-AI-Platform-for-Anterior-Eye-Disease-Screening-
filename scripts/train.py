"""Train a classifier: python scripts/train.py --task keratitis [--epochs N] [--limit N]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oculens.training.train_classifier import main  # noqa: E402

if __name__ == "__main__":
    main()
