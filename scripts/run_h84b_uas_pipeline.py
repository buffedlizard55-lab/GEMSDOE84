#!/usr/bin/env python3
"""Lane H84B-UAS experiments (preregistered in research/h84b_uas_hypotheses.md).

Stages: canary | holdout | build | all
Holdout = hide-and-recover: whole fault segments withheld by spatial block group
(gems84.holdout cache), buffer 3px, per-fold retrain (bagged HGB, distance-blind
features), visible faults masked pixel-exactly, pooled DTI alpha 0.2 beta 0.8 R=3px
(vendor gems57 metric semantics; components computed via weighted dilation).
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"vendor"), str(ROOT/"src")]
DATA = Path(os.environ.get("GEMS84_DATA", "/home/user/gemsdata"))
WORK = DATA/"work"
H, W = 3730, 3292
rng_global = np.random.default_rng(20261023)

# ---------- io helpers ----------
def load_labels():
    with rasterio.open(ROOT/"data/bridge/labels.tif") as ds: lab = ds.read(1)
    return lab != -1, lab == 1

def load_stack():
    meta = json.loads((WORK/"h84b_stack.json").read_text())
    mm = np.memmap(WORK/"h84b_stack.dat", dtype=np.float32, mode="r", shape=tuple(meta["shape"]))
    return mm, meta["channels"]

def sample_X(mm, rows, cols):
    return np.column_stack([np.asarray(mm[c][rows, cols], dtype=np.float32) for c in range(mm.shape[0])])

# ---------- DTI components (exact, finite kernel) ----------
OFFS = []
for dy in range(-3,4):
    for dx in range(-3,4):
        d = float(np.hypot(dy,dx))
        if d < 3.0: OFFS.append((dy,dx,1.0-d/3.0))

def weighted_dilation(p):
    M = np.zeros(p.shape, np.float32)
    pad = np.pad(p, 3)
    for dy,dx,w in OFFS:
        cand = pad[3+dy:3+dy+p.shape[0], 3+dx:3+dx+p.shape[1]] * w
        np.maximum(M, cand, out=M)
    return M

def dti_components(pred, truth):
    """pred float [0,1] full grid (already masked to domain), truth bool."""
    M = weighted_dilation(pred)
    tp_px = M[truth]
    dg = ndi.distance_transform_edt(~truth)
    q = np.maximum(1.0 - dg/3.0, 0.0)
    fp_map = pred * (1.0 - q)
    tp, fn = float(tp_px.sum()), float(truth.sum()) - float(tp_px.sum())
    fp = float(fp_map.sum())
    dti = tp/(tp + 0.2*fp + 0.8*fn + 1e-12)
    return dict(tp=tp, fp=fp, fn=fn, dti=float(dti), n_truth=int(truth.sum()),
                n_emit=int((pred>0).sum())), tp_px, fp_map

# ---------- emitter ----------
DISKS = {}
def disk_offsets(s):
    key = round(float(s),2)
    if key not in DISKS:
        r = int(np.ceil(s)); offs=[]
        for dy in range(-r,r+1):
            for dx in range(-r,r+1):
                if np.hypot(dy,dx) < s: offs.append((dy,dx))
        DISKS[key] = offs
    return DISKS[key]

def emit(mu, sig, domain_rows, domain_cols, dvis, N, mode, far_quota=0.40):
    """Greedy emission sorted by mu desc. mode: fixed28 | adaptive | adaptive_quota.
    Returns (rows, cols) of accepted dots."""
    muv = mu[domain_rows, domain_cols]
    order = np.argsort(-muv)
    cand_cap = min(len(order), max(N*14, 60000))
    order = order[:cand_cap]
    rows = domain_rows[order]; cols = domain_cols[order]
    svals = sig[rows, cols] if sig is not None else np.zeros(len(rows), np.float32)
    dvals = dvis[rows, cols]
    s95 = float(np.quantile(svals, 0.95)) if sig is not None and svals.max()>0 else 1.0
    blocked = np.zeros((H,W), bool)
    acc_r, acc_c = [], []
    def spacing(i):
        if mode == "fixed28": return 2.83
        shat = min(float(svals[i])/max(s95,1e-9), 1.0)
        return 1.5 + 1.9*shat
    def try_accept(i):
        r,c = int(rows[i]), int(cols[i])
        if blocked[r,c]: return False
        acc_r.append(r); acc_c.append(c)
        for dy,dx in disk_offsets(spacing(i)):
            rr,cc = r+dy, c+dx
            if 0 <= rr < H and 0 <= cc < W: blocked[rr,cc] = True
        return True
    if mode == "adaptive_quota":
        target = int(N*far_quota)
        for i in range(len(rows)):
            if len(acc_r) >= target: break
            if dvals[i] > 12.0: try_accept(i)
    for i in range(len(rows)):
        if len(acc_r) >= N: break
        try_accept(i)
    return np.array(acc_r), np.array(acc_c)

# ---------- model ----------
def fit_bagged(X, y, seeds=(0,1,2,3), frac=0.7):
    from sklearn.ensemble import HistGradientBoostingClassifier
    models, inbag = [], []
    n = len(y)
    for s in seeds:
        r = np.random.default_rng(1000+s)
        idx = r.choice(n, size=int(frac*n), replace=False)
        m = np.zeros(n, bool); m[idx] = True; inbag.append(m)
        clf = HistGradientBoostingClassifier(max_iter=280, learning_rate=0.06,
              max_leaf_nodes=63, min_samples_leaf=40, l2_regularization=1.0,
              random_state=s)
        clf.fit(X[idx], y[idx]); models.append(clf)
    # OOB predictions for calibration
    oob = np.full(n, np.nan, np.float32); cnt = np.zeros(n, np.float32); acc = np.zeros(n, np.float32)
    for clf, m in zip(models, inbag):
        p = clf.predict_proba(X[~m])[:,1].astype(np.float32)
        acc[~m] += p; cnt[~m] += 1
    ok = cnt > 0; oob[ok] = acc[ok]/cnt[ok]
    return models, oob

def predict_bagged(models, X):
    ps = np.column_stack([c.predict_proba(X)[:,1].astype(np.float32) for c in models])
    return ps.mean(axis=1), ps.std(axis=1)

# ---------- fold machinery ----------
def fold_setup(fault, k_folds=4):
    from gems84.holdout import prepare_holdout_cache
    cache = prepare_holdout_cache(fault, 6, 6, k_folds)
    return cache

def fold_masks(cache, fault, fp, k):
    block_id, fob, lab, seg_block = cache["block_id"], cache["fold_of_block"], cache["lab"], cache["seg_block"]
    wblocks = {b for b,f in fob.items() if f == k}
    wmask = np.isin(block_id, list(wblocks))
    buffer = ndi.binary_dilation(wmask, iterations=3) & ~wmask
    wsegs = {s for s,b in seg_block.items() if b in wblocks}
    withheld_seg_px = np.isin(lab, list(wsegs)) if wsegs else np.zeros_like(fault)
    truth = withheld_seg_px & wmask & fp
    visible = fault & ~withheld_seg_px
    domain = wmask & fp
    train_excl = wmask | buffer | withheld_seg_px
    return dict(wmask=wmask, buffer=buffer, truth=truth, visible=visible,
                domain=domain, train_excl=train_excl, block_id=block_id)

def train_sample(mm, fault, fm, rng, neg_ratio=4):
    visible = fm["visible"]
    pr, pc = np.nonzero(visible)
    dvis = ndi.distance_transform_edt(~visible)
    neg_ok = fm_domain_neg(fm, dvis)
    nr_all, nc_all = np.nonzero(neg_ok)
    n_neg = min(len(nr_all), neg_ratio*len(pr))
    sel = rng.choice(len(nr_all), size=n_neg, replace=False)
    rows = np.concatenate([pr, nr_all[sel]]); cols = np.concatenate([pc, nc_all[sel]])
    y = np.concatenate([np.ones(len(pr), np.int8), np.zeros(n_neg, np.int8)])
    X = sample_X(mm, rows, cols)
    return X, y, dvis

def fm_domain_neg(fm, dvis):
    fp_neg = (~fm["train_excl"]) & (dvis > 1.0)
    return fp_neg

# ---------- stages ----------
def stage_canary():
    from sklearn.metrics import roc_auc_score
    mm, channels = load_stack(); fp, fault = load_labels()
    cache = fold_setup(fault); fm = fold_masks(cache, fault, fp, 0)
    rng = np.random.default_rng(7)
    pr, pc = np.nonzero(fm["truth"])
    dfull = ndi.distance_transform_edt(~fault)
    neg_ok = fm["domain"] & (dfull > 3.0) & (~fm["truth"])
    nr, nc = np.nonzero(neg_ok)
    sel = rng.choice(len(nr), size=min(60000, len(nr)), replace=False)
    rows = np.concatenate([pr, nr[sel]]); cols = np.concatenate([pc, nc[sel]])
    y = np.concatenate([np.ones(len(pr)), np.zeros(len(sel))])
    X = sample_X(mm, rows, cols)
    out = {"stage":"EXP-84B-1 canary", "fold":0, "n_pos":int(len(pr)), "n_neg":int(len(sel)),
           "gate":"symmetric AUC <= 0.90", "channels":{}}
    worst = 0.0
    for j, name in enumerate(channels):
        v = X[:,j]
        if np.std(v) == 0: auc = 0.5
        else:
            a = roc_auc_score(y, v); auc = float(max(a, 1-a))
        out["channels"][name] = round(auc,4); worst = max(worst, auc)
    out["max_symmetric_auc"] = round(worst,4)
    out["verdict"] = "PASS" if worst <= 0.90 else "LEAKAGE-STOP"
    (ROOT/"evidence/h84b_exp1_canary.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k:out[k] for k in ("n_pos","n_neg","max_symmetric_auc","verdict")}))
    top = sorted(out["channels"].items(), key=lambda kv:-kv[1])[:8]
    print("TOP", top)
    return out

def stage_holdout():
    t0 = time.time()
    mm, channels = load_stack(); fp, fault = load_labels()
    cache = fold_setup(fault)
    arms = ["A0_fixed28","A1_adaptive","A2_adaptive_quota","A3_soft"]
    pooled = {a: dict(tp=0.0, fp=0.0, fn=0.0, n_truth=0, n_emit=0) for a in arms}
    block_rows = {a: [] for a in arms}   # per-block (tp,fp,fn) for bootstrap
    per_fold = {a: [] for a in arms}
    auc_mu_sig = []
    for k in range(4):
        fm = fold_masks(cache, fault, fp, k)
        rng = np.random.default_rng(50+k)
        X, y, dvis = train_sample(mm, fault, fm, rng)
        models, oob = fit_bagged(X, y)
        # isotonic calibration on OOB
        from sklearn.isotonic import IsotonicRegression
        ok = np.isfinite(oob)
        iso = IsotonicRegression(out_of_bounds="clip").fit(oob[ok], y[ok])
        # domain prediction (candidate domain: footprint & withheld blocks & collar>2 from visible)
        dr, dc = np.nonzero(fm["domain"] & (dvis > 2.0))
        mu = np.zeros((H,W), np.float32); sig = np.zeros((H,W), np.float32)
        for i in range(0, len(dr), 200000):
            sl = slice(i, i+200000)
            m_, s_ = predict_bagged(models, sample_X(mm, dr[sl], dc[sl]))
            mu[dr[sl], dc[sl]] = m_; sig[dr[sl], dc[sl]] = s_
        # AUC diagnostics for mu/sigma on this fold
        from sklearn.metrics import roc_auc_score
        tmask = fm["truth"][dr, dc]
        if tmask.sum() > 20:
            neg_idx = np.nonzero(~tmask)[0]
            sel = rng.choice(neg_idx, size=min(60000, len(neg_idx)), replace=False)
            yy = np.concatenate([np.ones(int(tmask.sum())), np.zeros(len(sel))])
            rows_i = np.concatenate([np.nonzero(tmask)[0], sel])
            a_mu = roc_auc_score(yy, mu[dr[rows_i], dc[rows_i]])
            a_sg = roc_auc_score(yy, sig[dr[rows_i], dc[rows_i]])
            auc_mu_sig.append(dict(fold=k, auc_mu=round(float(max(a_mu,1-a_mu)),4),
                                   auc_sigma_raw=round(float(a_sg),4)))
        N = int(round(37654 * fm["domain"].sum() / fp.sum()))
        dots = {}
        dots["A0_fixed28"] = emit(mu, None, dr, dc, dvis, N, "fixed28")
        dots["A1_adaptive"] = emit(mu, sig, dr, dc, dvis, N, "adaptive")
        dots["A2_adaptive_quota"] = emit(mu, sig, dr, dc, dvis, N, "adaptive_quota")
        dots["A3_soft"] = dots["A1_adaptive"]
        truth = fm["truth"]
        tr_rows, tr_cols = np.nonzero(truth)
        truth_block = fm["block_id"][tr_rows, tr_cols]
        for a in arms:
            pred = np.zeros((H,W), np.float32)
            r_, c_ = dots[a]
            if a == "A3_soft":
                pred[r_,c_] = iso.predict(mu[r_,c_]).astype(np.float32)
            else:
                pred[r_,c_] = 1.0
            comp, tp_px, fp_map = dti_components(pred, truth)
            for key in ("tp","fp","fn"): pooled[a][key] += comp[key]
            pooled[a]["n_truth"] += comp["n_truth"]; pooled[a]["n_emit"] += comp["n_emit"]
            per_fold[a].append(dict(fold=k, **{kk: comp[kk] for kk in ("tp","fp","fn","dti","n_truth","n_emit")}, budget_N=N))
            # per-block components
            for b in np.unique(truth_block):
                m_ = truth_block == b
                block_rows[a].append([float(tp_px[m_].sum()), 0.0, float(m_.sum()-tp_px[m_].sum())])
            fp_by_block = {}
            nz_r, nz_c = np.nonzero(fp_map > 0)
            fb = fm["block_id"][nz_r, nz_c]; fv = fp_map[nz_r, nz_c]
            for b in np.unique(fb): fp_by_block[int(b)] = float(fv[fb==b].sum())
            # attach fp to matching block rows (same order as unique truth blocks may differ; use dict rows)
            # rebuild: store dict rows instead
            block_rows[a] = block_rows[a]  # placeholder, fp handled below via fold dict
            per_fold[a][-1]["fp_by_block"] = fp_by_block
            per_fold[a][-1]["truth_blocks"] = [int(b) for b in np.unique(truth_block)]
            per_fold[a][-1]["tp_by_block"] = {int(b): float(tp_px[truth_block==b].sum()) for b in np.unique(truth_block)}
            per_fold[a][-1]["ntruth_by_block"] = {int(b): int((truth_block==b).sum()) for b in np.unique(truth_block)}
        print(f"fold {k} done N={N} truth={int(truth.sum())} t={time.time()-t0:.0f}s", flush=True)
        del mu, sig, X
    # pooled DTI + block bootstrap CI
    rng = np.random.default_rng(99)
    results = {}
    for a in arms:
        P = pooled[a]
        dti = P["tp"]/(P["tp"]+0.2*P["fp"]+0.8*P["fn"]+1e-12)
        # assemble per-block (tp,fp,fn) across folds (fp blocks without truth get fn=tp=0)
        blocks = {}
        for f in per_fold[a]:
            for b in set(f["truth_blocks"]) | set(f["fp_by_block"]):
                tp_ = f["tp_by_block"].get(b, 0.0); nt = f["ntruth_by_block"].get(b, 0)
                blocks.setdefault((f["fold"], b), [tp_, f["fp_by_block"].get(b,0.0), nt - tp_])
        B = np.array(list(blocks.values()))
        boots = []
        for _ in range(2000):
            s = B[rng.integers(0, len(B), len(B))].sum(axis=0)
            boots.append(s[0]/(s[0]+0.2*s[1]+0.8*s[2]+1e-12))
        lo, hi = np.percentile(boots, [2.5, 97.5])
        results[a] = dict(pooled_dti=round(float(dti),4), ci95=[round(float(lo),4), round(float(hi),4)],
                          tp=round(P["tp"],1), fp=round(P["fp"],1), fn=round(P["fn"],1),
                          n_truth=P["n_truth"], n_emit=P["n_emit"], n_blocks=int(len(B)),
                          per_fold=[{kk:vv for kk,vv in f.items() if kk not in ("fp_by_block","tp_by_block","ntruth_by_block","truth_blocks")} for f in per_fold[a]])
        print(a, results[a]["pooled_dti"], results[a]["ci95"], "emit", P["n_emit"])
    out = {"stage":"EXP-84B-2 holdout", "evidence_class":"HOLDOUT-DTI",
           "evaluator":"gems84b weighted-dilation exact finite-kernel (alpha 0.2 beta 0.8 R 3px), cross-checked vs vendor gems57 in tests",
           "n_withheld_positives_total": int(pooled["A0_fixed28"]["n_truth"]),
           "folds":4, "blocks":"6x6 checkerboard groups, whole segments, buffer 3px",
           "arms":results, "auc_mu_sigma":auc_mu_sig, "seconds":round(time.time()-t0,1)}
    (ROOT/"evidence/h84b_exp2_holdout.json").write_text(json.dumps(out, indent=1))
    return out

if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage in ("canary","all"): stage_canary()
    if stage in ("holdout","all"): stage_holdout()
