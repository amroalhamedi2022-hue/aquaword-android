#!/usr/bin/env python3
"""Validate captured, actually rendered Android emulator pixels; fail on black."""
from pathlib import Path
import argparse
from PIL import Image, ImageStat


def verify(path: Path, aspect: float | None = None) -> tuple[int,int]:
    image = Image.open(path).convert("RGB")
    w,h=image.size
    if w < 480 or h < 480:
        raise ValueError(f"Invalid emulator screenshot dimensions: {w}x{h}")
    statistics=ImageStat.Stat(image.resize((100,100)))
    if max(statistics.var)<100 or max(statistics.mean)<10:
        raise ValueError(f"Black/blank Android frame: {path}, RGB {statistics.mean}")
    if aspect is not None and abs((w/h)-aspect)>0.035:
        raise ValueError(f"Wrong orientation/aspect: {w}x{h} vs {aspect:.3f}")
    print(f"VALID pixels {path}: {w}x{h}, mean={statistics.mean}, variance={statistics.var}")
    return w,h


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("path",type=Path)
    p.add_argument("--aspect",type=float,default=None)
    a=p.parse_args()
    verify(a.path,a.aspect)
