"""Illumination correction and contrast normalisation."""

from __future__ import annotations

import numpy as np
from skimage import exposure, filters

from .imageio import to_gray


def flatten(img: np.ndarray, sigma_px: float, mask: np.ndarray | None = None) -> np.ndarray:
    """Divide out slow illumination changes (LED hot spots, vignetting).

    ``sigma_px`` should be several times the stoma length so that the
    background estimate does not follow the stomata themselves.
    """
    g = to_gray(img)
    if mask is not None:
        # Normalised convolution so the dark surround does not bleed inwards.
        m = mask.astype(np.float64)
        num = filters.gaussian(g * m, sigma_px)
        den = filters.gaussian(m, sigma_px)
        bg = np.divide(num, den, out=np.ones_like(g), where=den > 1e-6)
    else:
        bg = filters.gaussian(g, sigma_px)
    out = g / np.maximum(bg, 1e-3)
    if mask is not None:
        out = np.where(mask, out, 1.0)
    lo, hi = np.percentile(out[mask] if mask is not None else out, [0.5, 99.5])
    return np.clip((out - lo) / max(hi - lo, 1e-6), 0, 1)


def enhance(img: np.ndarray, clip_limit: float = 0.01) -> np.ndarray:
    """Local contrast enhancement (CLAHE)."""
    return exposure.equalize_adapthist(to_gray(img), clip_limit=clip_limit)
