#!/usr/bin/env python3
"""E1 -- fit the Leaderboard-Inverted Truth Intensity model and cross-validate it.

Inputs (all hash-verified):
  * registry/live_score_matches.json  (owner-reported live scores -> raster blobs)
  * raster blobs under $GEMS84_DATA/registry/<git-blob-sha>.tif, verified by
    recomputing the git blob SHA-1 of the bytes
  * physics basis (training_features.tif sha256 4371c82e..., pinned externals)

Outputs:
  * evidence/e1_liti_fit.json   (coefficients, CV table, per-raster predictions)
  * $GEMS84_DATA/work/liti_design.npz (cached design; out of Git)

Every predicted number is MODEL-PROJECTION; every target is OWNER-REPORTED.
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
sys.path.insert(0, str(ROOT / "src"))
from gems57.grid import load_grid  # noqa: E402
from gems84 import basis, liti  # noqa: E402
from gems84.paths import BRIDGE, REGISTRY_DIR, WORK  # noqa: E402

N_SAMPLE = 80_000
SEED = 8484


def git_blob_sha(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def main():
    t0 = time.time()
    g = load_grid(BRIDGE)
    fp, cat = g.footprint, g.catalogue
    X, names, oncat = basis.full_basis(fp, cat)
    print("basis", X.shape, f"{time.time()-t0:.0f}s", flush=True)
    rng = np.random.default_rng(SEED)
    nfp = int(fp.sum())
    samp = np.sort(rng.choice(nfp, N_SAMPLE, replace=False))
    fy, fx = np.nonzero(fp)
    ys, xs = fy[samp], fx[samp]
    Phi = np.concatenate([np.ones((N_SAMPLE, 1), np.float32), X[samp].astype(np.float32)], axis=1)
    support = ~oncat[samp]
    w = nfp / N_SAMPLE

    M = json.load(open(ROOT / "registry/live_score_matches.json"))["matched"]
    rows, C, Mm, S, dropped = [], [], [], [], []
    seen = {}
    for r in M:
        decoded = {}
        problems = []
        for repo, blob, path in r["matches"]:
            f = REGISTRY_DIR / f"{blob}.tif"
            if not f.exists():
                problems.append(f"missing blob {blob}")
                continue
            if git_blob_sha(f) != blob:
                problems.append(f"blob hash mismatch {blob}")
                continue
            try:
                a = liti.decoded_prediction(f, fp)
            except Exception as e:  # invalid raster: cannot carry a portal score
                problems.append(f"{blob}: {e}")
                continue
            decoded.setdefault(liti.decoded_sha(a), (a, blob, path))
        if len(decoded) != 1:
            dropped.append(dict(name=r["name"], score=r["score"], reason=(
                "ambiguous: matched rasters decode to %d different predictions" % len(decoded)
                if decoded else "; ".join(problems) or "no raster")))
            continue
        dsha, (a, blob, path) = next(iter(decoded.items()))
        if dsha in seen:  # same prediction scored twice (e.g. nan/zeros twins) -> keep both scores averaged
            rows[seen[dsha]]["scores"].append(r["score"])
            rows[seen[dsha]]["names"].append(r["name"])
            continue
        c, m = liti.coverage_at(a, ys, xs)
        seen[dsha] = len(rows)
        rows.append(dict(site=r["site"], names=[r["name"]], scores=[r["score"]], blob=blob, path=path,
                         decoded_sha256=dsha, emitted=int((a > 0).sum()), mass=float(a.sum()),
                         binary=bool(np.isin(np.unique(a), [0, 1]).all())))
        C.append(c); Mm.append(m); S.append(float(a.sum()))
    y = np.array([np.mean(r["scores"]) for r in rows])
    D = liti.Design(Phi=Phi, support=support, C=np.stack(C), Mm=np.stack(Mm), S=np.array(S), w=w,
                    names=["intercept"] + names)
    print("rasters used", len(rows), "dropped", len(dropped), f"{time.time()-t0:.0f}s", flush=True)

    sites = np.array([r["site"] for r in rows])
    usites = np.unique(sites)
    folds = {s: i % 8 for i, s in enumerate(sorted(usites, key=lambda s: hashlib.md5(s.encode()).hexdigest()))}
    fold_of = np.array([folds[s] for s in sites])

    # nested models: which basis families does the live board actually support?
    fam = {"intercept": [0]}
    idx = {n: i for i, n in enumerate(D.names)}
    dist_cols = [idx[n] for n in D.names if n.startswith("dcat_")]
    phys_cols = [idx[n] for n in D.names
                 if not n.startswith(("dcat_", "region_", "cat_density", "intercept"))]
    reg_cols = [idx[n] for n in D.names if n.startswith("region_")]
    dens_cols = [idx["cat_density_5km"]]
    models = {
        "M1_distance": [0] + dist_cols,
        "M3_dist_dens_physics": [0] + dist_cols + dens_cols + phys_cols,
        "M4_full_with_regions": [0] + dist_cols + dens_cols + phys_cols + reg_cols,
    }
    out = dict(evidence_class="MODEL-PROJECTION fitted to OWNER-REPORTED live scores",
               n_rasters=len(rows), n_dropped=len(dropped), dropped=dropped,
               n_sample=N_SAMPLE, seed=SEED, basis_names=D.names, cv_folds=8,
               cv_grouping="by site repository (a repo's variants never straddle train/test)",
               models={})
    best = None
    for mname, cols in models.items():
        sub = liti.Design(Phi=D.Phi[:, cols], support=D.support, C=D.C, Mm=D.Mm, S=D.S, w=D.w,
                          names=[D.names[c] for c in cols])
        for reg in (1e-3, 1e-2):
            pred = np.zeros(len(rows))
            for k in range(8):
                tr = np.flatnonzero(fold_of != k); te = np.flatnonzero(fold_of == k)
                th, el, _ = liti.fit(sub, y, tr, reg=reg)
                pred[te] = liti.predict(th, el, sub, te)[0]
            rmse = float(np.sqrt(np.mean((pred - y) ** 2)))
            rho = float(spearmanr(pred, y).correlation)
            top = np.argsort(-y)[:15]
            rho_top = float(spearmanr(pred[top], y[top]).correlation)
            key = f"{mname}|reg={reg:g}"
            out["models"][key] = dict(cv_rmse=rmse, cv_spearman=rho, cv_spearman_top15=rho_top,
                                      n_params=len(cols) + 1)
            print(key, f"rmse={rmse:.4f} rho={rho:.3f} rho_top15={rho_top:.3f}", f"{time.time()-t0:.0f}s", flush=True)
            if best is None or rmse < best[0]:
                best = (rmse, mname, reg, cols, pred.copy())
    rmse, mname, reg, cols, cvpred = best
    sub = liti.Design(Phi=D.Phi[:, cols], support=D.support, C=D.C, Mm=D.Mm, S=D.S, w=D.w,
                      names=[D.names[c] for c in cols])
    th, el, res = liti.fit(sub, y, np.arange(len(rows)), reg=reg)
    fitted, parts = liti.predict(th, el, sub)
    out["selected"] = dict(model=mname, reg=reg, cv_rmse=rmse, columns=sub.names,
                           theta=dict(zip(sub.names, map(float, th))), eta=float(parts["eta"]),
                           implied_truth_cells_G=float(parts["G"]), optimizer=dict(
                               success=bool(res.success), nit=int(res.nit), message=str(res.message)))
    out["rasters"] = [dict(r, live_mean=float(y[i]), cv_pred=float(cvpred[i]), fit_pred=float(fitted[i]),
                           expected_TPw=float(parts["A"][i]), expected_FPw=float(parts["F"][i]))
                      for i, r in enumerate(rows)]
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence/e1_liti_fit.json").write_text(json.dumps(out, indent=1))
    WORK.mkdir(parents=True, exist_ok=True)
    np.savez(WORK / "liti_selected.npz", theta=th, eta_logit=el, cols=np.array(cols),
             names=np.array(sub.names))
    print(json.dumps(out["selected"], indent=1))


if __name__ == "__main__":
    main()
