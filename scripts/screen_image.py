"""Screen one image from the command line.

    python scripts/screen_image.py path/to/eye.jpg --task keratitis --symptoms pain,redness
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from oculens.assistant.llm import explain  # noqa: E402
from oculens.assistant.report import doctor_report  # noqa: E402
from oculens.pipeline import ScreeningPipeline  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--task", default="keratitis")
    ap.add_argument("--symptoms", default="", help="comma separated, e.g. pain,redness")
    ap.add_argument("--language", default="en")
    args = ap.parse_args()

    pipe = ScreeningPipeline.from_task(args.task)
    img = np.array(Image.open(args.image).convert("RGB"))
    sym = {s.strip(): True for s in args.symptoms.split(",") if s.strip()}
    out = pipe.run(img, symptoms=sym, return_overlay=False)
    report = out["report"]
    print(doctor_report(report))
    print("\n--- patient explanation ---")
    print(json.dumps(explain(report, language=args.language), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
