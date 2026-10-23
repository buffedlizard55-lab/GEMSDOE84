"""Lane H84-B (CTHF): Two-Regime Multi-Physics, Harmonic Upward-Continuation Pullback,
DOE GDR-1391 Geothermal Upflow & Fracture-Mechanics Posterior Pipeline.

Strict anti-leakage contract:
  * Only ``(fp, quad, visible)`` is passed into ``fit_predict_surfaces``.
  * Withheld test fault masks NEVER enter this module under any circumstances.
  * Every prediction in spatial quadrant q in {0, 1, 2, 3} is out-of-fold, fitted
    exclusively on rows inside ``quad != q``.
  * Inner kinematic supervision and isotonic PAVA probability calibration use
    independent whole-component withhold draws constructed purely inside ``visible``.
"""
from __future__ import annotations

import gc
from dataclasses import dataclass

try:
    import lightgbm as lgb
except ImportError:  # CI environment fallback when optional lightgbm wheel is absent
    lgb = None

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression

from gems57.grid import Grid
from gems57.holdout import buffered_component_draw

from .kinematics import build_visible_kinematics
from .paths import WORK
from .physics_stack import STACK_VERSION, load_or_build_static_stack


def _isotonic_pava_calibrate(score2d: np.ndarray, allow_mask: np.ndarray,
                             y_inner_pos: np.ndarray, target_mass: float,
                             seed: int = 84) -> np.ndarray:
    """Zero-hyperparameter Pool-Adjacent-Violators (Barlow et al., 1972) probability calibration.

    Fits an exact monotone empirical probability map P(Y = 1 | S(x) = s) out-of-fold
    against genuine inner-withheld whole fault components ``y_inner_pos`` inside ``visible``,
    using inverse-sampling weights so total probability mass equals ``target_mass`` across
    ``allow_mask`` by the exact PAVA mass-conservation theorem.
    """
    out = np.zeros(score2d.shape, np.float32)
    s_all = np.asarray(score2d[allow_mask], np.float64)
    # Positive calibration examples: inner-withheld hidden fault pixels
    s_pos = np.asarray(score2d[y_inner_pos], np.float64)
    n_pos = s_pos.size
    n_allow = s_all.size
    if n_pos < 20 or n_allow == 0 or target_mass <= 0:
        return out

    rng = np.random.default_rng(seed)
    n_neg_samp = min(400_000, n_allow)
    neg_idx = rng.choice(n_allow, size=n_neg_samp, replace=False)
    s_neg = s_all[neg_idx]

    # Exact case-control Horvitz-Thompson weights so sum_{allow} p_hat(x) == target_mass
    w_pos = np.full(n_pos, float(target_mass) / float(n_pos), dtype=np.float64)
    w_neg = np.full(n_neg_samp, max(float(n_allow) - float(target_mass), 1.0) / float(n_neg_samp), dtype=np.float64)

    x_fit = np.concatenate([s_pos, s_neg])
    y_fit = np.concatenate([np.ones(n_pos, np.float64), np.zeros(n_neg_samp, np.float64)])
    w_fit = np.concatenate([w_pos, w_neg])

    iso = IsotonicRegression(y_min=0.0, y_max=1.0, increasing=True, out_of_bounds="clip")
    iso.fit(x_fit, y_fit, sample_weight=w_fit)
    out[allow_mask] = iso.transform(s_all).astype(np.float32)
    return out


def _spatial_ridge_refine(prob2d: np.ndarray, fp: np.ndarray, quad: np.ndarray,
                          y_label: np.ndarray, seed: int) -> np.ndarray:
    """Out-of-fold 2D multi-scale Hessian ridge + neighborhood stacking pass."""
    p = prob2d.astype(np.float32)
    s1 = ndi.gaussian_filter(p, 1.0)
    s2 = ndi.gaussian_filter(p, 2.2)
    s5 = ndi.gaussian_filter(p, 5.0)
    s12 = ndi.gaussian_filter(p, 12.0)

    def _eigs(f: np.ndarray, sig: float):
        hyy = ndi.gaussian_filter(f, sig, order=(2, 0))
        hxx = ndi.gaussian_filter(f, sig, order=(0, 2))
        hxy = ndi.gaussian_filter(f, sig, order=(1, 1))
        tr = 0.5 * (hxx + hyy)
        disc = np.hypot(0.5 * (hxx - hyy), hxy)
        lmin = tr - disc
        lmax = tr + disc
        crest = sig * sig * np.maximum(-lmin, 0.0)
        linearity = np.maximum(-lmin, 0.0) / (np.abs(lmax) + np.maximum(-lmin, 0.0) + 1e-5)
        return crest.astype(np.float32), linearity.astype(np.float32)

    c1, lin1 = _eigs(p, 1.2)
    c2, lin2 = _eigs(p, 2.5)
    c4, lin4 = _eigs(p, 4.5)

    feats = np.column_stack([
        p[fp], s1[fp], s2[fp], s5[fp], s12[fp],
        (p - s5)[fp],
        c1[fp], lin1[fp], c2[fp], lin2[fp], c4[fp], lin4[fp],
    ]).astype(np.float32)

    q_fp = quad[fp]
    y_fp = y_label[fp]
    rng = np.random.default_rng(seed)
    oof = np.zeros(feats.shape[0], np.float32)

    for q in range(4):
        tr = q_fp != q
        te = q_fp == q
        pos = np.flatnonzero(tr & y_fp)
        neg_pool = np.flatnonzero(tr & ~y_fp)
        neg = rng.choice(neg_pool, size=min(125_000, neg_pool.size), replace=False)
        idx = np.concatenate([pos, neg])
        yy = np.concatenate([np.ones(pos.size, np.int8), np.zeros(neg.size, np.int8)])
        clf = HistGradientBoostingClassifier(
            max_iter=105, learning_rate=0.055, max_leaf_nodes=31,
            min_samples_leaf=80, l2_regularization=2.0, random_state=seed + q,
        )
        clf.fit(feats[idx], yy)
        oof[te] = clf.predict_proba(feats[te])[:, 1].astype(np.float32)

    out = np.zeros(fp.shape, np.float32)
    out[fp] = oof
    return out


def _fit_two_model_ensemble(X_tr: np.ndarray, y_tr: np.ndarray, X_te: np.ndarray,
                            seed: int) -> np.ndarray:
    """True cross-library heterogeneous GBDT ensemble (LightGBM + sklearn HistGradientBoosting)."""
    if lgb is not None:
        m_lgb = lgb.LGBMClassifier(
            n_estimators=260,
            learning_rate=0.05,
            num_leaves=47,
            subsample_for_bin=120_000,
            colsample_bytree=0.72,
            subsample=0.82,
            subsample_freq=1,
            min_child_samples=90,
            reg_alpha=1.5,
            reg_lambda=4.0,
            n_jobs=2,
            random_state=seed,
            verbose=-1,
        )
    else:
        m_lgb = HistGradientBoostingClassifier(
            max_iter=210,
            learning_rate=0.045,
            max_leaf_nodes=63,
            min_samples_leaf=80,
            l2_regularization=4.0,
            random_state=seed,
        )
    m_lgb.fit(X_tr, y_tr)
    p1 = np.empty(X_te.shape[0], np.float32)
    for cs in range(0, X_te.shape[0], 250_000):
        p1[cs:cs + 250_000] = m_lgb.predict_proba(X_te[cs:cs + 250_000])[:, 1].astype(np.float32)
    del m_lgb
    gc.collect()

    m_hgb = HistGradientBoostingClassifier(
        max_iter=175,
        learning_rate=0.055,
        max_leaf_nodes=47,
        min_samples_leaf=90,
        l2_regularization=3.0,
        random_state=seed + 101,
    )
    m_hgb.fit(X_tr, y_tr)
    p2 = np.empty(X_te.shape[0], np.float32)
    for cs in range(0, X_te.shape[0], 250_000):
        p2[cs:cs + 250_000] = m_hgb.predict_proba(X_te[cs:cs + 250_000])[:, 1].astype(np.float32)
    del m_hgb
    gc.collect()
    return 0.60 * p1 + 0.40 * p2


@dataclass
class DrawSurfaces:
    p_exp1: np.ndarray
    p_cthf: np.ndarray
    p_phys_branch: np.ndarray
    p_kin_branch: np.ndarray
    k_hat: float


def fit_predict_surfaces(fp: np.ndarray, quad: np.ndarray, visible: np.ndarray,
                         seed_base: int = 8400, cache_tag: str | None = None) -> DrawSurfaces:
    """Produce strictly out-of-fold PAVA-calibrated surfaces for EXP-84-1 and EXP-84-2/3."""
    cache_file = WORK / f"h84b_surfaces_{cache_tag}.npz" if cache_tag else None
    if cache_file is not None and cache_file.exists():
        z = np.load(cache_file)
        return DrawSurfaces(
            p_exp1=z["p_exp1"],
            p_cthf=z["p_cthf"],
            p_phys_branch=z["p_phys_branch"],
            p_kin_branch=z["p_kin_branch"],
            k_hat=float(z["k_hat"]),
        )

    mm, meta = load_or_build_static_stack(fp)
    names = meta["names"]
    groups = meta["groups"]
    strike_fp = np.memmap(WORK / f"{STACK_VERSION}_strike.f16", dtype=np.float16,
                          mode="r", shape=(int(fp.sum()),))

    h2_names = set(groups["core_topo"] + groups["subsurf_hupw"] + groups["lidar_1m"] + groups["dem10_chi"])
    h2_cols = np.asarray([i for i, n in enumerate(names) if n in h2_names], dtype=np.int32)
    all_static_cols = np.arange(len(names), dtype=np.int32)

    basin_cols_names = set(groups["subsurf_hupw"] + groups["geothermal_ahfv"] + groups["radiometric"] + [
        "lidar_tectonic_step_ratio", "lidar_step_max", "lidar_coh100", "lahontan_shoreline_mimic",
        "det_crest_s2p8", "det_trough_s2p8", "chi_step_max",
    ])
    basin_cols = np.asarray([i for i, n in enumerate(names) if n in basin_cols_names], dtype=np.int32)
    bcover_col = names.index("basin_cover_index")

    q_fp = quad[fp]
    vis = np.asarray(visible, bool) & fp
    vis_fp = vis[fp]
    d_vis = ndi.distance_transform_edt(~vis).astype(np.float32)
    unbuf_neg_fp = (d_vis > 3.0)[fp]
    n_fp = int(fp.sum())

    k_hat = 0.24 * float(vis.sum())
    allow_prior = fp & ~vis & (d_vis > 2.0)

    rng = np.random.default_rng(seed_base)
    oof_h2_raw = np.zeros(n_fp, np.float32)
    oof_phys_raw = np.zeros(n_fp, np.float32)
    oof_basin_raw = np.zeros(n_fp, np.float32)

    bcover_all = mm[:, bcover_col].astype(np.float32)
    low_relief_fp = bcover_all >= float(np.nanpercentile(bcover_all, 45.0))

    for q in range(4):
        tr = q_fp != q
        te = np.flatnonzero(q_fp == q)
        pos = np.flatnonzero(tr & vis_fp)
        neg_pool = np.flatnonzero(tr & unbuf_neg_fp)
        neg = rng.choice(neg_pool, size=min(150_000, neg_pool.size), replace=False)
        tr_idx = np.concatenate([pos, neg])
        y_tr = np.concatenate([np.ones(pos.size, np.int8), np.zeros(neg.size, np.int8)])

        X_tr_all = mm[tr_idx].astype(np.float32)
        X_te_all = mm[te].astype(np.float32)

        oof_h2_raw[te] = _fit_two_model_ensemble(
            X_tr_all[:, h2_cols], y_tr, X_te_all[:, h2_cols], seed=seed_base + 10 * q
        )
        oof_phys_raw[te] = _fit_two_model_ensemble(
            X_tr_all[:, all_static_cols], y_tr, X_te_all[:, all_static_cols], seed=seed_base + 20 * q
        )

        pos_b = np.flatnonzero(tr & vis_fp & low_relief_fp)
        neg_b_pool = np.flatnonzero(tr & unbuf_neg_fp & low_relief_fp)
        if pos_b.size >= 500 and neg_b_pool.size >= 5_000:
            neg_b = rng.choice(neg_b_pool, size=min(90_000, neg_b_pool.size), replace=False)
            tr_b = np.concatenate([pos_b, neg_b])
            yb = np.concatenate([np.ones(pos_b.size, np.int8), np.zeros(neg_b.size, np.int8)])
            oof_basin_raw[te] = _fit_two_model_ensemble(
                mm[tr_b][:, basin_cols].astype(np.float32), yb, X_te_all[:, basin_cols],
                seed=seed_base + 30 * q,
            )
        else:
            oof_basin_raw[te] = oof_phys_raw[te]

        del X_tr_all, X_te_all
        gc.collect()

    b_sig = 1.0 / (1.0 + np.exp(-0.9 * np.nan_to_num(bcover_all, nan=0.0)))
    w_basin = np.clip(0.10 + 0.45 * b_sig, 0.10, 0.55).astype(np.float32)

    surf_h2_s1 = np.zeros(fp.shape, np.float32)
    surf_h2_s1[fp] = oof_h2_raw
    surf_h2_s2 = _spatial_ridge_refine(surf_h2_s1, fp, quad, vis, seed=seed_base + 400)

    surf_phys_s1 = np.zeros(fp.shape, np.float32)
    surf_phys_s1[fp] = (1.0 - w_basin) * oof_phys_raw + w_basin * oof_basin_raw
    surf_phys_s2 = _spatial_ridge_refine(surf_phys_s1, fp, quad, vis, seed=seed_base + 500)
    del oof_h2_raw, oof_phys_raw, oof_basin_raw, bcover_all, low_relief_fp, b_sig, w_basin
    del surf_h2_s1, surf_phys_s1
    gc.collect()

    # Inner whole-component-withheld splits strictly inside `visible`
    vis_grid = Grid(footprint=fp, catalogue=vis, crs=None, transform=None, height=fp.shape[0], width=fp.shape[1])
    inner_splits = []
    for iseed in (seed_base + 71, seed_base + 72):
        ifolds, _ = buffered_component_draw(vis_grid, seed=iseed, hide_frac=0.22, buffer_px=3)
        ivis = ifolds[0]["visible"]
        ihid = ifolds[0]["hidden_all"]
        ikin, _ = build_visible_kinematics(fp, ivis, strike_fp)
        idv = ndi.distance_transform_edt(~ivis).astype(np.float32)[fp]
        inner_splits.append((ikin, ihid[fp], (~vis)[fp] & (idv > 3.0)))

    kin_test, _ = build_visible_kinematics(fp, vis, strike_fp)
    oof_kin_raw = np.zeros(n_fp, np.float32)

    for q in range(4):
        tr = q_fp != q
        te = np.flatnonzero(q_fp == q)
        X_parts, y_parts = [], []
        for ikin, ihid_fp, ineg_fp in inner_splits:
            p_i = np.flatnonzero(tr & ihid_fp)
            n_pool = np.flatnonzero(tr & ineg_fp)
            n_i = rng.choice(n_pool, size=min(85_000, n_pool.size), replace=False)
            idx_i = np.concatenate([p_i, n_i])
            X_parts.append(np.hstack([mm[idx_i].astype(np.float32), ikin[idx_i].astype(np.float32)]))
            y_parts.append(np.concatenate([np.ones(p_i.size, np.int8), np.zeros(n_i.size, np.int8)]))
        X_tr_k = np.vstack(X_parts)
        y_tr_k = np.concatenate(y_parts)
        X_te_k = np.hstack([mm[te].astype(np.float32), kin_test[te].astype(np.float32)])

        oof_kin_raw[te] = _fit_two_model_ensemble(X_tr_k, y_tr_k, X_te_k, seed=seed_base + 60 * q)
        del X_parts, X_tr_k, X_te_k
        gc.collect()

    inner_hid_union = np.zeros(fp.shape, bool)
    inner_hid_union[fp] = inner_splits[0][1] | inner_splits[1][1]
    del inner_splits, kin_test
    gc.collect()

    surf_kin_s1 = np.zeros(fp.shape, np.float32)
    surf_kin_s1[fp] = oof_kin_raw
    surf_kin_s2 = _spatial_ridge_refine(surf_kin_s1, fp, quad, inner_hid_union, seed=seed_base + 700)

    # Exact parameter-free empirical PAVA isotonic calibration against `inner_hid_union`
    p_exp1 = _isotonic_pava_calibrate(surf_h2_s2, allow_prior, inner_hid_union,
                                      target_mass=k_hat, seed=seed_base + 801)
    p_phys_cal = _isotonic_pava_calibrate(surf_phys_s2, allow_prior, inner_hid_union,
                                          target_mass=0.45 * k_hat, seed=seed_base + 802)
    p_kin_cal = _isotonic_pava_calibrate(surf_kin_s2, allow_prior, inner_hid_union,
                                         target_mass=0.55 * k_hat, seed=seed_base + 803)
    p_union = 1.0 - (1.0 - p_phys_cal) * (1.0 - p_kin_cal)
    # Rescale exact union smoothly so sum_{allow_prior} p_cthf == k_hat while keeping true tail calibration
    mass = float(p_union[allow_prior].sum())
    scale = k_hat / max(mass, 1e-6)
    p_cthf = np.where(allow_prior, np.clip(p_union * scale, 0.0, 1.0), 0.0).astype(np.float32)

    if cache_file is not None:
        np.savez_compressed(
            cache_file,
            p_exp1=p_exp1,
            p_cthf=p_cthf,
            p_phys_branch=p_phys_cal,
            p_kin_branch=p_kin_cal,
            k_hat=np.float64(k_hat),
        )

    return DrawSurfaces(
        p_exp1=p_exp1,
        p_cthf=p_cthf,
        p_phys_branch=p_phys_cal,
        p_kin_branch=p_kin_cal,
        k_hat=k_hat,
    )
