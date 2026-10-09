"""Command-line interface: ``phytosense <command> ...``."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

from . import calibration as calib
from .analysis import analyze
from .detect import BlobDetector, read_points_csv, write_detections_csv
from .imageio import load_gray, save_gray
from .quality import field_mask
from .report import overlay, write_results
from .validation import agreement, match_points


def _xy(s: str) -> tuple[float, float]:
    x, y = s.split(",")
    return float(x), float(y)


def _crop(img: np.ndarray, box: str | None) -> np.ndarray:
    if not box:
        return img
    x0, y0, x1, y1 = (int(v) for v in box.split(","))
    return img[y0:y1, x0:x1]


def _meta(a) -> dict:
    return {"name": a.name, "phone": a.phone, "lens": a.lens, "zoom": a.zoom, "notes": a.notes}


def cmd_cal_micrometer(a) -> int:
    img = _crop(load_gray(a.image), a.crop)
    cal = calib.from_micrometer_image(img, a.spacing_um, **_meta(a))
    calib.add_profile(cal, a.profiles)
    print(f"{cal.name}: {cal.um_per_px:.4f} µm/px  ({1 / cal.um_per_px:.3f} px/µm) -> {a.profiles}")
    return 0


def cal_points(a) -> int:
    cal = calib.from_two_points(_xy(a.p1), _xy(a.p2), a.distance_um, **_meta(a))
    calib.add_profile(cal, a.profiles)
    print(f"{cal.name}: {cal.um_per_px:.4f} µm/px -> {a.profiles}")
    return 0


def _get_cal(a) -> calib.Calibration:
    if a.um_per_px:
        return calib.Calibration(um_per_px=a.um_per_px, name="manual", method="manual")
    profiles = calib.load_profiles(a.profiles)
    if a.profile not in profiles:
        sys.exit(f"Calibration profile '{a.profile}' not found in {a.profiles}. "
                 f"Available: {', '.join(profiles) or 'none'}")
    return profiles[a.profile]


def cmd_analyze(a) -> int:
    cal = _get_cal(a)
    detector = None
    if a.yolo:
        from .detect import YoloDetector

        detector = YoloDetector(a.yolo, conf=a.conf)
    elif not a.points_dir:
        detector = BlobDetector(
            cal.um_to_px(a.stoma_length_um), polarity=a.polarity, threshold_rel=a.threshold
        )

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for path in a.images:
        p = Path(path)
        img = load_gray(p)
        mask = np.ones_like(img, dtype=bool) if a.no_mask else field_mask(img)
        dets = None
        if a.points_dir:
            csv_path = Path(a.points_dir) / f"{p.stem}.csv"
            if not csv_path.exists():
                print(f"skip {p.name}: no {csv_path}", file=sys.stderr)
                continue
            dets = read_points_csv(csv_path, scale=a.points_scale)
        res = analyze(img, cal, detections=dets, detector=detector, mask=mask,
                      contact_factor=a.contact_factor, contact_dist_um=a.contact_dist_um,
                      image_name=p.name)
        results.append(res)
        overlay(img, res, mask).save(out / f"{p.stem}_overlay.png")
        write_detections_csv(res.detections, out / f"{p.stem}_stomata.csv")
        flags = ",".join(res.quality["flags"]) or "ok"
        print(f"{p.name}: n={res.n_stomata}  density={res.density_per_mm2:.1f}/mm²  "
              f"R={res.clark_evans['R']:.2f} ({res.clark_evans['pattern']})  quality={flags}")
    write_results(results, out)
    print(f"Results written to {out}/summary.csv and {out}/results.json")
    return 0


def cmd_match(a) -> int:
    pred = read_points_csv(a.pred)
    ref = read_points_csv(a.ref)
    m = match_points([[d.x, d.y] for d in pred], [[d.x, d.y] for d in ref], a.tol_px)
    print(json.dumps(m.to_dict(), indent=2))
    return 0


def cmd_agree(a) -> int:
    with open(a.table, newline="") as f:
        rows = list(csv.DictReader(f))

    def num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return float("nan")

    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r.get(a.group_col, "all") if a.group_col else "all", []).append(r)
    out = {}
    for g, rs in groups.items():
        t = [num(r[a.test_col]) for r in rs]
        ref = [num(r[a.ref_col]) for r in rs]
        try:
            out[g] = agreement(np.array(t), np.array(ref)).to_dict()
        except ValueError as e:
            out[g] = {"error": str(e)}
    print(json.dumps(out, indent=2))
    return 0


def cmd_demo(a) -> int:
    from .synthetic import epidermis

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    img, pts, _ = epidermis(seed=a.seed)
    save_gray(img, out / "synthetic.png")
    cal = calib.Calibration(um_per_px=1.0, name="synthetic")
    res = analyze(img, cal, detector=BlobDetector(24), image_name="synthetic.png")
    overlay(img, res, field_mask(img)).save(out / "synthetic_overlay.png")
    m = match_points([[d.x, d.y] for d in res.detections], pts, tol_px=8)
    print(f"true stomata: {len(pts)}  detected: {res.n_stomata}  "
          f"precision={m.precision:.3f} recall={m.recall:.3f}")
    print(f"Clark-Evans R={res.clark_evans['R']:.2f} ({res.clark_evans['pattern']})")
    print(f"Images written to {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="phytosense", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_meta(sp):
        sp.add_argument("--name", required=True, help="profile name, e.g. pixel7-apexel200-1x")
        sp.add_argument("--phone", default="")
        sp.add_argument("--lens", default="")
        sp.add_argument("--zoom", default="")
        sp.add_argument("--notes", default="")
        sp.add_argument("--profiles", default="calibrations.json")

    sp = sub.add_parser("calibrate-micrometer", help="calibrate from a stage micrometer photo")
    sp.add_argument("image")
    sp.add_argument("--spacing-um", type=float, default=10.0, help="distance between fine divisions")
    sp.add_argument("--crop", help="x0,y0,x1,y1 region containing only ruled lines")
    add_meta(sp)
    sp.set_defaults(func=cmd_cal_micrometer)

    sp = sub.add_parser("calibrate-points", help="calibrate from two points a known distance apart")
    sp.add_argument("--p1", required=True, help="x,y in pixels")
    sp.add_argument("--p2", required=True, help="x,y in pixels")
    sp.add_argument("--distance-um", type=float, required=True)
    add_meta(sp)
    sp.set_defaults(func=cal_points)

    sp = sub.add_parser("analyze", help="detect stomata and compute traits")
    sp.add_argument("images", nargs="+")
    sp.add_argument("--profiles", default="calibrations.json")
    sp.add_argument("--profile", default="default")
    sp.add_argument("--um-per-px", type=float, help="use this scale instead of a saved profile")
    sp.add_argument("--stoma-length-um", type=float, default=25.0,
                    help="expected stomatal complex length for the blob detector")
    sp.add_argument("--polarity", choices=["dark", "bright", "auto"], default="dark")
    sp.add_argument("--threshold", type=float, default=0.2)
    sp.add_argument("--yolo", help="path to trained YOLO weights")
    sp.add_argument("--conf", type=float, default=0.25)
    sp.add_argument("--points-dir", help="folder of manual point CSVs named <image-stem>.csv")
    sp.add_argument("--points-scale", type=float, default=1.0)
    sp.add_argument("--contact-factor", type=float, default=1.0,
                    help="contact distance for clusters, as a multiple of median stoma width")
    sp.add_argument("--contact-dist-um", type=float,
                    help="fixed contact distance in µm (needed for manual points)")
    sp.add_argument("--no-mask", action="store_true", help="analyse the full frame")
    sp.add_argument("--out", default="phytosense_out")
    sp.set_defaults(func=cmd_analyze)

    sp = sub.add_parser("match", help="object-level agreement between two point CSVs")
    sp.add_argument("pred")
    sp.add_argument("ref")
    sp.add_argument("--tol-px", type=float, required=True)
    sp.set_defaults(func=cmd_match)

    sp = sub.add_parser("agree", help="sample-level agreement (Bland-Altman, CCC) from a CSV")
    sp.add_argument("table")
    sp.add_argument("--test-col", required=True)
    sp.add_argument("--ref-col", required=True)
    sp.add_argument("--group-col", help="e.g. species or microscope")
    sp.set_defaults(func=cmd_agree)

    sp = sub.add_parser("demo", help="run the pipeline on a synthetic image")
    sp.add_argument("--out", default="phytosense_demo")
    sp.add_argument("--seed", type=int, default=0)
    sp.set_defaults(func=cmd_demo)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
