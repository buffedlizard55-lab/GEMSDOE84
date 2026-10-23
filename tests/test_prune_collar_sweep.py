"""Regression tests for the AXIS = PRUNE collar sweep (scripts/build_prune_collar_sweep.py).

These run from the committed bytes only (``releases/*.tif`` + ``data/bridge/*.tif``), so CI needs
no downloaded competition cache.  They assert the Brief v2 section 6 MUST-pass gates, the ledger
bookkeeping, and the *design* invariant that makes the three files a controlled experiment:
identical dot count, identical refill rule, only the catalogue collar width differs.
"""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "ledger" / "submissions.csv"
RECEIPT = ROOT / "evidence" / "prune_variants_receipt.json"
SAMPLE = ROOT / "data" / "bridge" / "sample_submission.tif"
LABELS = ROOT / "data" / "bridge" / "labels.tif"

PARENT_DOTS = 37654
EXPECTED_VALUES = {"d2p5": 2.5, "d3p0": 3.0, "d4p0": 4.0}


def _prune_rows() -> list[dict]:
    """The three rows produced by *this* script (a parallel session's PRUNE rows also exist)."""
    with LEDGER.open(newline="") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r.get("axis") == "PRUNE" and r.get("value") in EXPECTED_VALUES]
    assert len(rows) == 3, f"expected 3 collar-sweep rows, found {len(rows)}"
    return rows


def _foot() -> np.ndarray:
    with rasterio.open(SAMPLE) as src:
        return np.isfinite(src.read(1))


def _catalogue() -> np.ndarray:
    foot = _foot()
    with rasterio.open(LABELS) as src:
        return (src.read(1) > 0) & foot


def test_ledger_rows_are_unique_and_complete():
    rows = _prune_rows()
    assert {r["value"] for r in rows} == set(EXPECTED_VALUES)
    assert len({r["sha256"] for r in rows}) == 3
    assert len({r["sha8"] for r in rows}) == 3
    for r in rows:
        assert r["parent"] == "h33-2-b2"
        assert r["status"] == "BUILT"
        assert r["receipt"] == "N"
        assert r["n_dots"] == str(PARENT_DOTS)
        assert 1.0 <= float(r["pct_changed"]) <= 50.0
        assert len(r["form_note"]) <= 140
        assert r["sha256"] and r["sha256_zeros"]


@pytest.mark.parametrize("row", _prune_rows(), ids=lambda r: r["value"])
def test_release_files_pass_every_format_gate(row):
    foot = _foot()
    cat = _catalogue()
    with rasterio.open(SAMPLE) as ref:
        ref_crs, ref_shape, ref_transform = ref.crs, (ref.height, ref.width), ref.transform

    for suffix, outside_nan in ((".tif", True), ("-zeros.tif", False)):
        path = ROOT / "releases" / f"{row['id']}{suffix}"
        assert path.exists(), path
        with rasterio.open(path) as src:
            arr = src.read(1)
            assert src.crs == ref_crs == "EPSG:32611"
            assert (src.height, src.width) == ref_shape
            assert src.transform == ref_transform
            assert src.count == 1 and src.dtypes[0] == "float32"
        inside, outside = arr[foot], arr[~foot]
        assert np.isfinite(inside).all()
        assert ((inside >= 0.0) & (inside <= 1.0)).all()
        if outside_nan:
            assert np.isnan(outside).all()
        else:
            assert np.isfinite(outside).all() and np.all(outside == 0.0)
        assert int((arr == 1.0).sum()) == PARENT_DOTS
        assert float(np.nan_to_num(arr[cat], nan=0.0).sum()) == 0.0


@pytest.mark.parametrize("row", _prune_rows(), ids=lambda r: r["value"])
def test_refill_floor_and_parent_collar_are_respected(row):
    """No dot sits inside the 3.0 px refill floor (the parent's own 2.0 px collar is stricter still).

    Refill dots are placed at d_cat >= 3.0 px by design, so the *minimum* over the whole file is the
    floor, not the variant's collar width; the collar only bounds how many R0 dots were removed.
    """
    from scipy.ndimage import distance_transform_edt

    d_cat = distance_transform_edt(~_catalogue())
    with rasterio.open(ROOT / "releases" / f"{row['id']}.tif") as src:
        dots = src.read(1) == 1.0
    # The binding floor is min(collar, 3.0 px): pruned dots are strictly outside the collar, and
    # refill dots never sit inside the 3.0 px off-catalogue floor.
    floor = min(EXPECTED_VALUES[row["value"]], 3.0)
    assert float(d_cat[dots].min()) >= floor - 1e-9


def test_variants_are_distinct_and_nested_targets():
    masks = {}
    for row in _prune_rows():
        with rasterio.open(ROOT / "releases" / f"{row['id']}.tif") as src:
            masks[row["value"]] = src.read(1) == 1.0
    a, b, c = (masks[k] for k in ("d2p5", "d3p0", "d4p0"))
    assert not np.array_equal(a, b) and not np.array_equal(b, c) and not np.array_equal(a, c)
    assert int((a & ~b).sum()) > 0 and int((b & ~c).sum()) > 0


def test_receipt_matches_ledger_and_records_two_scenarios():
    receipt = json.loads(RECEIPT.read_text())
    assert receipt["axis"] == "PRUNE"
    assert receipt["parent"]["rebuild_byte_identical"] is True
    assert receipt["parent"]["zeros_sha256"].startswith("c55bafc4")
    by_value = {v["value"]: v for v in receipt["variants"]}
    for row in _prune_rows():
        rec = by_value[row["value"]]
        assert rec["id"] == row["id"]
        assert rec["nan_tif"]["sha256"] == row["sha256"]
        assert rec["zeros_tif"]["sha256"] == row["sha256_zeros"]
        assert rec["n_dots"] == PARENT_DOTS
        assert rec["dots_added_refill"] == rec["dots_removed_collar"]
        assert rec["added_d_cat_min_px"] >= 3.0
        comp = rec["model_delta_components"]
        assert comp["ranking_arithmetic_sign"] in {"negative", "positive"}
        lo, hi = comp["predicted_band_dti"]
        assert lo <= comp["lineage_anchor_central_dti"] <= hi
        card = rec["mechanism_card"]
        for key in ("hypothesis", "mechanism", "non_fault_mimic", "predicted_sign_and_size", "falsifier"):
            assert card[key].strip()
    diag = receipt["report_only_diagnostics"]
    assert diag["leakage_canary"]["passed"] is True
    assert diag["leakage_canary"]["max_single_feature_auc"] <= 0.90
    assert diag["evidence_label"] == "PROXY"


def test_script_variants_match_ledger():
    spec = importlib.util.spec_from_file_location(
        "build_prune_collar_sweep", ROOT / "scripts" / "build_prune_collar_sweep.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert {v["value"]: v["collar_px"] for v in mod.VARIANTS} == EXPECTED_VALUES
    assert mod.EXPECTED_R0_DOTS == PARENT_DOTS
    assert mod.AXIS == "PRUNE"
