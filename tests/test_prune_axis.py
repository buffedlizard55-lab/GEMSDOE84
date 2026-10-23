"""Tests for the AXIS=PRUNE work: the fixed-count collar operators and the shipped rasters.

The operator tests pin the semantics the brief demands of PRUNE: the dot count never moves
(so a live receipt cannot be a disguised MASS effect), the collar band that a variant
claims to vacate is actually empty, and the inward swap removes exactly the parent's
lowest-marginal-gain dots (deterministic tie-breaking, no RNG).
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

from gems84.prune import drop_collar_band, swap_in_near_collar  # noqa: E402

BRIDGE = ROOT / "data" / "bridge"
RELEASES = ROOT / "releases"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- operators
def _synthetic():
    """Catalogue = one vertical line; R0 dots at d>2; ring dots at 1<d<=2."""
    cat = np.zeros((15, 21), bool)
    cat[:, 10] = True
    d = distance_transform_edt(~cat)
    r0 = np.zeros((15, 21), bool)
    r0[2, 14] = r0[4, 15] = r0[6, 13] = r0[8, 16] = r0[10, 14] = r0[12, 17] = True
    assert (d[r0] > 2.0).all()
    ring = np.zeros((15, 21), bool)
    ring[3, 12] = ring[7, 8] = ring[11, 12] = True      # d == 2,2,2 -> in (1, 2]
    assert ((d[ring] > 1.0) & (d[ring] <= 2.0)).all()
    gain = np.zeros((15, 21))
    for i, (y, x) in enumerate(zip(*np.nonzero(r0))):
        gain[y, x] = 0.1 * (i + 1)                        # row-major ascending gains
    return cat, d, r0, ring, gain


def test_swap_in_holds_count_and_drops_lowest_gain():
    _cat, d, r0, ring, gain = _synthetic()
    out, stats = swap_in_near_collar(r0, ring, gain)
    assert int(out.sum()) == int(r0.sum()) == 6
    assert stats["dots_added"] == stats["dots_removed"] == 3
    assert out[ring].all()                                # whole ring swapped in
    removed = r0 & ~out
    kept_gains = gain[r0 & out]
    assert gain[removed].max() <= kept_gains.min()        # removed = 3 lowest gains
    assert float(d[out].min()) > 1.0                      # inward collar still > 1 px
    out2, _ = swap_in_near_collar(r0, ring, gain)
    assert np.array_equal(out, out2)                      # deterministic


def test_swap_in_rejects_oversized_or_empty_pool():
    _cat, _d, r0, ring, gain = _synthetic()
    with pytest.raises(ValueError):
        swap_in_near_collar(r0, np.zeros_like(r0), gain)
    too_big = np.ones_like(r0) & ~r0
    with pytest.raises(ValueError):
        swap_in_near_collar(r0, too_big, gain)


def test_drop_collar_band_exclusive_vs_inclusive():
    cat = np.zeros((9, 15), bool)
    cat[:, 7] = True
    d = distance_transform_edt(~cat)
    r0 = np.zeros((9, 15), bool)
    r0[2, 4] = True        # d == 3.0 exactly
    r0[4, 10] = True       # d == 3.0 exactly
    r0[6, 12] = True       # d == 5.0
    base_excl, rem_excl = None, None
    with pytest.raises(ValueError):                       # nothing strictly inside (2, 3)
        base_excl, rem_excl = drop_collar_band(r0, d, lo=2.0, hi=3.0, hi_inclusive=False)
    base_incl, rem_incl = drop_collar_band(r0, d, lo=2.0, hi=3.0, hi_inclusive=True)
    assert int(rem_incl.sum()) == 2 and int(base_incl.sum()) == 1
    assert float(d[base_incl].min()) > 3.0


def test_drop_collar_band_diagonal_distances():
    cat = np.zeros((11, 11), bool)
    cat[5, 5] = True
    d = distance_transform_edt(~cat)
    r0 = np.zeros((11, 11), bool)
    r0[3, 4] = True        # sqrt(5) ~= 2.236 -> in (2, 3)
    r0[7, 7] = True        # sqrt(8) ~= 2.828 -> in (2, 3)
    r0[1, 5] = True        # 4.0 -> kept
    base, removed = drop_collar_band(r0, d, lo=2.0, hi=3.0, hi_inclusive=False)
    assert int(removed.sum()) == 2 and int(base.sum()) == 1
    assert not (base & (d < 3.0)).any()


# --------------------------------------------------------------------------- shipped rasters
def _prune_rows() -> list[dict]:
    rows = json.loads((ROOT / "ledger" / "_prune_rows.json").read_text())
    assert len(rows) == 3 and all(r["axis"] == "PRUNE" for r in rows)
    return rows


def test_prune_releases_match_ledger_and_parent_count():
    with rasterio.open(BRIDGE / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        ref_crs, ref_tf = ds.crs, ds.transform
    with rasterio.open(BRIDGE / "existing_faults.tif") as ds:
        cat = (ds.read(1) > 0) & foot
    d = distance_transform_edt(~cat)
    collar_min = {"dcat>1px-swapin": 1.0, "dcat>=3px-refill": 3.0, "dcat>3px-refill": 3.0}
    strict = {"dcat>1px-swapin": True, "dcat>=3px-refill": False, "dcat>3px-refill": True}

    ledger = {r["id"]: r for r in csv.DictReader((ROOT / "ledger" / "submissions.csv").open())}
    for row in _prune_rows():
        assert ledger[row["id"]]["status"] == "BUILT"     # folded into the ledger
        assert ledger[row["id"]]["sha256"] == row["sha256"]
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
            assert int(dots.sum()) == 37654               # PRUNE holds the parent count
            assert not (dots & cat).any()                 # zero catalogue mass
            assert np.isfinite(arr[foot]).all()
            assert ((arr[foot] >= 0.0) & (arr[foot] <= 1.0)).all()
            if expect_nan:
                assert np.isnan(arr[~foot]).all()
            else:
                assert (arr[~foot] == 0.0).all()
            lo = float(d[dots].min())
            assert lo > collar_min[row["value"]] if strict[row["value"]] else lo >= collar_min[row["value"]]


def test_prune_rows_are_new_pairs_with_bounded_change():
    rows = list(csv.DictReader((ROOT / "ledger" / "submissions.csv").open()))
    # Scope to this script's values: a second, independent PRUNE implementation
    # (scripts/build_prune_collar_sweep.py) also has BUILT rows in the same ledger (IR-DEC-12).
    vals = {"dcat>1px-swapin", "dcat>=3px-refill", "dcat>3px-refill"}
    pairs = [(r["parent"], r["axis"], r["value"]) for r in rows
             if r["status"] == "BUILT" and r["axis"] == "PRUNE" and r["value"] in vals]
    assert len(pairs) == 3 and len(set(pairs)) == 3
    for r in rows:
        if r["status"] == "BUILT" and r["axis"] == "PRUNE" and r["value"] in vals:
            assert r["parent"] == "h33-h33-2-b2"
            assert 1.0 <= float(r["pct_changed"]) <= 50.0
            assert len(r["form_note"]) <= 140
    all_hashes = [r["sha256"] for r in rows if r["sha256"]]
    assert len(all_hashes) == len(set(all_hashes))       # no hash submitted/built twice
