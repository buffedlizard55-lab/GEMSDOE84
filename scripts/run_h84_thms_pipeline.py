#!/usr/bin/env python3
"""End-to-end 3-experiment pipeline for Lane H84-THMS (GEMSDOE84).

Executes within the 3-experiment budget:
  - EXP-84-1: 96-channel single-feature leakage canary audit (Seeds 30 & 20, gate <= 0.90)
              including all 12 novel H84-THMS thermo-hydro-mechanical, 2m-probe, paleo-sinter,
              10m-3DEP breakline, fluvial-chi & up-dip advection channels.
  - EXP-84-2: Paired 6-arm dual-seed spatial-quadrant holdout (Seed 30 = 11,342 withheld,
              Seed 20 = 11,321 withheld, combined = 22,663 withheld positives) on the
              unmodified `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`),
              plus independent zero-training diagnostic on buried piedmont SGMC faults.
  - EXP-84-3: Full-catalogue 4-fold LOQO production surface, pre-placement surface
              uniqueness scan across 214 registry rasters, Collar-Decoupled (excl_px=3.0)
              Quadrant-Calibrated Dual-Head Dinkelbach Submodular 300m Kernel + Uniqueness Cap
              (0.620 < 0.70) 37,654-dot emission, and unmodified `vendor/gems57/submission_writer.py`,
              `validate.py`, and `uniqueness.py` audits.
"""
from __future__ import annotations

import gc
import glob
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import lightgbm as lgb
import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import (  # noqa: E402
    evaluate_holdout as EH,
    grid as GRID,
    holdout as HO,
    submission_writer as SW,
    uniqueness as U,
    validate as V,
)
from gems84 import dinkelbach_emitter as DE, features as F, hypotheses as HYP  # noqa: E402

RAW_DIR = ROOT / ".cache" / "gems_data"
BRIDGE_DIR = ROOT / "data" / "bridge"
PROC_DIR = RAW_DIR / "processed"
EVID_DIR = ROOT / "evidence"
DOCS_EVID_DIR = ROOT / "docs" / "evidence"
SUB_DIR = ROOT / "submissions"
DOCS_DL_DIR = ROOT / "docs" / "downloads"

BUDGET = 37_654
OVERLAP_CAP = 0.650


def log(*a) -> None:
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def draw_training_parts(
    foot: np.ndarray,
    cat_known: np.ndarray,
    tr_reg: np.ndarray,
    sets: List[Tuple[np.ndarray, np.ndarray]],
    lut: np.ndarray,
    rng: np.random.Generator,
    pos_cap: int = 46_000,
) -> List[Tuple[np.ndarray, np.ndarray, int]]:
    d_cat = ndi.distance_transform_edt(~cat_known).astype(np.float32)
    neg_base = foot & tr_reg & (d_cat > 3.0)
    hard = lut[np.flatnonzero(neg_base & (d_cat <= 15.0))]
    easy = lut[np.flatnonzero(neg_base & (d_cat > 15.0))]
    out = []
    per_set = pos_cap // len(sets)
    for sid, (hid, _M) in enumerate(sets):
        pos = lut[np.flatnonzero(hid & tr_reg & foot)]
        if pos.size > per_set:
            pos = rng.choice(pos, per_set, replace=False)
        n_neg = 2 * pos.size
        nh = min(hard.size, n_neg // 2)
        ne = min(easy.size, n_neg - nh)
        neg = np.concatenate([rng.choice(hard, nh, replace=False), rng.choice(easy, ne, replace=False)])
        rows = np.concatenate([pos, neg])
        y = np.concatenate([np.ones(pos.size, np.int8), np.zeros(neg.size, np.int8)])
        out.append((rows, y, sid))
    return out


def gather_cols(
    X_phys: np.ndarray, rows: np.ndarray, M_sc: np.ndarray | None, mode: str = "full"
) -> np.ndarray:
    s_idx = np.sort(rows)
    inv = np.argsort(np.argsort(rows))
    if mode == "phys":
        return np.asarray(X_phys[s_idx], np.float32)[inv]
    assert M_sc is not None
    if mode == "struct":
        return np.asarray(M_sc[s_idx], np.float32)[inv]
    b = np.asarray(X_phys[s_idx], np.float32)[inv]
    n = np.asarray(M_sc[s_idx], np.float32)[inv]
    return np.hstack([b, n])


def fit_and_predict_fold(
    X_phys: np.ndarray,
    parts: List[Tuple[np.ndarray, np.ndarray, int]],
    sets: List[Tuple[np.ndarray, np.ndarray]],
    te_rows: np.ndarray,
    M_vis: np.ndarray,
    mode: str,
    seed_offset: int,
) -> np.ndarray:
    Xs, ys = [], []
    for rows, y, sid in parts:
        Xs.append(gather_cols(X_phys, rows, sets[sid][1], mode))
        ys.append(y)
    Xtr, ytr = np.vstack(Xs), np.concatenate(ys)
    del Xs, ys

    m1 = lgb.LGBMClassifier(
        n_estimators=190,
        learning_rate=0.062,
        num_leaves=45,
        min_child_samples=55,
        colsample_bytree=0.72,
        subsample=0.80,
        subsample_freq=1,
        reg_alpha=1.5,
        reg_lambda=4.0,
        n_jobs=-1,
        random_state=8401 + seed_offset,
        verbose=-1,
    )
    m1.fit(Xtr, ytr)

    m2 = None
    m3 = None
    if mode == "full":
        m2 = lgb.LGBMClassifier(
            n_estimators=210,
            learning_rate=0.052,
            num_leaves=31,
            min_child_samples=80,
            colsample_bytree=0.82,
            subsample=0.85,
            subsample_freq=1,
            extra_trees=True,
            reg_alpha=2.5,
            reg_lambda=8.0,
            n_jobs=-1,
            random_state=8402 + seed_offset,
            verbose=-1,
        )
        m2.fit(Xtr, ytr)

        m3 = lgb.LGBMClassifier(
            n_estimators=180,
            learning_rate=0.058,
            num_leaves=63,
            max_depth=8,
            min_child_samples=90,
            colsample_bytree=0.60,
            subsample=0.75,
            subsample_freq=1,
            reg_alpha=3.0,
            reg_lambda=6.0,
            n_jobs=-1,
            random_state=8403 + seed_offset,
            verbose=-1,
        )
        m3.fit(Xtr, ytr)
    del Xtr, ytr

    preds = np.empty(te_rows.size, np.float32)
    for s in range(0, te_rows.size, 300_000):
        r = te_rows[s : s + 300_000]
        Xte = gather_cols(X_phys, r, M_vis, mode)
        p1 = m1.predict_proba(Xte)[:, 1].astype(np.float32)
        if m2 is not None and m3 is not None:
            p2 = m2.predict_proba(Xte)[:, 1].astype(np.float32)
            p3 = m3.predict_proba(Xte)[:, 1].astype(np.float32)
            preds[s : s + 300_000] = 0.45 * p1 + 0.35 * p2 + 0.20 * p3
        else:
            preds[s : s + 300_000] = p1
    return preds


def run_exp1_canary(
    g: GRID.Grid,
    X_phys: np.ndarray,
    phys_names: List[str],
    lut: np.ndarray,
) -> dict:
    exp1_path = EVID_DIR / "h84_exp1_canary.json"
    if exp1_path.exists():
        log("Loading cached EXP-84-1 canary report from h84_exp1_canary.json")
        return json.loads(exp1_path.read_text())
    log("=== EXP-84-1: Single-Feature Leakage Canary Audit (96 channels, Seeds 30 & 20) ===")
    foot, cat = g.footprint, g.catalogue
    d_cat = ndi.distance_transform_edt(~cat).astype(np.float32)
    sc_names = list(F.STRUCTURAL_NETWORK_NAMES) + list(F.COUPLING_INTERACTION_NAMES)
    all_names = phys_names + sc_names

    canary_by_seed = {}
    for seed in (30, 20):
        folds, _ = HO.buffered_component_draw(g, seed=seed, hide_frac=0.20, buffer_px=3)
        hidden = folds[0]["hidden_all"]
        visible = folds[0]["visible"]
        M_vis = F.compute_structural_and_coupling_fp(
            visible, foot, X_phys, phys_names, PROC_DIR / f"h84_sc_s{seed}_vis.npy"
        )
        rng = np.random.default_rng(8400 + seed)
        pos_fp = lut[np.flatnonzero(hidden & foot)]
        neg_pool = lut[np.flatnonzero(foot & (~cat) & (d_cat > 3.0))]
        neg_fp = rng.choice(neg_pool, size=min(160_000, neg_pool.size), replace=False)
        eval_rows = np.concatenate([pos_fp, neg_fp])
        y = np.concatenate([np.ones(pos_fp.size, dtype=np.int8), np.zeros(neg_fp.size, dtype=np.int8)])

        X_ev = gather_cols(X_phys, eval_rows, M_vis, mode="full")
        aucs: Dict[str, float] = {}
        for j, nm in enumerate(all_names):
            v = X_ev[:, j]
            ok = np.isfinite(v)
            if ok.sum() > 100 and np.ptp(v[ok]) > 0:
                a = float(roc_auc_score(y[ok], v[ok]))
                aucs[nm] = round(max(a, 1.0 - a), 6)
            else:
                aucs[nm] = 0.5
        del X_ev
        gc.collect()
        max_nm = max(aucs, key=aucs.get)
        max_val = aucs[max_nm]
        novel_aucs = {k: aucs[k] for k in list(F.H84_NOVEL_PHYSICAL_NAMES) + ["coup_thm_valve_bridge", "coup_seamless_scarp_beam"]}
        max_nov_nm = max(novel_aucs, key=novel_aucs.get)
        max_nov_val = novel_aucs[max_nov_nm]
        log(
            f"Seed {seed}: {len(aucs)} channels audited, max symmetric AUC = {max_val:.4f} ({max_nm}) <= 0.90; "
            f"max novel H84 AUC = {max_nov_val:.4f} ({max_nov_nm})"
        )
        if max_val > 0.90:
            raise RuntimeError(f"LEAKAGE CANARY FAILED on seed {seed}: {max_nm} = {max_val}")
        top15 = sorted(aucs.items(), key=lambda kv: kv[1], reverse=True)[:15]
        canary_by_seed[str(seed)] = {
            "withheld_positive_pixels": int(pos_fp.size),
            "negative_pixels_sampled": int(neg_fp.size),
            "n_features_tested": len(aucs),
            "max_symmetric_auc": max_val,
            "max_feature": max_nm,
            "max_novel_h84_symmetric_auc": max_nov_val,
            "max_novel_h84_feature": max_nov_nm,
            "all_below_090": bool(max_val <= 0.90),
            "top_15_features": [{"feature": k, "symmetric_auc": v} for k, v in top15],
            "novel_h84_features_auc": novel_aucs,
            "per_feature_symmetric_auc": aucs,
        }

    report = {
        "experiment": "EXP-84-1",
        "evidence_class": "LEAKAGE-CANARY",
        "evaluator_version": EH.VERSION,
        "gate_ceiling_symmetric_auc": 0.90,
        "all_seeds_passed": True,
        "n_total_channels": len(all_names),
        "n_physical_channels": len(phys_names),
        "n_structural_and_coupling_channels": len(sc_names),
        "seeds": canary_by_seed,
    }
    EVID_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_EVID_DIR.mkdir(parents=True, exist_ok=True)
    (EVID_DIR / "h84_leakage_canary.json").write_text(json.dumps(report, indent=2) + "\n")
    (EVID_DIR / "h84_exp1_canary.json").write_text(json.dumps(report, indent=2) + "\n")
    (DOCS_EVID_DIR / "h84_exp1_canary.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def get_or_fit_seed_surfaces(
    seed: int,
    g: GRID.Grid,
    X_phys: np.ndarray,
    phys_names: List[str],
    flat_fp: np.ndarray,
    lut: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[dict]]:
    foot, cat = g.footprint, g.catalogue
    quad = HO.quadrant_ids(foot)
    folds, _ = HO.buffered_component_draw(g, seed=seed, hide_frac=0.20, buffer_px=3)
    cache_npz = PROC_DIR / f"h84_surfs_seed{seed}.npz"
    if cache_npz.exists():
        log(f"Loading cached OOF surfaces for Seed {seed} from {cache_npz.name}")
        npz = np.load(cache_npz)
        return (
            npz["phys"].astype(np.float32),
            npz["struct"].astype(np.float32),
            npz["thms"].astype(np.float32),
            folds,
        )

    visible = folds[0]["visible"]
    M_vis = F.compute_structural_and_coupling_fp(
        visible, foot, X_phys, phys_names, PROC_DIR / f"h84_sc_s{seed}_vis.npy"
    )
    sets = []
    for r in range(2):
        syn_hid, syn_st = F.synthetic_withhold(visible, foot, quad, seed=seed * 10 + r)
        M_syn = F.compute_structural_and_coupling_fp(
            syn_st, foot, X_phys, phys_names, PROC_DIR / f"h84_sc_s{seed}_syn{r}.npy"
        )
        sets.append((syn_hid, M_syn))

    surf_phys = np.zeros(foot.shape, np.float32)
    surf_struct = np.zeros(foot.shape, np.float32)
    surf_thms = np.zeros(foot.shape, np.float32)

    for k, fold in enumerate(folds):
        tf = time.time()
        tr_reg = np.zeros_like(foot)
        for j, f2 in enumerate(folds):
            if j != k:
                tr_reg |= f2["region"]
        rng = np.random.default_rng(8400 + 10 * seed + k)
        parts = draw_training_parts(foot, (cat & tr_reg) | visible, tr_reg, sets, lut, rng)
        te_rows = lut[np.flatnonzero(fold["region"] & foot)]

        for mode, target_surf in (("phys", surf_phys), ("struct", surf_struct), ("full", surf_thms)):
            preds = fit_and_predict_fold(X_phys, parts, sets, te_rows, M_vis, mode, seed_offset=10 * seed + k)
            target_surf.ravel()[flat_fp[te_rows]] = preds
        gc.collect()
        log(f"Seed {seed} Fold {fold['name']} trained & predicted in {time.time() - tf:.1f}s")

    np.savez_compressed(
        cache_npz,
        phys=surf_phys.astype(np.float16),
        struct=surf_struct.astype(np.float16),
        thms=surf_thms.astype(np.float16),
    )
    return surf_phys, surf_struct, surf_thms, folds


def evaluate_piedmont_sgmc_diagnostic(
    g: GRID.Grid,
    surf_phys: np.ndarray,
    surf_thms: np.ndarray,
    dots_thms: np.ndarray,
) -> dict:
    """Zero-training external diagnostic against USGS SGMC faults strictly inside
    low-slope, off-catalogue (d_cat > 3 px) piedmont/basin terrain."""
    sgmc_path = RAW_DIR / "external" / "derived_sgmc_faults_100m_u8.tif"
    topo10_path = RAW_DIR / "external" / "topo_10m_derived_100m_u8.tif"
    if not (sgmc_path.exists() and topo10_path.exists()):
        return {"available": False}
    with rasterio.open(sgmc_path) as ds_s, rasterio.open(topo10_path) as ds_t:
        sgmc = (ds_s.read(1) > 0) & g.footprint
        slope_p90_deg = (ds_t.read(1).astype(np.float32) - 1.0) / 254.0 * 41.8245
    d_cat = ndi.distance_transform_edt(~g.catalogue).astype(np.float32)
    pied_mask = g.footprint & (d_cat > 3.0) & (slope_p90_deg <= 6.0)
    y_sgmc = sgmc[pied_mask].astype(np.int8)
    if int(y_sgmc.sum()) < 50:
        return {"available": False}
    auc_phys = float(roc_auc_score(y_sgmc, surf_phys[pied_mask]))
    auc_thms = float(roc_auc_score(y_sgmc, surf_thms[pied_mask]))
    d_sgmc_pied = ndi.distance_transform_edt(~(sgmc & pied_mask)).astype(np.float32)
    pied_dots = dots_thms & pied_mask
    hit_300m = float((d_sgmc_pied[pied_dots] <= 3.0).mean()) if pied_dots.any() else 0.0
    return {
        "schema": "gemsdoe84-piedmont-sgmc-diagnostic-v1",
        "note": "USGS SGMC faults are NEVER used in features or training; evaluated strictly as an external zero-training diagnostic in low-slope (<=6 deg) off-catalogue (d_cat > 3 px) piedmont/basin terrain.",
        "piedmont_off_catalogue_pixels": int(pied_mask.sum()),
        "piedmont_sgmc_positive_pixels": int(y_sgmc.sum()),
        "surface_roc_auc_phys72_loqo": round(auc_phys, 6),
        "surface_roc_auc_thms96_loqo": round(auc_thms, 6),
        "piedmont_emitted_dots": int(pied_dots.sum()),
        "piedmont_dot_hit_rate_within_300m": round(hit_300m, 6),
    }


def run_exp2_dualseed_holdout(
    g: GRID.Grid,
    X_phys: np.ndarray,
    phys_names: List[str],
    flat_fp: np.ndarray,
    lut: np.ndarray,
    packed_halos: np.ndarray,
    n_halos: int,
) -> dict:
    exp2_path = EVID_DIR / "h84_exp2_dualseed_holdout.json"
    if exp2_path.exists():
        log("Loading cached EXP-84-2 dual-seed holdout report from h84_exp2_dualseed_holdout.json")
        return json.loads(exp2_path.read_text())
    log("=== EXP-84-2: Paired 6-Arm Dual-Seed Spatial-Quadrant Holdout (Seeds 30 & 20) ===")
    foot = g.footprint
    arm_names = (
        "A0_random",
        "A1_phys72_poisson",
        "A2_struct24_poisson",
        "A3_thms96_poisson",
        "A4_thms96_dink_c20",
        "A5_thms96_dualhead_dink_c30",
    )
    combined_terms: Dict[str, np.ndarray] = {}
    per_seed_out = {}
    piedmont_diag = {}

    for seed in (30, 20):
        surf_phys, surf_struct, surf_thms, folds = get_or_fit_seed_surfaces(
            seed, g, X_phys, phys_names, flat_fp, lut
        )
        dist_known = ndi.distance_transform_edt(~folds[0]["masked_known"]).astype(np.float32)
        allow_20 = foot & (dist_known > 2.0)
        allow_30 = foot & (dist_known > 3.0)

        rng_rand = np.random.default_rng(999 + seed)
        surf_rand = (rng_rand.random(foot.shape, dtype=np.float32) * foot).astype(np.float32)

        dots_by_arm = {
            "A0_random": DE.emit_poisson_disk(surf_rand, allow_20, BUDGET, 2.8),
            "A1_phys72_poisson": DE.emit_poisson_disk(surf_phys, allow_20, BUDGET, 2.8),
            "A2_struct24_poisson": DE.emit_poisson_disk(surf_struct, allow_20, BUDGET, 2.8),
            "A3_thms96_poisson": DE.emit_poisson_disk(surf_thms, allow_20, BUDGET, 2.8),
            "A4_thms96_dink_c20": DE.emit_dinkelbach_submodular(
                surf_thms,
                allow_20,
                BUDGET,
                temperature=0.55,
                min_sep_px=2.45,
                packed_halos_fp=None,
                fp_lut=None,
                n_halos=0,
                overlap_cap=OVERLAP_CAP,
                dual_head_ridge=False,
            )[0],
            "A5_thms96_dualhead_dink_c30": DE.emit_dinkelbach_submodular(
                surf_thms,
                allow_30,
                BUDGET,
                temperature=0.70,
                min_sep_px=2.40,
                packed_halos_fp=packed_halos,
                fp_lut=lut,
                n_halos=n_halos,
                overlap_cap=OVERLAP_CAP,
                dual_head_ridge=True,
            )[0],
        }

        if seed == 30:
            piedmont_diag = evaluate_piedmont_sgmc_diagnostic(
                g, surf_phys, surf_thms, dots_by_arm["A5_thms96_dualhead_dink_c30"]
            )

        seed_terms: Dict[str, np.ndarray] = {}
        fold_details: Dict[str, dict] = {}
        for arm in arm_names:
            d = dots_by_arm[arm].astype(np.float32)
            acc = None
            pf = {}
            for fold in folds:
                res, t = EH.evaluate(d, fold, foot)
                pf[fold["name"]] = {
                    "dti": round(float(res["dti"]), 6),
                    "tpw": round(float(res["tpw"]), 4),
                    "fpw": round(float(res["fpw"]), 4),
                    "fnw": round(float(res["fnw"]), 4),
                    "n_truth": int(res["n_truth"]),
                    "n_emitted": int(res["n_emitted"]),
                    "coverage": round(float(res["coverage"]), 6),
                }
                acc = t if acc is None else acc + t
            seed_terms[arm] = acc
            combined_terms[arm] = acc if arm not in combined_terms else combined_terms[arm] + acc
            fold_details[arm] = pf
            dti_val = float(EH.from_terms(acc.sum(axis=0)))
            log(f"[Seed {seed}] {arm:28s} -> HOLDOUT-DTI = {dti_val:.6f}")

        summ = EH.pooled_summary(
            seed_terms, draws=2000, seed=520810 + seed, candidate="A5_thms96_dualhead_dink_c30"
        )
        per_seed_out[str(seed)] = {
            "withheld_positive_pixels": int(folds[0]["hidden_all"].sum()),
            "budget_dots": BUDGET,
            "summary": summ,
            "per_fold": fold_details,
            "fold_receipts": [f["receipt"] for f in folds],
        }

    dualseed_summary = EH.pooled_summary(
        combined_terms, draws=2000, seed=840840, candidate="A5_thms96_dualhead_dink_c30"
    )
    for arm, sc in dualseed_summary["scores"].items():
        log(
            f"[DUAL-SEED 22,663px] {arm:28s} -> HOLDOUT-DTI = {sc['dti']:.6f} "
            f"(95% CI [{sc['ci95'][0]:.4f}, {sc['ci95'][1]:.4f}])"
        )

    out = {
        "experiment": "EXP-84-2",
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": EH.VERSION,
        "implementation_sha256": EH.implementation_hashes(),
        "total_withheld_positive_pixels": int(
            dualseed_summary["scores"]["A5_thms96_dualhead_dink_c30"]["withheld_positive_pixels"]
        ),
        "dualseed_pooled_summary": dualseed_summary,
        "seeds": per_seed_out,
        "piedmont_sgmc_diagnostic": piedmont_diag,
    }
    (EVID_DIR / "h84_exp2_dualseed_holdout.json").write_text(json.dumps(out, indent=2) + "\n")
    (DOCS_EVID_DIR / "h84_exp2_dualseed_holdout.json").write_text(json.dumps(out, indent=2) + "\n")
    return out


def build_or_load_full_production_surface(
    g: GRID.Grid,
    X_phys: np.ndarray,
    phys_names: List[str],
    flat_fp: np.ndarray,
    lut: np.ndarray,
) -> np.ndarray:
    foot, cat = g.footprint, g.catalogue
    cache_npy = PROC_DIR / "h84_surf_full_loqo.f16.npy"
    if cache_npy.exists():
        log(f"Loading cached full-catalogue LOQO surface from {cache_npy.name}")
        return np.load(cache_npy).astype(np.float32)

    log("=== Fitting Full-Catalogue 4-Quadrant LOQO Production Surface (96 channels) ===")
    quad = HO.quadrant_ids(foot)
    M_full = F.compute_structural_and_coupling_fp(
        cat, foot, X_phys, phys_names, PROC_DIR / "h84_sc_full.npy"
    )
    sets = []
    for r in range(2):
        syn_hid, syn_st = F.synthetic_withhold(cat, foot, quad, seed=900 + r)
        M_syn = F.compute_structural_and_coupling_fp(
            syn_st, foot, X_phys, phys_names, PROC_DIR / f"h84_sc_full_syn{r}.npy"
        )
        sets.append((syn_hid, M_syn))

    surf_full = np.zeros(foot.shape, np.float32)
    for q in range(4):
        tf = time.time()
        te_reg = (quad == q) & foot
        tr_reg = (quad != q) & foot
        rng = np.random.default_rng(8490 + q)
        parts = draw_training_parts(foot, cat, tr_reg, sets, lut, rng, pos_cap=46_000)
        te_rows = lut[np.flatnonzero(te_reg)]
        preds = fit_and_predict_fold(X_phys, parts, sets, te_rows, M_full, mode="full", seed_offset=90 + q)
        surf_full.ravel()[flat_fp[te_rows]] = preds
        gc.collect()
        log(f"Full-catalogue Quadrant Q{q} predicted in {time.time() - tf:.1f}s")

    np.save(cache_npy, surf_full.astype(np.float16))
    return surf_full


def audit_uniqueness_against_registry(
    surf_full: np.ndarray,
    dots: np.ndarray,
    foot: np.ndarray,
    cat: np.ndarray,
    scored_dir: Path,
    packed_halos: np.ndarray,
    lut: np.ndarray,
    n_halos: int,
) -> dict:
    log("=== Auditing Pre-Placement Surface & Final Dots Against Registry Rasters ===")
    d_cat = ndi.distance_transform_edt(~cat).astype(np.float32)
    allow_20 = foot & (d_cat > 2.0)
    allow_30 = foot & (d_cat > 3.0)
    pre_dots, _ = DE.emit_dinkelbach_submodular(
        surf_full,
        allow_20,
        budget=BUDGET,
        pi_true=0.0022,
        temperature=0.70,
        fp_lambda=0.012,
        min_sep_px=2.45,
        packed_halos_fp=packed_halos,
        fp_lut=lut,
        n_halos=n_halos,
        overlap_cap=OVERLAP_CAP,
        dual_head_ridge=False,
    )

    paths = sorted(glob.glob(str(scored_dir / "*.tif")))
    rng = np.random.default_rng(8484)
    fp_idx = np.flatnonzero(foot.ravel())
    sample_idx = rng.choice(fp_idx, size=min(250_000, fp_idx.size), replace=False)

    surf_sample = surf_full.ravel()[sample_idx].astype(np.float32)
    dots_sample = dots.ravel()[sample_idx].astype(np.float32)
    pre_pts = np.flatnonzero(pre_dots)
    fin_pts = np.flatnonzero(dots)
    n_fp = int(foot.sum())
    y, x = np.ogrid[-3:4, -3:4]
    disk3 = (x * x + y * y) <= 9.0

    pre_rows = []
    fin_rows = []
    disc_max_pre_ov = 0.0
    disc_max_pre_file = ""
    disc_max_fin_ov = 0.0
    disc_max_fin_file = ""
    max_pre_rho = 0.0
    max_pre_rho_file = ""
    max_fin_rho = 0.0
    max_fin_rho_file = ""

    for p_str in paths:
        p = Path(p_str)
        try:
            with rasterio.open(p) as ds:
                if ds.shape != foot.shape:
                    continue
                arr = ds.read(1).astype(np.float32)
        except Exception:
            continue
        pos = np.isfinite(arr) & (arr > 0) & foot
        n_pos = int(pos.sum())
        if n_pos == 0:
            continue
        arr_clean = np.where(np.isfinite(arr) & foot, arr, 0.0)
        their_sample = arr_clean.ravel()[sample_idx]
        if np.ptp(their_sample) > 0:
            r_pre = float(spearmanr(surf_sample, their_sample).statistic)
            r_fin = float(spearmanr(dots_sample, their_sample).statistic)
        else:
            r_pre, r_fin = 0.0, 0.0
        if not np.isfinite(r_pre):
            r_pre = 0.0
        if not np.isfinite(r_fin):
            r_fin = 0.0

        if n_pos > 2 * BUDGET:
            vals = np.where(foot & np.isfinite(arr), arr, -np.inf).ravel()
            top_idx = np.argpartition(vals, -BUDGET)[-BUDGET:]
            b_trunc = np.zeros(foot.shape, dtype=bool)
            b_trunc.ravel()[top_idx] = True
            b_trunc &= foot & (arr > 0)
            halo = ndi.binary_dilation(b_trunc, structure=disk3)
        else:
            halo = ndi.binary_dilation(pos, structure=disk3)
        halo_cov = float(halo[allow_30].mean())
        ov_pre = float(halo.ravel()[pre_pts].mean())
        ov_fin = float(halo.ravel()[fin_pts].mean())
        is_disc = (n_pos <= int(0.05 * n_fp)) and (halo_cov < 0.70)

        if abs(r_pre) > abs(max_pre_rho):
            max_pre_rho = r_pre
            max_pre_rho_file = p.name
        if abs(r_fin) > abs(max_fin_rho):
            max_fin_rho = r_fin
            max_fin_rho_file = p.name
        if is_disc:
            if ov_pre > disc_max_pre_ov:
                disc_max_pre_ov = ov_pre
                disc_max_pre_file = p.name
            if ov_fin > disc_max_fin_ov:
                disc_max_fin_ov = ov_fin
                disc_max_fin_file = p.name

        fin_rows.append(
            {
                "submission": p.name,
                "file": p.name,
                "their_dots": n_pos,
                "halo_coverage": round(halo_cov, 6),
                "representation": "dot_field" if is_disc else "continuous_surface",
                "spearman_full_footprint": round(r_fin, 6),
                "forward_overlap": round(ov_fin, 6),
                "my_dots_within_3px_of_theirs": round(ov_fin, 6),
            }
        )
        pre_rows.append(
            {
                "submission": p.name,
                "file": p.name,
                "their_dots": n_pos,
                "halo_coverage": round(halo_cov, 6),
                "spearman_full_footprint": round(r_pre, 6),
                "forward_overlap": round(ov_pre, 6),
            }
        )

    binding_pre = U.binding_duplicate_decision(pre_rows)
    binding_fin = U.binding_duplicate_decision(fin_rows)

    # Specific key comparisons (H33 0.2778, D2.8 0.2600, H83-GVCD, H82-CSAM)
    key_comparisons = {}
    for row in fin_rows:
        fn = row["file"]
        if any(k in fn for k in ("h33-h33-2-b2", "dotted-h19-5-d2-8", "gems83-h83-gvcd", "gems82-h82-csam")):
            key_comparisons[fn] = {
                "spearman_rho": row["spearman_full_footprint"],
                "forward_overlap_3px": row["forward_overlap"],
                "their_dots": row["their_dots"],
            }

    out = {
        "evidence_class": "REGISTRY-MEASUREMENT",
        "rasters_checked": len(fin_rows),
        "thresholds": {"max_spearman_rho": 0.90, "max_3px_overlap": 0.70},
        "pre_placement_surface": {
            "unique": bool(not binding_pre["duplicate"]),
            "worst_spearman_full_footprint": round(float(max_pre_rho), 6),
            "worst_spearman_file": max_pre_rho_file,
            "worst_dot_overlap_3px": round(float(disc_max_pre_ov), 6),
            "worst_dot_overlap_file": disc_max_pre_file,
            "binding_decision": binding_pre,
        },
        "final_emitted_dots": {
            "unique": bool(not binding_fin["duplicate"]),
            "worst_spearman_full_footprint": round(float(max_fin_rho), 6),
            "worst_spearman_file": max_fin_rho_file,
            "worst_dot_overlap_3px": round(float(disc_max_fin_ov), 6),
            "worst_dot_overlap_file": disc_max_fin_file,
            "binding_decision": binding_fin,
        },
        "key_comparisons": key_comparisons,
    }
    (EVID_DIR / "h84_uniqueness.json").write_text(json.dumps(out, indent=2) + "\n")
    (DOCS_EVID_DIR / "h84_uniqueness.json").write_text(json.dumps(out, indent=2) + "\n")
    log(
        f"Uniqueness vs {len(fin_rows)} registry rasters: pre_rho={max_pre_rho:.4f}, "
        f"pre_ov={disc_max_pre_ov:.4f}; fin_rho={max_fin_rho:.4f}, fin_ov={disc_max_fin_ov:.4f}"
    )
    return out


def run_exp3_build_and_audit(
    g: GRID.Grid,
    X_phys: np.ndarray,
    phys_names: List[str],
    flat_fp: np.ndarray,
    lut: np.ndarray,
    packed_halos: np.ndarray,
    n_halos: int,
) -> Tuple[dict, dict, Path, Path]:
    foot, cat = g.footprint, g.catalogue
    surf_full = build_or_load_full_production_surface(g, X_phys, phys_names, flat_fp, lut)
    d_cat = ndi.distance_transform_edt(~cat).astype(np.float32)
    allow_30 = foot & (d_cat > 3.0)

    log("=== Emitting 37,654 Binary Dots via Dual-Head Ridge-Coherent Dinkelbach 300m Submodular Allocator ===")
    dots, dink_stats = DE.emit_dinkelbach_submodular(
        surf_full,
        allow_30,
        budget=BUDGET,
        pi_true=0.0022,
        temperature=0.70,
        fp_lambda=0.012,
        min_sep_px=2.40,
        packed_halos_fp=packed_halos,
        fp_lut=lut,
        n_halos=n_halos,
        overlap_cap=OVERLAP_CAP,
        dual_head_ridge=True,
    )

    uniq_out = audit_uniqueness_against_registry(
        surf_full, dots, foot, cat, RAW_DIR / "scored", packed_halos, lut, n_halos
    )
    if not (uniq_out["pre_placement_surface"]["unique"] and uniq_out["final_emitted_dots"]["unique"]):
        raise RuntimeError(f"Uniqueness gate failed: {uniq_out}")

    pred_f32 = np.where(dots & foot, np.float32(1.0), np.float32(0.0)).astype(np.float32)
    raw_hash8 = hashlib.sha256(pred_f32.tobytes()).hexdigest()[:8]
    sub_stem = f"gems84-h84-thms-dink300-{BUDGET}dots-20261022-{raw_hash8}-zeros"

    SUB_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DL_DIR.mkdir(parents=True, exist_ok=True)
    final_tif = SUB_DIR / f"{sub_stem}.tif"
    final_zip = SUB_DIR / f"{sub_stem}.zip"
    final_rec = SUB_DIR / f"{sub_stem}.json"

    note_str = (
        f"H84-THMS silica-valve & 1m/10m scarp-chi Dual-Head Dinkelbach 300m; "
        f"{BUDGET} dots >3px off cat; overlap<=0.650; 0 NaN"
    )[:140]
    receipt = SW.write_submission(
        final_tif,
        pred_f32,
        BRIDGE_DIR / "sample_submission.tif",
        g.footprint,
        note=note_str,
        name=sub_stem,
        catalogue=g.catalogue,
    )
    sha = receipt["sha256"]

    shutil.copy2(final_tif, DOCS_DL_DIR / final_tif.name)
    shutil.copy2(final_zip, DOCS_DL_DIR / final_zip.name)
    shutil.copy2(final_rec, DOCS_DL_DIR / final_rec.name)

    val_report = V.validate(final_tif, g.footprint, g.catalogue)
    log(f"Validator on {final_tif.name}: all_checks_passed={val_report['all_checks_passed']}")
    if not val_report["all_checks_passed"]:
        raise RuntimeError(f"Submission validator failed: {val_report}")

    d_emitted = d_cat[dots]
    dist_breakdown = {
        "total_binary_dots": int(dots.sum()),
        "min_distance_to_catalogue_px": round(float(d_emitted.min()), 4),
        "median_distance_to_catalogue_px": round(float(np.median(d_emitted)), 4),
        "mean_distance_to_catalogue_px": round(float(np.mean(d_emitted)), 4),
        "p90_distance_to_catalogue_px": round(float(np.percentile(d_emitted, 90)), 4),
        "near_continuation_300m_to_1p2km_dots": int(((d_emitted > 3.0) & (d_emitted <= 12.0)).sum()),
        "step_over_and_piedmont_1p2km_to_5km_dots": int(((d_emitted > 12.0) & (d_emitted <= 50.0)).sum()),
        "blind_intrabasin_gt_5km_dots": int((d_emitted > 50.0).sum()),
    }

    exp3_report = {
        "experiment": "EXP-84-3",
        "evidence_class": "BUILD-AND-VALIDATION",
        "submission_name": sub_stem,
        "submission_note": note_str,
        "submission_note_chars": len(note_str),
        "tif_path": f"submissions/{final_tif.name}",
        "zip_path": f"submissions/{final_zip.name}",
        "docs_tif_path": f"docs/downloads/{final_tif.name}",
        "docs_zip_path": f"docs/downloads/{final_zip.name}",
        "raster_sha256": sha,
        "zip_sha256": sha256_file(final_zip),
        "tif_size_bytes": final_tif.stat().st_size,
        "zip_size_bytes": final_zip.stat().st_size,
        "dinkelbach_stats": dink_stats,
        "distance_breakdown": dist_breakdown,
        "validator_output": val_report,
    }
    (EVID_DIR / "h84_exp3_build_and_uniqueness.json").write_text(json.dumps(exp3_report, indent=2) + "\n")
    (DOCS_EVID_DIR / "h84_exp3_build_and_uniqueness.json").write_text(json.dumps(exp3_report, indent=2) + "\n")
    return exp3_report, uniq_out, final_tif, final_zip


def main() -> int:
    t0 = time.time()
    g = GRID.load_grid(BRIDGE_DIR)
    foot = g.footprint
    phys_names, X_phys = F.load_or_build_rowmajor_f16(RAW_DIR, foot, PROC_DIR)
    flat_fp = np.flatnonzero(foot.ravel())
    lut = np.full(foot.size, -1, dtype=np.int64)
    lut[flat_fp] = np.arange(flat_fp.size)

    packed_halos, n_halos, _ = DE.build_or_load_registry_halos(
        RAW_DIR / "scored", foot, PROC_DIR, budget=BUDGET
    )

    exp1 = run_exp1_canary(g, X_phys, phys_names, lut)
    exp2 = run_exp2_dualseed_holdout(g, X_phys, phys_names, flat_fp, lut, packed_halos, n_halos)
    exp3, uniq, final_tif, final_zip = run_exp3_build_and_audit(
        g, X_phys, phys_names, flat_fp, lut, packed_halos, n_halos
    )

    s30_dti = exp2["seeds"]["30"]["summary"]["scores"]["A5_thms96_dualhead_dink_c30"]
    s20_dti = exp2["seeds"]["20"]["summary"]["scores"]["A5_thms96_dualhead_dink_c30"]
    dual_dti = exp2["dualseed_pooled_summary"]["scores"]["A5_thms96_dualhead_dink_c30"]

    beats_all = (
        s30_dti["dti"] > 0.172837
        and s20_dti["dti"] > 0.158701
        and dual_dti["dti"] > 0.206817
        and exp1["all_seeds_passed"]
        and uniq["pre_placement_surface"]["unique"]
        and uniq["final_emitted_dots"]["unique"]
        and exp3["validator_output"]["all_checks_passed"]
    )

    portal_note = (
        f"H84-THMS silica-valve & 1m/10m scarp-chi Dual-Head Dinkelbach 300m; "
        f"37654 dots >3px off cat; HOLDOUT-DTI {dual_dti['dti']:.4f}"
    )[:140]

    run_card = {
        "lane_id": "H84-THMS",
        "repo": "buffedlizard55-lab/GEMSDOE84",
        "branch": "arena/010446b1-gemsdoe84",
        "date_utc": "2026-10-22",
        "hypothesis": HYP.H84_HYPOTHESES[0]["title"] + " — " + str(HYP.H84_HYPOTHESES[0]["why_off_catalogue"]),
        "mechanism": HYP.H84_HYPOTHESES[0]["physical_signature"],
        "named_nonfault_mimic": HYP.H84_HYPOTHESES[0]["named_nonfault_mimic"],
        "preregistered_hypotheses": HYP.H84_HYPOTHESES,
        "submission_name": exp3["submission_name"],
        "portal_note": portal_note,
        "portal_note_chars": len(portal_note),
        "tif_download": exp3["docs_tif_path"],
        "zip_download": exp3["docs_zip_path"],
        "submissions_tif": exp3["tif_path"],
        "submissions_zip": exp3["zip_path"],
        "raster_sha256": exp3["raster_sha256"],
        "zip_sha256": exp3["zip_sha256"],
        "tif_size_bytes": exp3["tif_size_bytes"],
        "zip_size_bytes": exp3["zip_size_bytes"],
        "ok_to_download": bool(exp3["validator_output"]["all_checks_passed"]),
        "ok_to_submit": False,
            "submission_authorized": False,
            "selector_status": "pending" if beats_all else "blocked by holdout",
        "verdict": "promote" if beats_all else "negative",
        "verdict_banner": "PROMOTE TO SELECTOR REVIEW ONLY — NOT AUTHORIZED TO SUBMIT" if beats_all else "HOLD — DO NOT SUBMIT",
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": EH.VERSION,
        "organizer_confirmed_score": None,
        "weekly_slots_used": 0,
        "experiments_executed": 3,
        "experiment_budget_limit": 3,
        "holdout_dti": {
            "dualseed_pooled_22663px": dual_dti,
            "seed_30_11342px": s30_dti,
            "seed_20_11321px": s20_dti,
            "all_arms_dualseed": exp2["dualseed_pooled_summary"]["scores"],
            "all_arms_seed30": exp2["seeds"]["30"]["summary"]["scores"],
            "all_arms_seed20": exp2["seeds"]["20"]["summary"]["scores"],
            "paired_differences_dualseed": exp2["dualseed_pooled_summary"]["paired_differences"],
            "piedmont_sgmc_diagnostic": exp2["piedmont_sgmc_diagnostic"],
        },
        "incumbent_comparisons": {
            "vs_H33_static_ref_dualseed_0004006": round(dual_dti["dti"] - 0.004006, 6),
            "vs_H33_fold_fair_dualseed_0097493": round(dual_dti["dti"] - 0.097493, 6),
            "vs_H82_CSAM_dualseed_0165778": round(dual_dti["dti"] - 0.165778, 6),
            "vs_H85_EDTI_dualseed_0182804": round(dual_dti["dti"] - 0.182804, 6),
            "vs_H83_GVCD_dualseed_0206817": round(dual_dti["dti"] - 0.206817, 6),
            "vs_H83_GVCD_seed30_0213755": round(s30_dti["dti"] - 0.213755, 6),
            "vs_H83_GVCD_seed20_0199862": round(s20_dti["dti"] - 0.199862, 6),
        },
        "user_reported_reference_context": {
            "evidence_class": "OWNER-REPORTED (no submission-page receipt attached)",
            "GEMSDOE32_H33_2_B2_live_dti": 0.2778,
            "GEMSDOE36_PINN_live_dti": 0.2750,
            "GEMSDOE28_H36_1_live_dti": 0.2710,
            "GEMSDOE31_H27_4_live_dti": 0.2708,
            "GEMSDOE33_H33D_live_dti": 0.2632,
            "GEMSDOE25_D2_8_live_dti": 0.2600,
            "GEMSDOE70_P5_live_dti": 0.2478,
            "GEMSDOE24_D1_5_live_dti": 0.2477,
            "GEMSDOE19_H19_5_live_dti": 0.1922,
            "GEMSDOE73_MCSC_live_dti": 0.1917,
            "competition_reference_benchmark": 0.3195,
            "competition_leaderboard_top": 0.4413,
        },
        "leakage_canary": {
            "passed": exp1["all_seeds_passed"],
            "gate_limit": 0.90,
            "n_channels_tested": exp1["n_total_channels"],
            "seed_30_max_auc": exp1["seeds"]["30"]["max_symmetric_auc"],
            "seed_30_max_feature": exp1["seeds"]["30"]["max_feature"],
            "seed_30_max_novel_h84_auc": exp1["seeds"]["30"]["max_novel_h84_symmetric_auc"],
            "seed_30_max_novel_h84_feature": exp1["seeds"]["30"]["max_novel_h84_feature"],
            "seed_20_max_auc": exp1["seeds"]["20"]["max_symmetric_auc"],
            "seed_20_max_feature": exp1["seeds"]["20"]["max_feature"],
            "seed_20_max_novel_h84_auc": exp1["seeds"]["20"]["max_novel_h84_symmetric_auc"],
            "seed_20_max_novel_h84_feature": exp1["seeds"]["20"]["max_novel_h84_feature"],
        },
        "correlation_overlap_vs_registry": {
            "pre_placement_surface_unique": uniq["pre_placement_surface"]["unique"],
            "pre_placement_worst_spearman": uniq["pre_placement_surface"]["worst_spearman_full_footprint"],
            "pre_placement_worst_spearman_file": uniq["pre_placement_surface"]["worst_spearman_file"],
            "pre_placement_worst_overlap_3px": uniq["pre_placement_surface"]["worst_dot_overlap_3px"],
            "pre_placement_worst_overlap_file": uniq["pre_placement_surface"]["worst_dot_overlap_file"],
            "final_dots_unique": uniq["final_emitted_dots"]["unique"],
            "final_dots_worst_spearman": uniq["final_emitted_dots"]["worst_spearman_full_footprint"],
            "final_dots_worst_spearman_file": uniq["final_emitted_dots"]["worst_spearman_file"],
            "final_dots_worst_overlap_3px": uniq["final_emitted_dots"]["worst_dot_overlap_3px"],
            "final_dots_worst_overlap_file": uniq["final_emitted_dots"]["worst_dot_overlap_file"],
            "rasters_checked": uniq["rasters_checked"],
            "key_comparisons": uniq["key_comparisons"],
        },
        "validator_output": exp3["validator_output"],
        "distance_breakdown": exp3["distance_breakdown"],
        "dinkelbach_stats": exp3["dinkelbach_stats"],
        "elapsed_s": round(time.time() - t0, 1),
    }
    (EVID_DIR / "h84_run_card.json").write_text(json.dumps(run_card, indent=2) + "\n")
    (EVID_DIR / "run_card.json").write_text(json.dumps(run_card, indent=2) + "\n")
    (DOCS_EVID_DIR / "h84_run_card.json").write_text(json.dumps(run_card, indent=2) + "\n")
    (DOCS_EVID_DIR / "run_card.json").write_text(json.dumps(run_card, indent=2) + "\n")
    (ROOT / "docs" / "run-card.json").write_text(json.dumps(run_card, indent=2) + "\n")
    (ROOT / "run_card.json").write_text(json.dumps(run_card, indent=2) + "\n")
    log(f"=== PIPELINE COMPLETE in {run_card['elapsed_s']}s: verdict={run_card['verdict_banner']} ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
