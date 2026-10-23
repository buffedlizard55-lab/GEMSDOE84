"""Regression tests for Brief v2 guards (no data downloads or live submissions)."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from scipy.ndimage import distance_transform_edt

from gems84.brief_v2 import (
    BriefViolation, R0_ID, catalogue_clearance, ledger_hashes,
    read_experiment_history, read_ledger_rows, require_new_experiments,
    verify_pinned_files,
)
from scripts.validate_submission import validate

ROOT = Path(__file__).resolve().parents[1]


def row(**overrides):
    record = dict(id="old", parent=R0_ID, axis="MASS", value="-10pct",
                  sha256="a" * 64, status="BUILT", receipt_score="", date="")
    record.update(overrides)
    return record


def write_ledger(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_axis_must_be_explicit_and_values_are_limited():
    with pytest.raises(BriefViolation, match="session must explicitly select"):
        require_new_experiments([], R0_ID, None, ["x"])
    for values in ([], [""], ["1", "2", "3", "4"], ["x", "X"]):
        with pytest.raises(BriefViolation):
            require_new_experiments([], R0_ID, "RELIEF", values)
    require_new_experiments([], R0_ID, "RELIEF", ["basin_to_front_10pct"])


def test_pair_reuse_normalizes_existing_r0_alias_and_axis_case():
    existing = row()
    existing.update(parent="h33-2-b2 (R0, sha256 c55bafc47005...)", axis="snap", value="2p0px-g0p02")
    with pytest.raises(BriefViolation, match="Already built/recorded"):
        require_new_experiments([existing], R0_ID, "SNAP", ["2P0PX-G0P02"])
    # Pair reuse is not a similarity test. A different setting is not rejected.
    require_new_experiments([existing], R0_ID, "SNAP", ["unbuilt_setting"])


def test_only_full_exact_file_hashes_are_deduped():
    existing = row()
    existing.update(sha8="bbbbbbbb", sha256_zeros="c" * 64)
    hashes = ledger_hashes([existing])
    assert hashes == {"a" * 64, "c" * 64}
    assert "bbbbbbbb" not in hashes
    assert "b" * 64 not in hashes
    assert "a" * 63 + "b" not in hashes


def test_primary_ledger_and_human_receipts_are_never_rewritten(tmp_path):
    ledger = tmp_path / "submissions.csv"
    existing = row()
    existing.update(receipt_score="0.2801", date="2026-10-23")
    write_ledger(ledger, [existing])
    before = ledger.read_bytes()
    with pytest.raises(BriefViolation, match="Already built/recorded"):
        require_new_experiments(read_experiment_history(ledger), R0_ID, "MASS", ["-10pct"])
    assert ledger.read_bytes() == before
    assert read_ledger_rows(ledger)[0]["receipt_score"] == "0.2801"


def test_sibling_session_reservations_prevent_pair_reuse(tmp_path):
    ledger = tmp_path / "submissions.csv"
    write_ledger(ledger, [row()])
    reserved = row()
    reserved.update(id="other-session", axis="PRUNE", value="3")
    document = {
        "schema_version": 1,
        "sources": [{"ledger_sha256": "b" * 64,
                     "ledger_url": "https://github.com/example/repo/blob/commit/ledger/submissions.csv",
                     "experiments": [reserved]}],
    }
    (tmp_path / "experiment_reservations.json").write_text(json.dumps(document))
    history = read_experiment_history(ledger)
    assert len(history) == 2
    with pytest.raises(BriefViolation, match="Already built/recorded"):
        require_new_experiments(history, R0_ID, "PRUNE", ["3"])
    assert len(read_ledger_rows(ledger)) == 1


def test_missing_or_malformed_history_fails_closed(tmp_path):
    ledger = tmp_path / "submissions.csv"
    with pytest.raises(FileNotFoundError):
        read_experiment_history(ledger)
    ledger.write_text("id,sha256\nold,abc\n")
    with pytest.raises(BriefViolation, match="columns"):
        read_ledger_rows(ledger)
    write_ledger(ledger, [row()])
    (tmp_path / "experiment_reservations.json").write_text('{"schema_version": 2}')
    with pytest.raises(BriefViolation, match="Malformed"):
        read_experiment_history(ledger)


def test_hashes_and_byte_sizes_are_verified_before_use(tmp_path):
    path = tmp_path / "input.bin"
    path.write_bytes(b"pinned input")
    pin = dict(id="toy", dest="input.bin", bytes=path.stat().st_size,
               sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    assert verify_pinned_files(tmp_path, [pin])[0]["verified"]
    path.write_bytes(b"tampered inp")
    with pytest.raises(BriefViolation, match="mismatch"):
        verify_pinned_files(tmp_path, [pin])
    with pytest.raises(BriefViolation, match="escapes"):
        verify_pinned_files(tmp_path, [dict(pin, dest="../outside.bin")])


def test_strict_collar_applies_to_unchanged_parent_dots():
    catalogue = np.zeros((12, 12), bool)
    catalogue[4, 4] = True
    distance = distance_transform_edt(~catalogue)
    dots = np.zeros_like(catalogue)
    dots[6, 5] = True  # sqrt(5), retained by >2 but NOT by >=3
    dots[4, 7] = True  # exactly 3, allowed by the literal >=3 rule
    for axis in ("MASS", "SNAP", "CONCENTRATION", "RELIEF", "SPACING", "TRACKB"):
        clearance = catalogue_clearance(dots, catalogue, distance, axis)
        assert not clearance["passed"]
        assert clearance["dots_below_3px"] == 1
    assert catalogue_clearance(dots, catalogue, distance, "PRUNE")["passed"]
    dots[4, 4] = True
    assert not catalogue_clearance(dots, catalogue, distance, "PRUNE")["passed"]


def write_tif(path, array, *, dtype="float32", nodata=None):
    array = np.asarray(array, dtype=dtype)
    with rasterio.open(path, "w", driver="GTiff", height=array.shape[0], width=array.shape[1],
                       count=1, dtype=dtype, crs="EPSG:32611", nodata=nodata,
                       transform=from_origin(243350, 4508550, 100, 100)) as ds:
        ds.write(array, 1)


@pytest.mark.parametrize("encoding", ["nan", "zeros"])
def test_validator_supports_both_explicit_exterior_encodings(tmp_path, encoding):
    template = tmp_path / "sample.tif"
    candidate = tmp_path / "candidate.tif"
    sample = np.zeros((5, 5), np.float32)
    sample[0] = np.nan
    write_tif(template, sample, nodata=np.nan)
    values = np.zeros_like(sample)
    values[2, 2] = 1.0
    if encoding == "nan":
        values[0] = np.nan
    write_tif(candidate, values, nodata=np.nan if encoding == "nan" else None)
    result = validate(candidate, template, encoding)
    assert result["format_valid"]
    assert not result["submission_authorized"]
    assert not validate(candidate, template, "zeros" if encoding == "nan" else "nan")["format_valid"]
    values[2, 2] = np.nan
    write_tif(candidate, values, nodata=np.nan)
    assert not validate(candidate, template, encoding)["format_valid"]


@pytest.mark.parametrize("dtype", ["float64", "uint8", "int16"])
def test_validator_requires_float32_not_merely_a_real_dtype(tmp_path, dtype):
    template, candidate = tmp_path / "sample.tif", tmp_path / "candidate.tif"
    write_tif(template, np.zeros((3, 3)))
    write_tif(candidate, np.zeros((3, 3)), dtype=dtype)
    result = validate(candidate, template)
    assert not result["format_valid"]
    assert not result["checks"]["dtype_float32"]


@pytest.mark.parametrize("script,axis", [
    ("build_r0_variants.py", "MASS"), ("build_snap_variants.py", "SNAP"),
])
def test_historical_builders_stop_before_io_for_unassigned_or_reused_axes(tmp_path, script, axis):
    ledger = ROOT / "ledger/submissions.csv"
    before = ledger.read_bytes()
    missing_data = tmp_path / "must-not-be-created"
    command = [sys.executable, str(ROOT / "scripts" / script), "--data-dir", str(missing_data)]
    unassigned = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert unassigned.returncode == 2
    assert "--axis" in unassigned.stderr
    repeated = subprocess.run(command + ["--axis", axis], cwd=ROOT, capture_output=True, text=True)
    assert repeated.returncode == 2
    assert "Already built/recorded" in repeated.stderr
    assert not missing_data.exists()
    assert ledger.read_bytes() == before


def test_checked_in_preflight_is_honestly_blocked_and_preserves_history():
    report = json.loads((ROOT / "evidence/brief_v2_preflight_796cb891.json").read_text())
    assert report["assigned_axis"] is None
    assert report["verdict"] == "BLOCKED"
    assert report["new_variants_built"] == report["submission_slots_used"] == 0
    assert not report["submission_authorized"]
    assert report["ledger_unchanged"]
    assert report["ledger"]["rows"] == 119
    assert report["ledger"]["cross_session_reserved_rows"] == 3
    assert report["ledger"]["submission_page_receipts"] == 0
    assert report["parent_rebuild"]["all_checks_passed"]
    assert report["inputs"]["manifest_files_verified"] == 23
    assert report["inputs"]["parent_lineage_pins_verified"] == 4
    assert report["parent_catalogue_geometry"]["dots_below_3px"] == 1611
    assert len(report["inherited_variants"]) == 6
    assert all(not variant["strict_catalogue_clearance"]["passed"]
               for variant in report["inherited_variants"])
    assert not report["policy"]["similarity_gates_applied"]


def test_preflight_stops_before_rebuild_when_a_pinned_input_is_missing(tmp_path):
    from scripts import preflight_brief_v2 as preflight

    work = tmp_path / "no-parent-outputs"
    report = preflight.run_audit(tmp_path / "missing-data", work, None, [])
    assert report["verdict"] == "BLOCKED"
    assert report["blockers"][0]["code"] == "PREFLIGHT_FAILED_STOP"
    assert "parent_rebuild" not in report
    assert not work.exists()
    assert report["ledger_unchanged"]


def test_preflight_never_approximates_a_failed_parent(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from scripts import preflight_brief_v2 as preflight

    monkeypatch.setattr(preflight, "verify_pinned_files", lambda *args: [])
    monkeypatch.setattr(preflight, "subprocess", SimpleNamespace(
        check_output=lambda *args, **kwargs: "unit-test-git-sha",
        run=lambda *args, **kwargs: SimpleNamespace(returncode=1),
    ))
    monkeypatch.setattr(preflight, "load_grid", lambda *args: pytest.fail("must not read a failed parent"))
    report = preflight.run_audit(tmp_path, tmp_path / "work", "RELIEF", ["unused"])
    assert report["verdict"] == "BLOCKED"
    assert "never approximate" in report["blockers"][0]["detail"]
    assert "parent_rebuild" not in report
    assert report["new_variants_built"] == 0


def test_audit_report_cannot_overwrite_primary_ledger():
    ledger = ROOT / "ledger/submissions.csv"
    before = ledger.read_bytes()
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/preflight_brief_v2.py"), "--receipt", str(ledger)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "never over the ledger or inputs" in result.stderr
    assert ledger.read_bytes() == before
