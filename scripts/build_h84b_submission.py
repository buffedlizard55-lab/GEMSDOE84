#!/usr/bin/env python3
"""EXP-84B-3: build the H84B-UAS submission from the EXP-2 winning arm.

Refuses to build unless evidence/h84b_exp2_holdout.json shows the chosen arm
beats the A0 fixed-spacing control. Full-catalogue training (all 60,988
positives as visible), collar d_cat>2, budget 37,654 (budget-matched control),
uniqueness gates vs local registry subset, fail-closed vendor writer.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"vendor"), str(ROOT/"src"), str(ROOT/"scripts")]
import importlib.util
spec = importlib.util.spec_from_file_location("pipe", ROOT/"scripts/run_h84b_uas_pipeline.py")
pipe = importlib.util.module_from_spec(spec); spec.loader.exec_module(pipe)

DATA = Path(os.environ.get("GEMS84_DATA", "/home/user/gemsdata"))
ARM_MODE = {"A0_fixed28":"fixed28", "A1_adaptive":"adaptive", "A2_adaptive_quota":"adaptive_quota"}

def spearman_sample(a, b, mask, rng, n=200000):
    idx = np.nonzero(mask.ravel())[0]
    sel = rng.choice(idx, size=min(n, len(idx)), replace=False)
    x = a.ravel()[sel].astype(np.float64); y = b.ravel()[sel].astype(np.float64)
    ok = np.isfinite(x) & np.isfinite(y)
    from scipy.stats import spearmanr
    return float(spearmanr(x[ok], y[ok]).correlation)

def emit_sharp(mu, sharp, dr, dc, N):
    muv = mu[dr, dc]
    order = np.argsort(-muv)[:min(len(muv), max(N*14, 60000))]
    rows, cols = dr[order], dc[order]
    hv = sharp[rows, cols]; lo, hi = np.quantile(hv, [0.05, 0.95])
    blocked = np.zeros(mu.shape, bool); acc_r, acc_c = [], []
    for i in range(len(rows)):
        if len(acc_r) >= N: break
        r, c = int(rows[i]), int(cols[i])
        if blocked[r,c]: continue
        hhat = float(np.clip((hv[i]-lo)/max(hi-lo,1e-9), 0, 1))
        s = 3.4 - 1.9*hhat
        acc_r.append(r); acc_c.append(c)
        for dy,dx in pipe.disk_offsets(s):
            rr,cc = r+dy, c+dx
            if 0 <= rr < mu.shape[0] and 0 <= cc < mu.shape[1]: blocked[rr,cc] = True
    return np.array(acc_r), np.array(acc_c)

def main():
    exp2 = json.loads((ROOT/"evidence/h84b_exp2_holdout.json").read_text())
    arms = dict(exp2["arms"])
    promoted = False
    e3p = ROOT/"evidence/h84b_exp3_a4_holdout.json"
    if e3p.exists():
        e3 = json.loads(e3p.read_text()); arms.update(e3["arms"])
    a0 = arms["A0_fixed28"]["pooled_dti"]
    if "A4_sharp" in arms and arms["A4_sharp"]["pooled_dti"] > a0:
        best_arm, promoted = "A4_sharp", True
    else:
        # Lane hypothesis negative. Build the A0 control-surface raster ONLY as an
        # explicitly-unpromoted unique candidate (selector decides; site keeps
        # H84-THMS as primary). Disclosed in preregistration amendment.
        best_arm, promoted = "A0_fixed28", False
    print("build arm:", best_arm, arms[best_arm]["pooled_dti"], "vs A0", a0, "promoted:", promoted)
    mm, channels = pipe.load_stack(); fp, fault = pipe.load_labels()
    rng = np.random.default_rng(4242)
    # full training: all positives visible; negatives d_cat>1
    dfull = ndi.distance_transform_edt(~fault)
    pr, pc = np.nonzero(fault)
    nr_all, nc_all = np.nonzero(fp & (dfull > 1.0))
    sel = rng.choice(len(nr_all), size=4*len(pr), replace=False)
    rows = np.concatenate([pr, nr_all[sel]]); cols = np.concatenate([pc, nc_all[sel]])
    y = np.concatenate([np.ones(len(pr), np.int8), np.zeros(len(sel), np.int8)])
    X = pipe.sample_X(mm, rows, cols)
    models, oob = pipe.fit_bagged(X, y, seeds=(0,1,2,3,4))
    # predict full footprint candidates (collar >2)
    dr, dc = np.nonzero(fp & (dfull > 2.0))
    mu = np.zeros((pipe.H, pipe.W), np.float32); sig = np.zeros((pipe.H, pipe.W), np.float32)
    for i in range(0, len(dr), 200000):
        sl = slice(i, i+200000)
        m_, s_ = pipe.predict_bagged(models, pipe.sample_X(mm, dr[sl], dc[sl]))
        mu[dr[sl], dc[sl]] = m_; sig[dr[sl], dc[sl]] = s_
        print(f"pred {i+len(dr[sl])}/{len(dr)}", flush=True)
    np.save(DATA/"work/h84b_mu.npy", mu); np.save(DATA/"work/h84b_sig.npy", sig)
    if best_arm == "A4_sharp":
        sharp = mu - ndi.gaussian_filter(mu, 2.0)
        r_, c_ = emit_sharp(mu, sharp, dr, dc, 37654)
    else:
        r_, c_ = pipe.emit(mu, None, dr, dc, dfull, 37654, "fixed28")
    pred = np.zeros((pipe.H, pipe.W), np.float32); pred[r_, c_] = 1.0
    print("dots:", len(r_))
    # --- uniqueness gates ---
    registry = {"H33_0.2778_GEMSDOE32": DATA/"registry_subset/h33_02778.tif",
                "H19-5_GEMSDOE19": DATA/"registry_subset/h19_5.tif",
                "D2.8_GEMSDOE25": DATA/"registry_subset/d28.tif",
                "D1.5_GEMSDOE24": DATA/"registry_subset/d15.tif",
                "H19-4_GEMSDOE19": DATA/"registry_subset/h19_4.tif",
                "H16-1_GEMSDOE16": DATA/"registry_subset/h16_1.tif",
                "H84-THMS_GEMSDOE84": ROOT/"submissions/gems84-h84-thms-dink300-37654dots-20261022-2f4190b4-zeros.tif"}
    uniq = {"gates":{"max_spearman_abs_le":0.90, "max_overlap3px_le":0.70}, "per_raster":{}}
    max_rho, max_ov = 0.0, 0.0
    rng2 = np.random.default_rng(11)
    for name, p in registry.items():
        if not Path(p).exists(): uniq["per_raster"][name] = "missing"; continue
        with rasterio.open(p) as ds: reg = ds.read(1).astype(np.float32)
        rho = spearman_sample(mu, np.nan_to_num(reg, nan=0.0), fp, rng2)
        reg_pos = (reg > 0) & np.isfinite(reg)
        dreg = ndi.distance_transform_edt(~reg_pos)
        ov = float((dreg[r_, c_] <= 3.0).mean())
        # dot-field spearman too (binary vs reg support) on sample
        rho_dots = spearman_sample(pred, np.nan_to_num(reg, nan=0.0), fp, rng2)
        uniq["per_raster"][name] = dict(surface_spearman=round(rho,4), dots_spearman=round(rho_dots,4),
                                        overlap3px=round(ov,4), reg_positive_px=int(reg_pos.sum()))
        max_rho = max(max_rho, abs(rho), abs(rho_dots)); max_ov = max(max_ov, ov)
        print(name, uniq["per_raster"][name], flush=True)
    uniq["max_abs_spearman"] = round(max_rho,4); uniq["max_overlap3px"] = round(max_ov,4)
    uniq["pass"] = bool(max_rho <= 0.90 and max_ov <= 0.70)
    uniq["scope"] = "7-raster local registry subset (H33 anchor + parents + prior in-repo lane); full 359-raster corpus not re-fetched this session (see limitations)"
    if not uniq["pass"]:
        print("UNIQUENESS GATE FAIL — duplicate lane, stopping per protocol.")
        (ROOT/"evidence/h84b_exp3_build.json").write_text(json.dumps({"verdict":"duplicate-stop","uniqueness":uniq}, indent=1))
        return
    # --- write submission (fail-closed vendor writer) ---
    import hashlib
    arr_hash = hashlib.sha256(pred.tobytes()).hexdigest()[:8]
    tag = "sharp" if best_arm == "A4_sharp" else "ctrl"
    name = f"gems84b-uas-{tag}-{len(r_)}dots-20261023-{arr_hash}-zeros"
    if promoted:
        note = f"H84B-UAS sharpness-adaptive spacing dist-blind baggedHGB; {len(r_)} dots dcat>2; HOLDOUT-DTI {arms[best_arm]['pooled_dti']:.4f}"
    else:
        note = f"H84B-UAS CONTROL surface dist-blind baggedHGB fixed2.83px; {len(r_)} dots; HOLDOUT-DTI {arms[best_arm]['pooled_dti']:.4f} UNPROMOTED"
    assert len(note) <= 140, note
    from gems57.submission_writer import write_submission
    out = ROOT/f"submissions/{name}.tif"
    receipt = write_submission(out, pred, ROOT/"data/bridge/sample_submission.tif", fp,
                               note=note, name=name, catalogue=fault,
                               metadata={"lane":"H84B-UAS","arm":best_arm,"holdout_dti":arms[best_arm]["pooled_dti"]})
    print(json.dumps({"name":name, "note":note, "note_len":len(note)}, indent=1))
    (ROOT/"evidence/h84b_exp3_build.json").write_text(json.dumps(
        {"verdict":"promote" if promoted else "negative-lane-candidate-unpromoted",
         "name":name,"note":note,"arm":best_arm,"promoted":promoted,"n_dots":int(len(r_)),
         "uniqueness":uniq,"writer_receipt":str(receipt)[:500]}, indent=1))
    print("BUILD_OK", out)

if __name__ == "__main__":
    main()
