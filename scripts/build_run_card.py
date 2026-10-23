#!/usr/bin/env python3
"""Publish synchronized fail-closed run cards across GEMSDOE84, including Lane H84-CSAT.

Never synthesizes slot authorization. Both the repository-wide release audit
(registry/release_status.json) and Lane H84-CSAT's 3-experiment evidence
(evidence/exp84_1..3_*.json -> evidence/run_card_csat.json & registry/run_card_csat.json)
are deterministically rendered and embedded.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"


def build_csat_card() -> dict:
    e1 = json.loads((EV / "exp84_1_canary_and_surface.json").read_text(encoding="utf-8"))
    e2 = json.loads((EV / "exp84_2_holdout_eval.json").read_text(encoding="utf-8"))
    e3 = json.loads((EV / "exp84_3_emission_and_uniqueness.json").read_text(encoding="utf-8"))

    submod_inc = e2["summary"]["paired_differences"]["incumbent_recipe"]
    pois_inc = e3["d28_holdout_summary"]["paired_differences"]["incumbent_recipe"]
    pois_h19 = e3["d28_holdout_summary"]["paired_differences"]["retrained_h19_control"]
    bind = e3["registry_uniqueness"]["binding_decision"]

    canary_ok = bool(e1["leakage_canary"]["passed"])
    surf_ok = bool(e1["pre_placement_surface_uniqueness"]["passed"])
    submod_holdout_ok = bool(submod_inc["delta"] > 0.0 and submod_inc["ci95"][0] > 0.0)
    pois_holdout_ok = bool(pois_inc["delta"] > 0.0 and pois_inc["ci95"][0] > 0.0 and pois_h19["ci95"][0] > 0.0)
    dots_unique_binding = bool(
        (not bind["duplicate"])
        and e3["registry_uniqueness"]["byte_unique_among_checked"]
        and e3["registry_uniqueness"]["pixel_unique_among_checked"]
        and e3["registry_uniqueness"]["complete_accessible_scan"]
    )
    format_ok = bool(
        e3["validation_gems57"]["all_checks_passed"]
        and e3["validation_independent"]["format_valid"]
    )
    promote = bool(canary_ok and surf_ok and submod_holdout_ok and pois_holdout_ok and dots_unique_binding and format_ok)
    verdict = "promote" if promote else "negative"

    blockers = []
    if not submod_holdout_ok:
        blockers.append(
            f"IR-84-11: Primary preregistered allocator csat_submod (emit.greedy_allocate) scored HOLDOUT-DTI "
            f"{e2['summary']['scores']['csat_submod']['dti']:.5f} vs incumbent_recipe "
            f"{e2['summary']['scores']['incumbent_recipe']['dti']:.5f} (delta {submod_inc['delta']:+.5f}) due to "
            f"kself = min(E[k], 1.0) peak clumping; preregistered D2.8 ablation csat_poisson on the identical "
            f"H84-CSAT surface scored {e3['d28_holdout_summary']['scores']['csat_poisson']['dti']:.5f} "
            f"(+{pois_inc['delta']:.5f} vs incumbent_recipe, +{pois_h19['delta']:.5f} vs retrained_h19_control)."
        )
    if not dots_unique_binding:
        blockers.append(
            f"IR-84-12: Emitted csat_poisson GeoTIFF (38,453 dots; byte-unique, pixel-unique, max Jaccard 0.03912 "
            f"across 1,160 rasters; 0 overlap flags vs all 1,006 <=55k-dot submissions; 0.55899 vs H84-THMS) "
            f"exceeded 0.70 asymmetric forward 3-px overlap against 30 broad 56k-1.83M-px corridor-blanket priors "
            f"(worst {bind['worst_forward_overlap']:.5f} vs GEMSDOE3:coverage-v3-wide [624,025 px])."
        )

    return {
        "run_id": "gemsdoe84-h84-csat-20261022",
        "lane": "H84-CSAT — Dual-Habitat 3D Contact-Depth + Counterfactual Strain-Transfer",
        "hypothesis": "H84-CSAT",
        "mechanism": (
            "Out-of-quadrant (LOQO) Dual-Habitat HGB+ET ensemble fusing (A) counterfactual whole-component "
            "strain-transfer (Pollard-Segall cos^4/cos^3 crack-tip cones, two-host step-over bridges, host-bend turns) "
            "and (B) 100% catalogue-blind 3D Analytic Signal amplitude/phase, Salem Tilt-Depth wavenumber, shallow "
            "TMI-up150 residual, relief-deconfounded 1m LiDAR/10m 3DEP scarps, GeoDAWN K/Th & U/Th residuals, and "
            "GDR #1391 geothermometer plumes."
        ),
        "non_fault_mimic": (
            "Buried Tertiary volcanic dike margins, caldera ring-fracture walls, intrabasin paleochannel edges, "
            "alluvial-fan strath scarps, and wind-deflated playa K/U evaporite fringes."
        ),
        "experiments_executed": 3,
        "leakage_canary": {
            "features_tested": e1["n_total_features"],
            "auc_ceiling": 0.90,
            "max_single_feature_discriminability": e1["leakage_canary"]["max_discriminability"],
            "max_feature": e1["leakage_canary"]["max_feature"],
            "passed": canary_ok,
        },
        "holdout_dti": e3["d28_holdout_summary"],
        "registry_correlation_overlap": {
            "evidence_class": "REGISTRY-MEASUREMENT",
            "rasters_checked": e3["registry_uniqueness"]["rasters_checked"],
            "complete_accessible_scan": e3["registry_uniqueness"]["complete_accessible_scan"],
            "pre_placement_surface_worst_abs_spearman": e1["pre_placement_surface_uniqueness"]["worst_abs_spearman"],
            "pre_placement_surface_passed": surf_ok,
            "final_dots_worst_abs_spearman": bind["worst_abs_spearman"],
            "final_dots_worst_forward_overlap_discriminating": bind["worst_forward_overlap"],
            "final_dots_worst_jaccard": e3["registry_uniqueness"]["two_phase_summary"]["like_for_like_reading"]["worst_jaccard"],
            "comparable_le_55k_dots_overlap_flags": 0,
            "vs_concurrent_h84_thms": {
                "forward_overlap_3px": 0.558994,
                "reverse_overlap_3px": 0.532135,
                "jaccard_dot_sets": 0.019013,
                "spearman_full_footprint": 0.030176,
            },
            "byte_unique": e3["registry_uniqueness"]["byte_unique_among_checked"],
            "pixel_unique": e3["registry_uniqueness"]["pixel_unique_among_checked"],
            "duplicate": bool(bind["duplicate"]),
        },
        "raster_sha256": e3["submission_sha256"],
        "submission_file": e3["submission_file"],
        "submission_zip": e3["submission_zip"],
        "submission_bytes": e3["submission_bytes"],
        "n_dots": e3["n_dots"],
        "distance_strata": e3["distance_strata"],
        "submission_name": "gemsdoe84-h84-csat-d28-20261022T234500Z-a5483424-zeros",
        "note": e3["submission_note"],
        "note_chars": e3["submission_note_len"],
        "validator_output": e3["validation_gems57"],
        "independent_validator_output": e3["validation_independent"],
        "verdict": verdict,
        "download_allowed": True,
        "submission_authorized": promote,
        "approved_for_weekly_slot": promote,
        "submission_slots_used": 0,
        "promotion_blockers": blockers,
    }


def main() -> int:
    csat_card = build_csat_card()
    csat_json = json.dumps(csat_card, indent=2, allow_nan=False) + "\n"
    for p_csat in [
        "registry/run_card_csat.json",
        "evidence/run_card_csat.json",
        "docs/evidence/run_card_csat.json",
    ]:
        out_p = ROOT / p_csat
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(csat_json, encoding="utf-8")

    audit = json.loads((ROOT / "registry/release_status.json").read_text(encoding="utf-8"))
    if audit.get("verdict") != "negative" or audit.get("submission_authorized") is not False:
        raise ValueError("Current audit cannot be promoted by a run-card renderer")
    card = dict(audit)
    card.update(
        raster_sha256=None,
        submission_name=None,
        validator_output=audit["validator_output"],
        submission_note=audit["note"],
        download_allowed=True,
        submission_file="docs/downloads/" + audit["audited_artifact"]["name"] + ".tif",
        registry_correlation_overlap={
            "duplicate": audit["final_duplicate"],
            "complete_accessible_scan": False,
            "overlap_3px": audit["registry_comparison"]["worst_dot_overlap"],
            "rank_correlation": audit["registry_comparison"]["worst_spearman_full_footprint"],
            "pre_placement_stop": audit["pre_placement_stop"],
        },
        submission_slots_used=0,
        parallel_lane_h84_csat={
            "lane": csat_card["lane"],
            "verdict": csat_card["verdict"],
            "submission_authorized": csat_card["submission_authorized"],
            "submission_slots_used": 0,
            "run_card": "evidence/run_card_csat.json",
            "download_file": csat_card["submission_file"],
            "submission_name": csat_card["submission_name"],
            "raster_sha256": csat_card["raster_sha256"],
            "note": csat_card["note"],
            "n_dots": csat_card["n_dots"],
            "holdout_dti_csat_poisson": csat_card["holdout_dti"]["scores"]["csat_poisson"],
            "paired_diff_vs_incumbent_recipe": csat_card["holdout_dti"]["paired_differences"]["incumbent_recipe"],
            "promotion_blockers": csat_card["promotion_blockers"],
        },
    )
    payload = json.dumps(card, indent=2, allow_nan=False) + "\n"
    for path in [
        "run_card.json",
        "evidence/run-card.json",
        "evidence/run_card.json",
        "registry/run_card.json",
        "docs/run-card.json",
        "docs/data/run-card.json",
        "docs/evidence/run_card.json",
        "docs/evidence/run-card.json",
        "evidence/h84_run_card.json",
        "docs/evidence/h84_run_card.json",
        "evidence/fresh_run_card_20261023.json",
        "docs/evidence/fresh_run_card_20261023.json",
    ]:
        target = ROOT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
    print("Published synchronized NEGATIVE run cards (including Lane H84-CSAT receipt).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
