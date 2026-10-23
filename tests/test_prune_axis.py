"""Unit tests for the AXIS=PRUNE session (Brief v2): fixed-count collar variants of R0.

Covered here:
* ledger rows for the two PRUNE builds (schema, exact-hash and (parent, axis, value)
  dedupe across the whole ledger, no receipts claimed);
* the evidence receipt (parent byte-identity, collar-ladder identities, ranking-fidelity
  gate at its IR-DEC-07 tolerance -- NOT bit-identity);
* the written GeoTIFF pairs re-read from disk (format, NaN/zeros footprint semantics,
  zero catalogue mass, exact dot counts, and the actual collar each file claims);
* REPORT-ONLY diagnostics as recorded (canary pass, withheld-positive count, and the
  shipped-mask d_cat>3 score of exactly 0.0, which is a construction artifact: every
  dot is >3 px from the full catalogue, so the 300 m kernel can earn nothing from
  withheld catalogue pixels);
* the IR-DEC-07 sentinel fix in ``ensure_unpacked_bands`` on a synthetic raster.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT)]

from scripts import validate_submission  # noqa: E402

EV_PATH = ROOT / "evidence" / "r0_prune_variants_20261023.json"
EXPECTED = {
    "prune_dcat_gt3": {"swap": 2171, "pct": 11.53},
    "prune_dcat_gt1": {"swap": 2492, "pct": 13.24},
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_ledger_prune_rows():
    rows = list(csv.DictReader((ROOT / "ledger" / "submissions.csv").open()))
    built = [r for r in rows if r["status"] == "BUILT"]
    prune = [r for r in built if r["axis"] == "PRUNE"]
    assert len(prune) == 2
    assert {r["value"] for r in prune} == {"dcat>3px-refill37654", "dcat>1px-trim37654"}
    for r in prune:
        assert r["parent"] == "h33-h33-2-b2"
        assert r["n_dots"] == "37654"  # count held exactly: the axis is the collar alone
        assert 1.0 <= float(r["pct_changed"]) <= 50.0
        assert r["receipt"] == "N" and r["receipt_score"] == "" and r["date"] == ""
        assert len(r["sha256"]) == 64 and len(r["sha256_zeros"]) == 64

    # Brief section 6 dedupe: exact hash and repeated (parent, axis, value) only.
    shas = [r["sha256"] for r in rows if r["sha256"]] + \
           [r["sha256_zeros"] for r in rows if r["sha256_zeros"]]
    assert len(shas) == len(set(shas))
    pairs = [(r["parent"], r["axis"], r["value"]) for r in rows if r["axis"]]
    assert len(pairs) == len(set(pairs))

    summary = json.loads((ROOT / "ledger" / "_summary.json").read_text())
    assert summary["built"] == len(built) == 8
    assert summary["receipts_committed"] == 0  # every live number is still CLAIM


def test_evidence_and_release_gates():
    ev = json.loads(EV_PATH.read_text())

    # Parent and lineage identities are measured, exact, and non-negotiable.
    assert ev["parent_r0"]["exact_rebuild_verified"] is True
    assert ev["parent_r0"]["n_dots"] == 37654
    assert ev["parent_r0"]["zeros_sha256"] == \
        "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
    lin = ev["lineage_identities_measured"]
    assert lin["dot_thin_h19_5_equals_pinned_d28"] is True
    assert lin["solo_equals_d28_and_dcat_gt_1"] is True
    assert lin["r0_equals_d28_and_dcat_gt_2"] is True
    assert (lin["ring_1_2_dots"], lin["ring_2_3_dots"]) == (2545, 2171)

    # IR-DEC-07: the ranking reproduces the MASS masks within tolerance, not exactly.
    gate = ev["ranking_fidelity_gate"]
    assert gate["all_within_ir_dec07_tolerance"] is True
    for arm, rec in gate["arms"].items():
        assert rec["mismatch_pixels"] <= 50, (arm, rec)

    template = ROOT / "data" / "bridge" / "sample_submission.tif"
    with rasterio.open(template) as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(ROOT / "data" / "bridge" / "existing_faults.tif") as ds:
        cat = (ds.read(1) > 0) & foot
    dcat = distance_transform_edt(~cat)

    assert {v["key"] for v in ev["variants"]} == set(EXPECTED)
    for v in ev["variants"]:
        exp = EXPECTED[v["key"]]
        assert v["n_dots"] == 37654
        assert v["dots_added_vs_r0"] == v["dots_removed_vs_r0"] == exp["swap"]
        assert v["pct_changed_vs_r0"] == exp["pct"]
        assert len(v["form_note"]) <= 140
        for field in ("hypothesis", "mechanism", "non_fault_mimic",
                      "predicted_sign_and_size", "falsifier"):
            assert v["mechanism_card"].get(field)

        nan_path, zeros_path = ROOT / v["nan_tif"]["path"], ROOT / v["zeros_tif"]["path"]
        assert _sha256(nan_path) == v["nan_tif"]["sha256"]
        assert _sha256(zeros_path) == v["zeros_tif"]["sha256"]
        assert validate_submission.validate(zeros_path, template)["format_valid"] is True

        with rasterio.open(nan_path) as ds:
            arr = ds.read(1)
        assert np.isfinite(arr[foot]).all() and np.isnan(arr[~foot]).all()
        dots = np.isfinite(arr) & (arr == 1.0)
        assert int(dots.sum()) == 37654
        assert int((dots & cat).sum()) == 0  # zero catalogue mass (MUST gate)

        with rasterio.open(zeros_path) as ds:
            arr_z = ds.read(1)
        assert np.isfinite(arr_z).all() and np.all(arr_z[~foot] == 0.0)
        assert int((arr_z == 1.0).sum()) == 37654

        # Each file must actually sit at the collar it claims to test.
        dvals = dcat[dots]
        if v["key"] == "prune_dcat_gt3":
            assert float(dvals.min()) > 3.0
        else:
            assert float(dvals.min()) > 1.0
            # The re-admitted (1, 2] px ring dots are really there (2,492 of 2,545).
            assert int((dots & (dcat <= 2.0)).sum()) == 2492


def test_report_only_diagnostics_recorded():
    ev = json.loads(EV_PATH.read_text())
    diag = ev["report_only_diagnostics"]
    assert diag["evidence_label"] == "PROXY"
    canary = diag["leakage_canary"]
    assert canary["passed"] is True and canary["max_single_feature_auc"] <= 0.90
    assert canary["n_features_checked"] == 27

    hide = diag["catalogue_hide_and_recover_proxy"]
    assert hide["withheld_positive_pixels"] == 22893
    fc = hide["fold_clean_recipe_scores"]
    # Fold-clean R0 reproduces the MASS session's recorded R0 number (cross-check).
    assert abs(fc["R0"]["dti"] - 0.105645) < 1e-5
    for arm in ("R0", "prune_dcat_gt1", "prune_dcat_gt3"):
        lo, hi = fc[arm]["ci95"]
        assert lo < fc[arm]["dti"] < hi
    # Construction artifact, recorded so nobody misreads it as variant quality:
    # shipped d_cat>3 dots are >3 px from every withheld pixel, kernel credit is 0.
    assert hide["shipped_mask_scores"]["prune_dcat_gt3"]["dti"] == 0.0
    # The SGMC control's structural bias for this axis must stay documented.
    assert "biased in favour of the tighter collar" in diag["sgmc_structural_bias_note"]


def test_sentinel_cleaning_in_band_unpack(tmp_path):
    """IR-DEC-07: ensure_unpacked_bands must turn the float32 nodata sentinel into NaN."""
    from scripts.build_r0_variants import BAND_NAMES, ensure_unpacked_bands

    profile = dict(driver="GTiff", dtype="float32", width=6, height=5,
                   count=len(BAND_NAMES), crs="EPSG:32611",
                   transform=rasterio.Affine(100.0, 0.0, 0.0, 0.0, -100.0, 0.0),
                   nodata=-3.4028234663852886e38)
    data = np.ones((len(BAND_NAMES), 5, 6), dtype=np.float32)
    data[:, 0, 0] = np.float32(-3.4028234663852886e38)
    with rasterio.open(tmp_path / "training_features.tif", "w", **profile) as ds:
        ds.write(data)

    bands = ensure_unpacked_bands(tmp_path)
    for name in BAND_NAMES:
        a = np.load(bands / f"{name}.npy")
        assert not (a <= -1e30).any()
        assert np.isnan(a[0, 0]) and a[2, 2] == 1.0
    # Idempotent: a second call leaves cleaned bands untouched.
    assert ensure_unpacked_bands(tmp_path) == bands


def test_prune_documents_reference_both_variants():
    ev = json.loads(EV_PATH.read_text())
    submit = (ROOT / "docs" / "SUBMIT.md").read_text()
    plan = (ROOT / "SLOT_PLAN.md").read_text()
    readme = (ROOT / "README.md").read_text()
    for v in ev["variants"]:
        assert v["nan_tif"]["sha256"] in submit
        assert v["zeros_tif"]["sha256"] in submit
        assert v["form_note"] in submit
        assert v["id"] in plan
    for doc in (submit, plan, readme):
        assert "IR-DEC-07" in doc or "a7d86ed4" in doc  # session is traceable in each doc
