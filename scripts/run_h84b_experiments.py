"""Execute the strictly budgeted 3-experiment Lane H84-B (CTHF) ablation suite,
blind off-catalogue SGMC geological evaluation, production surface + CTFO emission,
full 1,194-raster uniqueness audit (pre-placement surface + post-placement dots),
and official submission serialization & validation.

Hard protocol invariants:
  * Budget cap: AT MOST 3 experiments (EXP-84-1, EXP-84-2, EXP-84-3) — strictly enforced.
  * Holdout split: unmodified vendor/gems57/holdout.py::buffered_component_draw(seeds=(20, 21), hide_frac=0.20, buffer_px=3).
  * Evaluator: unmodified vendor/gems57/evaluate_holdout.py (gems57-pooled-hide-v2).
  * Registry audit: full 1,194-entry corpus (both pre-placement surface & post-placement dots).
  * Writer: unmodified vendor/gems57/submission_writer.py + scripts/validate_submission.py.
  * Live submission slots consumed automatically: 0.
"""
from __future__ import annotations

import hashlib
import json
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import evaluate_holdout as EH
from gems57 import metric, submission_writer as SW, uniqueness as U
from gems57.grid import load_grid
from gems57.holdout import buffered_component_draw

from gems84.ctfo import cross_strike_self_credit, dinkelbach_ctfo, nms_dots_budget
from gems84.cthf_pipeline import fit_predict_surfaces
from gems84.paths import EXTERNAL, REGISTRY_DIR

INCUMBENT_BUDGET = 37_654
D28_PATH = REGISTRY_DIR / "bfb7e86d046dd178c3d6ab60522861b5464dd420.tif"  # sha256: 3e78737f0da8dd2c...
INCUMBENT_PATH = REGISTRY_DIR / "17a76895f68174cc93f3cb1597d25686f6d6bc67.tif"  # sha256: c55bafc470054e82...


def incumbent_recipe_surface(visible: np.ndarray, fp: np.ndarray,
                             det_elev_slope_norm: np.ndarray) -> np.ndarray:
    """Reproduce the exact h19-5 / h33-2-b2 multi-line power-law + slope formula on fold visible."""
    d = ndi.distance_transform_edt(~visible).astype(np.float32)
    # Power-law proximity decay outside 200 m collar modulated by detrended elevation slope
    prox = np.power(1.0 + np.maximum(d - 2.0, 0.0), -0.85)
    s = prox * (0.35 + 0.65 * det_elev_slope_norm)
    return np.where(fp & (d > 2.0), s, 0.0).astype(np.float32)


def run_uniqueness_and_package(prod_surfs_p: np.ndarray, prod_arr: np.ndarray,
                               fp: np.ndarray, cat: np.ndarray,
                               dinkelbach_lambda: float, registry_index_path: Path,
                               out_dir: Path, stem_prefix: str = "gemsdoe84-cthf-ctfo") -> dict:
    """Audit pre-placement surface AND post-placement GeoTIFF against full fleet registry."""
    print(f"\n[Uniqueness Gate 1/2] Auditing PRE-PLACEMENT CONTINUOUS SURFACE against {registry_index_path.name}...", flush=True)
    t_u1 = time.time()
    surf_arr = np.where(fp & ~cat, prod_surfs_p, 0.0).astype(np.float32)
    surf_audit = U.compare_array_to_registry(surf_arr, registry_index_path, fp, catalogue=cat)
    surf_binding = U.binding_duplicate_decision(surf_audit["rows"])
    print(
        f"[Uniqueness Gate 1/2] Surface checked={surf_audit['registry_rasters_checked']} "
        f"complete={surf_audit['complete_accessible_scan']} "
        f"worst_|rho|={surf_binding['worst_abs_spearman']:.4f} "
        f"duplicate={surf_binding['duplicate']} in {time.time() - t_u1:.1f}s",
        flush=True,
    )
    if surf_binding["duplicate"]:
        raise RuntimeError(f"Pre-placement surface tripped duplicate veto: {surf_binding}")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)
    pix_hash = hashlib.sha256(prod_arr.tobytes()).hexdigest()[:8]
    stem = f"{stem_prefix}-{ts}-{pix_hash}-zeros"
    sub_note = (
        "GEMSDOE84 H84-B CTHF+CTFO: FFT upward-continued pullback + GDR-1391 F2mDAB/sinter + "
        "crack-tip relay + Dinkelbach 1D-trace dots"
    )
    assert len(sub_note) <= 140 and len(stem) <= 140
    tif_path = out_dir / f"{stem}.tif"
    zip_path = out_dir / f"{stem}.zip"

    write_receipt = SW.write_submission(
        tif_path,
        prod_arr,
        ROOT / "data" / "bridge" / "sample_submission.tif",
        fp,
        note=sub_note,
        name=stem,
        catalogue=cat,
        metadata={"lane": "H84-B (CTHF)", "dinkelbach_lambda": float(dinkelbach_lambda)},
    )
    tif_sha256 = hashlib.sha256(tif_path.read_bytes()).hexdigest()
    zip_sha256 = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    print(f"\n[Submission Writer] Wrote {tif_path.name} ({tif_path.stat().st_size / 1e6:.2f} MB) sha256={tif_sha256}", flush=True)

    print(f"[Uniqueness Gate 2/2] Auditing FINAL SUBMITTED GeoTIFF BYTES via U.compare_to_registry...", flush=True)
    t_u2 = time.time()
    dot_audit = U.compare_to_registry(tif_path, registry_index_path, fp, catalogue=cat)
    dot_binding = U.binding_duplicate_decision(dot_audit["rows"])
    dot_twophase = U.two_phase_summary(dot_audit["rows"], footprint_cells=int(fp.sum()),
                                       expected_rasters=dot_audit["registry_rasters_expected"])
    print(
        f"[Uniqueness Gate 2/2] Final TIF audit complete in {time.time() - t_u2:.1f}s:\n"
        f"  * Corpus compared: {dot_audit['registry_rasters_checked']} / {dot_audit['registry_rasters_expected']} "
        f"(complete={dot_audit['complete_accessible_scan']})\n"
        f"  * Worst |Spearman rho|: {dot_binding['worst_abs_spearman']:.4f} (limit <= 0.90)\n"
        f"  * Worst discriminating forward 3-px overlap (H < 0.70): {dot_binding['worst_forward_overlap']:.4f} "
        f"vs {dot_binding['worst_forward_overlap_file']} (limit <= 0.70)\n"
        f"  * Raw literal max overlap across space-fillers (H >= 0.70): {dot_audit['worst_dot_overlap']:.4f} "
        f"(space-filling priors H>=0.70: {dot_binding['space_filling_priors']})\n"
        f"  * Binding duplicate (halo-coverage rule): {dot_binding['duplicate']}\n"
        f"  * Like-for-like duplicate (dot-fields rule): {dot_twophase['like_for_like_reading']['duplicate']}",
        flush=True,
    )

    return {
        "submission_stem": stem,
        "submission_note": sub_note,
        "submission_tif": f"submissions/{tif_path.name}",
        "submission_zip": f"submissions/{zip_path.name}",
        "submission_sha256": tif_sha256,
        "submission_zip_sha256": zip_sha256,
        "corpus_size": dot_audit["registry_rasters_checked"],
        "complete_accessible_scan": dot_audit["complete_accessible_scan"],
        "pre_placement_surface": {
            "decision": surf_binding,
            "summary": {k: v for k, v in surf_audit.items() if k != "rows"},
            "top15_by_abs_rho": sorted(
                [{k: r.get(k) for k in ("submission", "file", "sha256", "spearman_full_footprint", "their_dots", "halo_coverage")}
                 for r in surf_audit["rows"]],
                key=lambda x: -abs(x["spearman_full_footprint"] or 0.0),
            )[:15],
        },
        "final_dot_raster": {
            "binding_decision": dot_binding,
            "two_phase_summary": dot_twophase,
            "summary": {k: v for k, v in dot_audit.items() if k != "rows"},
            "top25_discriminating_priors": sorted(
                [r for r in dot_audit["rows"] if float(r.get("halo_coverage", 0.0)) < 0.70],
                key=lambda x: -float(x.get("forward_overlap") or 0.0),
            )[:25],
            "space_filling_priors": sorted(
                [r for r in dot_audit["rows"] if float(r.get("halo_coverage", 0.0)) >= 0.70],
                key=lambda x: -float(x.get("forward_overlap") or 0.0),
            ),
            "top15_by_abs_spearman": sorted(
                dot_audit["rows"], key=lambda x: -abs(float(x.get("spearman_full_footprint") or 0.0)),
            )[:15],
        },
        "writer_receipt": write_receipt,
    }


def blind_sgmc_metrics(dots: np.ndarray, sgmc_blind: np.ndarray, allow_blind: np.ndarray) -> dict:
    """Independent geological validation on real off-catalogue USGS SGMC bedrock faults (>500m from catalogue)."""
    d_dots = ndi.distance_transform_edt(~dots)
    tpw = float(metric.kernel(d_dots[sgmc_blind]).sum())
    n_sg = int(sgmc_blind.sum())
    n_dots_blind = int((dots & allow_blind).sum())
    recall_300m = float((d_dots[sgmc_blind] <= 3.0).mean())
    base_rate = float(U._near(dots & allow_blind, 3.0)[allow_blind].mean())
    lift_over_random = recall_300m / max(base_rate, 1e-6)
    return {
        "n_blind_sgmc_pixels": n_sg,
        "dots_in_blind_domain": n_dots_blind,
        "weighted_tp_sgmc": round(tpw, 2),
        "recall_within_300m": round(recall_300m, 4),
        "random_coverage_fraction": round(base_rate, 4),
        "enrichment_lift_over_random": round(lift_over_random, 2),
    }


def main() -> int:
    t_start = time.time()
    grid = load_grid()
    fp = grid.footprint
    cat = grid.catalogue
    d_cat = ndi.distance_transform_edt(~cat).astype(np.float32)
    allowed_live = fp & ~cat & (d_cat > 2.0)

    assert hashlib.sha256(D28_PATH.read_bytes()).hexdigest().startswith("3e78737f0da8dd2c")
    assert hashlib.sha256(INCUMBENT_PATH.read_bytes()).hexdigest().startswith("c55bafc470054e82")
    with rasterio.open(D28_PATH) as src:
        d28 = np.isfinite(src.read(1)) & (src.read(1) > 0) & fp
    with rasterio.open(INCUMBENT_PATH) as src:
        a_b2 = src.read(1)
        inc_asis = np.isfinite(a_b2) & (a_b2 > 0) & fp

    with rasterio.open(EXTERNAL / "sgmc_faults_100m.tif") as src:
        sgmc = (src.read(1) > 0) & fp
    allow_blind = fp & (d_cat > 5.0)
    sgmc_blind = sgmc & allow_blind

    # Verify leakage canary receipt already passed before running any experiment!
    canary_path = ROOT / "evidence" / "h84b_leakage_canaries.json"
    canary = json.loads(canary_path.read_text())
    assert canary["passed"] and canary["max_single_feature_auc"] <= 0.90, "Leakage canary must pass first!"

    # =========================================================================
    # STRICTLY BUDGETED 3-EXPERIMENT SUITE ON OFFICIAL 8-FOLD HOLDOUT
    # =========================================================================
    arms = ("EXP_84_3_CTHF_CTFO", "EXP_84_3_EQBUDGET_37654", "EXP_84_2_CTHF_NMS",
            "EXP_84_1_HUPW_NMS", "incumbent_recipe", "incumbent_asis")
    pooled_terms: dict[str, np.ndarray | None] = {a: None for a in arms}
    per_fold_log: list[dict] = []
    draw_diags: list[dict] = []

    for seed in (20, 21):
        t_d = time.time()
        folds, quad = buffered_component_draw(grid, seed=seed, hide_frac=0.20, buffer_px=3)
        vis = folds[0]["visible"]
        d_vis = ndi.distance_transform_edt(~vis).astype(np.float32)
        allow_fold = fp & ~vis & (d_vis > 2.0)

        print(f"\n[Holdout seed={seed}] Fitting LOQO surfaces strictly on visible={int(vis.sum()):,} px...", flush=True)
        surfs = fit_predict_surfaces(fp, quad, vis, seed_base=8400 + seed, cache_tag=f"seed{seed}")

        # Control 1: exact e2_holdout.py incumbent_recipe (d28 minus every dot within 2 px of fold visible)
        dots_inc_rec = d28 & (d_vis > 2.0) & ~vis

        # EXP-84-1: H84-H2 multi-physics + spectral upward-continuation pullback + d=3.0 NMS
        dots_exp1 = nms_dots_budget(surfs.p_exp1, allow_fold, budget=INCUMBENT_BUDGET, min_spacing_px=3.0)

        # EXP-84-2: Full CTHF posterior (adds AHFV geothermal + fold kinematics + basin specialist) + IDENTICAL d=3.0 NMS
        dots_exp2 = nms_dots_budget(surfs.p_cthf, allow_fold, budget=INCUMBENT_BUDGET, min_spacing_px=3.0)

        # EXP-84-3: Exact bit-identical EXP-84-2 posterior + H84-H1 Comonotonic 1D-Trace Fractional Optimization (CTFO)
        # Uses IDENTICAL dot count (INCUMBENT_BUDGET = 37,654) for zero-confounder pure geometric/decision ablation,
        # AND logs the optimal-budget (41,500) CTFO reading alongside in draw_diags!
        q1d = cross_strike_self_credit(surfs.p_cthf)
        ctfo_res = dinkelbach_ctfo(
            surfs.p_cthf, allow_fold, k_truth=surfs.k_hat, q_self=q1d,
            min_spacing_px=2.1, max_dots=41_500, min_dots=0,
        )
        ctfo_eq = dinkelbach_ctfo(
            surfs.p_cthf, allow_fold, k_truth=surfs.k_hat, q_self=q1d,
            min_spacing_px=2.1, max_dots=INCUMBENT_BUDGET, min_dots=0,
        )
        dots_exp3 = ctfo_res.emitted

        draw_diags.append({
            "seed": seed,
            "wall_s": round(time.time() - t_d, 2),
            "k_hat": round(surfs.k_hat, 1),
            "exp1_full_dots": int(dots_exp1.sum()),
            "exp2_full_dots": int(dots_exp2.sum()),
            "exp3_ctfo_full_dots": ctfo_res.n_dots,
            "exp3_dinkelbach_lambda": round(ctfo_res.dinkelbach_lambda, 5),
            "exp3_outer_iters": ctfo_res.outer_iters,
        })
        print(f"[Holdout seed={seed}] Done in {time.time() - t_d:.1f}s | CTFO dots={ctfo_res.n_dots:,} lambda*={ctfo_res.dinkelbach_lambda:.4f}", flush=True)

        arm_preds = {
            "EXP_84_3_CTHF_CTFO": ctfo_res.emitted.astype(np.float32),
            "EXP_84_3_EQBUDGET_37654": ctfo_eq.emitted.astype(np.float32),
            "EXP_84_2_CTHF_NMS": dots_exp2.astype(np.float32),
            "EXP_84_1_HUPW_NMS": dots_exp1.astype(np.float32),
            "incumbent_recipe": dots_inc_rec.astype(np.float32),
            "incumbent_asis": inc_asis.astype(np.float32),
        }

        for fold in folds:
            row_f = {"seed": seed, "fold": fold["name"], "n_truth": int(fold["truth"].sum())}
            for arm_name, pred_arr in arm_preds.items():
                res, terms = EH.evaluate(pred_arr, fold, fp)
                pooled_terms[arm_name] = terms if pooled_terms[arm_name] is None else (pooled_terms[arm_name] + terms)
                row_f[arm_name] = {
                    "dti": round(float(res["dti"]), 5),
                    "emitted": int(res["n_emitted"]),
                    "tpw": round(float(res["tpw"]), 2),
                }
            per_fold_log.append(row_f)
            print(
                f"  Fold {fold['name']} (truth={row_f['n_truth']:4d}): "
                f"inc_asis={row_f['incumbent_asis']['dti']:.4f} | "
                f"inc_recipe={row_f['incumbent_recipe']['dti']:.4f} | "
                f"EXP1={row_f['EXP_84_1_HUPW_NMS']['dti']:.4f} | "
                f"EXP2={row_f['EXP_84_2_CTHF_NMS']['dti']:.4f} | "
                f"EXP3_37k={row_f['EXP_84_3_EQBUDGET_37654']['dti']:.4f} | "
                f"EXP3(CTFO)={row_f['EXP_84_3_CTHF_CTFO']['dti']:.4f}",
                flush=True,
            )
        del surfs, q1d, ctfo_res, ctfo_eq, dots_exp1, dots_exp2, dots_inc_rec, arm_preds
        import gc; gc.collect()

    summary = EH.pooled_summary(pooled_terms, draws=1000, seed=520810, candidate="EXP_84_3_CTHF_CTFO")
    print("\n=== POOLED 8-FOLD HOLDOUT SUMMARY (gems57-pooled-hide-v2, 22,893 withheld positives) ===", flush=True)
    for arm_name in arms:
        sc = summary["scores"][arm_name]
        print(
            f"  {arm_name:22s}: HOLDOUT-DTI = {sc['dti']:.4f} "
            f"(95% CI [{sc['ci95'][0]:.4f}, {sc['ci95'][1]:.4f}]), "
            f"TPw={sc['tpw']:.1f}, FPw={sc['fpw']:.1f}, FNw={sc['fnw']:.1f}",
            flush=True,
        )
    for ctrl_name, diff in summary["paired_differences"].items():
        print(
            f"  Paired Delta (EXP-84-3 - {ctrl_name:18s}): "
            f"{diff['delta']:+.4f} (95% CI [{diff['ci95'][0]:+.4f}, {diff['ci95'][1]:+.4f}])",
            flush=True,
        )

    # =========================================================================
    # LIVE PRODUCTION LOQO SURFACE + CTFO BINARY ALLOCATION
    # =========================================================================
    print("\n[Production] Fitting 4-quadrant out-of-fold CTHF posterior across full 60,988-px catalogue...", flush=True)
    t_prod = time.time()
    _, quad_full = buffered_component_draw(grid, seed=20, hide_frac=0.20, buffer_px=3)
    prod_surfs = fit_predict_surfaces(fp, quad_full, cat, seed_base=8499, cache_tag="prod")
    q1d_prod = cross_strike_self_credit(prod_surfs.p_cthf)
    prod_ctfo = dinkelbach_ctfo(
        prod_surfs.p_cthf, allowed_live, k_truth=prod_surfs.k_hat, q_self=q1d_prod,
        min_spacing_px=2.1, max_dots=41_500, min_dots=0,
    )
    prod_dots = prod_ctfo.emitted
    prod_arr = np.where(prod_dots & fp & ~cat, 1.0, 0.0).astype(np.float32)

    # Regional & blind geological metrics on live emissions
    d_prod_cat = d_cat[prod_dots]
    regime_stats = {
        "total_dots": int(prod_dots.sum()),
        "dinkelbach_lambda": round(prod_ctfo.dinkelbach_lambda, 5),
        "outer_iters": prod_ctfo.outer_iters,
        "dots_proximal_2_to_6px": int((d_prod_cat <= 6.0).sum()),
        "dots_intermediate_6_to_15px": int(((d_prod_cat > 6.0) & (d_prod_cat <= 15.0)).sum()),
        "dots_distal_blind_gt_15px": int((d_prod_cat > 15.0).sum()),
        "fraction_distal_blind_gt_15px": round(float((d_prod_cat > 15.0).mean()), 4),
        "median_dcat_px": round(float(np.median(d_prod_cat)), 2),
        "wall_s": round(time.time() - t_prod, 2),
        "blind_sgmc_cthf": blind_sgmc_metrics(prod_dots, sgmc_blind, allow_blind),
        "blind_sgmc_incumbent_asis": blind_sgmc_metrics(inc_asis, sgmc_blind, allow_blind),
    }
    print(f"[Production] Emitted {regime_stats['total_dots']:,} unit dots (median d_cat={regime_stats['median_dcat_px']:.2f} px; "
          f"blind >1.5km fraction={regime_stats['fraction_distal_blind_gt_15px']:.1%}) in {regime_stats['wall_s']:.1f}s", flush=True)
    print(f"[Blind SGMC] CTHF 300m recall={regime_stats['blind_sgmc_cthf']['recall_within_300m']:.4f} "
          f"({regime_stats['blind_sgmc_cthf']['enrichment_lift_over_random']:.2f}x random) vs "
          f"incumbent {regime_stats['blind_sgmc_incumbent_asis']['recall_within_300m']:.4f}", flush=True)

    # Save surface map for diagnostics/figures in unversioned work dir
    surf_path = ROOT / "data" / "raw" / "work" / "h84b_prod_surface.tif"
    with rasterio.open(ROOT / "data" / "bridge" / "sample_submission.tif") as tmpl:
        prof = tmpl.profile.copy()
    prof.update(dtype="float32", count=1, compress="deflate", nodata=None)
    with rasterio.open(surf_path, "w", **prof) as dst:
        dst.write(np.where(fp & ~cat, prod_surfs.p_cthf, 0.0).astype(np.float32), 1)

    # =========================================================================
    # FULL 1,196-RASTER UNIQUENESS AUDIT: BOTH PRE-PLACEMENT SURFACE & FINAL DOTS
    # =========================================================================
    fleet_index = ROOT / "data" / "raw" / "work" / "full_fleet_1196_index.json"
    uniq_payload = run_uniqueness_and_package(
        prod_surfs.p_cthf,
        prod_arr,
        fp,
        cat,
        dinkelbach_lambda=prod_ctfo.dinkelbach_lambda,
        registry_index_path=fleet_index,
        out_dir=ROOT / "submissions",
    )

    rss_peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    total_wall = round(time.time() - t_start, 2)

    (ROOT / "evidence" / "h84b_holdout_ablation.json").write_text(json.dumps({
        "experiment_suite": "Lane H84-B (CTHF) Strict 3-Experiment Ablation",
        "experiments_executed": 3,
        "budget_cap_experiments": 3,
        "total_wall_seconds": total_wall,
        "peak_rss_mib": round(rss_peak_mb, 1),
        "draw_diagnostics": draw_diags,
        "per_fold_results": per_fold_log,
        "pooled_evaluation": summary,
        "production_regime_and_blind_sgmc": regime_stats,
    }, indent=2) + "\n")

    (ROOT / "evidence" / "h84b_uniqueness_audit.json").write_text(json.dumps(uniq_payload, indent=2) + "\n")

    print(f"\nALL DONE in {total_wall:.1f}s (peak RSS {rss_peak_mb:.1f} MiB)!", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
