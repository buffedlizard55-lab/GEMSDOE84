"""Automated verification tests for GEMSDOE84 Lane H84-B (H84-TCDH) & site."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]

from gems57 import validate as vendor_validate  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems84 import tcdh  # noqa: E402
from gems84.paths import BRIDGE  # noqa: E402


def test_tcdh_geotiff_zip_and_300m_spacing():
    rc = json.loads((ROOT / "evidence" / "run_card.json").read_text())
    assert rc["verdict"] == "promote"
    assert rc["lane"] == "H84-B"
    assert rc["experiments_used"] <= 3
    assert rc["submission_slots_used"] == 0
    assert len(rc["note"]) <= 140

    tif_path = ROOT / rc["artifact"]
    zip_path = ROOT / rc["zip_artifact"]
    assert tif_path.is_file() and zip_path.is_file()

    tif_bytes = tif_path.read_bytes()
    assert hashlib.sha256(tif_bytes).hexdigest() == rc["raster_sha256"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == rc["zip_sha256"]

    with zipfile.ZipFile(zip_path) as zf:
        assert zf.namelist() == [tif_path.name]
        assert zf.read(tif_path.name) == tif_bytes

    grid = load_grid(BRIDGE)
    vrep = vendor_validate.validate(
        tif_path,
        grid.footprint,
        catalogue=grid.catalogue,
    )
    assert vrep["all_checks_passed"] is True
    assert vrep["n_nan"] == 0 and vrep["n_infinite"] == 0
    assert vrep["min"] == 0.0 and vrep["max"] == 1.0
    assert vrep["on_catalogue_positive_pixels"] == 0
    assert vrep["emitted_positive_pixels"] == 39_000

    # Verify strict >= 3.0 px (300 m) Euclidean inter-dot spacing across all 39,000 dots
    with rasterio.open(tif_path) as src:
        arr = src.read(1)
    ys, xs = np.nonzero(arr > 0)
    assert len(ys) == 39_000
    assert np.all(arr[ys, xs] == 1.0)
    pts = np.column_stack([ys.astype(np.float64), xs.astype(np.float64)])
    d2, _ = cKDTree(pts).query(pts, k=2)
    min_nn_dist = float(d2[:, 1].min())
    assert min_nn_dist >= 3.0 - 1e-9, f"Found dots closer than 3 px: {min_nn_dist}"


def test_tcdh_protocol_gates_and_evidence_labels():
    e1 = json.loads((ROOT / "evidence" / "exp84b1_ablation.json").read_text())
    e2 = json.loads((ROOT / "evidence" / "exp84b2_allocation.json").read_text())
    e3 = json.loads((ROOT / "evidence" / "exp84b3_uniqueness_and_packaging.json").read_text())
    e3_stop = json.loads((ROOT / "evidence" / "exp84b3_unstratified_gate3b_stop.json").read_text())

    # Leakage canary: all 52 features <= 0.90
    assert e1["canary_gate"]["passed"] is True
    assert e1["canary_gate"]["n_features_checked"] == 52
    assert e1["canary_gate"]["max_symmetric_auc"] <= 0.90

    # Holdout DTI superiority with strictly positive 95% block-bootstrap CI
    assert e2["evidence_class"] == "HOLDOUT-DTI"
    assert e2["evaluator_version"] == "gems57-pooled-hide-v2"
    assert e2["withheld_positive_pixels"] == 22_893
    diff = e2["pooled_twostrat_nms3_39k"]["paired_differences"]["incumbent_h33_b2_recipe"]
    assert diff["delta"] > 0.015
    assert diff["ci95"][0] > 0.0

    # Transparent preservation of unstratified Gate 3B stop + promoted Gate 3A/3B clearance
    assert e3_stop["verdict"] == "duplicate_stop"
    assert e3_stop["gate_3b_post_placement_dots"]["binding_decision"]["worst_forward_overlap"] > 0.70

    assert e3["verdict"] == "promote"
    assert e3["gate_3a_pre_placement_surface"]["passed"] is True
    assert e3["gate_3a_pre_placement_surface"]["max_abs_spearman"] <= 0.90
    assert e3["gate_3b_post_placement_dots"]["passed"] is True
    assert e3["gate_3b_post_placement_dots"]["rasters_checked"] >= 1149
    assert e3["gate_3b_post_placement_dots"]["binding_decision"]["duplicate"] is False
    assert e3["gate_3b_post_placement_dots"]["binding_decision"]["worst_forward_overlap"] <= 0.70
    assert e3["gate_3b_post_placement_dots"]["binding_decision"]["worst_abs_spearman"] <= 0.90


def test_tcdh_algorithms_and_sentinel_safety():
    # Sentinel -3.4028235e+38 is finite in float32; _fill + _robust_z_2d must neutralize it cleanly
    raw = np.array([[1.0, -3.4028235e38], [2.0, 3.0]], dtype=np.float32)
    fp = np.ones((2, 2), dtype=bool)
    cleaned = np.where(~np.isfinite(raw) | (np.abs(raw) > 1e15), np.nan, raw)
    assert np.isnan(cleaned[0, 1])
    z = tcdh._robust_z_2d(tcdh._fill(cleaned), fp)
    assert np.isfinite(z).all() and np.abs(z).max() <= 8.0

    # Two-stratum NMS3 unit check
    H, W = 80, 80
    fp2 = np.ones((H, W), dtype=bool)
    cat2 = np.zeros((H, W), dtype=bool)
    cat2[10, 10:30] = True
    n_fp = int(fp2.sum())
    rng = np.random.default_rng(42)
    Xp = rng.standard_normal((n_fp, len(tcdh.PHYS_FEATURES))).astype(np.float32)
    Xb = rng.standard_normal((n_fp, 19)).astype(np.float32)
    Xb[:, 1] = -1.0  # low slope basin interior
    blind = tcdh.concealed_blind_basin_score_fp(Xp, Xb)
    assert blind.shape == (n_fp,) and np.isfinite(blind).all()

    yy, xx = np.indices((H, W))
    d1 = np.hypot(yy - 10, np.clip(xx, 10, 29) - xx).ravel().astype(np.float32)
    em, surf = tcdh.emit_twostrat_nms3(
        fp2, cat2, rng.uniform(0.05, 0.9, n_fp).astype(np.float32),
        rng.uniform(0.05, 0.9, n_fp).astype(np.float32),
        blind, d1, d1, np.zeros_like(d1),
        n_corridor=15, n_far_blind=15, far_min_dist_px=30.0, sep_px=3,
    )
    assert int(em.sum()) == 30
    assert not (em & cat2).any()
    assert np.isfinite(surf).all() and surf.min() >= 0.0 and surf.max() <= 1.0


def test_site_verdict_ai_disclosure_and_idempotency():
    idx = (ROOT / "docs" / "index.html").read_text()
    exe = (ROOT / "docs" / "executive-summary.html").read_text()
    assert "OK TO DOWNLOAD &amp; SUBMIT" in idx
    assert "OK TO DOWNLOAD &amp; SUBMIT" in exe
    assert "Section 3.2" in exe
    assert "gems84-h84b-tcdh-twostrat-39000d-20261022T235800Z-zeros.zip" in idx
    assert "gems84-h84b-tcdh-twostrat-39000d-20261022T235800Z-zeros.tif" in idx

    before = {p: p.read_bytes() for p in (ROOT / "docs").glob("*.html")}
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_site.py")], check=True)
    after = {p: p.read_bytes() for p in (ROOT / "docs").glob("*.html")}
    assert before == after
