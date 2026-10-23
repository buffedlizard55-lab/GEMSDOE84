#!/usr/bin/env python3
"""Publish synchronized fail-closed run cards across GEMSDOE84, uniting:
  - Lane H84-B (CTHF + CTFO: Crack-Tip Hydrothermal-Geopotential Posterior + Comonotonic 1D-Trace Fractional Optimization)
  - Lane H84-CSAT (Dual-Habitat 3D Contact-Depth + Counterfactual Strain-Transfer)
  - Repository-wide audited release gate (registry/release_status.json)

Never synthesizes automatic slot authorization (submission_slots_used = 0).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"


def build_cthf_card() -> dict:
    can = json.loads((EV / "h84b_leakage_canaries.json").read_text(encoding="utf-8"))
    abl = json.loads((EV / "h84b_holdout_ablation.json").read_text(encoding="utf-8"))
    uni = json.loads((EV / "h84b_uniqueness_audit.json").read_text(encoding="utf-8"))
    val = json.loads((EV / "h84b_validator_receipt.json").read_text(encoding="utf-8"))

    pooled = abl["pooled_evaluation"]
    sc = pooled["scores"]
    diffs = pooled["paired_differences"]
    prod = abl["production_regime_and_blind_sgmc"]
    inc_a = json.loads((EV / "incumbent_anatomy.json").read_text(encoding="utf-8"))

    sub_name = "gemsdoe84-cthf-ctfo-20261023T013252Z-8c0b5a8b-zeros"
    sub_note = (
        "GEMSDOE84 H84-B CTHF+CTFO: FFT upward-continued pullback + "
        "GDR-1391 F2mDAB/sinter + crack-tip relay + Dinkelbach 1D-trace dots"
    )
    assert len(sub_note) <= 140

    s_uni = uni["pre_placement_surface"]
    d_uni = uni["final_dot_raster"]
    s_dec = s_uni["decision"]
    d_dec = d_uni["binding_decision"]
    d_sum = d_uni["summary"]
    surf_ok = not bool(s_dec["duplicate"])
    dots_ok = not bool(d_dec["duplicate"])
    canary_ok = bool(can["passed"])
    holdout_ok = bool(diffs["incumbent_recipe"]["delta"] > 0.0 and diffs["incumbent_recipe"]["ci95"][0] > 0.0)
    format_ok = bool(val["format_valid"])
    promote = bool(canary_ok and surf_ok and dots_ok and holdout_ok and format_ok)
    verdict = "promote" if promote else "negative"

    blockers = []
    if not dots_ok:
        blockers.append(
            "Protocol Rule 1 asymmetric forward 3-px overlap exceeded 0.70 against multi-lane "
            f"corridor priors ({d_dec['worst_forward_overlap']:.4f}) despite "
            f"byte_unique=True, pixel_unique=True, max exact Jaccard={d_sum['worst_jaccard_dot_sets']:.4f}, "
            "max surface |Spearman|=0.6953 <= 0.90, max dot |Spearman|=0.1086 <= 0.90, and "
            "38.26% 3-px overlap against live incumbent h33-2-b2 (61.7% novel dots)."
        )

    return {
        "schema_version": "gemsdoe84-run-card-v2",
        "run_id": sub_name,
        "lane": "Lane H84-B — Crack-Tip Hydrothermal-Geopotential Posterior (CTHF) + Comonotonic 1D-Trace Fractional Optimization (CTFO)",
        "hypothesis": (
            "H84-B (CTHF + CTFO): Unmapped Basin-and-Range geothermal faults in GeoDAWN are discoverable "
            "by fusing (1) multi-altitude FFT upward-continued magnetic/gravity tilt worms pulled back updip "
            "to footwall subcrop with 1 m LiDAR / 10 m fluvial chi scarps, (2) DOE GDR-1391 2 m temperature "
            "probes (F2mDAB), Quaternary sinter/travertine vents, and cationic/silica geothermometers, and "
            "(3) fold-visible crack-tip stress lobes & dilational relay bridges, then solving Charnes-Cooper "
            "fractional submodular allocation using comonotonic 1D cross-strike self-credit Q_1D-trace(x)."
        ),
        "mechanism": (
            "2-seed out-of-fold LightGBM + HistGradientBoosting ensemble over 57 non-catalogue geopotential, "
            "1m/10m tectonic geomorphology, and GDR-1391 hydrothermal features plus 27 fold-visible kinematic "
            "features, combined via Noisy-OR prior coupling and allocated by exact CELF Charnes-Cooper "
            "Dinkelbach optimization on the official 300 m triangular DTI kernel."
        ),
        "named_nonfault_mimic": (
            "Pleistocene Lake Lahontan wave-cut shoreline benches (~1,265-1,348 m ASL Sehoo highstand "
            "contour-parallel scarps) and lateral shallow thermal outflow plumes in piedmont gravels."
        ),
        "experiments_executed": 3,
        "budget_cap_respected": True,
        "leakage_canaries": {
            "evidence_class": "HOLDOUT-AUC-CANARY",
            "n_features_checked": can["n_features_checked"],
            "auc_threshold": can["threshold"],
            "max_single_feature_abs_auc": can["max_single_feature_auc"],
            "passed": canary_ok,
        },
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": pooled["evaluator_version"],
            "alpha": pooled["alpha"],
            "beta": pooled["beta"],
            "triangular_radius_m": pooled["triangular_radius_m"],
            "n_folds_pooled": 8,
            "withheld_positive_pixels": sc["EXP_84_3_CTHF_CTFO"]["withheld_positive_pixels"],
            "dti": sc["EXP_84_3_CTHF_CTFO"]["dti"],
            "ci95": sc["EXP_84_3_CTHF_CTFO"]["ci95"],
            "tpw": sc["EXP_84_3_CTHF_CTFO"]["tpw"],
            "fpw": sc["EXP_84_3_CTHF_CTFO"]["fpw"],
            "fnw": sc["EXP_84_3_CTHF_CTFO"]["fnw"],
            "all_arms": sc,
            "paired_differences_vs_exp_84_3": diffs,
            "blind_sgmc_validation": prod,
        },
        "incumbent_forensics": {
            "evidence_class": "OWNER-REPORTED-AND-GEOMETRIC-EXACT",
            "live_incumbent": "h33-h33-2-b2-zeros (GEMSDOE32)",
            "owner_reported_dti": inc_a["algebra"]["reported_s2"],
            "closed_form_covered_truth_T": inc_a["algebra"]["implied_TPw"],
            "closed_form_predicted_h33_dti": inc_a["algebra"]["predicted_s2_if_zero_credit"],
            "residual": inc_a["algebra"]["residual"],
        },
        "registry_correlation_overlap": {
            "evidence_class": "REGISTRY-MEASUREMENT",
            "non_sample_rasters_checked": d_sum["registry_rasters_checked"],
            "pre_placement_surface_passed": surf_ok,
            "pre_placement_surface_worst_abs_spearman": s_dec["worst_abs_spearman"],
            "final_dots_byte_unique": d_sum["byte_unique_among_checked"],
            "final_dots_pixel_unique": d_sum["pixel_unique_among_checked"],
            "final_dots_worst_abs_spearman": d_dec["worst_abs_spearman"],
            "final_dots_worst_jaccard": d_sum["worst_jaccard_dot_sets"],
            "final_dots_overlap_vs_h33_2_b2_3px": 0.382602,
            "final_dots_overlap_vs_h33_2_b2_1px": 0.024000,
            "final_dots_worst_forward_overlap_discriminating": d_dec["worst_forward_overlap"],
            "duplicate": bool(d_dec["duplicate"]),
        },
        "raster_sha256": val["sha256"],
        "decoded_array_sha256": d_sum["candidate_decoded_sha256"],
        "submission_file": f"docs/downloads/{sub_name}.tif",
        "submission_zip": f"docs/downloads/{sub_name}.zip",
        "submissions_dir_tif": f"submissions/{sub_name}.tif",
        "submissions_dir_zip": f"submissions/{sub_name}.zip",
        "submission_bytes": uni["writer_receipt"]["bytes"],
        "n_dots": prod["total_dots"],
        "dinkelbach_lambda_star": prod["dinkelbach_lambda"],
        "submission_name": sub_name,
        "note": sub_note,
        "note_chars": len(sub_note),
        "validator_output": val,
        "verdict": verdict,
        "download_allowed": True,
        "submission_authorized": promote,
        "approved_for_weekly_slot": promote,
        "submission_slots_used": 0,
        "promotion_blockers": blockers,
    }


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
    cthf_card = build_cthf_card()
    cthf_json = json.dumps(cthf_card, indent=2, allow_nan=False) + "\n"
    for p_cthf in [
        "registry/run_card_cthf.json",
        "evidence/run_card_cthf.json",
        "docs/evidence/run_card_cthf.json",
    ]:
        out_p = ROOT / p_cthf
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(cthf_json, encoding="utf-8")

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
        parallel_lane_h84b_cthf={
            "lane": cthf_card["lane"],
            "verdict": cthf_card["verdict"],
            "submission_authorized": cthf_card["submission_authorized"],
            "submission_slots_used": 0,
            "run_card": "evidence/run_card_cthf.json",
            "download_file": cthf_card["submission_file"],
            "download_zip": cthf_card["submission_zip"],
            "submission_name": cthf_card["submission_name"],
            "raster_sha256": cthf_card["raster_sha256"],
            "note": cthf_card["note"],
            "n_dots": cthf_card["n_dots"],
            "holdout_dti_cthf_ctfo": cthf_card["holdout_dti"]["all_arms"]["EXP_84_3_CTHF_CTFO"],
            "holdout_dti_eqbudget_37654": cthf_card["holdout_dti"]["all_arms"]["EXP_84_3_EQBUDGET_37654"],
            "paired_diff_vs_incumbent_recipe": cthf_card["holdout_dti"]["paired_differences_vs_exp_84_3"]["incumbent_recipe"],
            "promotion_blockers": cthf_card["promotion_blockers"],
        },
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
    print("Published synchronized NEGATIVE run cards (uniting Lane H84-B CTHF+CTFO & Lane H84-CSAT).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
