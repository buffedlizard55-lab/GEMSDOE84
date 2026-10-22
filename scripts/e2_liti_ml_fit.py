#!/usr/bin/env python3
"""E2a -- refit LITI with the catalogue-analogue ML columns added (ml_prob, ml_ridge).

Question: does a fine-scale "looks like a mapped fault" term let the live-score
inversion explain the top of the board, which the physics-only model (E1)
under-predicted by ~2x?  Same sample, same raster set, same grouped 8-fold CV.
Output: evidence/e2a_liti_ml_fit.json, $GEMS84_DATA/work/liti_ml_selected.npz
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]; sys.path.insert(0, str(ROOT / "scripts"))
from e1_liti_fit import N_SAMPLE, SEED  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems84 import basis, liti, mlfield  # noqa: E402
from gems84.paths import BRIDGE, REGISTRY_DIR, WORK  # noqa: E402


def main():
    t0 = time.time()
    g = load_grid(BRIDGE)
    fp, cat = g.footprint, g.catalogue
    Xp, n_p = basis.physics_basis(fp)
    Xr, n_r = basis.region_basis(fp)
    Xc, n_c, oncat = basis.catalogue_basis(fp, cat)
    Xm, n_m, ml_info = mlfield.train_predict(Xp, fp, cat, seed=84)
    np.save(WORK / "ml_cols_live.npy", Xm)
    names = ["intercept"] + n_p + n_r + n_c + n_m
    print("ml field", ml_info, f"{time.time()-t0:.0f}s", flush=True)
    nfp = int(fp.sum())
    samp = np.sort(np.random.default_rng(SEED).choice(nfp, N_SAMPLE, replace=False))
    fy, fx = np.nonzero(fp); ys, xs = fy[samp], fx[samp]
    X = np.concatenate([Xp, Xr, Xc, Xm], axis=1)
    Phi = np.concatenate([np.ones((N_SAMPLE, 1), np.float32), X[samp].astype(np.float32)], axis=1)
    del X
    support = ~oncat[samp]; w = nfp / N_SAMPLE
    M = json.load(open(ROOT / "registry/live_score_matches.json"))["matched"]
    rows, C, Mm, S, dropped = liti.load_scored(M, fp, ys, xs, REGISTRY_DIR)
    y = np.array([np.mean(r["scores"]) for r in rows])
    print("rasters", len(rows), "dropped", len(dropped), f"{time.time()-t0:.0f}s", flush=True)
    sites = np.array([r["site"] for r in rows])
    order = sorted(np.unique(sites), key=lambda s: hashlib.md5(s.encode()).hexdigest())
    fold_of = np.array([{s: i % 8 for i, s in enumerate(order)}[s] for s in sites])
    idx = {n: i for i, n in enumerate(names)}
    dist = [idx[n] for n in names if n.startswith("dcat_")]
    phys = [idx[n] for n in n_p]
    models = {"M3_dist_dens_physics": [0] + dist + [idx["cat_density_5km"]] + phys,
              "M5_M3_plus_ml": [0] + dist + [idx["cat_density_5km"]] + phys + [idx["ml_prob"], idx["ml_ridge"]]}
    out = dict(evidence_class="MODEL-PROJECTION fitted to OWNER-REPORTED live scores",
               n_rasters=len(rows), dropped=dropped, ml_info=ml_info, models={})
    best = None
    top = np.argsort(-y)[:15]
    for mname, cols in models.items():
        for reg in (1e-3, 1e-4):
            D = liti.Design(Phi=Phi[:, cols], support=support, C=C, Mm=Mm, S=S, w=w, names=[names[c] for c in cols])
            pred = np.zeros(len(rows))
            for k in range(8):
                tr = np.flatnonzero(fold_of != k); te = np.flatnonzero(fold_of == k)
                th, el, _ = liti.fit(D, y, tr, reg=reg, maxiter=600)
                pred[te] = liti.predict(th, el, D, te)[0]
            th, el, res = liti.fit(D, y, np.arange(len(rows)), reg=reg, maxiter=600)
            fitted, parts = liti.predict(th, el, D)
            rec = dict(cv_rmse=float(np.sqrt(np.mean((pred - y) ** 2))), cv_spearman=float(spearmanr(pred, y).correlation),
                       cv_mean_abs_err_top15=float(np.mean(np.abs(pred[top] - y[top]))),
                       insample_rmse=float(np.sqrt(np.mean((fitted - y) ** 2))),
                       insample_pred_best_raster=float(fitted[np.argmax(y)]), G=float(parts["G"]),
                       optimizer=str(res.message), theta=dict(zip(D.names, map(float, th))))
            key = f"{mname}|reg={reg:g}"; out["models"][key] = rec
            print(key, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in rec.items() if k != "theta"},
                  f"{time.time()-t0:.0f}s", flush=True)
            if best is None or rec["cv_rmse"] < best[0]:
                best = (rec["cv_rmse"], key, cols, th, el, pred.copy(), fitted.copy())
    _, key, cols, th, el, pred, fitted = best
    out["selected"] = key
    out["rasters"] = [dict(name=r["names"][0], site=r["site"], live=float(y[i]), cv_pred=float(pred[i]),
                           fit_pred=float(fitted[i])) for i, r in enumerate(rows)]
    (ROOT / "evidence/e2a_liti_ml_fit.json").write_text(json.dumps(out, indent=1))
    np.savez(WORK / "liti_ml_selected.npz", theta=th, eta_logit=el, cols=np.array(cols),
             names=np.array([names[c] for c in cols]))
    print("selected", key)


if __name__ == "__main__":
    main()
