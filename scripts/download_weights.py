"""Download ImageNet weights for timm backbones into models/pretrained/.

    python scripts/download_weights.py efficientnet_b0.ra_in1k convnext_tiny.fb_in1k
"""
import sys
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "models" / "pretrained"


def main(names):
    OUT.mkdir(parents=True, exist_ok=True)
    for name in names or ["efficientnet_b0.ra_in1k"]:
        dest = OUT / f"{name}.safetensors"
        url = f"https://huggingface.co/timm/{name}/resolve/main/model.safetensors"
        print("downloading", url)
        urllib.request.urlretrieve(url, dest)
        print("  ->", dest, dest.stat().st_size // 1_000_000, "MB")


if __name__ == "__main__":
    main(sys.argv[1:])
