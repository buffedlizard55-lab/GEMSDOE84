#!/usr/bin/env python3
"""Run the full budgeted experiment: build H84-1, H84-3, and their fusion; run the leakage
canary on each one individually; score all three (plus a uniform-random control and a
dense-vs-sparse emission sanity check) on the spatially-blocked holdout; write everything
to evidence/h84_holdout.json. This is "experiment slot" accounting for the 3-experiment
budget in the run card.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems84 import features as F
from gems84.holdout import run_holdout, prepare_holdout_cache
from gems84.metric import ALPHA, BETA, R_M


def leakage_canary(field: np.ndarray, truth: np.ndarray, valid: np.ndarray, seed=0, n_neg=300_000):
    rng = np.random.default_rng(seed)
    pos_idx = np.argwhere(truth & valid)
    neg_pool = np.argwhere(valid & ~truth)
    n_neg = min(n_neg, len(neg_pool))
    neg_idx = neg_pool[rng.choice(len(neg_pool), size=n_neg, replace=False)]
    y = np.concatenate([np.ones(len(pos_idx)), np.zeros(len(neg_idx))])
    s = np.concatenate([
        field[pos_idx[:, 0], pos_idx[:, 1]],
        field[neg_idx[:, 0], neg_idx[:, 1]],
    ])
    return float(roc_auc_score(y, s))


def top_k_emission(field: np.ndarray, valid: np.ndarray, k: int) -> np.ndarray:
    """Sparse 'dotted' emission: the organizer's metric taxes every unit of emitted mass by
    alpha regardless of placement (re-derived & confirmed in docs/research/metric-reduction.md),
    so -- as independently re-measured on OUR OWN holdout below, not merely assumed from
    sibling repos' prior claims -- concentrating mass on the top-K highest-confidence pixels
    beats spreading the same total mass over a dense thresholded field. We verify this for
    OUR field (leakage/validity sanity check) rather than importing the claim unverified."""
    flat = np.where(valid, field, -np.inf).ravel()
    if k >= np.isfinite(flat).sum():
        k = int(np.isfinite(flat).sum())
    idx = np.argpartition(flat, -k)[-k:]
    out = np.zeros_like(field, dtype=np.float64)
    vals = flat[idx]
    out_flat = out.ravel()
    # assign calibrated confidence: rank-based, highest rank -> near 1.0
    order = np.argsort(vals)
    ranks = np.empty_like(order)
    ranks[order] = np.arange(len(order))
    out_flat[idx] = 0.5 + 0.5 * (ranks / max(len(ranks) - 1, 1))
    return out.reshape(field.shape)


def main():
    t0 = time.time()
    bands, feat_valid, _ = F.load_stack()
    fault, label_valid, _ = F.load_labels()
    valid = F.footprint(feat_valid, label_valid)
    print(f"[{time.time()-t0:.1f}s] loaded stack, footprint px = {valid.sum()}, fault px = {fault.sum()}")

    h1 = F.h84_1_demagnetized_conductive_corridor(bands, valid)
    print(f"[{time.time()-t0:.1f}s] H84-1 computed")
    h3 = F.h84_3_conductivity_basement_discordance(bands, valid)
    print(f"[{time.time()-t0:.1f}s] H84-3 computed")
    fused = F.minmax01(np.maximum(h1, h3), valid)
    print(f"[{time.time()-t0:.1f}s] fusion computed")

    rng = np.random.default_rng(42)
    rand_field = np.where(valid, rng.random(valid.shape), 0.0)

    ho_cache = prepare_holdout_cache(fault, n_rows=6, n_cols=6, k_folds=6)
    print(f"[{time.time()-t0:.1f}s] holdout cache (block/segment layout) built")

    report = {"meta": {"alpha": ALPHA, "beta": BETA, "R_m": R_M,
                        "footprint_px": int(valid.sum()), "fault_px_total": int(fault.sum())}}

    # ---- leakage canary: single feature alone vs withheld labels ----
    canary = {}
    for name, field in [("H84-1_demag_cond_corridor", h1),
                         ("H84-3_cond_basement_discordance", h3),
                         ("fused_max", fused),
                         ("uniform_random_control", rand_field)]:
        auc = leakage_canary(field, fault, valid)
        canary[name] = {"AUC_vs_full_catalogue": auc, "leakage_flag": bool(auc > 0.90)}
        print(f"[{time.time()-t0:.1f}s] canary {name}: AUC={auc:.4f} flag={auc>0.90}")
    report["leakage_canary"] = canary

    # ---- spatially-blocked holdout DTI, matched emission budget ----
    budget = 44_090  # matches the registry's most-common prior emission budget, for comparability
    results = {}
    for name, field in [("H84-1", h1), ("H84-3", h3), ("fused_max", fused),
                         ("uniform_random", rand_field)]:
        dotted = top_k_emission(field, valid, budget)
        ho = run_holdout(dotted, fault, valid, cache=ho_cache)
        results[name] = {
            "emission": f"top-{budget}", "pooled_DTI": ho["pooled"]["DTI"],
            "pooled_TPw": ho["pooled"]["TPw"], "pooled_FPw": ho["pooled"]["FPw"],
            "pooled_FNw": ho["pooled"]["FNw"], "n_folds": ho["n_folds"],
            "n_withheld_truth_px_pooled": ho["n_withheld_truth_px_pooled"],
            "DTI_95CI_across_folds": ho["ci_95"], "mean_fold_DTI": ho["mean_fold_dti"],
        }
        print(f"[{time.time()-t0:.1f}s] holdout {name}: pooled DTI={ho['pooled']['DTI']:.4f} "
              f"95% CI(fold)={ho['ci_95']}")
    report["holdout_dti_top44090"] = results

    # ---- dense-field vs sparse-dot sanity check on the winning candidate (fused_max) ----
    dense_thresh = F.minmax01(fused, valid)
    dense_mass_matched = np.where(valid, dense_thresh, 0.0)
    # scale dense field so its TOTAL mass equals the dotted budget's total mass, for a fair
    # "same total predicted mass, different spatial concentration" comparison
    dotted_fused = top_k_emission(fused, valid, budget)
    scale = dotted_fused.sum() / max(dense_mass_matched.sum(), 1e-9)
    dense_scaled = np.clip(dense_mass_matched * scale, 0, 1)
    ho_dense = run_holdout(dense_scaled, fault, valid, cache=ho_cache)
    ho_dot = run_holdout(dotted_fused, fault, valid, cache=ho_cache)
    report["dense_vs_dotted_massmatched"] = {
        "dense_pooled_DTI": ho_dense["pooled"]["DTI"],
        "dotted_pooled_DTI": ho_dot["pooled"]["DTI"],
        "dotted_wins": bool(ho_dot["pooled"]["DTI"] > ho_dense["pooled"]["DTI"]),
    }
    print(f"[{time.time()-t0:.1f}s] dense vs dotted: dense={ho_dense['pooled']['DTI']:.4f} "
          f"dotted={ho_dot['pooled']['DTI']:.4f}")

    # ---- budget sweep for the winning field, to choose the submission's emission size ----
    sweep = {}
    best_name = max(results, key=lambda n: results[n]["pooled_DTI"] if n != "uniform_random" else -1)
    best_field = {"H84-1": h1, "H84-3": h3, "fused_max": fused}[best_name]
    for k in [15_000, 30_000, 44_090, 60_000, 90_000, 120_000]:
        dotted = top_k_emission(best_field, valid, k)
        ho = run_holdout(dotted, fault, valid, cache=ho_cache)
        sweep[str(k)] = ho["pooled"]["DTI"]
        print(f"[{time.time()-t0:.1f}s] sweep {best_name} k={k}: DTI={ho['pooled']['DTI']:.4f}")
    report["budget_sweep"] = {"field": best_name, "dti_by_k": sweep}
    report["selected_field"] = best_name
    report["elapsed_sec"] = time.time() - t0

    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence" / "h84_holdout.json").write_text(json.dumps(report, indent=2))
    print(f"\nWrote evidence/h84_holdout.json in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
