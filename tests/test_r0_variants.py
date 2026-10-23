"""Unit tests for Brief v2: DTI algebra, ledger, R0 rebuild, and MASS variant gates."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT)]

from gems57 import metric  # noqa: E402
from scripts import validate_submission  # noqa: E402


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_metric_algebra_identity_and_breakeven():
    """Verify DTI = T / (0.2*T + 0.2*(S - M) + 0.8*|G|) and isolated vs line-like dot economics."""
    rng = np.random.default_rng(42)
    H, W = 40, 40
    valid = np.ones((H, W), dtype=bool)
    truth = np.zeros((H, W), dtype=bool)
    truth[20, 10:30] = True  # 20-pixel horizontal fault trace
    G = float(truth.sum())

    pred = np.zeros((H, W), dtype=np.float32)
    ys = rng.integers(5, 35, size=25)
    xs = rng.integers(5, 35, size=25)
    pred[ys, xs] = 1.0

    exact = metric.dti_exact(pred, truth, valid=valid)
    covers, q_kernel, _ = metric.max_cover(pred, truth)
    S = float(pred[valid].sum())
    T = float(covers.sum())
    M = float((pred * q_kernel)[valid].sum())

    dti_algebra = T / (0.2 * T + 0.2 * (S - M) + 0.8 * G + metric.EPS)
    assert np.isclose(exact["dti"], dti_algebra, atol=1e-7)

    # Break-even threshold at s = 0.28 for an isolated off-truth dot (Delta(S - M) = 1):
    s = 0.28
    breakeven_dT = (0.2 * s) / (1.0 - 0.2 * s)
    assert np.isclose(breakeven_dT, 0.05932203, atol=1e-5)
    # At s0 = 0.2778 (R0 CLAIM), break-even dT is ~0.05883 (and < 0.072 across [0.27, 0.31])
    assert 0.055 < breakeven_dT < 0.075

    # Line-like emission on the 1-px-wide tracetruth[20, 10:30]:
    # Solid 1-px line (20 dots) vs 3-px-spaced dots (7 dots at cols 10, 13, 16, 19, 22, 25, 28)
    p_solid = np.zeros((H, W), dtype=np.float32)
    p_solid[20, 10:30] = 1.0
    # Add realistic off-fault false-positive background (80 dots far from truth)
    p_solid[2:6, 5:25] = 1.0

    p_dotted = np.zeros((H, W), dtype=np.float32)
    p_dotted[20, 10:30:3] = 1.0
    p_dotted[2:6, 5:25] = 1.0

    cov_solid = metric.max_cover(p_solid, truth)[0].sum()
    cov_dotted = metric.max_cover(p_dotted, truth)[0].sum()
    # 7 dots (~1/3 the mass on the trace) achieve >75% of the solid line's truth coverage
    assert cov_dotted / cov_solid > 0.75


def test_ledger_schema_and_built_variants():
    """Verify ledger/raw_paste.txt and ledger/submissions.csv structure and deduplication."""
    raw_paste = ROOT / "ledger" / "raw_paste.txt"
    sub_csv = ROOT / "ledger" / "submissions.csv"
    assert raw_paste.exists()
    assert sub_csv.exists()

    rows = list(csv.DictReader(sub_csv.open()))
    assert len(rows) >= 106

    built = [r for r in rows if r["status"] == "BUILT"]
    mass_built = [r for r in built if r["axis"].upper() == "MASS"]
    assert len(mass_built) == 3

    seen_shas = set()
    seen_pairs = set()
    for r in mass_built:
        assert r["parent"] == "h33-h33-2-b2"
        assert r["axis"] == "MASS"
        assert r["value"] in {"-10pct", "+10pct", "-20pct"}
        pct = float(r["pct_changed"])
        assert 1.0 <= pct <= 50.0
        assert len(r["sha256"]) == 64
        assert r["sha256"] not in seen_shas
        seen_shas.add(r["sha256"])
        pair = (r["parent"], r["axis"], r["value"])
        assert pair not in seen_pairs
        seen_pairs.add(pair)
        # The brief explicitly reserves these fields for human receipts.
        if r["receipt_score"]:
            assert 0.0 <= float(r["receipt_score"]) <= 1.0
            assert r["date"]


def test_releases_and_evidence_gates():
    """Verify all 3 MASS variant GeoTIFF pairs in releases/ and evidence/r0_mass_variants_20261023.json."""
    ev_path = ROOT / "evidence" / "r0_mass_variants_20261023.json"
    assert ev_path.exists()
    ev = json.loads(ev_path.read_text())

    r0 = ev["parent_r0"]
    assert r0["exact_rebuild_verified"] is True
    assert r0["n_dots"] == 37654
    assert r0["digest8"] == "e5eb6e7e"
    assert r0["zeros_sha256"] == "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
    assert r0["nan_sha256"] == "baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd"

    template = ROOT / "data" / "bridge" / "sample_submission.tif"
    cat_path = ROOT / "data" / "bridge" / "existing_faults.tif"
    with rasterio.open(template) as ref_ds:
        foot = np.isfinite(ref_ds.read(1))
    with rasterio.open(cat_path) as cat_ds:
        cat = (cat_ds.read(1) > 0) & foot

    expected_counts = {"drop10pct": 33889, "add10pct": 41419, "drop20pct": 30123}
    assert len(ev["variants"]) == 3

    for v in ev["variants"]:
        key = v["key"]
        assert v["n_dots"] == expected_counts[key]
        assert 1.0 <= v["pct_changed_vs_r0"] <= 50.0
        assert len(v["form_note"]) <= 140
        for card_field in (
            "hypothesis",
            "mechanism",
            "non_fault_mimic",
            "predicted_sign_and_size",
            "falsifier",
        ):
            assert v["mechanism_card"].get(card_field)

        nan_path = ROOT / v["nan_tif"]["path"]
        zeros_path = ROOT / v["zeros_tif"]["path"]
        assert nan_path.exists()
        assert zeros_path.exists()
        assert _sha256(nan_path) == v["nan_tif"]["sha256"]
        assert _sha256(zeros_path) == v["zeros_tif"]["sha256"]

        # Independent validator check on -zeros.tif
        val_res = validate_submission.validate(zeros_path, template)
        assert val_res["format_valid"] is True

        # Direct pixel & NaN/zero encoding checks on both files
        with rasterio.open(nan_path) as ds_nan:
            arr_nan = ds_nan.read(1)
        assert np.isfinite(arr_nan[foot]).all()
        assert np.isnan(arr_nan[~foot]).all()
        assert int((arr_nan == 1.0).sum()) == v["n_dots"]
        assert float(np.nan_to_num(arr_nan[cat], nan=0.0).sum()) == 0.0

        with rasterio.open(zeros_path) as ds_z:
            arr_z = ds_z.read(1)
        assert np.isfinite(arr_z).all()
        assert np.all(arr_z[~foot] == 0.0)
        assert int((arr_z == 1.0).sum()) == v["n_dots"]
        assert float(arr_z[cat].sum()) == 0.0

    diag = ev["report_only_diagnostics"]
    assert diag["leakage_canary"]["passed"] is True
    assert diag["leakage_canary"]["max_single_feature_auc"] <= 0.90
    assert diag["catalogue_hide_and_recover_proxy"]["withheld_positive_pixels"] == 22893
    assert diag["sgmc_off_catalogue_control"]["add10pct"]["sgmc_raw_dti"] > diag["sgmc_off_catalogue_control"]["R0"]["sgmc_raw_dti"]


def test_required_brief_v2_documents_exist():
    """Verify SLOT_PLAN.md, docs/SUBMIT.md, IRREGULARITIES.md, AI_USE.md, and README CURRENT STATE block."""
    for rel in ("SLOT_PLAN.md", "docs/SUBMIT.md", "IRREGULARITIES.md", "AI_USE.md"):
        p = ROOT / rel
        assert p.exists(), f"Missing {rel}"
        assert p.stat().st_size > 200

    readme = (ROOT / "README.md").read_text()
    assert "<!-- CURRENT_STATE_START -->" in readme
    assert "<!-- CURRENT_STATE_END -->" in readme
    # CURRENT STATE must name at least one built candidate per axis it reports on, and the packet
    # (docs/SUBMIT.md) must name every BUILT candidate, whatever axis the session worked on.
    with (ROOT / "ledger" / "submissions.csv").open(newline="") as fh:
        built = [r for r in csv.DictReader(fh) if r.get("status") == "BUILT"]
    submit_text = (ROOT / "docs" / "SUBMIT.md").read_text()
    assert built, "expected BUILT rows in the ledger"
    for axis in {r["axis"] for r in built}:
        ids = [r["id"] for r in built if r["axis"] == axis]
        assert any(i in readme for i in ids), f"README CURRENT STATE names no {axis} candidate"
    for r in built:
        assert r["id"] in submit_text, f"{r['id']} missing from docs/SUBMIT.md"

    submit_doc = (ROOT / "docs" / "SUBMIT.md").read_text()
    ev = json.loads((ROOT / "evidence" / "r0_mass_variants_20261023.json").read_text())
    for v in ev["variants"]:
        assert v["nan_tif"]["sha256"] in submit_doc
        assert v["zeros_tif"]["sha256"] in submit_doc
        assert v["form_note"] in submit_doc
