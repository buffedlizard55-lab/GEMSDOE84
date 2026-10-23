#!/usr/bin/env python3
"""Offline Brief v2 audit: verify pins, rebuild exact R0, read history, report blockers.

This command NEVER emits candidate rasters, changes the ledger, fetches web pages,
trains features, submits, or authorizes slots. Rebuilt parent rasters stay in .cache.
Exit 0 = technical preflight passed with explicit unused axis values; 2 = BLOCKED.
A local JSON validation report is not a submission-page score RECEIPT.

Example (audit only; exit 2 is expected until the human assigns an axis):
    python scripts/preflight_brief_v2.py --receipt evidence/brief_v2_preflight.json
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor")]

from gems84.brief_v2 import (  # noqa: E402
    AXES, R0_ID, BriefViolation, canonical_parent, catalogue_clearance,
    experiment_key, read_experiment_history, read_ledger_rows,
    require_new_experiments, verify_pinned_files,
)
from gems84.parent import load_grid, read_binary, sha256_file  # noqa: E402
from gems57.validate import validate as shared_validate  # noqa: E402
from scripts.restore_pinned_inputs import EXTRA_PINS  # noqa: E402
from scripts.validate_submission import validate as format_validate  # noqa: E402

SOURCE_FILES = (
    "registry/data_manifest.json", "ledger/experiment_reservations.json",
    "requirements-lock.txt", "src/gems84/brief_v2.py", "src/gems84/parent.py",
    "scripts/preflight_brief_v2.py", "scripts/rebuild_r0.py",
    "scripts/restore_pinned_inputs.py", "scripts/validate_submission.py",
    "vendor/gems57/validate.py",
)


def audit_inherited_variant(root: Path, row: dict, grid, r0: np.ndarray) -> dict:
    """Measure existing bytes without rebuilding, renaming, or promoting them."""
    record = {key: row[key] for key in ("id", "parent", "axis", "value", "status")}
    arrays = {}
    files = {}
    for encoding, suffix, hash_column in (
        ("nan", ".tif", "sha256"), ("zeros", "-zeros.tif", "sha256_zeros"),
    ):
        path = root / "releases" / f"{row['id']}{suffix}"
        actual = sha256_file(path)
        if actual != row.get(hash_column):
            raise BriefViolation(f"Inherited variant hash mismatch: {path.name}")
        result = format_validate(path, root / "data/bridge/sample_submission.tif", encoding)
        if not result["format_valid"]:
            raise BriefViolation(f"Inherited variant format failure: {path.name}")
        with rasterio.open(path) as src:
            arrays[encoding] = src.read(1)
        files[encoding] = result
    nan, zeros = arrays["nan"], arrays["zeros"]
    if not np.array_equal(nan[grid.foot], zeros[grid.foot]):
        raise BriefViolation(f"Inherited encoding twins differ inside the footprint: {row['id']}")
    if not np.isin(zeros[grid.foot], (0.0, 1.0)).all():
        raise BriefViolation(f"Inherited raster is not a unit-mass dot mask: {row['id']}")
    mask = zeros > 0
    added = int(np.count_nonzero(mask & ~r0))
    removed = int(np.count_nonzero(r0 & ~mask))
    n_parent = int(r0.sum())
    record.update(
        files=files, n_dots=int(mask.sum()), dots_added=added, dots_removed=removed,
        symmetric_diff_pixels=added + removed,
        symmetric_diff_pct=100.0 * (added + removed) / n_parent,
        removed_parent_dots_pct=100.0 * removed / n_parent,
        strict_catalogue_clearance=catalogue_clearance(
            mask, grid.catalogue, grid.d_cat, row["axis"].upper()
        ),
        rebuilt_this_session=False,
        submission_authorized=False,
    )
    return record


def run_audit(data_dir: Path, work_dir: Path, axis: str | None, values: list[str]) -> dict:
    report = {
        "schema_version": 1,
        "measurement_kind": "Local hash/rebuild/format audit, not a submission-page score receipt",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_sha256": {name: sha256_file(ROOT / name) for name in SOURCE_FILES},
        "runtime": {
            "python": sys.version.split()[0], "gdal": rasterio.__gdal_version__,
            **{name: importlib.metadata.version(name)
               for name in ("numpy", "scipy", "rasterio")},
        },
        "assigned_axis": axis, "requested_values": values,
        "randomness": {"uses_rng": False, "seed": None,
                       "method": "Deterministic recorded R0 recipe; no new feature fit or placement"},
        "new_variants_built": 0, "submission_slots_used": 0,
        "submission_authorized": False, "verdict": "BLOCKED", "blockers": [],
        "policy": {
            "dedupe": ["exact full file SHA-256", "repeated (parent, axis, value)"],
            "similarity_gates_applied": False,
            "non_prune_catalogue_clearance_px": 3.0,
            "implicit_parent_collar_exception": False,
            "no_evidence_absolute_live_delta_below": 0.01,
        },
        "human_inputs_unverified": [
            "AXIS and unused value(s)", "catalogue-collar conflict decision",
            "TOP_PUBLIC and read date", "single-entity slots left / rolling-week submission dates",
            "R0 submission-page receipt", "2026-12-03 deadline and exact cutoff/timezone",
            "permission/data-use terms for existing public competition-data mirrors",
        ],
        "report_only_diagnostics": {
            "catalogue_hide_and_recover": "NOT RERUN: no new variant; inherited results are PROXY, not a gate",
            "single_feature_canary": "NOT RERUN: no features fitted/used; AUC>0.90 would require investigation",
            "sgmc_control": "NOT RERUN: no new variant; REPORT ONLY",
        },
    }
    ledger = ROOT / "ledger/submissions.csv"
    ledger_before = sha256_file(ledger)
    try:
        # All input integrity checks precede any raster reading or parent rebuilding.
        manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
        entries = list(manifest["files"]) + list(EXTRA_PINS)
        verified = verify_pinned_files(data_dir, entries)
        # Also pin-check the committed template used by the independent validator.
        core = {entry["id"]: entry for entry in manifest["files"]}
        for name in ("labels", "existing_faults", "sample_submission"):
            if sha256_file(ROOT / "data/bridge" / core[name]["dest"]) != core[name]["sha256"]:
                raise BriefViolation(f"Committed bridge copy has drifted: {name}")
        report["inputs"] = {
            "manifest_sha256": sha256_file(ROOT / "registry/data_manifest.json"),
            "manifest_files_verified": len(manifest["files"]),
            "parent_lineage_pins_verified": len(EXTRA_PINS),
            "all_hashes_match": True, "files": verified,
            "provenance": "Integrity-pinned owner mirrors; NOT organizer-authenticated",
        }

        work_dir.mkdir(parents=True, exist_ok=True)
        rebuild_receipt = work_dir / "r0-rebuild.json"
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/rebuild_r0.py"),
             "--data-dir", str(data_dir), "--out", str(work_dir / "parent"),
             "--receipt", str(rebuild_receipt)],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            raise BriefViolation("Exact R0 rebuild failed; stop, never approximate the parent.")
        rebuild = json.loads(rebuild_receipt.read_text())
        if not rebuild["all_checks_passed"]:
            raise BriefViolation("R0 rebuild receipt failed a required identity check.")
        report["parent_rebuild"] = rebuild

        grid = load_grid(data_dir)
        r0_path = work_dir / "parent/r0-rebuilt-zeros.tif"
        r0 = read_binary(r0_path)
        report["parent_format"] = {
            "zeros": format_validate(r0_path, data_dir / "sample_submission.tif", "zeros"),
            "nan": format_validate(work_dir / "parent/r0-rebuilt-nan.tif",
                                   data_dir / "sample_submission.tif", "nan"),
            "shared_zeros": shared_validate(r0_path, grid.foot, grid.catalogue),
        }
        if not (report["parent_format"]["zeros"]["format_valid"]
                and report["parent_format"]["nan"]["format_valid"]
                and report["parent_format"]["shared_zeros"]["all_checks_passed"]):
            raise BriefViolation("Rebuilt parent failed disk re-read format validation.")
        parent_clearance = catalogue_clearance(r0, grid.catalogue, grid.d_cat, "MASS")
        report["parent_catalogue_geometry"] = {
            **parent_clearance, "dots": int(r0.sum()),
            "at_or_below_2px": int(np.count_nonzero(r0 & (grid.d_cat <= 2.0))),
            "exactly_3px": int(np.count_nonzero(r0 & (grid.d_cat == 3.0))),
            "strictly_above_3px": int(np.count_nonzero(r0 & (grid.d_cat > 3.0))),
        }

        primary_rows = read_ledger_rows(ledger)
        history = read_experiment_history(ledger)
        used_pairs = sorted({experiment_key(row["parent"], row["axis"], row["value"])
                             for row in history if row["parent"] and row["axis"] and row["value"]})
        report["ledger"] = {
            "sha256": ledger_before, "rows": len(primary_rows),
            "built_rows": sum(row["status"] == "BUILT" for row in primary_rows),
            "submission_page_receipts": sum(row.get("receipt") == "Y" for row in primary_rows),
            "cross_session_reserved_rows": len(history) - len(primary_rows),
            "used_pairs": [list(pair) for pair in used_pairs],
            "r0_claim": {"value": 0.2778, "evidence_class": "CLAIM", "parent": R0_ID},
        }
        try:
            require_new_experiments(history, R0_ID, axis, values)
        except BriefViolation as exc:
            report["blockers"].append({"code": "EXPERIMENT_NOT_ASSIGNED_OR_ALREADY_BUILT", "detail": str(exc)})
        if not parent_clearance["passed"] and axis != "PRUNE":
            report["blockers"].append({
                "code": "R0_COLLAR_CONFLICT_UNRESOLVED",
                "detail": f"R0 has {parent_clearance['dots_below_3px']} dots below 3 px. "
                          "Do not implicitly waive the rule or introduce a second-axis collar edit.",
            })
        report["inherited_variants"] = [
            audit_inherited_variant(ROOT, row, grid, r0)
            for row in primary_rows
            if row["status"] == "BUILT" and canonical_parent(row["parent"]) == R0_ID
        ]
        if not report["blockers"]:
            report["verdict"] = "TECHNICAL_PREFLIGHT_ONLY"
    except (BriefViolation, OSError, ValueError, KeyError, rasterio.errors.RasterioError) as exc:
        report["blockers"].append({"code": "PREFLIGHT_FAILED_STOP", "detail": str(exc)})
    report["ledger_unchanged"] = sha256_file(ledger) == ledger_before
    if not report["ledger_unchanged"]:
        report["blockers"].append({"code": "LEDGER_CHANGED_DURING_AUDIT", "detail": "Stop and re-read history."})
        report["verdict"] = "BLOCKED"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".cache/gems_data")
    parser.add_argument("--work-dir", type=Path, default=ROOT / ".cache/brief-v2-preflight")
    parser.add_argument("--receipt", type=Path, default=ROOT / ".cache/brief-v2-preflight.json")
    parser.add_argument("--axis", choices=AXES, help="Human-assigned; omitted means audit only.")
    parser.add_argument("--value", action="append", default=[], help="An explicit unused axis value (up to three).")
    args = parser.parse_args()
    cache_root = (ROOT / ".cache").resolve()
    if not args.work_dir.resolve().is_relative_to(cache_root):
        parser.error("Rebuilt parent outputs must remain under the ignored .cache directory.")
    receipt = args.receipt.resolve()
    if not any(receipt.is_relative_to(directory.resolve())
               for directory in (ROOT / ".cache", ROOT / "evidence")):
        parser.error("Audit reports must be under .cache/ or evidence/, never over the ledger or inputs.")
    protected = {ROOT / name for name in SOURCE_FILES}
    protected.update((ROOT / "evidence/h33-original-audit.json", ROOT / "evidence/h33_validation.json"))
    if receipt in {path.resolve() for path in protected}:
        parser.error("The audit report cannot overwrite a pinned input or source record.")
    report = run_audit(args.data_dir.resolve(), args.work_dir.resolve(), args.axis, args.value)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({
        "verdict": report["verdict"], "blockers": report["blockers"],
        "new_variants_built": 0, "submission_authorized": False,
        "receipt": str(args.receipt),
    }, indent=2))
    return 2 if report["verdict"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
