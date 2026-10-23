"""Tests for AXIS=CONCENTRATION: block operators, shipped rasters, ledger/evidence/docs.

Semantics pinned: dot count never moves (a receipt cannot be a disguised MASS effect),
donor/recipient 5 km block sets are disjoint with frozen edge strips, donors are the
lowest-gain dots inside donor blocks (deterministic, no RNG), refills sit >= 3 px from
the catalogue, and the reported block-density CVs recompute exactly from the shipped
rasters under the shared ``gems84.snap.density_cv`` definition.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems84.concentration import (  # noqa: E402
    block_dot_shares,
    block_prior,
    donor_recipient_masks,
    expand_blocks,
    lowest_gain_dots,
)
from gems84.snap import density_cv  # noqa: E402

BRIDGE = ROOT / "data" / "bridge"
RELEASES = ROOT / "releases"
EVIDENCE = ROOT / "evidence" / "r0_concentration_variants_20261023.json"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- operators
def _synthetic():
    foot = np.ones((210, 160), bool)
    foot[:50, :50] = False                       # one fully ineligible block
    q = np.full((210, 160), 0.1, dtype=np.float32)
    q[50:100, :] = 0.3
    q[100:150, :] = 0.6
    q[150:, :] = 0.9                             # graded prior, no mass ties at p50/p75
    q[~foot] = 5.0                               # must be ignored off-footprint
    return q, foot


def test_block_prior_eligibility_and_values():
    q, foot = _synthetic()
    prior, elig = block_prior(q, foot, block_px=50)
    assert prior.shape == (4, 3)
    assert not elig[0, 0] and np.isnan(prior[0, 0])
    assert prior[3, 2] == pytest.approx(0.9)
    assert prior[0, 2] == pytest.approx(0.1)


def test_donor_recipient_disjoint_and_strips_frozen():
    q, foot = _synthetic()
    prior, elig = block_prior(q, foot, block_px=50)
    r = donor_recipient_masks(prior, elig, foot.shape, block_px=50)
    assert not (r["bot50"] & r["top50"]).any()
    assert not (r["bot50"] & r["top25"]).any()
    assert r["top25"][150, 100] and r["bot50"][10, 100]
    assert not r["bot50"][205, :].any() and not r["top50"][:, 155:].any()  # strips frozen
    full = expand_blocks(elig, foot.shape, block_px=50)
    assert full.shape == foot.shape and not full[200:, :].any()


def test_lowest_gain_dots_region_and_determinism():
    gain = np.arange(210 * 160, dtype=float).reshape(210, 160)
    mask = np.zeros((210, 160), bool)
    mask[::10, ::10] = True
    region = np.zeros((210, 160), bool)
    region[:100, :] = True
    drop = lowest_gain_dots(mask, region, gain, 5)
    assert int(drop.sum()) == 5 and not (drop & ~region).any() and not (drop & ~mask).any()
    kept = mask & region & ~drop
    assert gain[drop].max() <= gain[kept].min()
    assert np.array_equal(drop, lowest_gain_dots(mask, region, gain, 5))
    with pytest.raises(ValueError):
        lowest_gain_dots(mask, region, gain, 10_000)


def test_block_dot_shares_accounting():
    q, foot = _synthetic()
    prior, elig = block_prior(q, foot, block_px=50)
    r = donor_recipient_masks(prior, elig, foot.shape, block_px=50)
    mask = np.zeros_like(foot)
    mask[10, 100] = mask[150, 100] = mask[205, 100] = True
    s = block_dot_shares(mask, r, foot)
    assert s["n_dots"] == 3 and s["dots_bot50"] == 1 and s["dots_top25"] == 1
    assert s["dots_outside_eligible_blocks"] == 1


# --------------------------------------------------------------------------- shipped rasters
def _conc_rows() -> list[dict]:
    rows = json.loads((ROOT / "ledger" / "_concentration_rows.json").read_text())
    assert len(rows) == 3 and all(r["axis"] == "CONCENTRATION" for r in rows)
    return rows


def test_conc_releases_match_ledger_receipt_and_gates():
    with rasterio.open(BRIDGE / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        ref_crs, ref_tf = ds.crs, ds.transform
    with rasterio.open(BRIDGE / "existing_faults.tif") as ds:
        cat = (ds.read(1) > 0) & foot
    d = distance_transform_edt(~cat)
    ev = {v["id"]: v for v in json.loads(EVIDENCE.read_text())["variants"]}
    ledger = {r["id"]: r for r in csv.DictReader((ROOT / "ledger/submissions.csv").open())}
    for row in _conc_rows():
        assert ledger[row["id"]]["status"] == "BUILT"
        assert ledger[row["id"]]["sha256"] == row["sha256"]
        rec = ev[row["id"]]
        for suffix, field, expect_nan in [(".tif", "sha256", True),
                                          ("-zeros.tif", "sha256_zeros", False)]:
            p = RELEASES / f"{row['id']}{suffix}"
            assert _sha256(p) == row[field]
            if suffix == ".tif":
                assert row[field][:8] == row["sha8"] == row["id"].rsplit("-", 1)[-1]
            with rasterio.open(p) as ds:
                arr = ds.read(1)
                assert ds.crs == ref_crs and ds.transform == ref_tf
                assert ds.count == 1 and ds.dtypes[0] == "float32"
            dots = np.isfinite(arr) & (arr > 0.5)
            assert int(dots.sum()) == 37654                  # count held at parent
            assert not (dots & cat).any()                    # zero catalogue mass
            assert np.isfinite(arr[foot]).all()
            assert ((arr[foot] >= 0.0) & (arr[foot] <= 1.0)).all()
            assert np.isnan(arr[~foot]).all() if expect_nan else (arr[~foot] == 0.0).all()
            assert float(d[dots].min()) == pytest.approx(rec["d_cat_min_px"], abs=1e-3)
            for bp, name in ((10, "1km_10px"), (50, "5km_50px"), (100, "10km_100px")):
                assert density_cv(dots, foot, bp) == pytest.approx(
                    rec["density_cv"][name], abs=5e-4)
        assert rec["added_dots_d_cat_min_px"] >= 3.0         # refills obey >=3 px
        assert rec["dots_added"] == rec["dots_removed"] == rec["dots_moved"]
        for f in ("hypothesis", "mechanism", "non_fault_mimic",
                  "predicted_sign_and_size", "falsifier"):
            assert rec["mechanism_card"].get(f)


def test_conc_rows_unique_pairs_bounded_change_and_docs():
    rows = list(csv.DictReader((ROOT / "ledger/submissions.csv").open()))
    vals = {"5km-t50-move3765", "5km-t25-move2400", "spread5km-move2400"}
    mine = [r for r in rows if r["status"] == "BUILT" and r["axis"] == "CONCENTRATION"]
    assert {r["value"] for r in mine} == vals
    pairs = [(r["parent"], r["axis"], r["value"]) for r in mine]
    assert len(pairs) == len(set(pairs)) == 3
    for r in mine:
        assert r["parent"] == "h33-h33-2-b2"
        assert 1.0 <= float(r["pct_changed"]) <= 50.0
        assert len(r["form_note"]) <= 140
        assert r["receipt_score"] == "" and r["date"] == ""   # human fills after upload
    all_hashes = [r["sha256"] for r in rows if r["sha256"]]
    assert len(all_hashes) == len(set(all_hashes))
    # every merged PRUNE row survives the ledger rebuild (regression: _prune_sweep_rows)
    assert sum(1 for r in rows if r["status"] == "BUILT" and r["axis"] == "PRUNE") == 6
    ev = json.loads(EVIDENCE.read_text())
    assert ev["ranking_audit"]["canonical_ranking_reproduces_prune_dgt1in_removals"] is True
    assert ev["report_only_diagnostics"]["leakage_canary"]["passed"] is True
    assert ev["report_only_diagnostics"]["leakage_canary"]["max_single_feature_auc"] <= 0.90
    assert ev["report_only_diagnostics"]["catalogue_hide_and_recover_proxy"][
        "withheld_positive_pixels"] == 22893
    submit = (ROOT / "docs" / "SUBMIT.md").read_text()
    readme = (ROOT / "README.md").read_text()
    for v in ev["variants"]:
        assert v["nan_tif"]["sha256"] in submit and v["zeros_tif"]["sha256"] in submit
        assert v["form_note"] in submit
        assert v["id"] in readme
