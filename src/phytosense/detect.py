"""Stoma detection.

Two detectors share one output format:

``BlobDetector``
    A classical baseline that needs no training data. It finds blobs of the
    expected stoma size with a Laplacian-of-Gaussian filter and estimates
    each one's orientation and axis lengths from local image moments. It is
    useful for first tests, for well-contrasted epidermal impressions, and as
    a pre-annotation tool. Its size estimates are approximate.

``YoloDetector``
    Wraps a YOLO model (Ultralytics) trained on annotated images. This is the
    intended production detector once enough images from the clip-on setup
    have been annotated and checked against lab microscopes.

Manual counts made in ImageJ/Fiji (multi-point tool, Analyze > Measure,
saved as CSV) can be loaded with :func:`read_points_csv` and go through the
same density and pattern statistics.
"""

from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from skimage.feature import blob_log

from .imageio import to_gray


@dataclass
class Detection:
    x: float  # column, pixels
    y: float  # row, pixels
    length_px: float = float("nan")  # long axis of the stomatal complex
    width_px: float = float("nan")
    angle_deg: float = float("nan")  # long-axis orientation, 0-180, counter-clockwise from +x
    score: float = 1.0
    source: str = ""
    is_open: bool | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def filter_by_mask(dets: list[Detection], mask: np.ndarray | None) -> list[Detection]:
    if mask is None:
        return dets
    h, w = mask.shape
    out = []
    for d in dets:
        r, c = int(round(d.y)), int(round(d.x))
        if 0 <= r < h and 0 <= c < w and mask[r, c]:
            out.append(d)
    return out


def _moments_shape(patch: np.ndarray) -> tuple[float, float, float]:
    """Return (length, width, angle_deg) of the intensity distribution in a patch."""
    wgt = np.clip(patch - np.median(patch), 0, None)
    s = wgt.sum()
    if s <= 0:
        return float("nan"), float("nan"), float("nan")
    h, w = patch.shape
    yy, xx = np.mgrid[0:h, 0:w]
    my, mx = (wgt * yy).sum() / s, (wgt * xx).sum() / s
    cyy = (wgt * (yy - my) ** 2).sum() / s
    cxx = (wgt * (xx - mx) ** 2).sum() / s
    cxy = (wgt * (xx - mx) * (yy - my)).sum() / s
    evals, evecs = np.linalg.eigh(np.array([[cxx, cxy], [cxy, cyy]]))
    l2, l1 = evals  # ascending
    vx, vy = evecs[:, 1]
    # Image rows grow downwards; flip y so the angle is counter-clockwise.
    angle = math.degrees(math.atan2(-vy, vx)) % 180.0
    # For a uniform ellipse the semi-axis equals 2*sqrt(eigenvalue).
    return 4 * math.sqrt(max(l1, 0)), 4 * math.sqrt(max(l2, 0)), angle


class BlobDetector:
    def __init__(
        self,
        stoma_length_px: float,
        polarity: str = "dark",
        threshold_rel: float = 0.2,
        min_sep_frac: float = 0.6,
    ) -> None:
        """
        stoma_length_px: expected long-axis length of a stomatal complex in pixels
            (species length in µm divided by the calibration's µm/px).
        polarity: "dark" if stomata are darker than the surrounding epidermis,
            "bright" if lighter, "auto" to pick the stronger response.
        threshold_rel: LoG response threshold relative to the strongest blob.
        min_sep_frac: minimum centre distance between detections, as a fraction
            of the stoma length.
        """
        if stoma_length_px < 3:
            raise ValueError("Stomata smaller than ~3 px cannot be resolved; increase magnification")
        self.L = float(stoma_length_px)
        self.polarity = polarity
        self.threshold_rel = threshold_rel
        self.min_sep = min_sep_frac * self.L

    def _run(self, g: np.ndarray) -> np.ndarray:
        # A blob of radius r responds most strongly at sigma = r / sqrt(2).
        r = 0.4 * self.L
        s0 = r / math.sqrt(2)
        return blob_log(
            g,
            min_sigma=0.6 * s0,
            max_sigma=1.6 * s0,
            num_sigma=8,
            threshold=None,
            threshold_rel=self.threshold_rel,
            overlap=0.3,
            exclude_border=False,
        )

    def detect(self, img: np.ndarray, mask: np.ndarray | None = None) -> list[Detection]:
        g = to_gray(img)
        if mask is not None:
            fill = np.median(g[mask])
            g = np.where(mask, g, fill)

        candidates = {"dark": 1.0 - g, "bright": g}
        if self.polarity == "auto":
            best, best_score = None, -1.0
            for name, im in candidates.items():
                b = self._run(im)
                score = float(np.median([im[int(y), int(x)] for y, x, _ in b])) if len(b) else 0.0
                score *= len(b) > 0
                if score > best_score:
                    best, best_score, pol = b, score, name
            blobs, work = best, candidates[pol]
        else:
            work = candidates[self.polarity]
            blobs = self._run(work)

        # Greedy non-maximum suppression on centre distance, strongest first.
        strengths = [work[int(y), int(x)] for y, x, _ in blobs]
        order = np.argsort(strengths)[::-1]
        kept: list[tuple[float, float, float]] = []
        for i in order:
            y, x, s = blobs[i]
            if all(math.hypot(y - ky, x - kx) >= self.min_sep for ky, kx, _ in kept):
                kept.append((y, x, strengths[i]))

        half = int(math.ceil(0.75 * self.L))
        h, w = g.shape
        dets = []
        for y, x, s in kept:
            r0, r1 = max(0, int(y) - half), min(h, int(y) + half + 1)
            c0, c1 = max(0, int(x) - half), min(w, int(x) + half + 1)
            length, width, angle = _moments_shape(work[r0:r1, c0:c1])
            dets.append(
                Detection(
                    x=float(x), y=float(y), length_px=length, width_px=width,
                    angle_deg=angle, score=float(s), source="blob",
                )
            )
        return filter_by_mask(dets, mask)


def paleness(img: np.ndarray) -> np.ndarray:
    """Map an RGB image to [0, 1], high where pixels are pale (bright and unsaturated).

    On clip-on phone images of green leaves, stomata appear as whitish rings on
    a green background, so paleness separates them from pavement cells better
    than brightness does. Gray input is returned as gray.
    """
    a = np.asarray(img)
    if a.ndim == 2:
        return to_gray(a)
    a = a[..., :3].astype(np.float64)
    if a.max() > 1.0:
        a = a / 255.0
    mx, mn = a.max(-1), a.min(-1)
    sat = (mx - mn) / (mx + 1e-6)
    return 0.5 * (1.0 - sat) + 0.5 * mn


class PaleSpotDetector:
    """Detects stomata as pale spots of the expected size, for colour phone images.

    Band-pass filters the paleness map at the stoma scale, normalises contrast
    locally (so dark oil glands or uneven lighting do not shift the threshold),
    and keeps local maxima above ``threshold`` local standard deviations.
    Needs no training data; intended as a baseline and pre-annotation tool.
    """

    def __init__(self, stoma_length_px: float, threshold: float = 1.0, min_sep_frac: float = 0.65) -> None:
        if stoma_length_px < 6:
            raise ValueError("Stomata smaller than ~6 px cannot be resolved; increase magnification")
        self.L = float(stoma_length_px)
        self.threshold = threshold
        self.min_sep = max(2, int(min_sep_frac * self.L))

    def detect(self, img: np.ndarray, mask: np.ndarray | None = None) -> list[Detection]:
        from scipy import ndimage as ndi
        from skimage.feature import peak_local_max

        p = paleness(img)
        if mask is not None:
            p = np.where(mask, p, np.median(p[mask]))
        sig = self.L / 4.0
        band = ndi.gaussian_filter(p, sig) - ndi.gaussian_filter(p, 4 * sig)
        win = 8 * sig
        m = ndi.gaussian_filter(band, win)
        sd = np.sqrt(np.maximum(ndi.gaussian_filter(band * band, win) - m * m, 1e-12))
        z = (band - m) / sd
        peaks = peak_local_max(z, min_distance=self.min_sep, threshold_abs=self.threshold,
                               exclude_border=self.min_sep)
        # Drop peaks inside large dark regions such as oil glands, where local
        # normalisation amplifies noise.
        coarse = ndi.gaussian_filter(p, self.L)
        med = np.median(coarse)
        mad = 1.4826 * np.median(np.abs(coarse - med)) + 1e-9
        peaks = [(y, x) for y, x in peaks if coarse[y, x] > med - 2.5 * mad]
        half = int(math.ceil(0.75 * self.L))
        h, w = p.shape
        dets = []
        for y, x in peaks:
            r0, r1 = max(0, y - half), min(h, y + half + 1)
            c0, c1 = max(0, x - half), min(w, x + half + 1)
            length, width, angle = _moments_shape(np.clip(band[r0:r1, c0:c1], 0, None))
            dets.append(Detection(x=float(x), y=float(y), length_px=length, width_px=width,
                                  angle_deg=angle, score=float(z[y, x]), source="pale"))
        return filter_by_mask(dets, mask)


class YoloDetector:
    """Detector backed by an Ultralytics YOLO model (axis-aligned or oriented boxes).

    Class names containing "open" or "closed" set ``Detection.is_open``.
    """

    def __init__(self, weights: str | Path, conf: float = 0.25, imgsz: int = 1280) -> None:
        try:
            from ultralytics import YOLO
        except ImportError as e:  # pragma: no cover - optional dependency
            raise ImportError("Install the optional dependency: pip install 'phytosense[yolo]'") from e
        self.model = YOLO(str(weights))
        self.conf = conf
        self.imgsz = imgsz

    def detect(self, img: np.ndarray, mask: np.ndarray | None = None) -> list[Detection]:  # pragma: no cover
        a = np.asarray(img)
        if a.ndim == 2:
            a = np.stack([a] * 3, axis=-1)
        if a.dtype != np.uint8:
            a = (np.clip(a, 0, 1) * 255).astype(np.uint8)
        res = self.model.predict(a, conf=self.conf, imgsz=self.imgsz, verbose=False)[0]
        names = res.names
        dets: list[Detection] = []
        if getattr(res, "obb", None) is not None and len(res.obb):
            for (cx, cy, bw, bh, rot), conf, cls in zip(
                res.obb.xywhr.tolist(), res.obb.conf.tolist(), res.obb.cls.tolist()
            ):
                length, width = max(bw, bh), min(bw, bh)
                ang = math.degrees(-rot) + (0 if bw >= bh else 90)
                dets.append(Detection(cx, cy, length, width, ang % 180, conf, "yolo-obb", _open(names[int(cls)])))
        elif res.boxes is not None:
            for (cx, cy, bw, bh), conf, cls in zip(
                res.boxes.xywh.tolist(), res.boxes.conf.tolist(), res.boxes.cls.tolist()
            ):
                ang = 0.0 if bw >= bh else 90.0
                dets.append(Detection(cx, cy, max(bw, bh), min(bw, bh), ang, conf, "yolo", _open(names[int(cls)])))
        return filter_by_mask(dets, mask)


def _open(name: str) -> bool | None:
    n = name.lower()
    if "closed" in n:
        return False
    if "open" in n:
        return True
    return None


def read_points_csv(path: str | Path, scale: float = 1.0) -> list[Detection]:
    """Read point annotations from CSV.

    Accepts ImageJ/Fiji Results tables (columns ``X`` and ``Y``) or any CSV
    with ``x``/``y`` columns. If ImageJ measured in calibrated units, pass
    ``scale`` = pixels per unit to convert back to pixels.
    """
    dets = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        cols = {c.lower(): c for c in (reader.fieldnames or [])}
        if "x" not in cols or "y" not in cols:
            raise ValueError(f"{path}: expected X and Y columns, found {reader.fieldnames}")
        for row in reader:
            dets.append(
                Detection(
                    x=float(row[cols["x"]]) * scale,
                    y=float(row[cols["y"]]) * scale,
                    source="manual",
                )
            )
    return dets


def write_detections_csv(dets: list[Detection], path: str | Path) -> None:
    fields = list(Detection.__dataclass_fields__)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for d in dets:
            w.writerow(d.to_dict())
