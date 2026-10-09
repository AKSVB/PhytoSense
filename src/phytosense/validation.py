"""Agreement between PhytoSense and reference measurements.

Two levels are covered:

* Object level: which predicted stomata match reference stomata on the same
  image (precision, recall, F1). Use this when the same field has been
  annotated by hand.
* Sample level: paired trait values per leaf or per image from the phone
  setup and from a reference microscope (bias, Bland-Altman limits of
  agreement, Lin's concordance correlation, regression).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist


@dataclass
class MatchResult:
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    mean_offset_px: float

    def to_dict(self) -> dict:
        return asdict(self)


def match_points(pred: np.ndarray, ref: np.ndarray, tol_px: float) -> MatchResult:
    """One-to-one matching of predicted to reference centres within ``tol_px``."""
    pred = np.asarray(pred, dtype=float).reshape(-1, 2)
    ref = np.asarray(ref, dtype=float).reshape(-1, 2)
    if len(pred) == 0 or len(ref) == 0:
        tp = 0
        offs = []
    else:
        d = cdist(pred, ref)
        cost = np.where(d <= tol_px, d, 1e9)
        r, c = linear_sum_assignment(cost)
        ok = d[r, c] <= tol_px
        tp = int(ok.sum())
        offs = d[r, c][ok]
    fp = len(pred) - tp
    fn = len(ref) - tp
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if tp else 0.0
    return MatchResult(tp, fp, fn, prec, rec, f1, float(np.mean(offs)) if len(offs) else float("nan"))


@dataclass
class Agreement:
    n: int
    mean_ref: float
    mean_test: float
    bias: float
    sd_diff: float
    loa_low: float
    loa_high: float
    mae: float
    mape_percent: float
    pearson_r: float
    ccc: float
    slope: float
    intercept: float

    def to_dict(self) -> dict:
        return asdict(self)


def agreement(test: np.ndarray, ref: np.ndarray) -> Agreement:
    """Compare paired measurements (e.g. phone density vs. light-microscope density)."""
    t = np.asarray(test, dtype=float)
    r = np.asarray(ref, dtype=float)
    ok = np.isfinite(t) & np.isfinite(r)
    t, r = t[ok], r[ok]
    n = len(t)
    if n < 3:
        raise ValueError("Need at least 3 paired values")
    diff = t - r
    bias = float(diff.mean())
    sd = float(diff.std(ddof=1))
    pr = float(np.corrcoef(t, r)[0, 1])
    # Lin's concordance correlation coefficient
    st2, sr2 = t.var(), r.var()
    cov = ((t - t.mean()) * (r - r.mean())).mean()
    ccc = float(2 * cov / (st2 + sr2 + (t.mean() - r.mean()) ** 2))
    slope, intercept = np.polyfit(r, t, 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        ape = np.abs(diff) / np.abs(r)
    mape = float(np.nanmean(np.where(np.isfinite(ape), ape, np.nan)) * 100)
    return Agreement(
        n=n,
        mean_ref=float(r.mean()),
        mean_test=float(t.mean()),
        bias=bias,
        sd_diff=sd,
        loa_low=bias - 1.96 * sd,
        loa_high=bias + 1.96 * sd,
        mae=float(np.abs(diff).mean()),
        mape_percent=mape if math.isfinite(mape) else float("nan"),
        pearson_r=pr,
        ccc=ccc,
        slope=float(slope),
        intercept=float(intercept),
    )
