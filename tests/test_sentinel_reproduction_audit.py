"""IR-DEC-17 guardrails: sentinel-cleaned bands, the reproduction audit, and the
withdrawal of the third parallel PRUNE implementation's duplicate files."""
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WITHDRAWN_IDS = {
    "h33-h33-2-b2-prune-dcatgt3px-20261023-a7d86ed4",
    "h33-h33-2-b2-prune-dcatgt1px-20261023-f5c7e4fb",
}
MAIN_PRUNE_IDS = {
    "h33-h33-2-b2-prune-dgt1in-20261023-02ad0d5c",
    "h33-h33-2-b2-prune-dge3refill-20261023-3745ebf6",
    "h33-h33-2-b2-prune-dgt3refill-20261023-10ce9ad1",
    "h33-2-b2-pruned2p5-20261023-45faee56",
    "h33-2-b2-pruned3p0-20261023-26e80847",
    "h33-2-b2-pruned4p0-20261023-ff079f66",
}
DGT3 = "h33-h33-2-b2-prune-dgt3refill-20261023-10ce9ad1"
PRUNED3 = "h33-2-b2-pruned3p0-20261023-26e80847"


def _ledger_rows():
    return list(csv.DictReader((ROOT / "ledger" / "submissions.csv").open()))


def test_sentinel_bands_rewritten_as_nan(tmp_path):
    """The fixed unpacker must never leave the finite float32 sentinel as data."""
    from scripts.build_r0_variants import BAND_NAMES, ensure_unpacked_bands

    sentinel = np.float32(-3.4028235e38)
    arr = np.ones((4, 4), dtype=np.float32)
    arr[0, 0] = sentinel
    profile = {"driver": "GTiff", "dtype": "float32", "width": 4, "height": 4,
               "count": len(BAND_NAMES), "nodata": float(sentinel)}
    with rasterio.open(tmp_path / "training_features.tif", "w", **profile) as ds:
        for idx in range(1, len(BAND_NAMES) + 1):
            ds.write(arr, idx)
    bands_dir = ensure_unpacked_bands(tmp_path)
    cleaned = np.load(bands_dir / f"{BAND_NAMES[0]}.npy")
    assert np.isnan(cleaned[0, 0])
    assert not np.any(cleaned <= -1e30)
    # A pre-existing poisoned band file must be detected and rewritten.
    np.save(bands_dir / f"{BAND_NAMES[0]}.npy", arr)
    ensure_unpacked_bands(tmp_path)
    assert np.isnan(np.load(bands_dir / f"{BAND_NAMES[0]}.npy")[0, 0])


def test_audit_evidence_records_fidelity_and_fingerprints():
    ev = json.loads((ROOT / "evidence" / "prune_reproduction_audit_20261023.json").read_text())
    assert ev["manifest_files_verified"] >= 23
    assert ev["parent_r0_sha256_verified"] is True
    gate = ev["ranking_fidelity_gate"]
    assert gate["tolerance_px"] == 50
    for key, arm in gate["arms"].items():
        assert arm["mismatch_pixels"] <= gate["tolerance_px"], (key, arm)
    fp = ev["canary_fingerprints"]
    # Cleaned ranking reproduces the MASS session's recorded canary values…
    assert fp["q_posterior"]["cleaned_ranking_auc_seed20"] == 0.6039
    assert fp["h33_union"]["cleaned_ranking_auc_seed20"] == 0.5813
    # …while the merged PRUNE sessions' recorded values match the pre-fix ranking.
    assert fp["q_posterior"]["merged_prune_sessions_recorded"] == [0.6035, 0.5853]
    assert fp["h33_union"]["merged_prune_sessions_recorded"] == [0.581, 0.5583]
    # H33-A is alive under the cleaned ranking (it was exactly 0.5000 pre-fix).
    assert fp["H33-A"]["cleaned_ranking_auc_seed20"] > 0.51


def test_clean_gt3_agrees_with_merged_gt3_class():
    ev = json.loads((ROOT / "evidence" / "prune_reproduction_audit_20261023.json").read_text())
    agree = ev["mask_agreements"]["clean_gt3_vs_each_merged_prune_file"]
    assert agree[DGT3] == {"shared_dots": 37447, "symmetric_diff_dots": 414}
    assert agree[PRUNED3]["symmetric_diff_dots"] == 546
    within = ev["mask_agreements"]["within_merged_gt3_class"][f"{DGT3} vs {PRUNED3}"]
    assert within["shared_dots"] == 37519


def test_historical_prune_inventory_survives_later_unused_values():
    rows = _ledger_rows()
    prune = {r["id"] for r in rows if r.get("axis") == "PRUNE"}
    # The audit owns six historical endpoint files, not a ban on future unused
    # collar states. Preserve all six; the new PRUNE1.5 pair has independent
    # byte/metric/geometry regression tests in test_prune_intermediate.py.
    assert MAIN_PRUNE_IDS <= prune
    for r in rows:
        assert r["id"] not in WITHDRAWN_IDS
    side_ids = set()
    for name in ("_prune_rows.json", "_prune_sweep_rows.json"):
        side_rows = json.loads((ROOT / "ledger" / name).read_text())
        assert isinstance(side_rows, list)
        side_ids |= {r["id"] for r in side_rows}
    assert side_ids == MAIN_PRUNE_IDS
    summary = json.loads((ROOT / "ledger" / "_summary.json").read_text())
    assert summary["rows"] == len(rows)
    assert summary["built"] == sum(r.get("status") == "BUILT" for r in rows)


def test_withdrawn_files_are_not_in_releases():
    for wid in WITHDRAWN_IDS:
        assert not (ROOT / "releases" / f"{wid}.tif").exists()
        assert not (ROOT / "releases" / f"{wid}-zeros.tif").exists()


def test_merged_prune_files_match_ledger_sha256():
    rows = {r["id"]: r for r in _ledger_rows() if r["id"] in MAIN_PRUNE_IDS}
    assert set(rows) == MAIN_PRUNE_IDS
    for pid, row in rows.items():
        nan_data = (ROOT / "releases" / f"{pid}.tif").read_bytes()
        zeros_data = (ROOT / "releases" / f"{pid}-zeros.tif").read_bytes()
        assert hashlib.sha256(nan_data).hexdigest() == row["sha256"], pid
        assert hashlib.sha256(zeros_data).hexdigest() == row["sha256_zeros"], pid


def test_audit_is_wired_into_docs():
    slot = (ROOT / "SLOT_PLAN.md").read_text()
    readme = (ROOT / "README.md").read_text()
    submit = (ROOT / "docs" / "SUBMIT.md").read_text()
    irregularities = (ROOT / "IRREGULARITIES.md").read_text()
    doc = Path(ROOT, "scripts", "audit_prune_reproduction.py").read_text()
    for text in (slot, readme, submit, irregularities):
        assert "IR-DEC-17" in text
    assert "IR-DEC-18" in irregularities
    for wid in WITHDRAWN_IDS:
        assert wid in doc  # withdrawal record lives in the audit module docstring
    assert "a7d86ed4" in submit          # operator-facing do-not-submit note
