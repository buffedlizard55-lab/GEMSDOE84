#!/usr/bin/env python3
"""Rebuild parent R0 (``h33-h33-2-b2``) from its recorded recipe and assert its SHA-256.

Session gate (brief section 5): *rebuild R0 and match its sha256; if you cannot, stop and
report -- never approximate the parent.*  This script is that gate.  It fails closed with a
non-zero exit code when any of these do not hold:

1. every input hash matches its pin (``scripts/restore_pinned_inputs.py`` receipt);
2. the rebuilt dot mask has exactly 37,654 dots, zero on the catalogue;
3. the re-emitted ``-zeros`` raster is byte-identical to the pinned parent
   (SHA-256 ``c55bafc4...``, read from ``evidence/h33-original-audit.json``).

Usage:  python scripts/rebuild_r0.py [--data-dir .cache/gems_data] [--out .cache/r0_rebuild]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems84.parent import (  # noqa: E402
    BASE_02708_SHA256,
    EXPECTED_R0_DOTS,
    R0_NAN_SHA256,
    R0_ZEROS_SHA256,
    emit_dots,
    load_grid,
    r0_pins_from_evidence,
    rebuild_r0_mask,
    sha256_file,
    verify_r0_file,
)


def git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:  # pragma: no cover
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", default=str(ROOT / ".cache" / "gems_data"))
    ap.add_argument("--out", default=str(ROOT / ".cache" / "r0_rebuild"))
    ap.add_argument("--receipt", default=str(ROOT / "evidence" / "r0_rebuild_receipt.json"))
    args = ap.parse_args()

    t0 = time.time()
    data_dir = Path(args.data_dir)
    out_dir = Path(args.out)
    pins = r0_pins_from_evidence(ROOT)
    grid = load_grid(data_dir)

    print(f"[r0] footprint pixels = {int(grid.foot.sum()):,}")
    print(f"[r0] catalogue pixels = {int(grid.catalogue.sum()):,}")

    mask, base = rebuild_r0_mask(data_dir)
    n_dots = int(mask.sum())
    print(f"[r0] base dots        = {int(base.sum()):,}")
    print(f"[r0] rebuilt R0 dots  = {n_dots:,}")

    zeros_path = emit_dots(mask, grid, out_dir / "r0-rebuilt-zeros.tif", mode="zeros")
    nan_path = emit_dots(mask, grid, out_dir / "r0-rebuilt-nan.tif", mode="nan")
    got_zeros = sha256_file(zeros_path)
    got_nan = sha256_file(nan_path)

    checks = {
        "footprint_pixels_5167373": int(grid.foot.sum()) == 5_167_373,
        "dots_37654": n_dots == EXPECTED_R0_DOTS == pins["dots"],
        "zero_on_catalogue": int((mask & grid.catalogue).sum()) == 0,
        "zeros_sha256_matches_pin": got_zeros == pins["zeros_sha256"] == R0_ZEROS_SHA256,
        "nan_sha256_matches_pin": got_nan == pins["nan_sha256"] == R0_NAN_SHA256,
        "base_sha256_matches_pin": sha256_file(data_dir / "parent" /
                                               "gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif")
        == BASE_02708_SHA256,
    }

    receipt = {
        "schema_version": 1,
        "evidence_class": "REBUILD (byte-identity against a SHA-256-pinned parent artifact)",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_sha": git_sha(),
        "parent": {
            "candidate_id": pins["candidate_id"],
            "slug": pins["slug"],
            "role": "R0 / incumbent; owner-reported live 0.2778 is a CLAIM (no receipt in ledger/)",
            "claimed_live": 0.2778,
            "claimed_live_evidence_class": "CLAIM",
            "zeros_sha256_pin": R0_ZEROS_SHA256,
            "nan_sha256_pin": R0_NAN_SHA256,
            "base_02708_sha256_pin": BASE_02708_SHA256,
        },
        "recipe": {
            "foot": "np.isfinite(sample_submission.tif band 1)",
            "catalogue": "read_binary(labels.tif) & foot   (existing_faults.tif is byte-identical)",
            "base": "read_binary(gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif)",
            "mask": "base & (distance_transform_edt(~catalogue) > 2)",
            "emit": "clean = mask & foot & ~catalogue; GTiff deflate/predictor=3/zlevel=9/tiled256",
            "upstream_source": "buffedlizard55-lab/GEMSDOE32@main src/gems32/hypotheses33.py:307-329, "
                               "src/gems32/submission.py:118-166, scripts/run_h33_validation.py:112",
        },
        "rebuilt": {
            "dots": n_dots,
            "zeros_tif": verify_r0_file(zeros_path, grid),
            "nan_tif": verify_r0_file(nan_path, grid),
        },
        "checks": checks,
        "all_checks_passed": all(checks.values()),
        "elapsed_s": round(time.time() - t0, 1),
    }
    Path(args.receipt).write_text(json.dumps(receipt, indent=2) + "\n")
    for k, v in checks.items():
        print(f"[r0]   {'PASS' if v else 'FAIL'}  {k}")
    print(f"[r0] rebuilt zeros sha256 = {got_zeros}")
    print(f"[r0] pinned   zeros sha256 = {pins['zeros_sha256']}")
    print(f"[r0] receipt -> {args.receipt}  ({receipt['elapsed_s']}s)")
    if not all(checks.values()):
        print("[r0] R0 REBUILD FAILED -- do not build variants from an approximated parent.")
        return 1
    print("[r0] R0 REBUILT BYTE-IDENTICAL to the pinned parent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
