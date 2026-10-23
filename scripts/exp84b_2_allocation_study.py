#!/usr/bin/env python3
"""EXP-84B-2: Paired post-surface DTI allocation comparison on the frozen
EXP-84B-1 out-of-fold probability surfaces (seeds 20, 21; 22,893 withheld positives).

Compares four emission/allocation arms using shared vendor/gems57 tools:
  1. incumbent_h33_b2_recipe  : H33-2-B2 baseline (fairly masked to visible faults)
  2. alloc_fixed_nms3_37k     : Fixed sep=3 px greedy NMS thinning (37,654 dots, H33-style)
  3. alloc_iso_patient        : Isotropic d>2 px + template emit.allocate_patient on p_tcdh
  4. alloc_aniso_patient      : Anisotropic tip-preserving mask + calibrated emit.allocate_patient
  5. alloc_aniso_phys_sup     : Anisotropic mask + supremum blind-crest fusion max(p_tcdh_gated, gamma*p_blind_crest)
                                + template emit.allocate_patient (balances relay/tip + off-collar blind discovery)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]

from gems57 import emit, evaluate_holdout, holdout  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems84 import tcdh  # noqa: E402
from gems84.paths import BRIDGE, DATA as DATA_DIR  # noqa: E402

SEEDS = (20, 21)


def build_supremum_surface(
    fp: np.ndarray,
    raw_stage_b_fp: np.ndarray,
    phys_prob_fp: np.ndarray,
    phys_r1_fp: np.ndarray,
    phys_r2_fp: np.ndarray,
    d1_fp: np.ndarray,
) -> np.ndarray:
    """Fuse inner-holdout structural-physics posterior with sharp Stage-A blind crests.

    - Requires stronger local physical corroboration on near-collar cells so featureless
      alluvial halos are suppressed, while allowing strong multi-altitude/hydrothermal/scarp
      blind ridges at d > 8 px to clear the marginal DTI bar.
    """
    p_med = max(float(np.median(phys_prob_fp)), 1e-5)
    phys_rel = np.clip(phys_prob_fp / p_med, 0.20, 5.0)
    crest = np.clip(0.52 + 0.28 * phys_r1_fp + 0.16 * phys_r2_fp, 0.30, 2.20)

    # Strongly gate near-collar halo predictions by local physical crest evidence
    p_struct_phys = raw_stage_b_fp * (0.30 + 0.70 * np.sqrt(phys_rel)) * crest

    # Off-collar blind discovery floor along sharp multi-physics crests (d1 > 7 px)
    off_w = np.clip((d1_fp - 6.0) / 8.0, 0.0, 1.0)
    p_blind_crest = 0.30 * phys_prob_fp * np.clip(0.35 + 0.40 * phys_r1_fp + 0.22 * phys_r2_fp, 0.20, 2.40) * off_w

    fused = np.maximum(p_struct_phys, p_blind_crest)
    # Calibrate total mass to 1.12x Stage-B unmapped-component mass (optimal expected |G| scale)
    target_mass = 1.12 * float(raw_stage_b_fp.sum())
    cur_mass = float(fused.sum())
    if cur_mass > 0:
        fused = fused * (target_mass / cur_mass)
    p2d = np.zeros(fp.shape, np.float32)
    p2d[fp] = np.clip(fused, 0.0, 1.0).astype(np.float32)
    return p2d


def main() -> int:
    t0 = time.time()
    data_dir = Path(os.environ.get("GEMS84_DATA", str(DATA_DIR)))
    work_dir = data_dir / "work"
    grid = load_grid(BRIDGE)
    fp = grid.footprint

    with rasterio.open(data_dir / "ref_rasters" / "GEMSDOE25__dotted-h19-5-d2-8.tif") as src:
        a = src.read(1)
        d28_dots = np.isfinite(a) & (a > 0) & fp

    X_phys = np.load(work_dir / "tcdh_phys_v1.npy", mmap_mode="r")
    X_base19 = np.load(work_dir / "tcdh_base19_v1.npy", mmap_mode="r")
    blind_basin_fp = tcdh.concealed_blind_basin_score_fp(X_phys, X_base19)

    arm_names = (
        "incumbent_h33_b2_recipe",
        "ctrl_b19_nms3_37k",
        "alloc_fixed_nms3_37k",
        "alloc_twostrat_nms3_39k",
        "alloc_iso_patient",
        "alloc_aniso_patient",
        "alloc_aniso_phys_sup",
    )
    terms = {a: [] for a in arm_names}
    per_fold = []
    dot_dist_share = {a: {"le_6px": 0, "6_to_15px": 0, "gt_15px": 0, "total": 0} for a in arm_names}
    dist_bins = [(1, 3), (3, 6), (6, 12), (12, 25), (25, 9999)]
    dist_cov = {a: {f"{lo}_{hi}px": [0.0, 0] for lo, hi in dist_bins} for a in arm_names}

    for seed in SEEDS:
        folds, _ = holdout.buffered_component_draw(grid, seed=seed, hide_frac=0.20, buffer_px=3)
        visible = folds[0]["visible"]
        dvis = ndi.distance_transform_edt(~visible)

        zc = np.load(work_dir / f"exp84b1_oof_seed{seed}.npz")
        p_tcdh_2d = np.zeros(fp.shape, np.float32)
        p_tcdh_2d[fp] = zc["p_tcdh_fp"]
        p_b19_2d = np.zeros(fp.shape, np.float32)
        p_b19_2d[fp] = zc["p_b19_fp"]
        raw_sb = zc["raw_stage_b_fp"]
        phys_prob = zc["phys_prob_fp"]
        phys_r1 = zc["phys_r1_fp"]
        phys_r2 = zc["phys_r2_fp"]
        d1_fp = zc["d1_fp"]
        dperp_fp = zc["dperp_fp"]
        dpar_fp = zc["dpar_fp"]

        allowed_iso = fp & ~visible & (dvis > 2.0)
        allowed_aniso = tcdh.anisotropic_allowed_mask(
            fp, visible, d1_fp, dperp_fp, dpar_fp, phys_prob, lateral_collar_px=2.0
        )

        # Control: Base-19 + anatomy under identical sep=3 px 37,654-dot NMS allocator
        em_b19_nms3 = tcdh.greedy_thin_fixed_sep(p_b19_2d, allowed_aniso, max_dots=37_654, sep_px=3)

        # Arm 2: Fixed sep=3 px greedy NMS thinning (37,654 dots, unstratified)
        em_nms3 = tcdh.greedy_thin_fixed_sep(p_tcdh_2d, allowed_aniso, max_dots=37_654, sep_px=3)

        # Arm 2b: Two-stratum sep=3 px NMS (24,500 LOQO corridor/relay/tip + 14,500 concealed blind basin = 39,000 dots)
        em_twostrat, _ = tcdh.emit_twostrat_nms3(
            fp, visible, p_tcdh_2d[fp], phys_prob, blind_basin_fp,
            d1_fp, dperp_fp, dpar_fp, n_corridor=24_500, n_far_blind=14_500,
            far_min_dist_px=36.0, sep_px=3,
        )

        # Arm 3: Isotropic d>2 px + template emit.allocate_patient
        al_iso = emit.allocate_patient(
            p_tcdh_2d, allowed_iso, k_truth=float(p_tcdh_2d[allowed_iso].sum()),
            floor=0.015, max_dots=65_000, patience=80_000,
        )

        # Arm 4: Anisotropic tip-preserving mask + calibrated k_truth scale (0.85 * sum -> tighter precision bar)
        al_aniso = emit.allocate_patient(
            p_tcdh_2d, allowed_aniso, k_truth=0.82 * float(p_tcdh_2d[allowed_aniso].sum()),
            floor=0.015, max_dots=60_000, patience=80_000,
        )

        # Arm 5: Anisotropic tip-preserving + blind-crest supremum posterior + emit.allocate_patient
        p_sup_2d = build_supremum_surface(fp, raw_sb, phys_prob, phys_r1, phys_r2, d1_fp)
        al_sup = emit.allocate_patient(
            p_sup_2d, allowed_aniso, k_truth=0.82 * float(p_sup_2d[allowed_aniso].sum()),
            floor=0.015, max_dots=60_000, patience=80_000,
        )

        arms = {
            "incumbent_h33_b2_recipe": d28_dots & (dvis > 2.0) & ~visible,
            "ctrl_b19_nms3_37k": em_b19_nms3,
            "alloc_fixed_nms3_37k": em_nms3,
            "alloc_twostrat_nms3_39k": em_twostrat,
            "alloc_iso_patient": al_iso.emitted,
            "alloc_aniso_patient": al_aniso.emitted,
            "alloc_aniso_phys_sup": al_sup.emitted,
        }

        for arm, pred in arms.items():
            dv = dvis[pred]
            dot_dist_share[arm]["le_6px"] += int((dv <= 6.0).sum())
            dot_dist_share[arm]["6_to_15px"] += int(((dv > 6.0) & (dv <= 15.0)).sum())
            dot_dist_share[arm]["gt_15px"] += int((dv > 15.0).sum())
            dot_dist_share[arm]["total"] += int(dv.size)

        for f in folds:
            active_f = fp & f["region"] & ~f["masked_known"]
            truth_f = f["truth"] & active_f
            for arm, pred in arms.items():
                res, t = evaluate_holdout.evaluate(pred.astype(np.float32), f, fp, block_side=200)
                terms[arm].append(t)
                per_fold.append(dict(
                    seed=seed, fold=f["name"], arm=arm,
                    dti=float(res["dti"]), tp=float(res["tp"]), fp=float(res["fp"]),
                    fn=float(res["fn"]), n_truth=int(res["n_truth"]), n_emitted=int(res["n_emitted"]),
                ))
                pred_act = pred & active_f
                if pred_act.any() and truth_f.any():
                    dp = ndi.distance_transform_edt(~pred_act)
                    kcov = np.maximum(1.0 - dp / 3.0, 0.0)
                    for lo, hi in dist_bins:
                        bm = truth_f & (dvis > lo) & (dvis <= hi)
                        if bm.any():
                            dist_cov[arm][f"{lo}_{hi}px"][0] += float(kcov[bm].sum())
                            dist_cov[arm][f"{lo}_{hi}px"][1] += int(bm.sum())

        print(f"[EXP-84B-2] Seed {seed} evaluated: " + ", ".join(f"{a}={int(arms[a].sum()):,}" for a in arm_names))

    stacked = {a: np.vstack(v) for a, v in terms.items()}
    # Select best H84-B allocator by pooled HOLDOUT-DTI
    cand_arms = ["alloc_fixed_nms3_37k", "alloc_iso_patient", "alloc_aniso_patient", "alloc_aniso_phys_sup"]
    best_cand = max(cand_arms, key=lambda a: float(evaluate_holdout.from_terms(stacked[a].sum(axis=0))))

    pooled = evaluate_holdout.pooled_summary(
        stacked, draws=1000, seed=520810, candidate=best_cand,
    )
    pooled_twostrat = evaluate_holdout.pooled_summary(
        stacked, draws=1000, seed=520810, candidate="alloc_twostrat_nms3_39k",
    )
    pooled_sup = evaluate_holdout.pooled_summary(
        stacked, draws=1000, seed=520810, candidate="alloc_aniso_phys_sup",
    )

    dot_share_summary = {}
    for a, d in dot_dist_share.items():
        tot = max(d["total"], 1)
        dot_share_summary[a] = {
            "mean_dots_per_seed": round(d["total"] / len(SEEDS), 1),
            "frac_le_6px": round(d["le_6px"] / tot, 4),
            "frac_6_to_15px": round(d["6_to_15px"] / tot, 4),
            "frac_gt_15px": round(d["gt_15px"] / tot, 4),
        }

    dist_summary = {
        arm: {
            bk: {
                "covered_tp": round(vals[0], 2),
                "n_truth": int(vals[1]),
                "kernel_recall": round(vals[0] / max(vals[1], 1), 4),
            }
            for bk, vals in bins_d.items()
        }
        for arm, bins_d in dist_cov.items()
    }

    out = {
        "experiment_id": "EXP-84B-2",
        "lane": "H84-B (H84-TCDH)",
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": evaluate_holdout.VERSION,
        "split_version": "buffered-whole-components-loqo-v2",
        "seeds": list(SEEDS),
        "withheld_positive_pixels": int(stacked[best_cand][:, 3].sum()),
        "best_allocator_by_holdout_dti": best_cand,
        "promoted_uniqueness_safe_allocator": "alloc_twostrat_nms3_39k",
        "pooled_best_candidate": pooled,
        "pooled_twostrat_nms3_39k": pooled_twostrat,
        "pooled_aniso_phys_sup": pooled_sup,
        "dot_distance_distribution": dot_share_summary,
        "distance_stratified_recall": dist_summary,
        "per_fold": per_fold,
        "elapsed_s": round(time.time() - t0, 2),
    }
    out_path = ROOT / "evidence" / "exp84b2_allocation.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n")

    print(f"\n=== EXP-84B-2 ALLOCATION COMPARISON (best = {best_cand}) ===")
    for k, v in pooled["scores"].items():
        sh = dot_share_summary[k]
        print(
            f"  {k:26s}: HOLDOUT-DTI = {v['dti']:.4f}  95% CI {v['ci95']}  "
            f"| dots/seed={sh['mean_dots_per_seed']:7.0f} (<=6px:{sh['frac_le_6px']:.1%}, 6-15px:{sh['frac_6_to_15px']:.1%}, >15px:{sh['frac_gt_15px']:.1%})"
        )
    for k, v in pooled["paired_differences"].items():
        print(f"  Delta ({best_cand} - {k:24s}): {v['delta']:+.4f}  95% CI {v['ci95']}")
    inc_d = pooled_twostrat["paired_differences"]["incumbent_h33_b2_recipe"]
    print(f"  Delta (alloc_twostrat_nms3_39k - incumbent_h33_b2_recipe): {inc_d['delta']:+.4f}  95% CI {inc_d['ci95']}")
    print(f"  Saved {out_path} in {out['elapsed_s']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
