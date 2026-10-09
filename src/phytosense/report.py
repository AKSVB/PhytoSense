"""Overlay images and result files."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .analysis import ImageResult
from .imageio import to_gray


def overlay(img: np.ndarray, result: ImageResult, mask: np.ndarray | None = None) -> Image.Image:
    """Draw detections (ellipses or points) and the analysed field boundary."""
    g = to_gray(img)
    base = Image.fromarray((np.clip(g, 0, 1) * 255).astype(np.uint8)).convert("RGB")
    if mask is not None:
        from skimage.segmentation import find_boundaries

        b = find_boundaries(mask, mode="inner")
        arr = np.asarray(base).copy()
        arr[b] = (255, 200, 0)
        base = Image.fromarray(arr)
    d = ImageDraw.Draw(base)
    lw = max(1, int(min(base.size) / 400))
    for det in result.detections:
        colour = (0, 220, 0) if det.is_open is not False else (220, 60, 60)
        if math.isfinite(det.length_px) and math.isfinite(det.angle_deg):
            a = math.radians(det.angle_deg)
            dx, dy = 0.5 * det.length_px * math.cos(a), -0.5 * det.length_px * math.sin(a)
            d.line([(det.x - dx, det.y - dy), (det.x + dx, det.y + dy)], fill=colour, width=lw)
            r = 0.5 * det.length_px
        else:
            r = 4 * lw
        d.ellipse([det.x - r, det.y - r, det.x + r, det.y + r], outline=colour, width=lw)
    return base


def write_results(results: list[ImageResult], out_dir: str | Path) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = [r.flat_row() for r in results]
    if rows:
        with open(out / "summary.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    with open(out / "results.json", "w") as f:
        json.dump([r.to_dict(with_detections=True) for r in results], f, indent=2, default=_json_default)


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    raise TypeError(type(o))
