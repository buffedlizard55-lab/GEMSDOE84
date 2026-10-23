#!/usr/bin/env python3
"""Report whether the shared GEMS holdout/submission workflow is present.

This is intentionally a read-only check. It does not download data or create a
private evaluator/writer. When ``data_dir`` is omitted, it inspects the default
in-tree ``data/raw`` layout (preserving ``tests/test_readiness.py``). When
``--data-dir`` (or ``data_dir=...``) is supplied, it inspects that external
hydrated cache root alongside the pinned ``vendor/gems57`` modules and checks
whether a validated submission package is present in ``docs/downloads``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

REQUIRED = (
    ("data/raw/external/lidar_scarp_features_u8.tif", "cached derived LiDAR stack, hash verification still required"),
    ("data/raw/external/geodawn_rad_u8.tif", "cached derived radiometric stack, hash verification still required"),
    ("data/raw/existing_faults.tif", "mirrored catalogue raster"),
    ("data/raw/sample_submission.tif", "mirrored reference grid"),
    ("vendor/gems57/evaluate_holdout.py", "shared spatially blocked holdout evaluator"),
    ("vendor/gems57/submission_writer.py", "shared submission writer"),
)


def readiness(
    root: Path,
    required: Iterable[tuple[str, str]] = REQUIRED,
    data_dir: Path | None = None,
) -> dict:
    checks = []
    if data_dir is None:
        for relpath, description in required:
            exists = (root / relpath).is_file()
            checks.append({"path": relpath, "description": description, "present": exists})
        sub_avail = False
        note = "Presence checks only; scientific evaluation and output validation are still required."
    else:
        dd = Path(data_dir).resolve()
        ext_items = (
            (dd / "training_features.tif", "19-band GEMS geophysical training stack"),
            (dd / "labels.tif", "mapped fault catalogue raster (labels.tif)"),
            (dd / "sample_submission.tif", "canonical EPSG:32611 100 m reference grid"),
            (dd / "external" / "lidar_scarp_features_u8.tif", "cached derived LiDAR scarp stack"),
            (dd / "external" / "geodawn_rad_u8.tif", "cached GeoDAWN radiometric stack"),
            (dd / "external" / "paleo_geothermal_regional.zip", "DOE GDR 1391 INGENIOUS paleo-geothermal deposits"),
            (dd / "external" / "2m_temperature_probe_INGENIOUS_regional_data.zip", "DOE GDR 1391 INGENIOUS 2 m temperature probe archive"),
            (root / "vendor" / "gems57" / "evaluate_holdout.py", "shared spatially blocked holdout evaluator"),
            (root / "vendor" / "gems57" / "submission_writer.py", "shared submission writer"),
        )
        for p, description in ext_items:
            checks.append({"path": str(p), "description": description, "present": p.is_file()})
        dl_tifs = sorted((root / "docs" / "downloads").glob("gems84-h84b-tcdh-*-zeros.tif"))
        sub_avail = len(dl_tifs) > 0
        note = (
            f"External cache root checked ({dd}); validated H84-TCDH GeoTIFF present: {sub_avail}."
        )

    missing = [item["path"] for item in checks if not item["present"]]
    return {
        "status": "READY_FOR_SHARED_PIPELINE" if not missing else "BLOCKED",
        "root": str(root.resolve()),
        "checks": checks,
        "missing": missing,
        "submission_available": sub_avail,
        "note": note,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Optional external hydrated data directory (e.g. .cache/gemsdata)",
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()
    result = readiness(args.root, data_dir=args.data_dir)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{result['status']}: {len(result['missing'])} required item(s) missing")
        for item in result["checks"]:
            marker = "OK" if item["present"] else "MISSING"
            print(f"[{marker}] {item['path']} — {item['description']}")
        print(f"Submission available: {'yes' if result['submission_available'] else 'no'}.")
    return 0 if not result["missing"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
