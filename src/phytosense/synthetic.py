"""Synthetic test images with known ground truth.

These do not look like real leaves. They exist to test the pipeline's
geometry: calibration, field masking, counting, density and pattern
statistics, where the true answer must be known exactly.
"""

from __future__ import annotations

import math

import numpy as np
from skimage import draw, filters


def poisson_disc(width: float, height: float, min_dist: float, n_target: int, rng) -> np.ndarray:
    """Dart-throwing points with a hard minimum distance (an inhibition process)."""
    pts: list[tuple[float, float]] = []
    tries = 0
    while len(pts) < n_target and tries < n_target * 200:
        tries += 1
        p = (rng.uniform(0, width), rng.uniform(0, height))
        if all(math.hypot(p[0] - q[0], p[1] - q[1]) >= min_dist for q in pts):
            pts.append(p)
    return np.array(pts).reshape(-1, 2)


def epidermis(
    size: int = 800,
    stoma_length_px: float = 24,
    n_stomata: int = 120,
    min_dist_frac: float = 1.8,
    vignette: bool = True,
    noise: float = 0.03,
    blur_sigma: float = 1.0,
    seed: int = 0,
    clusters: int = 0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (image, true_points_xy, true_field_mask).

    Stomata are dark ellipses with a lighter pore slit on a mottled
    background. With ``vignette`` the image has a circular field and dark
    surround, as with a clip-on lens. ``clusters`` adds that many extra
    stomata placed in contact with existing ones.
    """
    rng = np.random.default_rng(seed)
    L = stoma_length_px
    W = 0.65 * L
    img = 0.7 + 0.05 * filters.gaussian(rng.normal(size=(size, size)), 6) * 10

    if vignette:
        yy, xx = np.mgrid[0:size, 0:size]
        r = np.hypot(yy - size / 2, xx - size / 2)
        R = 0.45 * size
        field = r < R
    else:
        field = np.ones((size, size), dtype=bool)

    pad = L
    cand = poisson_disc(size - 2 * pad, size - 2 * pad, min_dist_frac * L, n_stomata * 3, rng) + pad
    inside = np.array([field[int(y), int(x)] for x, y in cand], dtype=bool) if len(cand) else np.array([], bool)
    pts = cand[inside][:n_stomata]

    extra = []
    for i in range(min(clusters, len(pts))):
        x, y = pts[i]
        ang = rng.uniform(0, 2 * math.pi)
        extra.append((x + 0.95 * W * math.cos(ang), y + 0.95 * W * math.sin(ang)))
    if extra:
        pts = np.vstack([pts, np.array(extra)])

    for x, y in pts:
        theta = rng.uniform(0, math.pi)
        rr, cc = draw.ellipse(y, x, W / 2, L / 2, shape=img.shape, rotation=theta)
        img[rr, cc] = 0.35
        rr, cc = draw.ellipse(y, x, W / 10, L / 3.5, shape=img.shape, rotation=theta)
        img[rr, cc] = 0.55

    img = filters.gaussian(img, blur_sigma)
    img = img + rng.normal(0, noise, img.shape)
    if vignette:
        yy, xx = np.mgrid[0:size, 0:size]
        r = np.hypot(yy - size / 2, xx - size / 2)
        fall = np.clip((0.5 * size - r) / (0.05 * size), 0, 1)
        img = img * fall + 0.03 * (1 - fall)
    return np.clip(img, 0, 1), pts, field


def grating(size: int = 600, period_px: float = 17.3, angle_deg: float = 12.0, seed: int = 0) -> np.ndarray:
    """A ruled-line pattern like a stage micrometer, at an arbitrary angle."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size].astype(float)
    a = math.radians(angle_deg)
    u = xx * math.cos(a) + yy * math.sin(a)
    lines = (np.mod(u, period_px) < 2.0).astype(float)
    img = 0.85 - 0.6 * lines
    img = filters.gaussian(img, 0.8) + rng.normal(0, 0.02, img.shape)
    return np.clip(img, 0, 1)
