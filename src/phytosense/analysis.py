"""Per-image trait extraction."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .calibration import Calibration
from .detect import Detection, filter_by_mask
from .quality import QualityReport, assess, field_mask, mask_perimeter_px
from .spatial import axial_orientation, clark_evans, contact_clusters, nearest_neighbour_distances


def _summary(vals: list[float]) -> dict:
    v = np.asarray([x for x in vals if x is not None and math.isfinite(x)], dtype=float)
    if len(v) == 0:
        return {"n": 0, "mean": None, "sd": None, "median": None}
    return {
        "n": int(len(v)),
        "mean": float(v.mean()),
        "sd": float(v.std(ddof=1)) if len(v) > 1 else None,
        "median": float(np.median(v)),
    }


def _finite_median(vals: list[float]) -> float:
    v = [x for x in vals if math.isfinite(x)]
    return float(np.median(v)) if v else float("nan")


@dataclass
class ImageResult:
    image: str
    calibration: str
    um_per_px: float
    n_stomata: int
    field_area_mm2: float
    density_per_mm2: float
    stomatal_index: float | None
    length_um: dict
    width_um: dict
    nnd_um: dict
    clark_evans: dict
    clusters: dict
    orientation_mean_deg: float | None
    orientation_r: float | None
    open_fraction: float | None
    quality: dict
    detections: list[Detection] = field(repr=False, default_factory=list)

    def to_dict(self, with_detections: bool = False) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "detections"}
        if with_detections:
            d["detections"] = [x.to_dict() for x in self.detections]
        return d

    def flat_row(self) -> dict:
        """One CSV row with the main traits."""
        return {
            "image": self.image,
            "calibration": self.calibration,
            "um_per_px": self.um_per_px,
            "n_stomata": self.n_stomata,
            "field_area_mm2": self.field_area_mm2,
            "density_per_mm2": self.density_per_mm2,
            "stomatal_index": self.stomatal_index,
            "length_um_mean": self.length_um["mean"],
            "width_um_mean": self.width_um["mean"],
            "nnd_um_mean": self.nnd_um["mean"],
            "clark_evans_R": self.clark_evans["R"],
            "clark_evans_p": self.clark_evans["p_two_sided"],
            "pattern": self.clark_evans["pattern"],
            "frac_in_clusters": self.clusters["frac_in_clusters"],
            "orientation_r": self.orientation_r,
            "open_fraction": self.open_fraction,
            "quality_flags": ";".join(self.quality.get("flags", [])),
        }


def analyze(
    img: np.ndarray,
    cal: Calibration,
    detections: list[Detection] | None = None,
    detector=None,
    mask: np.ndarray | None = None,
    pavement_cells: int | None = None,
    contact_factor: float = 1.0,
    contact_dist_um: float | None = None,
    image_name: str = "",
) -> ImageResult:
    """Detect (or accept) stomata and compute traits for one image.

    Either ``detections`` (e.g. manual points) or a ``detector`` must be given.
    ``contact_factor`` sets the contact distance for cluster detection as a
    multiple of the median stoma width (or 0.6 x length when width is unknown).
    ``contact_dist_um`` overrides it; it is needed for manual point
    annotations, which carry no size.
    """
    if mask is None:
        mask = field_mask(img)
    q: QualityReport = assess(img, mask)
    if detections is None:
        if detector is None:
            raise ValueError("Provide detections or a detector")
        detections = detector.detect(img, mask)
    else:
        detections = filter_by_mask(detections, mask)

    n = len(detections)
    area_px = float(mask.sum())
    area_mm2 = cal.px_area_to_mm2(area_px)
    pts = np.array([[d.x, d.y] for d in detections], dtype=float).reshape(-1, 2)

    lengths = [cal.px_to_um(d.length_px) for d in detections]
    widths = [cal.px_to_um(d.width_px) for d in detections]
    nnd = nearest_neighbour_distances(pts) * cal.um_per_px

    ce = clark_evans(pts, area_px, mask_perimeter_px(mask))

    if contact_dist_um is not None:
        contact_px = cal.um_to_px(contact_dist_um)
    else:
        w_med = _finite_median([d.width_px for d in detections])
        if not math.isfinite(w_med):
            w_med = 0.6 * _finite_median([d.length_px for d in detections])
        contact_px = contact_factor * w_med
    clusters = contact_clusters(pts, contact_px) if math.isfinite(contact_px) else None

    om, orr = axial_orientation([d.angle_deg for d in detections])
    opens = [d.is_open for d in detections if d.is_open is not None]

    si = None
    if pavement_cells is not None and (n + pavement_cells) > 0:
        si = n / (n + pavement_cells)

    return ImageResult(
        image=image_name,
        calibration=cal.name,
        um_per_px=cal.um_per_px,
        n_stomata=n,
        field_area_mm2=area_mm2,
        density_per_mm2=n / area_mm2 if area_mm2 > 0 else float("nan"),
        stomatal_index=si,
        length_um=_summary(lengths),
        width_um=_summary(widths),
        nnd_um=_summary(list(nnd)),
        clark_evans=ce.to_dict(),
        clusters=clusters.to_dict() if clusters else {"frac_in_clusters": None},
        orientation_mean_deg=None if not math.isfinite(om) else om,
        orientation_r=None if not math.isfinite(orr) else orr,
        open_fraction=(sum(opens) / len(opens)) if opens else None,
        quality=q.to_dict(),
        detections=detections,
    )
