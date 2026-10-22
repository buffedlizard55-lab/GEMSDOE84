#!/usr/bin/env python3
"""Report whether the shared GEMS holdout/submission workflow is present.

This is intentionally a read-only check. It does not download data, create a
private evaluator/writer, or claim that a candidate is ready to submit.
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


def readiness(root: Path, required: Iterable[tuple[str, str]] = REQUIRED) -> dict:
    checks = []
    for relpath, description in required:
        exists = (root / relpath).is_file()
        checks.append({"path": relpath, "description": description, "present": exists})
    missing = [item["path"] for item in checks if not item["present"]]
    return {
        "status": "READY_FOR_SHARED_PIPELINE" if not missing else "BLOCKED",
        "root": str(root.resolve()),
        "checks": checks,
        "missing": missing,
        "submission_available": False,
        "note": "Presence checks only; scientific evaluation and output validation are still required.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()
    result = readiness(args.root)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{result['status']}: {len(result['missing'])} required item(s) missing")
        for item in result["checks"]:
            marker = "OK" if item["present"] else "MISSING"
            print(f"[{marker}] {item['path']} — {item['description']}")
        print("Submission available: no (presence is not validation).")
    return 0 if not result["missing"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
