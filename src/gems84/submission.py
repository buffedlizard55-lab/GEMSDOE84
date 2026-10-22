"""Write and validate a competition-format submission GeoTIFF.

Hard requirements, copied VERBATIM from the official page ("Submission format" section,
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/, fetched
2026-10-22):

  - same CRS as training data: projected UTM zone 11N, EPSG:32611
  - same resolution: 100 m
  - same bounds as the training data; data outside the bounds is null or nan
  - single band, float32, values in [0, 1]

KNOWN PORTAL ISSUE reported by the user (verbatim): uploading a NaN-outside file returned
"Predicted values must be in range [0, 1]". We cannot inspect the portal's validator code
(no login), so we treat this as an empirically corroborated community finding (nearly every
sibling repo in this lineage that documents the issue ships a 0.0-outside twin as its
*primary* one-click download, with a NaN-outside file offered only as a secondary/spec-
literal alternative) rather than a guess. This module writes BOTH variants and the build
script recommends the 0.0-outside file as primary, with the reasoning stated on the site --
never silently assumed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio


def write_submission_tif(path: Path, prob: np.ndarray, valid: np.ndarray, template_tif: Path,
                          outside_value: float = 0.0) -> dict:
    """prob: float array in [0,1] already computed over the WHOLE grid (values outside
    `valid` are ignored and overwritten with outside_value, which is 0.0 for the
    "zeros" submission variant and np.nan for the spec-literal "nan" variant)."""
    with rasterio.open(template_tif) as tpl:
        profile = tpl.profile.copy()
        crs, transform, shape = tpl.crs, tpl.transform, tpl.shape

    assert prob.shape == shape, f"shape mismatch {prob.shape} vs template {shape}"
    out = np.where(valid, np.clip(prob, 0.0, 1.0), outside_value).astype(np.float32)
    if not np.isnan(outside_value):
        assert np.isfinite(out).all(), "non-finite value present in a 'zeros' variant -- bug"
    profile.update(dtype="float32", count=1, crs=crs, transform=transform,
                    nodata=(np.nan if np.isnan(outside_value) else None),
                    compress="deflate", predictor=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(out, 1)

    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"path": str(path), "sha256": h, "bytes": path.stat().st_size}


def validate_submission(path: Path, template_tif: Path) -> dict:
    """Re-reads the bytes on disk (never trusts in-memory state) and checks every
    requirement a human reviewer -- or the portal -- would check."""
    checks = {}
    with rasterio.open(template_tif) as tpl:
        t_crs, t_transform, t_shape = tpl.crs, tpl.transform, tpl.shape

    with rasterio.open(path) as ds:
        checks["single_band"] = ds.count == 1
        checks["dtype_float32"] = ds.dtypes[0] == "float32"
        checks["crs_matches"] = ds.crs == t_crs
        checks["shape_matches"] = ds.shape == t_shape
        checks["transform_matches"] = tuple(ds.transform)[:6] == tuple(t_transform)[:6]
        arr = ds.read(1)
        nodata = ds.nodata

    finite = np.isfinite(arr)
    nan_mask = ~finite
    checks["has_nan_or_nodata"] = bool(nan_mask.any())
    finite_vals = arr[finite]
    checks["finite_values_in_0_1"] = bool(finite_vals.size == 0 or
                                           (finite_vals.min() >= -1e-6 and finite_vals.max() <= 1.0 + 1e-6))
    checks["no_negative"] = bool(finite_vals.size == 0 or finite_vals.min() >= -1e-6)
    checks["no_above_one"] = bool(finite_vals.size == 0 or finite_vals.max() <= 1.0 + 1e-6)
    checks["min"] = float(finite_vals.min()) if finite_vals.size else None
    checks["max"] = float(finite_vals.max()) if finite_vals.size else None
    checks["n_finite_px"] = int(finite.sum())
    checks["n_nonfinite_px"] = int(nan_mask.sum())
    checks["all_pass"] = all(v for k, v in checks.items()
                              if isinstance(v, bool) and k not in ("has_nan_or_nodata",))
    return checks
