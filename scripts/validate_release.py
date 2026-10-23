#!/usr/bin/env python3
"""Brief-v2 section-6 MUST gates for one release GeoTIFF (format + catalogue).

Checks, reading the file back from disk: single band, float32, CRS/shape/
transform/bounds identical to sample_submission.tif, all values finite and
in [0,1] inside the footprint (finite cells of the sample), no NaN inside,
outside-footprint values are all NaN (mode=nan) or all 0.0 (mode=zeros),
zero positive mass on catalogue pixels, dot count, sha256.  Optionally
records parent-diff statistics against a parent TIFF (--parent).

This is a local format gate only -- not organiser acceptance.  Report-only
instruments (holdout PROXY, canary, SGMC) live in scripts/proxy_report.py
and never gate.  No correlation/overlap thresholds are applied (brief v2 s6).

Usage:
  python scripts/validate_release.py releases/<id>.tif --mode nan
  python scripts/validate_release.py releases/<id>-zeros.tif --mode zeros \
      --parent $GEMS84_DATA/parent/r0-zeros.tif
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "data" / "bridge"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate(path: Path, mode: str, parent: Path | None) -> dict:
    with rasterio.open(BRIDGE / "sample_submission.tif") as ref:
        sample = ref.read(1)
        ref_meta = (str(ref.crs), (ref.height, ref.width),
                    tuple(ref.transform)[:6], tuple(ref.bounds))
    foot = np.isfinite(sample)
    with rasterio.open(BRIDGE / "labels.tif") as ds:
        cat = (ds.read(1) > 0) & foot
    with rasterio.open(path) as ds:
        a = ds.read(1)
        meta = (str(ds.crs), (ds.height, ds.width),
                tuple(ds.transform)[:6], tuple(ds.bounds))
        checks = {
            "single_band": ds.count == 1,
            "dtype_float32": ds.dtypes[0] == "float32",
            "crs_shape_transform_bounds_match_sample": meta == ref_meta,
        }
        nodata = ds.nodata
    inside = a[foot]
    outside = a[~foot]
    checks["no_nan_inside_footprint"] = bool(np.isfinite(inside).all())
    checks["values_in_0_1_inside"] = bool(
        np.isfinite(inside).all() and inside.min() >= 0.0 and inside.max() <= 1.0)
    if mode == "nan":
        checks["nan_outside_footprint"] = bool(np.isnan(outside).all())
    else:
        checks["zeros_outside_footprint"] = bool((outside == 0.0).all())
    dotmask = np.isfinite(a) & (a > 0)
    checks["zero_catalogue_mass"] = int((dotmask & cat).sum()) == 0
    checks["nodata_tag_consistent"] = bool(
        (nodata is not None and np.isnan(nodata)) if mode == "nan"
        else (nodata is None or (np.isfinite(nodata) and nodata == 0.0)))
    out: dict = {
        "file": str(path), "mode": mode, "sha256": sha256(path),
        "bytes": path.stat().st_size, "n_dots": int(dotmask.sum()),
        "on_catalogue_dots": int((dotmask & cat).sum()),
        "checks": checks, "all_must_gates_passed": bool(all(checks.values())),
        "scope": "local format/catalogue gate (brief v2 s6); not organiser acceptance",
    }
    if parent is not None:
        with rasterio.open(parent) as ds:
            parr = ds.read(1)
        pmask = np.isfinite(parr) & (parr > 0)
        dist = distance_transform_edt(~cat)
        out["parent_diff"] = {
            "parent": str(parent),
            "parent_dots": int(pmask.sum()),
            "kept": int((dotmask & pmask).sum()),
            "removed": int((pmask & ~dotmask).sum()),
            "added": int((dotmask & ~pmask).sum()),
            "pct_of_parent_dots_replaced": round(
                100.0 * int((pmask & ~dotmask).sum()) / int(pmask.sum()), 4),
            "candidate_min_d_catalogue_px": float(dist[dotmask].min()),
            "candidate_median_d_catalogue_px": float(np.median(dist[dotmask])),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--mode", choices=("nan", "zeros"), required=True)
    ap.add_argument("--parent", type=Path)
    args = ap.parse_args()
    result = validate(args.candidate, args.mode, args.parent)
    print(json.dumps(result, indent=2))
    return 0 if result["all_must_gates_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
