"""Unit tests for Lane H84-CSAT physical, structural-transfer, and allocation primitives."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]

from gems57.holdout import quadrant_ids  # noqa: E402
from gems84 import csat  # noqa: E402


def test_robust_z_ignores_outside_and_nans():
    v = np.array([1.0, 2.0, 3.0, 4.0, 5.0, np.nan, 1e9], dtype=np.float32)
    sub = np.array([True, True, True, True, True, True, False])
    z = csat.robust_z_1d(v, valid_sub=sub)
    assert np.isfinite(z).all()
    assert z[-1] == 0.0
    assert z[-2] == 0.0
    assert abs(float(z[2])) < 1e-6


def test_gdr_rasterizer_ignores_dist_known_fault_px(tmp_path):
    fp = np.ones((40, 40), dtype=bool)
    well_csv = tmp_path / "wells.csv"
    vent_csv = tmp_path / "vents.csv"
    with open(well_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["row", "col", "dist_known_fault_px", "temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c"])
        w.writerow([20, 20, "0.0", "85.0", "190.0", "170.0", "200.0"])
    with open(vent_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["row", "col", "dist_known_fault_px"])
        w.writerow([10, 10, "0.0"])

    g1 = csat.rasterize_gdr_geothermal((40, 40), fp, well_csv, vent_csv)
    # Perturb dist_known_fault_px wildly and verify identical output (column is never read)
    with open(well_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["row", "col", "dist_known_fault_px", "temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c"])
        w.writerow([20, 20, "999999.0", "85.0", "190.0", "170.0", "200.0"])
    g2 = csat.rasterize_gdr_geothermal((40, 40), fp, well_csv, vent_csv)
    np.testing.assert_array_equal(g1, g2)
    assert g1[20, 20] > g1[0, 0]


def test_transfer_features_detect_relay_and_tip_cones():
    fp = np.ones((60, 60), dtype=bool)
    vis = np.zeros((60, 60), dtype=bool)
    # Two colinear East-West fault segments separated by an unmapped gap (cols 22..37)
    vis[30, 8:22] = True
    vis[30, 38:52] = True

    phys_names = list(csat.OFFICIAL_BAND_NAMES) + [
        "p20_analytic_mag", "p21_analytic_grav", "p22_phase_vz_mag", "p23_phase_vz_grav",
        "p24_salem_tilt_wavenumber", "p25_basement_grad", "p26_basement_crest",
        "p27_mag_shallow_resid", "p28_det_crest_s1p5", "p29_det_crest_s4",
        "p30_topo10m_breakline", "p31_topo10m_lineament", "p32_topo10m_relief",
        "p33_lidar_norm_step", "p34_lidar_facing_asym", "p35_rad_k_th_resid",
        "p36_rad_u_th_resid", "p37_geotherm_enthalpy_plume", "p38_claycap_transtension",
    ]
    X_phys = np.ones((fp.sum(), len(phys_names)), dtype=np.float16)
    Xs, names, d1 = csat.build_transfer_features(vis, fp, X_phys, phys_names)
    assert Xs.shape == (3600, 20)
    assert np.isfinite(Xs).all()

    idx_map = {n: i for i, n in enumerate(names)}
    # Midpoint inside the step-over bridge (30, 30) vs far corner (5, 5)
    mid = 30 * 60 + 30
    far = 5 * 60 + 5
    assert float(Xs[mid, idx_map["s07_relay_facing"]]) > 0.95
    assert float(Xs[mid, idx_map["s09_relay_bridge_s12"]]) > float(Xs[far, idx_map["s09_relay_bridge_s12"]])
    # Ahead of tip (30, 26) vs perpendicular flank (24, 15)
    ahead = 30 * 60 + 26
    perp = 24 * 60 + 15
    assert float(Xs[ahead, idx_map["s14_tip_cone_s8"]]) > float(Xs[perp, idx_map["s14_tip_cone_s8"]])


def test_bayes_quadrant_calibration_and_collar_allocation():
    fp = np.ones((80, 80), dtype=bool)
    vis = np.zeros((80, 80), dtype=bool)
    vis[40, 10:30] = True
    quad = quadrant_ids(fp)
    rng = np.random.default_rng(42)
    surf = rng.uniform(0.01, 0.5, size=(80, 80)).astype(np.float32)
    surf[40, 35:70] = 0.95
    from scipy import ndimage as ndi
    d1 = ndi.distance_transform_edt(~vis).astype(np.float32)
    allowed = fp & (~vis) & (d1 > 2.5)
    cal = csat.bayes_quadrant_calibrate(surf, allowed, quad, pi0=0.01)
    for q in range(4):
        m = allowed & (quad == q)
        assert abs(float(cal[m].mean()) - 0.01) < 5e-4
    dots, info = csat.allocate_submodular_dots(surf, fp, vis, d1, quad, collar_px=2.5, pi0=0.01)
    assert info["n_dots"] > 0
    assert not (dots[vis] > 0).any()
    assert not (dots[d1 <= 2.5] > 0).any()


def test_h84_csat_artifact_and_run_cards_synchronized():
    import hashlib
    import json
    import zipfile
    from gems57 import grid as ggrid, validate as gvalidate
    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_submission as indep_validator

    c1 = (ROOT / "evidence/run-card.json").read_text(encoding="utf-8")
    c2 = (ROOT / "evidence/run_card.json").read_text(encoding="utf-8")
    c3 = (ROOT / "docs/data/run-card.json").read_text(encoding="utf-8")
    c4 = (ROOT / "docs/run-card.json").read_text(encoding="utf-8")
    assert c1 == c2 == c3 == c4

    cs1 = (ROOT / "evidence/run_card_csat.json").read_text(encoding="utf-8")
    cs2 = (ROOT / "registry/run_card_csat.json").read_text(encoding="utf-8")
    cs3 = (ROOT / "docs/evidence/run_card_csat.json").read_text(encoding="utf-8")
    assert cs1 == cs2 == cs3

    card = json.loads(cs1)
    assert len(card["note"]) <= 140
    assert card["submission_slots_used"] == 0
    tif_path = ROOT / card["submission_file"]
    zip_path = ROOT / card["submission_zip"]
    assert tif_path.is_file() and zip_path.is_file()
    assert hashlib.sha256(tif_path.read_bytes()).hexdigest() == card["raster_sha256"]

    g = ggrid.load_grid()
    rec_g = gvalidate.validate(tif_path, g.footprint, g.catalogue)
    gvalidate.assert_submittable(rec_g)
    rec_i = indep_validator.audit(tif_path, ROOT / "data/bridge/sample_submission.tif")
    assert rec_i["status"] == "PASS" and rec_i["format_valid"]

    with zipfile.ZipFile(zip_path) as zf:
        assert zf.namelist() == [tif_path.name]
        assert zf.read(tif_path.name) == tif_path.read_bytes()

