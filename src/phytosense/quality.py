"""Image quality control and the usable field of view.

Clip-on lenses project a circular image with a dark, vignetted surround and
a soft edge. Density must be computed over the area that is actually in
focus and illuminated, not over the whole sensor frame, so the first step is
to find that field.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy import ndimage as ndi
from skimage import filters, morphology

from .imageio import to_gray


def field_mask(img: np.ndarray, margin_frac: float = 0.03, min_frac: float = 0.05) -> np.ndarray:
    """Boolean mask of the illuminated field of view.

    The image is heavily blurred, thresholded with Otsu's method, and the
    largest bright connected region is kept, hole-filled and eroded by
    ``margin_frac`` of the short image side to drop the soft vignette edge.
    If no dark surround is found (e.g. a lab microscope image that fills the
    frame), the whole frame minus the margin is returned.
    """
    g = to_gray(img)
    h, w = g.shape
    sigma = max(h, w) / 100
    blur = filters.gaussian(g, sigma=sigma)
    margin = max(1, int(round(min(h, w) * margin_frac)))

    full = np.zeros_like(g, dtype=bool)
    full[margin : h - margin, margin : w - margin] = True

    if blur.max() - blur.min() < 0.05:
        return full
    t = filters.threshold_otsu(blur)
    bright = blur > t
    # A real vignetted field leaves a dark border on most of the frame edge.
    edge = np.concatenate([bright[0], bright[-1], bright[:, 0], bright[:, -1]])
    if edge.mean() > 0.6:
        return full

    lab, n = ndi.label(bright)
    if n == 0:
        return full
    sizes = ndi.sum(bright, lab, index=np.arange(1, n + 1))
    keep = lab == (np.argmax(sizes) + 1)
    keep = ndi.binary_fill_holes(keep)
    keep = ndi.binary_erosion(keep, structure=morphology.disk(margin))
    if keep.mean() < min_frac:
        return full
    return keep


def mask_perimeter_px(mask: np.ndarray) -> float:
    """Approximate perimeter length of a binary mask in pixels."""
    from skimage.measure import perimeter

    return float(perimeter(mask))


@dataclass
class QualityReport:
    focus: float
    saturated_frac: float
    dark_frac: float
    field_frac: float
    flags: list[str]

    def ok(self) -> bool:
        return not self.flags

    def to_dict(self) -> dict:
        return asdict(self)


def focus_score(img: np.ndarray, mask: np.ndarray | None = None) -> float:
    """Variance of the Laplacian, normalised by local contrast.

    Higher is sharper. The value depends on magnification and subject, so
    thresholds should be set per calibration profile from a few known-good
    and known-blurred images.
    """
    g = to_gray(img)
    lap = ndi.laplace(filters.gaussian(g, 1.0))
    if mask is None:
        mask = np.ones_like(g, dtype=bool)
    std = g[mask].std()
    if std == 0:
        return 0.0
    return float(lap[mask].var() / (std**2))


def assess(img: np.ndarray, mask: np.ndarray | None = None, min_focus: float = 0.002) -> QualityReport:
    g = to_gray(img)
    if mask is None:
        mask = field_mask(g)
    vals = g[mask]
    rep = QualityReport(
        focus=focus_score(g, mask),
        saturated_frac=float((vals >= 0.98).mean()),
        dark_frac=float((vals <= 0.02).mean()),
        field_frac=float(mask.mean()),
        flags=[],
    )
    if rep.focus < min_focus:
        rep.flags.append("blurred")
    if rep.saturated_frac > 0.05:
        rep.flags.append("overexposed")
    if rep.dark_frac > 0.2:
        rep.flags.append("underexposed")
    if rep.field_frac < 0.1:
        rep.flags.append("small_field")
    return rep
