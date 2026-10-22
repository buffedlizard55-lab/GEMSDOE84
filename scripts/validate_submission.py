#!/usr/bin/env python3
"""Strict, independent format audit for a candidate GEMS GeoTIFF.

This validates file structure/range against the official sample/reference;
it does not evaluate geological quality, uniqueness, holdout performance, or
competition acceptance. It is a safety check, not a replacement for the
shared submission writer or organizer validator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit(candidate: Path, reference: Path, footprint_path: Path | None = None,
          footprint_band: int = 1) -> dict:
    try:
        import numpy as np
        import rasterio
    except ImportError as exc:
        raise RuntimeError("Install requirements from requirements-validation.txt (rasterio, numpy).") from exc

    errors: list[str] = []
    checks: dict[str, object] = {}
    with rasterio.open(reference) as ref, rasterio.open(candidate) as src:
        checks["band_count"] = src.count
        checks["dtype"] = src.dtypes[0] if src.count else None
        checks["crs_match"] = src.crs == ref.crs
        checks["shape_match"] = (src.width, src.height) == (ref.width, ref.height)
        checks["transform_match"] = src.transform == ref.transform
        checks["bounds_match"] = src.bounds == ref.bounds
        checks["candidate_crs"] = str(src.crs)
        checks["reference_crs"] = str(ref.crs)
        checks["candidate_shape"] = [src.height, src.width]
        checks["reference_shape"] = [ref.height, ref.width]
        checks["candidate_transform"] = list(src.transform)[:6]
        checks["reference_transform"] = list(ref.transform)[:6]

        if src.count != 1:
            errors.append(f"expected exactly one band, got {src.count}")
        if src.count < 1:
            raise ValueError("candidate raster has no bands")
        if src.dtypes[0] != "float32":
            errors.append(f"expected float32, got {src.dtypes[0]}")
        for key in ("crs_match", "shape_match", "transform_match", "bounds_match"):
            if not checks[key]:
                errors.append(f"{key.replace('_', ' ')} failed")

        if footprint_path is None:
            footprint = ref.dataset_mask() > 0
            footprint_source = "reference dataset mask"
        else:
            with rasterio.open(footprint_path) as mask_ds:
                if mask_ds.count < footprint_band:
                    raise ValueError(f"footprint band {footprint_band} not present")
                if (mask_ds.width, mask_ds.height) != (ref.width, ref.height):
                    raise ValueError("footprint raster shape differs from reference")
                if mask_ds.crs != ref.crs or mask_ds.transform != ref.transform:
                    raise ValueError("footprint raster CRS/transform differs from reference")
                footprint = mask_ds.read_masks(footprint_band) > 0
            footprint_source = f"{footprint_path} band {footprint_band} mask"
        if footprint.shape != (src.height, src.width):
            raise ValueError("derived footprint shape does not match candidate")

        values = src.read(1, masked=False)
        inside_count = int(footprint.sum())
        finite = np.isfinite(values)
        nan_inside = int((np.isnan(values) & footprint).sum())
        inf_count = int(np.isinf(values).sum())
        finite_outside_range = finite & ((values < 0.0) | (values > 1.0))
        out_of_range_count = int(finite_outside_range.sum())
        outside_nan_count = int((np.isnan(values) & ~footprint).sum())
        checks.update({
            "footprint_source": footprint_source,
            "footprint_pixels": inside_count,
            "finite_inside_footprint": bool(finite[footprint].all()),
            "nan_inside_footprint": nan_inside,
            "infinity_count": inf_count,
            "finite_values_outside_[0,1]_count": out_of_range_count,
            "nan_outside_footprint_count": outside_nan_count,
            "all_finite_values_in_[0,1]": out_of_range_count == 0,
            "min_finite": float(values[finite].min()) if finite.any() else None,
            "max_finite": float(values[finite].max()) if finite.any() else None,
            "nodata_tag": None if src.nodata is None else str(src.nodata),
            "footprint_has_no_nan": nan_inside == 0,
        })
        if inside_count == 0:
            errors.append("footprint is empty")
        if not finite[footprint].all():
            errors.append("non-finite value inside the valid footprint")
        if inf_count:
            errors.append(f"infinite values found: {inf_count}")
        if out_of_range_count:
            errors.append(f"finite values outside [0, 1]: {out_of_range_count}")

    return {
        "status": "PASS" if not errors else "FAIL",
        "candidate": str(candidate),
        "reference": str(reference),
        "sha256": _sha256(candidate),
        "checks": checks,
        "errors": errors,
        "scope": "GeoTIFF format/range audit only; not a holdout, uniqueness, scientific-quality, or organizer validation.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--reference", type=Path, required=True,
                        help="official sample_submission.tif or another exact official grid reference")
    parser.add_argument("--footprint", type=Path,
                        help="optional aligned raster whose dataset mask defines valid footprint")
    parser.add_argument("--footprint-band", type=int, default=1)
    parser.add_argument("--json", action="store_true", help="print machine-readable audit JSON")
    args = parser.parse_args()
    try:
        result = audit(args.candidate, args.reference, args.footprint, args.footprint_band)
    except Exception as exc:
        result = {"status": "ERROR", "error": str(exc), "candidate": str(args.candidate),
                  "reference": str(args.reference)}
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2) if args.json else json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
