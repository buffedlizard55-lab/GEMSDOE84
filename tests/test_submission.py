"""Sanity tests for src/gems84/submission.py -- built on a small synthetic template so this
test is fast and does not depend on the (gitignored, restore-script-fetched) real competition
data being present.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio")
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems84.submission import write_submission_tif, validate_submission


@pytest.fixture
def template_tif(tmp_path):
    """A tiny synthetic single-band float32 GeoTIFF standing in for sample_submission.tif."""
    path = tmp_path / "template.tif"
    h, w = 20, 16
    transform = from_origin(500000, 4400000, 100, 100)
    profile = dict(driver="GTiff", height=h, width=w, count=1, dtype="float32",
                   crs="EPSG:32611", transform=transform, nodata=np.nan)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(np.zeros((h, w), dtype=np.float32), 1)
    return path, (h, w)


def _toy_prob_and_valid(shape):
    rng = np.random.default_rng(42)
    prob = rng.random(shape).astype(np.float32)
    valid = np.ones(shape, dtype=bool)
    valid[:2, :] = False  # a strip "outside the footprint"
    return prob, valid


def test_write_and_validate_zeros_variant_passes(template_tif, tmp_path):
    template, shape = template_tif
    prob, valid = _toy_prob_and_valid(shape)
    out = tmp_path / "sub-zeros.tif"
    receipt = write_submission_tif(out, prob, valid, template, outside_value=0.0)
    assert out.exists()
    assert len(receipt["sha256"]) == 64

    checks = validate_submission(out, template)
    assert checks["all_pass"], checks
    assert checks["crs_matches"]
    assert checks["shape_matches"]
    assert checks["transform_matches"]
    assert checks["n_nonfinite_px"] == 0
    assert checks["min"] >= 0.0
    assert checks["max"] <= 1.0


def test_write_and_validate_nan_variant_outside_only(template_tif, tmp_path):
    template, shape = template_tif
    prob, valid = _toy_prob_and_valid(shape)
    out = tmp_path / "sub-nan.tif"
    write_submission_tif(out, prob, valid, template, outside_value=np.nan)

    checks = validate_submission(out, template)
    assert checks["all_pass"], checks
    # the non-finite pixels must be exactly the "outside footprint" region, nothing more
    assert checks["n_nonfinite_px"] == int((~valid).sum())
    assert checks["min"] >= 0.0
    assert checks["max"] <= 1.0


def test_out_of_range_input_is_clipped_not_rejected(template_tif, tmp_path):
    """Regression test for the reported portal error: values must never leave [0,1] even if
    the candidate field (e.g. a raw ratio or z-score) is handed in un-normalized."""
    template, shape = template_tif
    rng = np.random.default_rng(1)
    prob = (rng.random(shape).astype(np.float32) * 10.0) - 3.0  # deliberately out of [0,1]
    valid = np.ones(shape, dtype=bool)
    out = tmp_path / "sub-clip.tif"
    write_submission_tif(out, prob, valid, template, outside_value=0.0)

    checks = validate_submission(out, template)
    assert checks["all_pass"], checks
    assert checks["min"] >= 0.0
    assert checks["max"] <= 1.0


def test_shape_mismatch_raises(template_tif, tmp_path):
    template, shape = template_tif
    bad_prob = np.zeros((shape[0] + 1, shape[1]), dtype=np.float32)
    valid = np.ones((shape[0] + 1, shape[1]), dtype=bool)
    out = tmp_path / "sub-bad.tif"
    with pytest.raises(AssertionError):
        write_submission_tif(out, bad_prob, valid, template, outside_value=0.0)
