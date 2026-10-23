#!/usr/bin/env python3
"""Experiment 3 (final, per the 3-experiment budget): test H84-4, the scarp-alteration
concordance hypothesis, against the same spatially-blocked holdout, with the leakage
canary, and compare against H84-1/H84-3/fused_max (Experiment 1) and uniform random."""
import json
import pickle
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

CACHE_PATH = ROOT / "evidence" / "_holdout_cache.pkl"


def leakage_canary(field, truth, valid, seed=0, n_neg=300_000):
    rng = np.random.default_rng(seed)
    pos_idx = np.argwhere(truth & valid)
    neg_pool = np.argwhere(valid & ~truth)
    n_neg = min(n_neg, len(neg_pool))
    neg_idx = neg_pool[rng.choice(len(neg_pool), size=n_neg, replace=False)]
    y = np.concatenate([np.ones(len(pos_idx)), np.zeros(len(neg_idx))])
    s = np.concatenate([field[pos_idx[:, 0], pos_idx[:, 1]], field[neg_idx[:, 0], neg_idx[:, 1]]])
    return float(roc_auc_score(y, s))


def top_k_emission(field, valid, k):
    flat = np.where(valid, field, -np.inf).ravel()
    n_finite = np.isfinite(flat).sum()
    k = min(k, int(n_finite))
    idx = np.argpartition(flat, -k)[-k:]
    out = np.zeros_like(field, dtype=np.float32)
    vals = flat[idx]
    order = np.argsort(vals)
    ranks = np.empty_like(order)
    ranks[order] = np.arange(len(order))
    out.ravel()[idx] = 0.5 + 0.5 * (ranks / max(len(ranks) - 1, 1))
    return out.reshape(field.shape)


def main():
    t0 = time.time()
    bands, feat_valid, _ = F.load_stack()
    fault, label_valid, _ = F.load_labels()
    valid = F.footprint(feat_valid, label_valid)
    print(f"[{time.time()-t0:.1f}s] loaded")

    h1 = F.h84_1_demagnetized_conductive_corridor(bands, valid)
    h3 = F.h84_3_conductivity_basement_discordance(bands, valid)
    fused = F.minmax01(np.maximum(h1, h3), valid)
    h4 = F.h84_4_scarp_alteration_concordance(bands, valid, fused)
    print(f"[{time.time()-t0:.1f}s] all fields computed")

    if CACHE_PATH.exists():
        ho_cache = pickle.loads(CACHE_PATH.read_bytes())
        print(f"[{time.time()-t0:.1f}s] loaded persisted holdout cache")
    else:
        ho_cache = prepare_holdout_cache(fault, n_rows=6, n_cols=6, k_folds=6)
        CACHE_PATH.write_bytes(pickle.dumps(ho_cache))
        print(f"[{time.time()-t0:.1f}s] built + persisted holdout cache")

    rng = np.random.default_rng(42)
    rand_field = np.where(valid, rng.random(valid.shape), 0.0)

    report = {}
    canary = {}
    for name, field in [("H84-4_scarp_alteration_concordance", h4)]:
        auc = leakage_canary(field, fault, valid)
        canary[name] = {"AUC_vs_full_catalogue": auc, "leakage_flag": bool(auc > 0.90)}
        print(f"[{time.time()-t0:.1f}s] canary {name}: AUC={auc:.4f}")
    report["leakage_canary"] = canary

    budget = 44_090
    results = {}
    for name, field in [("H84-4", h4), ("fused_max_prev", fused), ("uniform_random", rand_field)]:
        dotted = top_k_emission(field, valid, budget)
        ho = run_holdout(dotted, fault, valid, cache=ho_cache)
        results[name] = {"pooled_DTI": ho["pooled"]["DTI"], "n_folds": ho["n_folds"],
                          "DTI_95CI_across_folds": ho["ci_95"], "mean_fold_DTI": ho["mean_fold_dti"],
                          "n_withheld_truth_px_pooled": ho["n_withheld_truth_px_pooled"]}
        print(f"[{time.time()-t0:.1f}s] holdout {name}: pooled DTI={ho['pooled']['DTI']:.4f} "
              f"95% CI={ho['ci_95']}")
    report["holdout_dti_top44090"] = results

    # budget sweep for H84-4
    sweep = {}
    for k in [15_000, 30_000, 44_090, 60_000, 90_000]:
        dotted = top_k_emission(h4, valid, k)
        ho = run_holdout(dotted, fault, valid, cache=ho_cache)
        sweep[str(k)] = ho["pooled"]["DTI"]
        print(f"[{time.time()-t0:.1f}s] sweep H84-4 k={k}: DTI={ho['pooled']['DTI']:.4f}")
    report["budget_sweep_h84_4"] = sweep
    report["elapsed_sec"] = time.time() - t0

    (ROOT / "evidence" / "h84_4_holdout.json").write_text(json.dumps(report, indent=2))
    print(f"\nWrote evidence/h84_4_holdout.json in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
