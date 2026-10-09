import math

import numpy as np
import pytest

from phytosense import calibration as calib
from phytosense.analysis import analyze
from phytosense.cli import main
from phytosense.detect import BlobDetector, read_points_csv
from phytosense.imageio import save_gray
from phytosense.quality import assess, field_mask
from phytosense.spatial import axial_orientation, clark_evans, contact_clusters, ripley_l
from phytosense.synthetic import epidermis, grating
from phytosense.validation import agreement, match_points


@pytest.mark.parametrize("period,angle", [(17.3, 12.0), (9.6, 0.0), (25.0, 75.0)])
def test_micrometer_calibration_recovers_period(period, angle):
    img = grating(period_px=period, angle_deg=angle)
    cal = calib.from_micrometer_image(img, spacing_um=10.0, name="t")
    assert cal.um_per_px == pytest.approx(10.0 / period, rel=0.01)


def test_two_point_calibration_and_profiles(tmp_path):
    cal = calib.from_two_points((0, 0), (300, 400), 100.0, name="p")
    assert cal.um_per_px == pytest.approx(0.2)
    path = tmp_path / "cal.json"
    calib.add_profile(cal, path)
    loaded = calib.load_profiles(path)
    assert loaded["p"].um_per_px == pytest.approx(0.2)
    with pytest.raises(ValueError):
        calib.Calibration(um_per_px=0)


def test_field_mask_matches_vignetted_field():
    img, _, field = epidermis(seed=1)
    m = field_mask(img)
    # Mask must lie inside the true field and cover most of it.
    assert (m & ~field).sum() / m.sum() < 0.01
    assert m.sum() / field.sum() > 0.85


def test_field_mask_full_frame_without_vignette():
    img, _, _ = epidermis(vignette=False, seed=2)
    assert field_mask(img).mean() > 0.85


def test_blob_detector_on_synthetic():
    img, pts, _ = epidermis(seed=3)
    mask = field_mask(img)
    dets = BlobDetector(24).detect(img, mask)
    m = match_points([[d.x, d.y] for d in dets], pts, tol_px=8)
    # Stomata partly cut by the eroded field edge are legitimately excluded.
    assert m.precision > 0.95
    assert m.recall > 0.9


def test_density_from_true_points_is_exact():
    img, pts, field = epidermis(seed=4)
    from phytosense.detect import Detection

    cal = calib.Calibration(um_per_px=0.5)
    dets = [Detection(x, y) for x, y in pts]
    res = analyze(img, cal, detections=dets, mask=field, contact_dist_um=0.65 * 24 * 1.05 * 0.5)
    expected = len(pts) / (field.sum() * 0.25 / 1e6)
    assert res.density_per_mm2 == pytest.approx(expected)
    assert res.clark_evans["pattern"] == "regular"
    assert res.clusters["n_clusters"] == 0


def test_clark_evans_detects_random_and_clustered():
    rng = np.random.default_rng(0)
    mask = np.ones((500, 500), dtype=bool)
    area, perim = 500 * 500, 4 * 500
    rand = rng.uniform(0, 500, size=(300, 2))
    ce = clark_evans(rand, area, perim)
    assert 0.9 < ce.R < 1.1
    parents = rng.uniform(50, 450, size=(30, 2))
    clustered = np.vstack([p + rng.normal(0, 4, size=(10, 2)) for p in parents])
    assert clark_evans(clustered, area, perim).pattern == "clustered"
    # Ripley's L-r is clearly positive at short range for a clustered pattern.
    assert ripley_l(clustered, mask, np.array([8.0]))[0] > 3


def test_contact_clusters_counts_pairs():
    img, pts, _ = epidermis(seed=5, clusters=6)
    cl = contact_clusters(pts, contact_dist_px=0.65 * 24 * 1.05)
    assert cl.n_clusters == 6
    assert cl.n_in_clusters == 12


def test_axial_orientation():
    mean, r = axial_orientation([10, 12, 8, 190, 170])
    assert r > 0.95
    assert mean < 15 or mean > 175


def test_agreement_statistics():
    rng = np.random.default_rng(1)
    ref = rng.uniform(80, 250, 40)
    test = ref * 1.0 + 5 + rng.normal(0, 3, 40)
    a = agreement(test, ref)
    assert a.bias == pytest.approx(5, abs=1.5)
    assert a.ccc > 0.95
    assert a.loa_low < a.bias < a.loa_high


def test_match_points_counts():
    m = match_points([[0, 0], [10, 10], [50, 50]], [[1, 0], [10, 12], [100, 100]], tol_px=3)
    assert (m.tp, m.fp, m.fn) == (2, 1, 1)


def test_quality_flags_blur():
    img, _, _ = epidermis(seed=6, blur_sigma=8, noise=0.0)
    sharp, _, _ = epidermis(seed=6)
    assert assess(img).focus < assess(sharp).focus


def test_points_csv_and_cli(tmp_path):
    img, pts, _ = epidermis(seed=7)
    save_gray(img, tmp_path / "leaf1.png")
    pdir = tmp_path / "points"
    pdir.mkdir()
    with open(pdir / "leaf1.csv", "w") as f:
        f.write(" ,X,Y\n")
        for i, (x, y) in enumerate(pts, 1):
            f.write(f"{i},{x},{y}\n")
    assert len(read_points_csv(pdir / "leaf1.csv")) == len(pts)

    out = tmp_path / "out"
    rc = main(["analyze", str(tmp_path / "leaf1.png"), "--um-per-px", "0.5",
               "--points-dir", str(pdir), "--out", str(out)])
    assert rc == 0
    assert (out / "summary.csv").exists()
    assert (out / "leaf1_overlay.png").exists()

    rc = main(["analyze", str(tmp_path / "leaf1.png"), "--um-per-px", "0.5",
               "--stoma-length-um", "12", "--out", str(tmp_path / "out2")])
    assert rc == 0

    g = grating(period_px=20)
    save_gray(g, tmp_path / "micro.png")
    prof = tmp_path / "cal.json"
    rc = main(["calibrate-micrometer", str(tmp_path / "micro.png"), "--spacing-um", "10",
               "--name", "phoneA", "--profiles", str(prof)])
    assert rc == 0
    assert math.isclose(calib.load_profiles(prof)["phoneA"].um_per_px, 0.5, rel_tol=0.02)
