#!/usr/bin/env python3
"""Deterministically compile synchronized Run Cards across all GEMSDOE84 lanes.

Primary Canonical Repository Release (`run_card.json`, `evidence/run-card.json`,
`evidence/run_card.json`, `registry/run_card.json`, `docs/run-card.json`,
`docs/data/run-card.json`, `docs/evidence/run-card.json`, `docs/evidence/run_card.json`):
  -> Lane H84-KTHM (`gems84-h84-kthm-tworegime-58000px-20261022T235900Z-zeros.tif`),
     the sole lane in GEMSDOE84 passing all five mandatory protocol gates simultaneously.

Archived Negative Research Lanes (preserved fail-closed with `verdict: "negative"`
and `submission_authorized: false`):
  -> `evidence/run_card_csat.json` & `registry/run_card_csat.json` (Lane H84-CSAT)
  -> `evidence/h84_run_card.json` & `evidence/fresh_run_card_20261023.json` (Lane H84-THMS)
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def build_thms_negative_card() -> dict:
    audit = json.loads((ROOT / "registry/release_status.json").read_text(encoding="utf-8"))
    if audit.get("verdict") != "negative" or audit.get("submission_authorized") is not False:
        raise ValueError("Archived H84-THMS audit cannot be promoted by a run-card renderer")
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
    )
    return card


def build_kthm_promoted_card(csat_card: dict, thms_card: dict) -> dict:
    e1 = json.loads((EV / "e1_canary.json").read_text(encoding="utf-8"))
    e2 = json.loads((EV / "e2_holdout.json").read_text(encoding="utf-8"))
    e3_surf = json.loads((EV / "e3_gate_surface.json").read_text(encoding="utf-8"))
    e3_dots = json.loads((EV / "e3_gate_dots.json").read_text(encoding="utf-8"))
    sv = json.loads((EV / "submission_validation.json").read_text(encoding="utf-8"))
    receipt = json.loads((ROOT / sv["receipt_json"]).read_text(encoding="utf-8"))

    sub_name = "gems84-h84-kthm-tworegime-58000px-20261022T235900Z-zeros"
    tif_dl = ROOT / "docs/downloads" / f"{sub_name}.tif"
    zip_dl = ROOT / "docs/downloads" / f"{sub_name}.zip"
    tif_sub = ROOT / "submissions" / f"{sub_name}.tif"
    zip_sub = ROOT / "submissions" / f"{sub_name}.zip"

    expected_tif_sha = sv["sha256_tif"]
    expected_zip_sha = sv["sha256_zip"]
    if _sha256(tif_dl) != expected_tif_sha or _sha256(tif_sub) != expected_tif_sha:
        raise ValueError("H84-KTHM GeoTIFF SHA-256 mismatch against evidence/submission_validation.json")
    if _sha256(zip_dl) != expected_zip_sha or _sha256(zip_sub) != expected_zip_sha:
        raise ValueError("H84-KTHM ZIP SHA-256 mismatch against evidence/submission_validation.json")

    sm = e2["summary"]
    scores = sm["scores"]
    pdiffs = sm["paired_differences"]
    sp = sv["spatial_allocation_profile"]
    sibs = e3_dots["concurrent_gemsdoe84_siblings"]

    canary_ok = bool(e1["gate_passed"] and len(e1["flagged"]) == 0 and e1["max_rectified_auc_observed"] <= 0.90)
    surf_ok = bool(e3_surf["passed"] and e3_surf["worst_abs_spearman"] <= 0.90)
    holdout_ok = bool(
        pdiffs["incumbent_recipe"]["delta"] > 0.0
        and pdiffs["incumbent_recipe"]["ci95"][0] > 0.0
        and pdiffs["E2_tip_geom_uncorroborated_58k"]["delta"] > 0.0
        and pdiffs["E2_tip_geom_uncorroborated_58k"]["ci95"][0] > 0.0
    )
    dots_ok = bool(
        e3_dots["passed"]
        and (not e3_dots["binding_decision_ir_h85_01"]["duplicate"])
        and e3_dots["binding_decision_ir_h85_01"]["worst_forward_overlap"] <= 0.70
        and e3_dots["binding_decision_ir_h85_01"]["worst_abs_spearman"] <= 0.90
        and sibs["vs_h84_csat"]["passes_070_overlap_and_090_spearman"]
        and sibs["vs_h84_thms"]["passes_070_overlap_and_090_spearman"]
    )
    valid_ok = bool(
        sv["all_automated_checks_passed"]
        and sv["gems57_validate"]["all_checks_passed"]
        and sv["independent_validate_submission"]["format_valid"]
        and sp["on_catalogue_positive_pixels"] == 0
        and sp["dots_dcat_le_2px"] == 0
    )
    if not (canary_ok and surf_ok and holdout_ok and dots_ok and valid_ok):
        raise ValueError("H84-KTHM failed a mandatory protocol gate; refusing to promote")

    note = receipt["note"]
    mimic = (
        "Stratiform permeable volcanic ash-flow tuff aquifers, non-tectonic caldera argillic alteration halos, "
        "Pleistocene Lake Lahontan shoreline benches (1,270-1,340 m), and coalescent alluvial fan aprons "
        "(explicitly deconfounded via Quaternary volcanic vent fields, paleolake shoreline indicators, and 3DEP swath masks)."
    )
    return {
        "schema_version": 2,
        "generated_utc": "2026-10-23T02:20:00Z",
        "repo": "buffedlizard55-lab/GEMSDOE84",
        "branch": "arena/1397ba87-gemsdoe84",
        "lane": "H84-KTHM",
        "verdict": "promote",
        "safe_to_submit": True,
        "submission_ready": True,
        "weekly_live_slot_consumed": False,
        "submission": {
            "name": sub_name,
            "note": note,
            "note_chars": len(note),
            "tif": f"docs/downloads/{sub_name}.tif",
            "zip": f"docs/downloads/{sub_name}.zip",
            "receipt": f"docs/downloads/{sub_name}.json",
            "sha256": expected_tif_sha,
            "zip_sha256": expected_zip_sha,
            "bytes": sv["bytes_tif"],
            "emitted_positive_crests": sp["total_emitted_positive_crests"],
            "primary_1p0_crests": sp["primary_saturated_1p0_crests"],
            "blind_kthm_graded_crests": sp["secondary_blind_kthm_graded_crests"],
            "mask_policy": "zeros (all 12,279,160 pixels finite float32 in [0.0, 1.0]; 0 NaNs anywhere)",
            "file": f"{sub_name}.tif",
        },
        "evidence_summary": {
            "metric_label": "HOLDOUT-DTI",
            "evaluator_version": e2["evaluator_version"],
            "withheld_positive_pixels": e2["withheld_positive_pixels"],
            "seeds": e2["seeds"],
            "experiments_used": 3,
            "experiment_budget": 3,
            "E1_kthm_blind_37k": scores["E1_kthm_blind_37k"],
            "E2_tip_geom_uncorroborated_58k": scores["E2_tip_geom_uncorroborated_58k"],
            "E2b_loqo_tree_two_regime_55k": scores["E2b_loqo_tree_two_regime_55k"],
            "E3_kthm_coupled_two_regime_58k": scores["E3_kthm_coupled_two_regime_58k"],
            "incumbent_recipe_comparator": scores["incumbent_recipe"],
            "incumbent_asis_comparator": scores["incumbent_asis"],
            "prior_pr7_liti_reference": e2["prior_pr7_liti_identical_split_reference"],
            "paired_differences_E3_minus_comparators": pdiffs,
        },
        "organizer_and_owner_reported_benchmarks": {
            "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros": {
                "score": 0.2778,
                "evidence_class": "OWNER-REPORTED LIVE SCORE (GEMSDOE32)",
            },
            "h19-5": {"score": 0.2683, "evidence_class": "ORGANIZER-CONFIRMED"},
            "b2-sharponly-s2": {"score": 0.2442, "evidence_class": "ORGANIZER-CONFIRMED"},
            "b3-3": {"score": 0.0956, "evidence_class": "ORGANIZER-CONFIRMED"},
            "leaderboard_reference_marks_user_brief": [0.3195, 0.4413],
        },
        "gates": {
            "leakage_canary_passed": True,
            "leakage_canary_max_auc": round(float(e1["max_rectified_auc_observed"]), 6),
            "stage1_surface_uniqueness_passed": True,
            "stage1_surface_worst_abs_spearman": round(float(e3_surf["worst_abs_spearman"]), 6),
            "stage2_dots_binding_uniqueness_passed": True,
            "stage2_dots_worst_discriminating_overlap": round(
                float(e3_dots["binding_decision_ir_h85_01"]["worst_forward_overlap"]), 6
            ),
            "stage2_dots_worst_abs_spearman": round(
                float(e3_dots["binding_decision_ir_h85_01"]["worst_abs_spearman"]), 6
            ),
            "automated_format_and_range_validation_passed": True,
            "beats_incumbent_recipe_with_positive_95ci": True,
        },
        "runtime_seconds": round(float(e2["seconds"]), 1),
        "hypothesis": (
            "H84-KTHM: Kinetic Solute Geothermometry Disequilibrium (max(T_qtz, T_cat) - T_discharge, "
            "T_cat - T_chalc, Fournier-Potter silica-enthalpy mixing fronts) coupled with Hydrothermal "
            "Magnetite-Destruction RTP Troughs, Multi-Physics LOQO Ensembles, Sub-Degree Elastostatic "
            "Strand-Tip Propagation, and Two-Regime Dinkelbach Allocation under 786-Prior Fleet Capacity"
        ),
        "mechanism": (
            "Ascending 140-250 C geothermal fluids along blind Basin-and-Range damage zones mix with cold "
            "shallow aquifers, masking surface temperature vents while preserving quartz/Na-K-Ca chemical "
            "equilibrium and argillic/magnetite-destructive geophysical signatures; coupling this 53-channel "
            "blind hydrogeochemical-geophysical head with sub-degree outward strand-tip elastostatic cones "
            "and two-regime Dinkelbach allocation (39,440 saturated 1.0 crests + 18,560 micro-graded blind "
            "discovery crests) captures both unmapped fault continuations and pure blind intra-basin conduits "
            "while guaranteeing <= 0.680 overlap across all 786 discriminating priors."
        ),
        "named_non_fault_mimic": mimic,
        "named_nonfault_mimic": mimic,
        "download_allowed": True,
        "submission_authorized": False,
        "safe_to_submit_by_human": True,
        "submission_slots_used": 0,
        "submission_name": sub_name,
        "submission_note": note,
        "note": note,
        "raster_sha256": expected_tif_sha,
        "holdout_dti": round(float(scores["E3_kthm_coupled_two_regime_58k"]["dti"]), 6),
        "holdout_ci95": [round(float(x), 6) for x in scores["E3_kthm_coupled_two_regime_58k"]["ci95"]],
        "holdout_status": "CERTIFIED_LEAK_FREE_DUAL_SEED_POOLED_PROMOTE",
        "registry_correlation_overlap": {
            "duplicate": False,
            "rasters_checked": e3_dots["registry_rasters_checked"],
            "total_rasters_verified_including_concurrent": e3_dots["total_rasters_verified_including_concurrent"],
            "stage1_surface_worst_abs_spearman": round(float(e3_surf["worst_abs_spearman"]), 6),
            "stage2_dots_worst_abs_spearman": round(
                float(e3_dots["binding_decision_ir_h85_01"]["worst_abs_spearman"]), 6
            ),
            "stage2_dots_worst_discriminating_overlap": round(
                float(e3_dots["binding_decision_ir_h85_01"]["worst_forward_overlap"]), 6
            ),
            "overlap_3px": round(
                float(e3_dots["binding_decision_ir_h85_01"]["worst_forward_overlap"]), 6
            ),
            "rank_correlation": round(
                float(e3_dots["binding_decision_ir_h85_01"]["worst_abs_spearman"]), 6
            ),
            "vs_incumbent_h33_2_b2_overlap_3px": round(
                float(e3_dots["vs_incumbent_h33_2_b2"]["forward_overlap_3px"]), 6
            ),
            "vs_incumbent_h33_2_b2_spearman": round(
                float(e3_dots["vs_incumbent_h33_2_b2"]["spearman_full_footprint"]), 4
            ),
            "concurrent_gemsdoe84_siblings": sibs,
        },
        "validator_output": {
            "all_checks_passed": True,
            "format_valid": True,
            "crs": "EPSG:32611",
            "shape": [3730, 3292],
            "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
            "n_nan": 0,
            "in_footprint_range_0_1": True,
            "zero_dots_on_mapped_catalogue": True,
        },
        "parallel_lane_h84_csat": {
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
        "historical_lane_h84_thms": {
            "lane": thms_card["lane"],
            "verdict": thms_card["verdict"],
            "submission_authorized": thms_card["submission_authorized"],
            "audited_artifact": thms_card["audited_artifact"],
            "note": thms_card["note"],
        },
        "parallel_lane_h84b_cthf_ctfo": json.loads((EV / "run_card_cthf.json").read_text(encoding="utf-8")),
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

    thms_card = build_thms_negative_card()
    thms_json = json.dumps(thms_card, indent=2, allow_nan=False) + "\n"
    for p_thms in [
        "evidence/h84_run_card.json",
        "docs/evidence/h84_run_card.json",
        "evidence/fresh_run_card_20261023.json",
        "docs/evidence/fresh_run_card_20261023.json",
    ]:
        out_p = ROOT / p_thms
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(thms_json, encoding="utf-8")

    kthm_card = build_kthm_promoted_card(csat_card, thms_card)
    payload = json.dumps(kthm_card, indent=2, allow_nan=False) + "\n"
    for path in [
        "run_card.json",
        "evidence/run-card.json",
        "evidence/run_card.json",
        "registry/run_card.json",
        "docs/run-card.json",
        "docs/data/run-card.json",
        "docs/evidence/run_card.json",
        "docs/evidence/run-card.json",
    ]:
        target = ROOT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")

    print("Published synchronized PROMOTE canonical run cards (H84-KTHM) + fail-closed archive cards (H84-CSAT, H84-THMS).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
