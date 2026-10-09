"""Image loading and basic conversions."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


def load_gray(path: str | Path) -> np.ndarray:
    """Load an image as float64 grayscale in [0, 1].

    EXIF orientation is applied so that phone photos come out the way they
    were taken.
    """
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        im = im.convert("L")
        arr = np.asarray(im, dtype=np.float64) / 255.0
    return arr


def load_rgb(path: str | Path) -> np.ndarray:
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        return np.asarray(im.convert("RGB"))


def to_gray(img: np.ndarray) -> np.ndarray:
    """Convert an array (gray or RGB, uint8 or float) to float grayscale in [0, 1]."""
    a = np.asarray(img)
    if a.ndim == 3:
        a = a[..., :3].astype(np.float64) @ np.array([0.299, 0.587, 0.114])
    else:
        a = a.astype(np.float64)
    if a.max() > 1.0:
        a = a / 255.0
    return a


def save_gray(img: np.ndarray, path: str | Path) -> None:
    a = np.clip(np.asarray(img, dtype=np.float64), 0, 1)
    Image.fromarray((a * 255).astype(np.uint8)).save(path)
