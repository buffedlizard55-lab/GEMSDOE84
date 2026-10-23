#!/usr/bin/env python3
"""EXP-84B-3: H-UAS-4 positional-sharpness adaptive spacing vs A0 control.
Identical folds/seeds/samples as EXP-84B-2 (determinism check: A0 must = 0.1703).
Also caches full-grid fold mu for reuse."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
import importlib.util
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pipe", ROOT/"scripts/run_h84b_uas_pipeline.py")
pipe = importlib.util.module_from_spec(spec); spec.loader.exec_module(pipe)
H, W = pipe.H, pipe.W

def emit_sharp(mu, sharp, dr, dc, N):
    muv = mu[dr, dc]
    order = np.argsort(-muv)[:min(len(muv), max(N*14, 60000))]
    rows, cols = dr[order], dc[order]
    hv = sharp[rows, cols]
    lo, hi = np.quantile(hv, [0.05, 0.95])
    blocked = np.zeros((H,W), bool); acc_r, acc_c = [], []
    for i in range(len(rows)):
        if len(acc_r) >= N: break
        r, c = int(rows[i]), int(cols[i])
        if blocked[r,c]: continue
        hhat = float(np.clip((hv[i]-lo)/max(hi-lo,1e-9), 0, 1))
        s = 3.4 - 1.9*hhat   # sharp ridge -> 1.5px dense; diffuse -> 3.4px sparse
        acc_r.append(r); acc_c.append(c)
        for dy,dx in pipe.disk_offsets(s):
            rr,cc = r+dy, c+dx
            if 0 <= rr < H and 0 <= cc < W: blocked[rr,cc] = True
    return np.array(acc_r), np.array(acc_c)

def main():
    t0 = time.time()
    mm, ch = pipe.load_stack(); fp, fault = pipe.load_labels()
    cache = pipe.fold_setup(fault)
    arms = ["A0_fixed28","A4_sharp"]
    pooled = {a: dict(tp=0.0,fp=0.0,fn=0.0,n_truth=0,n_emit=0) for a in arms}
    per_fold = {a: [] for a in arms}
    for k in range(4):
        fm = pipe.fold_masks(cache, fault, fp, k)
        rng = np.random.default_rng(50+k)
        X, y, dvis = pipe.train_sample(mm, fault, fm, rng)
        models, oob = pipe.fit_bagged(X, y)
        dr, dc = np.nonzero(fm["domain"] & (dvis > 2.0))
        mu = np.zeros((H,W), np.float32)
        for i in range(0, len(dr), 200000):
            sl = slice(i, i+200000)
            m_, s_ = pipe.predict_bagged(models, pipe.sample_X(mm, dr[sl], dc[sl]))
            mu[dr[sl], dc[sl]] = m_
        np.save(pipe.WORK/f"h84b_fold{k}_mu.npy", mu)
        sharp = mu - ndi.gaussian_filter(mu, 2.0)
        N = int(round(37654 * fm["domain"].sum() / fp.sum()))
        dots = {"A0_fixed28": pipe.emit(mu, None, dr, dc, dvis, N, "fixed28"),
                "A4_sharp": emit_sharp(mu, sharp, dr, dc, N)}
        truth = fm["truth"]; tr_rows, tr_cols = np.nonzero(truth)
        truth_block = fm["block_id"][tr_rows, tr_cols]
        for a in arms:
            pred = np.zeros((H,W), np.float32); r_,c_ = dots[a]; pred[r_,c_] = 1.0
            comp, tp_px, fp_map = pipe.dti_components(pred, truth)
            for key in ("tp","fp","fn"): pooled[a][key] += comp[key]
            pooled[a]["n_truth"] += comp["n_truth"]; pooled[a]["n_emit"] += comp["n_emit"]
            rec = dict(fold=k, **{kk: comp[kk] for kk in ("tp","fp","fn","dti","n_truth","n_emit")}, budget_N=N)
            nz_r, nz_c = np.nonzero(fp_map > 0); fb = fm["block_id"][nz_r,nz_c]; fv = fp_map[nz_r,nz_c]
            rec["fp_by_block"] = {int(b): float(fv[fb==b].sum()) for b in np.unique(fb)}
            rec["tp_by_block"] = {int(b): float(tp_px[truth_block==b].sum()) for b in np.unique(truth_block)}
            rec["ntruth_by_block"] = {int(b): int((truth_block==b).sum()) for b in np.unique(truth_block)}
            per_fold[a].append(rec)
        print(f"fold {k} done t={time.time()-t0:.0f}s", flush=True)
        del mu, sharp, X
    rng = np.random.default_rng(99); results = {}
    for a in arms:
        P = pooled[a]; dti = P["tp"]/(P["tp"]+0.2*P["fp"]+0.8*P["fn"]+1e-12)
        blocks = {}
        for f in per_fold[a]:
            for b in set(f["tp_by_block"]) | set(f["fp_by_block"]):
                tp_ = f["tp_by_block"].get(b,0.0); nt = f["ntruth_by_block"].get(b,0)
                blocks[(f["fold"],b)] = [tp_, f["fp_by_block"].get(b,0.0), nt-tp_]
        B = np.array(list(blocks.values()))
        boots = [ (lambda s: s[0]/(s[0]+0.2*s[1]+0.8*s[2]+1e-12))(B[rng.integers(0,len(B),len(B))].sum(axis=0)) for _ in range(2000)]
        lo,hi = np.percentile(boots,[2.5,97.5])
        results[a] = dict(pooled_dti=round(float(dti),4), ci95=[round(float(lo),4),round(float(hi),4)],
                          tp=round(P["tp"],1), fp=round(P["fp"],1), fn=round(P["fn"],1),
                          n_truth=P["n_truth"], n_emit=P["n_emit"],
                          per_fold=[{kk:vv for kk,vv in f.items() if kk not in ("fp_by_block","tp_by_block","ntruth_by_block")} for f in per_fold[a]])
        print(a, results[a]["pooled_dti"], results[a]["ci95"])
    out = {"stage":"EXP-84B-3 H-UAS-4 sharpness spacing","evidence_class":"HOLDOUT-DTI",
           "evaluator":"same as EXP-84B-2","n_withheld_positives_total":int(pooled["A0_fixed28"]["n_truth"]),
           "determinism_check_A0_expected":0.1703, "arms":results, "seconds":round(time.time()-t0,1)}
    (ROOT/"evidence/h84b_exp3_a4_holdout.json").write_text(json.dumps(out, indent=1))

if __name__ == "__main__":
    main()
