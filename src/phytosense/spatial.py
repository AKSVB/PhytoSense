"""Spatial pattern statistics for stomatal positions.

All functions take point coordinates in pixels together with the analysed
field (a boolean mask), so edge effects can be corrected. Convert distances
to micrometres with the calibration afterwards.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.stats import norm


def nearest_neighbour_distances(pts: np.ndarray) -> np.ndarray:
    pts = np.asarray(pts, dtype=float)
    if len(pts) < 2:
        return np.array([])
    d, _ = cKDTree(pts).query(pts, k=2)
    return d[:, 1]


@dataclass
class ClarkEvans:
    n: int
    mean_nnd: float
    expected_nnd: float
    R: float
    z: float
    p_two_sided: float
    pattern: str

    def to_dict(self) -> dict:
        return asdict(self)


def clark_evans(pts: np.ndarray, area: float, perimeter: float, alpha: float = 0.05) -> ClarkEvans:
    """Clark-Evans aggregation index with Donnelly's (1978) edge correction.

    R < 1 indicates clustering, R = 1 complete spatial randomness, R > 1
    regular spacing. Stomata usually give R > 1 because of the one-cell
    spacing rule; values near or below 1 point to patterning defects.
    """
    n = len(pts)
    if n < 3:
        nan = float("nan")
        return ClarkEvans(n, nan, nan, nan, nan, nan, "insufficient points")
    nnd = nearest_neighbour_distances(pts)
    mean = float(nnd.mean())
    expected = 0.5 * math.sqrt(area / n) + (0.0514 + 0.041 / math.sqrt(n)) * perimeter / n
    se = math.sqrt(0.0703 * area / n**2 + 0.037 * perimeter * math.sqrt(area / n**5))
    z = (mean - expected) / se
    p = float(2 * norm.sf(abs(z)))
    R = mean / expected
    if p >= alpha:
        pattern = "random"
    else:
        pattern = "regular" if R > 1 else "clustered"
    return ClarkEvans(n, mean, expected, R, z, p, pattern)


def ripley_l(pts: np.ndarray, mask: np.ndarray, radii: np.ndarray) -> np.ndarray:
    """Besag's L(r) - r with border correction.

    Only points at least r from the field edge serve as centres for radius r.
    Negative values at short range indicate inhibition (regular spacing),
    positive values indicate clustering.
    """
    pts = np.asarray(pts, dtype=float)
    n = len(pts)
    area = float(mask.sum())
    radii = np.asarray(radii, dtype=float)
    out = np.full(radii.shape, np.nan)
    if n < 2:
        return out
    edge_dist = ndi.distance_transform_edt(mask)
    rows = np.clip(np.round(pts[:, 1]).astype(int), 0, mask.shape[0] - 1)
    cols = np.clip(np.round(pts[:, 0]).astype(int), 0, mask.shape[1] - 1)
    b = edge_dist[rows, cols]
    tree = cKDTree(pts)
    lam = n / area
    for i, r in enumerate(radii):
        centres = np.where(b >= r)[0]
        if len(centres) == 0:
            continue
        counts = np.array([len(tree.query_ball_point(pts[c], r)) - 1 for c in centres])
        K = counts.mean() / lam
        out[i] = math.sqrt(K / math.pi) - r
    return out


def csr_envelope(
    mask: np.ndarray, n: int, radii: np.ndarray, nsim: int = 99, seed: int | None = 0
) -> tuple[np.ndarray, np.ndarray]:
    """Pointwise min/max of L(r) - r under complete spatial randomness in the same field."""
    rng = np.random.default_rng(seed)
    rr, cc = np.nonzero(mask)
    sims = np.empty((nsim, len(radii)))
    for k in range(nsim):
        idx = rng.choice(len(rr), size=n, replace=False)
        p = np.column_stack([cc[idx] + rng.random(n) - 0.5, rr[idx] + rng.random(n) - 0.5])
        sims[k] = ripley_l(p, mask, radii)
    return np.nanmin(sims, axis=0), np.nanmax(sims, axis=0)


@dataclass
class Clusters:
    n_in_clusters: int
    frac_in_clusters: float
    n_clusters: int
    largest_cluster: int
    sizes: list[int]

    def to_dict(self) -> dict:
        return asdict(self)


def contact_clusters(pts: np.ndarray, contact_dist_px: float) -> Clusters:
    """Group stomata whose centres are closer than ``contact_dist_px``.

    With ``contact_dist_px`` set near the width of one stomatal complex,
    groups of two or more are stomata in direct contact, i.e. violations of
    the one-cell spacing rule.
    """
    pts = np.asarray(pts, dtype=float)
    n = len(pts)
    if n == 0:
        return Clusters(0, float("nan"), 0, 0, [])
    pairs = cKDTree(pts).query_pairs(contact_dist_px, output_type="ndarray")
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in pairs:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    roots: dict[int, int] = {}
    for i in range(n):
        r = find(i)
        roots[r] = roots.get(r, 0) + 1
    sizes = sorted((s for s in roots.values() if s >= 2), reverse=True)
    in_cl = sum(sizes)
    return Clusters(in_cl, in_cl / n, len(sizes), max(sizes, default=1), sizes)


def axial_orientation(angles_deg: np.ndarray) -> tuple[float, float]:
    """Mean direction (0-180°) and alignment r (0 = random, 1 = parallel) for axial data."""
    a = np.radians(np.asarray(angles_deg, dtype=float))
    a = a[np.isfinite(a)]
    if len(a) == 0:
        return float("nan"), float("nan")
    c, s = np.cos(2 * a).mean(), np.sin(2 * a).mean()
    mean = (math.degrees(math.atan2(s, c)) / 2) % 180
    return mean, float(math.hypot(c, s))
