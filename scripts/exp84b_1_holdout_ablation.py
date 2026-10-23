#!/usr/bin/env python3
"""EXP-84B-1: Single-feature holdout leakage canary + 4-quadrant LOQO ablation
for Lane H84-B (H84-TCDH) on the shared buffered component holdout (seeds 20, 21).

Uses shared template vendor/gems57 (unmodified):
  * holdout.buffered_component_draw (whole 8-connected components, buffer_px=3)
  * emit.allocate_patient           (expected-kernel-credit greedy DTI bar)
  * evaluate_holdout.evaluate / pooled_summary (gems57-pooled-hide-v2, 20 km block bootstrap)
"""
from __future__ import annotations

import gc
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
from gems84.paths import BRIDGE, DATA as DATA_DIR, WORK  # noqa: E402

SEEDS = (20, 21)
CANARY_CEILING = 0.90


def exact_auc(score: np.ndarray, pos_mask: np.ndarray, neg_mask: np.ndarray) -> float:
    s = np.concatenate([score[pos_mask], score[neg_mask]]).astype(np.float64)
    n1 = int(pos_mask.sum())
    n0 = int(neg_mask.sum())
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(s.size, np.float64)
    ranks[order] = np.arange(1, s.size + 1, dtype=np.float64)
    _, inv, cnt = np.unique(s, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=ranks)
    ranks = (sums / cnt)[inv]
    return float((ranks[:n1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def _load_ref_dots(data_dir: Path, name: str, fp: np.ndarray) -> np.ndarray:
    cands = [
        data_dir / "ref_rasters" / name,
        data_dir / "registry" / name,
    ]
    for p in cands:
        if p.exists():
            with rasterio.open(p) as src:
                a = src.read(1)
            return np.isfinite(a) & (a > 0) & fp
    # Fallback search in registry dir by prefix
    prefix = name.split("__")[0] + "__" + name.split("__")[1][:18]
    for p in sorted((data_dir / "registry").glob(f"{prefix}*.tif")):
        with rasterio.open(p) as src:
            a = src.read(1)
        return np.isfinite(a) & (a > 0) & fp
    raise FileNotFoundError(f"Reference raster {name} not found under {data_dir}")


def main() -> int:
    t0 = time.time()
    data_dir = Path(os.environ.get("GEMS84_DATA", str(DATA_DIR)))
    work_dir = data_dir / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"[EXP-84B-1] Verifying SHA-256 digests and building/loading physics stack from {data_dir}...")
    grid = load_grid(BRIDGE)
    fp = grid.footprint
    X_phys, X_base19, geo_s2, geo_c2 = tcdh.build_or_load_physics_stack(data_dir, work_dir, fp)
    sense_src = tcdh.load_trace_sense_raster(data_dir / "external", fp.shape)
    print(f"[EXP-84B-1] Physics stack ready in {time.time() - t0:.1f}s: X_phys={X_phys.shape}, X_base19={X_base19.shape}")

    d28_dots = _load_ref_dots(data_dir, "GEMSDOE25__dotted-h19-5-d2-8.tif", fp)
    b2_dots = _load_ref_dots(data_dir, "GEMSDOE32__h33-2-b2-zeros.tif", fp)

    arm_names = (
        "incumbent_h33_b2_recipe",
        "ctrl_phys_blind_only",
        "ctrl_base19_anat",
        "h84b_tcdh_full",
    )
    terms = {a: [] for a in arm_names}
    per_fold = []
    canary_by_feat: dict[str, list[float]] = {}
    dist_bins = [(3, 6), (6, 12), (12, 25), (25, 9999)]
    dist_cov = {a: {f"{lo}_{hi}px": [0.0, 0] for lo, hi in dist_bins} for a in arm_names}

    for seed in SEEDS:
        ts = time.time()
        folds, quad = holdout.buffered_component_draw(grid, seed=seed, hide_frac=0.20, buffer_px=3)
        visible = folds[0]["visible"]
        dvis = ndi.distance_transform_edt(~visible)

        # 1. Single-feature holdout leakage canary across all 36 PHYS + 16 ANAT features
        Xa_vis, d1_fp, dperp_fp, dpar_fp = tcdh.compute_visible_anatomy_fp(visible, fp, sense_src)
        regions = np.zeros(fp.shape, bool)
        for f in folds:
            regions |= f["region"]
        act_fp = (regions & fp & ~folds[0]["masked_known"])[fp]
        pos_fp = (folds[0]["hidden_all"] & regions)[fp] & act_fp
        neg_all = np.flatnonzero(act_fp & ~pos_fp)
        rng = np.random.default_rng(seed + 840)
        neg_sub = rng.choice(neg_all, min(400_000, neg_all.size), replace=False)
        neg_fp = np.zeros(act_fp.size, bool)
        neg_fp[neg_sub] = True

        for j, name in enumerate(tcdh.PHYS_FEATURES):
            a = exact_auc(X_phys[:, j], pos_fp, neg_fp)
            canary_by_feat.setdefault(name, []).append(max(a, 1.0 - a))
        for j, name in enumerate(tcdh.ANAT_FEATURES):
            a = exact_auc(Xa_vis[:, j], pos_fp, neg_fp)
            canary_by_feat.setdefault(name, []).append(max(a, 1.0 - a))

        max_canary_draw = max(v[-1] for v in canary_by_feat.values())
        print(f"[EXP-84B-1] Seed {seed}: max single-feature symmetric AUC = {max_canary_draw:.4f} (ceiling {CANARY_CEILING})")
        if max_canary_draw > CANARY_CEILING:
            raise RuntimeError(f"LEAKAGE CANARY TRIPPED on seed {seed}: {max_canary_draw:.4f} > {CANARY_CEILING}")

        oof_cache = work_dir / f"exp84b1_oof_seed{seed}.npz"
        p_blind_2d = np.zeros(fp.shape, np.float32)
        p_b19_anat_2d = np.zeros(fp.shape, np.float32)
        p_tcdh_2d = np.zeros(fp.shape, np.float32)

        if oof_cache.exists() and oof_cache.stat().st_size > 1_000_000:
            print(f"[EXP-84B-1] Seed {seed}: loading cached OOF surfaces from {oof_cache.name}...")
            zc = np.load(oof_cache)
            p_blind_2d[fp] = zc["p_blind_fp"]
            p_b19_anat_2d[fp] = zc["p_b19_fp"]
            p_tcdh_2d[fp] = zc["p_tcdh_fp"]
            del zc
        else:
            # 2. Fit 4-quadrant LOQO models strictly on visible faults (zero access to hidden truth)
            oof_a_tcdh = tcdh.fit_predict_stage_a_loqo(X_phys, fp, quad, visible, seed=84 + seed)
            p_blind_fp = np.clip(
                0.22 * oof_a_tcdh[:, 0] * np.clip(0.55 + 0.25 * oof_a_tcdh[:, 1] + 0.15 * oof_a_tcdh[:, 2], 0.35, 2.0),
                0.0, 1.0,
            ).astype(np.float32)
            p_blind_2d[fp] = p_blind_fp

            oof_a_b19 = tcdh.fit_predict_stage_a_loqo(X_base19, fp, quad, visible, seed=184 + seed)
            p_b19_anat_2d, _ = tcdh.fit_predict_stage_b_loqo(
                X_base19, oof_a_b19, fp, quad, visible, sense_src,
                seed=84 + seed, phys_idx=tuple(range(19)), Xa_outer=Xa_vis,
            )

            p_tcdh_2d, raw_stage_b_fp = tcdh.fit_predict_stage_b_loqo(
                X_phys, oof_a_tcdh, fp, quad, visible, sense_src,
                seed=84 + seed, Xa_outer=Xa_vis,
            )

            tmp_cache = work_dir / f"exp84b1_oof_seed{seed}.tmp.npz"
            np.savez_compressed(
                tmp_cache,
                p_blind_fp=p_blind_fp,
                p_b19_fp=p_b19_anat_2d[fp],
                p_tcdh_fp=p_tcdh_2d[fp],
                raw_stage_b_fp=raw_stage_b_fp,
                phys_prob_fp=oof_a_tcdh[:, 0],
                phys_r1_fp=oof_a_tcdh[:, 1],
                phys_r2_fp=oof_a_tcdh[:, 2],
                d1_fp=d1_fp,
                dperp_fp=dperp_fp,
                dpar_fp=dpar_fp,
            )
            tmp_cache.replace(oof_cache)
            del oof_a_tcdh, oof_a_b19, p_blind_fp, raw_stage_b_fp

        # Shared fixed emission rule for EXP-84B-1 model ablation:
        # template emit.allocate_patient on allowed = fp & ~visible & (dvis > 2)
        allowed_iso = fp & ~visible & (dvis > 2.0)
        alloc_blind = emit.allocate_patient(
            p_blind_2d, allowed_iso, k_truth=float(p_blind_2d[allowed_iso].sum()),
            floor=0.012, max_dots=65_000, patience=80_000,
        )
        alloc_b19 = emit.allocate_patient(
            p_b19_anat_2d, allowed_iso, k_truth=float(p_b19_anat_2d[allowed_iso].sum()),
            floor=0.015, max_dots=65_000, patience=80_000,
        )
        alloc_tcdh = emit.allocate_patient(
            p_tcdh_2d, allowed_iso, k_truth=float(p_tcdh_2d[allowed_iso].sum()),
            floor=0.015, max_dots=65_000, patience=80_000,
        )

        arms = {
            "incumbent_h33_b2_recipe": d28_dots & (dvis > 2.0) & ~visible,
            "ctrl_phys_blind_only": alloc_blind.emitted,
            "ctrl_base19_anat": alloc_b19.emitted,
            "h84b_tcdh_full": alloc_tcdh.emitted,
        }

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
                # Distance-stratified kernel coverage
                pred_act = pred & active_f
                if pred_act.any() and truth_f.any():
                    dp = ndi.distance_transform_edt(~pred_act)
                    kcov = np.maximum(1.0 - dp / 3.0, 0.0)
                    for lo, hi in dist_bins:
                        bm = truth_f & (dvis > lo) & (dvis <= hi)
                        if bm.any():
                            dist_cov[arm][f"{lo}_{hi}px"][0] += float(kcov[bm].sum())
                            dist_cov[arm][f"{lo}_{hi}px"][1] += int(bm.sum())

        print(
            f"[EXP-84B-1] Seed {seed} done in {time.time() - ts:.1f}s | dots: "
            + ", ".join(f"{a}={int(arms[a].sum()):,}" for a in arm_names)
        )
        del Xa_vis, p_blind_2d, p_b19_anat_2d, p_tcdh_2d
        gc.collect()

    stacked = {a: np.vstack(v) for a, v in terms.items()}
    pooled = evaluate_holdout.pooled_summary(
        stacked,
        draws=1000,
        seed=520810,
        candidate="h84b_tcdh_full",
    )

    canary_summary = {
        k: {"mean_sym_auc": float(np.mean(v)), "max_sym_auc": float(np.max(v)), "by_seed": [float(x) for x in v]}
        for k, v in canary_by_feat.items()
    }
    top_canaries = sorted(canary_summary.items(), key=lambda kv: -kv[1]["max_sym_auc"])[:10]

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
        "experiment_id": "EXP-84B-1",
        "lane": "H84-B (H84-TCDH)",
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": evaluate_holdout.VERSION,
        "split_version": "buffered-whole-components-loqo-v2",
        "seeds": list(SEEDS),
        "withheld_positive_pixels": int(stacked["h84b_tcdh_full"][:, 3].sum()),
        "spatial_bootstrap_cluster_m": 20_000,
        "bootstrap_draws": 1000,
        "canary_gate": {
            "ceiling": CANARY_CEILING,
            "passed": True,
            "n_features_checked": len(canary_summary),
            "max_symmetric_auc": float(top_canaries[0][1]["max_sym_auc"]),
            "max_feature": top_canaries[0][0],
            "top_10_features": [{"feature": k, **v} for k, v in top_canaries],
            "all_features": canary_summary,
        },
        "pooled": pooled,
        "prior_lane_baseline_reference": {
            "h84a_liti_pooled_dti": 0.008667,
            "incumbent_asis_handicapped_dti": float(
                evaluate_holdout.from_terms(
                    np.vstack([
                        evaluate_holdout.evaluate(b2_dots.astype(np.float32), f, fp, block_side=200)[1]
                        for s in SEEDS
                        for f in holdout.buffered_component_draw(grid, seed=s, hide_frac=0.20, buffer_px=3)[0]
                    ]).sum(axis=0)
                )
            ),
        },
        "distance_stratified_recall": dist_summary,
        "per_fold": per_fold,
        "elapsed_s": round(time.time() - t0, 2),
    }

    out_path = ROOT / "evidence" / "exp84b1_ablation.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n")
    print("\n=== EXP-84B-1 POOLED HOLDOUT-DTI SUMMARY ===")
    for k, v in pooled["scores"].items():
        print(f"  {k:26s}: HOLDOUT-DTI = {v['dti']:.4f}  95% CI {v['ci95']}  (TP={v['tpw']:.1f}, FP={v['fpw']:.1f})")
    for k, v in pooled["paired_differences"].items():
        print(f"  Delta (h84b_tcdh_full - {k:24s}): {v['delta']:+.4f}  95% CI {v['ci95']}")
    print(f"  Saved {out_path} in {out['elapsed_s']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
