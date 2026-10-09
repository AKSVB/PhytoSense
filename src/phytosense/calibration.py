"""Spatial calibration (micrometres per pixel).

Clip-on lenses have no fixed magnification: it changes with the phone, the
camera module, the digital zoom level, and how far the lens sits from the
camera window. Each combination therefore needs its own calibration, stored
as a named profile and checked again whenever the clip is re-mounted.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import numpy as np

from .imageio import to_gray


@dataclass
class Calibration:
    um_per_px: float
    name: str = "default"
    phone: str = ""
    lens: str = ""
    zoom: str = ""
    method: str = ""
    created: str = field(default_factory=lambda: date.today().isoformat())
    notes: str = ""

    def __post_init__(self) -> None:
        if not (self.um_per_px > 0 and math.isfinite(self.um_per_px)):
            raise ValueError(f"um_per_px must be a positive number, got {self.um_per_px}")

    def px_to_um(self, px: float) -> float:
        return px * self.um_per_px

    def um_to_px(self, um: float) -> float:
        return um / self.um_per_px

    def px_area_to_mm2(self, area_px: float) -> float:
        return area_px * (self.um_per_px**2) / 1e6


def from_two_points(
    p1: tuple[float, float], p2: tuple[float, float], distance_um: float, **meta
) -> Calibration:
    """Calibrate from two points a known distance apart (e.g. two micrometer marks)."""
    d_px = math.dist(p1, p2)
    if d_px <= 0:
        raise ValueError("The two points must differ")
    return Calibration(um_per_px=distance_um / d_px, method="two-point", **meta)


def grating_period_px(img: np.ndarray, min_period_px: float = 4.0) -> float:
    """Estimate the period (in pixels) of a periodic line pattern.

    Works on an image of a stage micrometer or any ruled grating at any
    orientation. The dominant peak of the windowed 2-D power spectrum gives
    the fundamental spatial frequency; a parabolic fit on the neighbouring
    bins refines it to sub-bin precision.
    """
    g = to_gray(img)
    g = g - g.mean()
    h, w = g.shape
    win = np.outer(np.hanning(h), np.hanning(w))
    spec = np.abs(np.fft.fftshift(np.fft.fft2(g * win))) ** 2

    cy, cx = h // 2, w // 2
    yy, xx = np.mgrid[0:h, 0:w]
    fy = (yy - cy) / h
    fx = (xx - cx) / w
    fr = np.hypot(fy, fx)
    # Exclude DC and frequencies above the resolvable limit.
    valid = (fr > 1.0 / max(h, w) * 3) & (fr < 1.0 / min_period_px)
    spec_v = np.where(valid, spec, 0)
    iy, ix = np.unravel_index(np.argmax(spec_v), spec.shape)

    def refine(s_m, s_0, s_p):
        denom = s_m - 2 * s_0 + s_p
        return 0.0 if denom == 0 else 0.5 * (s_m - s_p) / denom

    dy = refine(spec[iy - 1, ix], spec[iy, ix], spec[iy + 1, ix]) if 0 < iy < h - 1 else 0.0
    dx = refine(spec[iy, ix - 1], spec[iy, ix], spec[iy, ix + 1]) if 0 < ix < w - 1 else 0.0
    f = math.hypot((iy + dy - cy) / h, (ix + dx - cx) / w)
    return 1.0 / f


def from_micrometer_image(img: np.ndarray, spacing_um: float, **meta) -> Calibration:
    """Calibrate from a photo of a stage micrometer.

    ``spacing_um`` is the distance between adjacent fine divisions
    (10 µm on the common 1 mm / 100 division slide). Crop the photo to the
    ruled region first if large text or the slide edge is in view.
    """
    period = grating_period_px(img)
    return Calibration(um_per_px=spacing_um / period, method="micrometer-fft", **meta)


def save_profiles(profiles: dict[str, Calibration], path: str | Path) -> None:
    data = {k: asdict(v) for k, v in profiles.items()}
    Path(path).write_text(json.dumps(data, indent=2) + "\n")


def load_profiles(path: str | Path) -> dict[str, Calibration]:
    p = Path(path)
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    return {k: Calibration(**v) for k, v in data.items()}


def add_profile(cal: Calibration, path: str | Path) -> None:
    profiles = load_profiles(path)
    profiles[cal.name] = cal
    save_profiles(profiles, path)
