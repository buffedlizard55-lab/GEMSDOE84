"""End-to-end verification test suite for GEMSDOE84 (Lane H84-THMS)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio

from gems84 import hypotheses as H
from vendor.gems57 import validate as V

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_hypotheses_specification():
    hyps = H.H84_HYPOTHESES
    assert len(hyps) == 5
    ranks = [h["rank"] for h in hyps]
    assert ranks == [1, 2, 3, 4, 5]
    for h in hyps:
        for key in (
            "id",
            "lane_code",
            "title",
            "layers",
            "physical_signature",
            "why_off_catalogue",
            "novelty_vs_prior",
            "named_nonfault_mimic",
            "expected_dti_gain",
            "cost",
        ):
            assert key in h and h[key], f"Missing {key} in {h.get('id')}"


def test_leakage_canary_gate():
    canary_path = ROOT / "evidence" / "h84_exp1_canary.json"
    assert canary_path.exists()
    data = json.loads(canary_path.read_text())
    assert data["all_seeds_passed"] is True
    assert data["gate_ceiling_symmetric_auc"] == 0.90
    assert data["n_total_channels"] == 96
    for seed_key in ("30", "20"):
        s = data["seeds"][seed_key]
        assert s["all_below_090"] is True
        assert s["max_symmetric_auc"] <= 0.90
        assert s["max_novel_h84_symmetric_auc"] <= 0.90
        assert len(s["per_feature_symmetric_auc"]) == 96


def test_dualseed_holdout_progression():
    card = json.loads((ROOT / "research/official/previous-h84-run-card.json").read_text())
    arms = card["holdout_dti"]["all_arms_dualseed"]
    required_arms = [
        "A0_random",
        "A1_phys72_poisson",
        "A2_struct24_poisson",
        "A3_thms96_poisson",
        "A4_thms96_dink_c20",
        "A5_thms96_dualhead_dink_c30",
    ]
    for k in required_arms:
        assert k in arms
        arm = arms[k]
        assert arm["evidence_class"] == "HOLDOUT-DTI"
        assert arm["evaluator_version"] == "gems57-pooled-hide-v2"
        assert arm["withheld_positive_pixels"] == 22663
        assert len(arm["ci95"]) == 2
        assert arm["ci95"][0] <= arm["dti"] <= arm["ci95"][1]

    # Archive arithmetic is inspectable, not scientific acceptance or a required
    # monotonic "success" progression. A5 is not certified leakage-free.
    for arm in arms.values():
        tp, fp, fn = arm['tpw'], arm['fpw'], arm['fnw']
        assert np.isclose(arm['dti'], tp / (tp + 0.2 * fp + 0.8 * fn))


def test_validated_submission_geotiff_and_zip():
    card = json.loads((ROOT / "research/official/previous-h84-run-card.json").read_text())
    sub_name = card["submission_name"]
    tif_sub = ROOT / "submissions" / f"{sub_name}.tif"
    zip_sub = ROOT / "submissions" / f"{sub_name}.zip"
    tif_doc = ROOT / "docs" / "downloads" / f"{sub_name}.tif"
    zip_doc = ROOT / "docs" / "downloads" / f"{sub_name}.zip"

    assert tif_sub.exists() and zip_sub.exists()
    assert tif_doc.exists() and zip_doc.exists()
    assert _sha256(tif_sub) == card["raster_sha256"] == _sha256(tif_doc)
    assert _sha256(zip_sub) == card["zip_sha256"] == _sha256(zip_doc)

    # Validate directly with vendor/gems57/validate.py
    val = V.validate(tif_sub)
    assert val["all_checks_passed"] is True
    for k, ok in val["checks"].items():
        assert ok is True, f"Check {k} failed"

    with rasterio.open(tif_sub) as src:
        arr = src.read(1)
        assert src.shape == (3730, 3292)
        assert str(src.crs) == "EPSG:32611"
        assert src.nodata is None
        assert arr.dtype == np.float32

    assert int(np.isnan(arr).sum()) == 0
    assert int(np.isinf(arr).sum()) == 0
    assert float(arr.min()) == 0.0
    assert float(arr.max()) == 1.0
    uniq = np.unique(arr)
    assert np.array_equal(uniq, np.array([0.0, 1.0], dtype=np.float32))
    assert int((arr == 1.0).sum()) == 37654


def test_uniqueness_and_run_card_contract():
    card = json.loads((ROOT / "run_card.json").read_text())
    for key in (
        "hypothesis",
        "mechanism",
        "named_nonfault_mimic",
        "holdout_dti",
        "holdout_status",
        "registry_correlation_overlap",
        "raster_sha256",
        "validator_output",
        "submission_name",
        "submission_note",
        "verdict",
    ):
        assert key in card

    assert card['verdict'] == 'negative'
    assert card['submission_authorized'] is False
    assert card['raster_sha256'] is None  # no new TIFF generated
    assert card['holdout_dti'] is None  # no freshly certified result
    assert len(card['submission_note']) <= 140
    assert card['registry_correlation_overlap']['duplicate'] is True
    assert card['registry_correlation_overlap']['overlap_3px'] > 0.70
    assert card['pre_placement_stop'] is True


def test_site_and_readme_deliverables():
    readme = (ROOT / "README.md").read_text()
    assert "PARALLEL-RUN PROTOCOL" in readme
    assert "gems84-h84-thms-dink300-37654dots-20261022-2f4190b4-zeros" in readme
    assert "DO NOT SUBMIT" in readme

    for rel in (
        "index.html",
        "executive-summary.html",
        "docs/index.html",
        "docs/executive-summary.html",
        "docs/methodology.html",
        "docs/results.html",
        "docs/irregularities.html",
        "docs/sources.html",
        "figures/h84_thms_surface_and_dots.png",
        "docs/figures/h84_thms_surface_and_dots.png",
    ):
        p = ROOT / rel
        assert p.exists() and p.stat().st_size > 0, f"Missing {rel}"
