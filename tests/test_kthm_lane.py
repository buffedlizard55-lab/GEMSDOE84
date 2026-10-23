"""Comprehensive unit, algorithmic, and end-to-end verification tests for Lane H84-KTHM."""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]

from gems84.kthm import (  # noqa: E402
    across_strike_sharpen,
    allocate_two_regime_kthm,
    bayes_prior_calibrate,
    build_coupled_kthm_surface,
    exact_pca_tip_propagation,
)


def test_exact_pca_tip_propagation_projects_along_true_oblique_tangent():
    H, W = 90, 90
    fp = np.ones((H, W), dtype=bool)
    fp[:3, :] = False
    vis = np.zeros((H, W), dtype=bool)
    # 45-degree diagonal segment ending at tip (40, 40)
    for k in range(10):
        vis[31 + k, 31 + k] = True

    cone = exact_pca_tip_propagation(vis, fp)
    assert cone.shape == (H, W)
    assert cone.dtype == np.float32
    assert np.isfinite(cone).all()
    assert not np.any(cone[~fp] != 0.0)
    # Along +45-deg continuation (50, 50) must strictly exceed orthogonal off-axis (50, 30)
    assert float(cone[50, 50]) > 5.0 * float(cone[50, 30])


def test_two_regime_allocator_enforces_simd_prior_capacity_and_range():
    rng = np.random.default_rng(84)
    H, W = 80, 80
    fp = np.ones((H, W), dtype=bool)
    alw = np.ones((H, W), dtype=bool)
    alw[:4, :] = False
    p_sharp = rng.uniform(0.01, 0.25, size=(H, W)).astype(np.float32)
    p_blind = rng.uniform(0.002, 0.03, size=(H, W)).astype(np.float32)

    # Construct 99-byte packed prior bitmatrix where prior #0 covers top half of grid
    n_fp = int(fp.sum())
    bits_bool = np.zeros((n_fp, 792), dtype=bool)
    yy_fp = np.repeat(np.arange(H), W)
    bits_bool[yy_fp < 55, 0] = True
    fp_bits = np.packbits(bits_bool, axis=1)

    pred, stats = allocate_two_regime_kthm(
        p_sharp,
        p_blind,
        alw,
        fp,
        fp_prior_bits=fp_bits,
        budget=120,
        min_sep_px=3.0,
        overlap_cap=0.60,
        secondary_min=0.008,
        secondary_max=0.024,
        secondary_scale=0.80,
    )
    assert pred.dtype == np.float32
    assert np.isfinite(pred).all()
    assert float(pred.min()) >= 0.0 and float(pred.max()) <= 1.0
    assert not np.any(pred[~alw] > 0.0)
    assert stats["n_total_positive_crests"] == 120
    assert stats["n_primary_saturated_1p0"] == 72
    assert stats["n_secondary_blind_kthm_graded"] == 48
    # Prior #0 overlap must never exceed 0.60!
    hits_p0 = int((pred[:55, :] > 0.0).sum())
    assert hits_p0 <= 72
    assert stats["max_discriminating_halo_overlap"] <= 0.600001


def test_coupled_surface_and_bayes_calibration():
    fp = np.ones((32, 32), dtype=bool)
    fp[0, :] = False
    raw = np.linspace(0.05, 0.95, int(fp.sum()), dtype=np.float32)
    cal = bayes_prior_calibrate(raw, pos_neg_ratio_prior=0.004)
    assert np.all(np.diff(cal) > 0.0)
    assert 0.0 < float(cal.mean()) < 0.025

    p_sh = np.zeros((32, 32), dtype=np.float32)
    p_bl = np.zeros((32, 32), dtype=np.float32)
    cone = np.zeros((32, 32), dtype=np.float32)
    cone[10, 10] = 0.5
    cone[20, 20] = 0.5
    p_bl[10, 10] = 0.08
    p_bl[20, 20] = 0.0005
    p_sh[10, 10] = 0.08
    p_sh[20, 20] = 0.0005
    surf, q = build_coupled_kthm_surface(p_sh, p_bl, across_strike_sharpen(cone, fp), fp)
    assert float(surf[10, 10]) > float(surf[20, 20])
    assert float(surf[~fp].max()) == 0.0


def test_shipped_h84_kthm_cross_artifact_parity():
    rc = json.loads((ROOT / "evidence/run_card.json").read_text())
    rc_docs = json.loads((ROOT / "docs/run-card.json").read_text())
    assert rc == rc_docs
    assert rc["verdict"] == "promote"
    assert rc["weekly_live_slot_consumed"] is False

    tif_path = ROOT / rc["submission"]["tif"]
    zip_path = ROOT / rc["submission"]["zip"]
    receipt = json.loads((ROOT / rc["submission"]["receipt"]).read_text())
    assert hashlib.sha256(tif_path.read_bytes()).hexdigest() == rc["submission"]["sha256"] == receipt["sha256"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == rc["submission"]["zip_sha256"] == receipt["zip_sha256"]

    with zipfile.ZipFile(zip_path) as zf:
        assert zf.namelist() == [tif_path.name]
        assert zf.read(tif_path.name) == tif_path.read_bytes()

    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert ds.shape == (3730, 3292)
        assert ds.crs.to_epsg() == 32611
        assert tuple(ds.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert ds.nodata is None
    assert int(np.isnan(arr).sum()) == 0
    assert int(np.isinf(arr).sum()) == 0
    assert float(arr.min()) == 0.0 and float(arr.max()) == 1.0
    assert int((arr > 0.0).sum()) == 58000
    assert int((arr == 1.0).sum()) == 39440
    assert int(((arr > 0.0) & (arr < 1.0)).sum()) == 18560

    # Verify exact numerical parity across README.md and docs/index.html
    readme = (ROOT / "README.md").read_text()
    index_html = (ROOT / "docs/index.html").read_text()
    for token in (
        rc["submission"]["file"],
        rc["submission"]["sha256"],
        "0.1654",
        "0.1056",
        "+0.0597",
        "0.7902",
        "0.6800",
        "0.2075",
    ):
        assert token in readme, f"Missing {token} in README.md"
        assert token in index_html, f"Missing {token} in docs/index.html"
