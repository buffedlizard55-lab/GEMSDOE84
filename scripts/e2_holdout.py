#!/usr/bin/env python3
"""E2 -- hide-and-recover holdout of the LITI emission vs the incumbent recipe.

Shared tools only (pinned template src/gems57, unmodified):
  * holdout.buffered_component_draw  -- whole components withheld, 3 px feature
    buffer, label-blind eroded quadrants, visible faults masked pixel-exactly
  * evaluate_holdout.evaluate / pooled_summary -- pooled DTI (alpha 0.2,
    beta 0.8, 300 m triangular kernel) with a paired 20 km spatial-block bootstrap
  * emit.greedy_allocate -- the template's exact-bar greedy emission

Every catalogue-derived input is recomputed from the fold's VISIBLE catalogue.

Arms
  liti            : LITI lambda (theta fitted in E1) -> greedy_allocate
  incumbent_recipe: D2.8 dots (GEMSDOE25, live 0.2600 OWNER-REPORTED) minus every
                    dot within 2 px of the VISIBLE catalogue  (= the H33-2-B2 rule
                    re-applied without seeing withheld faults)
  incumbent_asis  : the shipped H33-2-B2 raster (live 0.2778 OWNER-REPORTED); it
                    was pruned with the FULL catalogue, so on this holdout it is
                    handicapped (it avoids the withheld truth) -- reported, not
                    used as the gate
Leakage canary: per-basis-feature AUC for withheld-truth vs other scored cells.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems57 import emit, evaluate_holdout, holdout  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems84 import basis, liti, mlfield  # noqa: E402
from gems84.paths import BRIDGE, REGISTRY_DIR, WORK  # noqa: E402

SEEDS = (20, 21)
D28_BLOB = None  # resolved from the registry index below
REF = {
    "d28": "registry/rasters/GEMSDOE25__dotted-h19-5-d2-8.tif",
    "b2": "registry/rasters/GEMSDOE32__h33-2-b2-zeros.tif",
}


def auc(score, pos, neg):
    s = np.concatenate([score[pos], score[neg]]).astype(np.float64)
    lab = np.concatenate([np.ones(pos.sum()), np.zeros(neg.sum())])
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(s.size); ranks[order] = np.arange(1, s.size + 1)
    # average ties
    _, inv, cnt = np.unique(s, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=ranks); ranks = (sums / cnt)[inv]
    n1 = lab.sum(); n0 = lab.size - n1
    return float((ranks[lab == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def liti_emission(theta, cols, fp, visible, X_phys, X_reg, seed):
    Xc, nc, oncat = basis.catalogue_basis(fp, visible)
    # catalogue-analogue ML retrained on the VISIBLE catalogue only (label-blind negatives)
    Xm, nm, _ = mlfield.train_predict(X_phys, fp, visible, seed=84 + seed)
    Xfull = np.concatenate([X_phys, X_reg, Xc, Xm], axis=1)
    Xsel = Xfull[:, np.asarray(cols[1:]) - 1]          # cols index the [1, X] design
    lam_fp = liti.full_lambda(theta, Xsel, ~oncat)
    lam = np.zeros(fp.shape, np.float32); lam[fp] = lam_fp
    G = float(lam.sum())
    allowed = fp & ~visible
    alloc = emit.greedy_allocate(np.clip(lam, 0, 1), allowed, G)
    return alloc.emitted, dict(G=G, n_dots=int(alloc.n_dots), surrogate_dti=float(alloc.surrogate_dti),
                               rounds=int(alloc.rounds)), Xfull


def main():
    t0 = time.time()
    ref_root = Path("/home/user/ref/60GEMSDOE")
    g = load_grid(BRIDGE)
    fp, cat = g.footprint, g.catalogue
    sel = np.load(WORK / "liti_ml_selected.npz")
    theta, cols = sel["theta"], [int(c) for c in sel["cols"]]
    names_sel = [str(n) for n in sel["names"]]
    X_phys, n_phys = basis.physics_basis(fp)
    X_reg, n_reg = basis.region_basis(fp)
    all_names = n_phys + n_reg

    def read_dots(rel):
        with rasterio.open(ref_root / rel) as s:
            a = s.read(1)
        return np.isfinite(a) & (a > 0) & fp

    d28 = read_dots(REF["d28"]); b2 = read_dots(REF["b2"])
    terms = {"liti": [], "incumbent_recipe": [], "incumbent_asis": []}
    per_fold, canary = [], {}
    for seed in SEEDS:
        folds, quad = holdout.buffered_component_draw(g, seed=seed, hide_frac=0.20, buffer_px=3)
        visible = folds[0]["visible"]
        dvis = ndi.distance_transform_edt(~visible)
        arms = {}
        arms["liti"], info, Xfull = liti_emission(theta, cols, fp, visible, X_phys, X_reg, seed)
        arms["incumbent_recipe"] = d28 & (dvis > 2) & ~visible
        arms["incumbent_asis"] = b2.copy()
        # leakage canary on this draw (feature alone, withheld truth vs other scored cells)
        hidden = folds[0]["hidden_all"]; known = folds[0]["masked_known"]
        regions = np.zeros(fp.shape, bool)
        for f in folds:
            regions |= f["region"]
        act = (regions & fp & ~known)[fp]
        pos = (hidden & regions)[fp] & act
        neg = act & ~pos
        rng = np.random.default_rng(seed)
        negi = np.flatnonzero(neg); negi = rng.choice(negi, min(400_000, negi.size), replace=False)
        negm = np.zeros(neg.size, bool); negm[negi] = True
        cnames = all_names + basis.catalogue_basis(fp, visible)[1] + ["ml_prob", "ml_ridge"]
        for j, n in enumerate(cnames):
            a = auc(Xfull[:, j].astype(np.float32), pos, negm)
            canary.setdefault(n, []).append(max(a, 1 - a))
        lam_auc = None
        for fi, f in enumerate(folds):
            for arm, pred in arms.items():
                res, t = evaluate_holdout.evaluate(pred.astype(np.float32), f, fp, block_side=200)
                terms[arm].append(t)
                per_fold.append(dict(seed=seed, fold=f["name"], arm=arm, dti=res["dti"], tp=res["tp"],
                                     fp=res["fp"], fn=res["fn"], n_truth=res["n_truth"],
                                     n_emitted_in_region=res["n_emitted"]))
        per_fold.append(dict(seed=seed, liti_emission=info,
                             dots={k: int(v.sum()) for k, v in arms.items()}))
        print("seed", seed, info, {k: int(v.sum()) for k, v in arms.items()}, f"{time.time()-t0:.0f}s", flush=True)
    # stack terms (all arms share identical block grid & truth counts per (seed, fold))
    stacked = {k: np.sum(np.stack(v), axis=0) for k, v in terms.items()}
    summary = evaluate_holdout.pooled_summary(stacked, draws=1000, seed=520810, candidate="liti")
    out = dict(evidence_class="HOLDOUT-DTI", evaluator_version=evaluate_holdout.VERSION,
               split="holdout.buffered_component_draw (whole components, 3 px buffer, 4 quadrants)",
               seeds=list(SEEDS), selected_model=names_sel, summary=summary, per_fold=per_fold,
               leakage_canary=dict(rule="single feature AUC > 0.90 => leakage until proven otherwise",
                                   auc_max_over_polarity={k: float(np.mean(v)) for k, v in canary.items()},
                                   flagged=[k for k, v in canary.items() if np.mean(v) > 0.90]),
               seconds=round(time.time() - t0, 1))
    (ROOT / "evidence/e2_holdout.json").write_text(json.dumps(out, indent=1, default=float))
    s = summary["scores"]
    for k in s:
        print(k, "HOLDOUT-DTI", round(s[k]["dti"], 4), "CI", [round(x, 4) for x in s[k]["ci95"]],
              "withheld+", s[k]["withheld_positive_pixels"])
    for k, v in summary["paired_differences"].items():
        print("liti minus", k, round(v["delta"], 4), [round(x, 4) for x in v["ci95"]])
    print("canary flagged:", out["leakage_canary"]["flagged"])


if __name__ == "__main__":
    main()
