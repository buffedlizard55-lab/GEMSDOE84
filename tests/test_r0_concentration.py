import numpy as np
import rasterio
from rasterio.transform import from_origin
from scipy.ndimage import distance_transform_edt

from gems84.r0_concentration import (
    BlockGeometry, apply_dose, block_report, make_compliant_parent,
    validate_raster, write_mask,
)
from gems57.metric import ALPHA, BETA, dti_binary, kernel


def test_dti_algebra_matches_shared_metric():
    rng = np.random.default_rng(20261023)
    for _ in range(8):
        truth = rng.random((18, 17)) > 0.86
        pred = rng.random((18, 17)) > 0.80
        if not truth.any():
            truth[3, 4] = True
        if not pred.any():
            pred[2, 3] = True
        result = dti_binary(pred, truth)
        dp = distance_transform_edt(~pred)
        dg = distance_transform_edt(~truth)
        T = float(kernel(dp[truth]).sum())
        S = float(pred.sum())
        M = float(kernel(dg[pred]).sum())
        K = float(truth.sum())
        algebraic = T / (ALPHA * T + ALPHA * (S - M) + BETA * K + 1e-12)
        np.testing.assert_allclose(algebraic, result["dti"], rtol=0, atol=1e-12)


def test_dose_moves_exact_count_and_preserves_exclusions():
    parent = np.zeros((8, 9), dtype=bool)
    parent[2, 2] = parent[5, 6] = True
    eligible = np.ones_like(parent)
    eligible[0, 0] = False
    donors = np.array([2 * 9 + 2], dtype=np.int64)
    receivers = np.array([7 * 9 + 8], dtype=np.int64)
    out, info = apply_dose(parent, donors, receivers, 0.5, eligible)
    assert out.sum() == parent.sum() == 2
    assert not out[2, 2] and out[7, 8]
    assert not (out & ~eligible).any()
    assert info["moved_dots"] == 1
    assert info["moved_pct_of_37654"] == 50.0


def test_block_density_cv_reports_zero_blocks_and_occupied_diagnostic():
    foot = np.ones((10, 20), dtype=bool)
    dots = np.zeros_like(foot)
    dots[0, 0] = True
    geom = BlockGeometry(10, 20)
    report = block_report(dots, geom, foot, foot)
    assert report["occupied_blocks"] == 1
    assert report["occupied_block_dot_count_cv"] == 0.0
    assert report["all_footprint_block_density_cv"] == 1.0


def test_compliance_repair_is_count_preserving_and_strict():
    foot = np.ones((12, 12), dtype=bool)
    h19 = np.zeros_like(foot)
    h19[4:9, 4:9] = True
    r0 = np.zeros_like(foot)
    r0[2, 2] = r0[6, 6] = True
    eligible = np.ones_like(foot)
    eligible[2, 2] = False
    out, info = make_compliant_parent(r0, h19, eligible, BlockGeometry(12, 12))
    assert out.sum() == r0.sum()
    assert not (out & ~eligible).any()
    assert out[6, 6]
    assert info["replacement_dots"] == 1


def test_nan_and_zero_writers_re_read_from_disk(tmp_path):
    shape = (12, 12)
    foot = np.ones(shape, dtype=bool)
    foot[0, 0] = False
    cat = np.zeros(shape, dtype=bool)
    cat[5, 5] = True
    mask = np.zeros(shape, dtype=bool)
    mask[3, 2] = True  # sqrt(10) px from the catalogue: strictly above 3 px
    template = tmp_path / "template.tif"
    with rasterio.open(template, "w", driver="GTiff", height=shape[0], width=shape[1],
                       count=1, dtype="float32", crs="EPSG:32611",
                       transform=from_origin(243350, 4508550, 100, 100), nodata=np.nan) as dst:
        dst.write(np.where(foot, 0.0, np.nan).astype(np.float32), 1)
    distance = distance_transform_edt(~cat)
    for mode in ("nan", "zeros"):
        path = tmp_path / f"{mode}.tif"
        write_mask(path, mask, foot, template, mode)
        receipt = validate_raster(path, template, foot, cat, distance, mode, expected_dots=1)
        assert receipt["all_checks_passed"]
        assert receipt["n_dots"] == 1
