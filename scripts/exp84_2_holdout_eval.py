#!/usr/bin/env python3
"""EXP-84-2: Paired hide-and-recover spatially-blocked holdout evaluation of Lane H84-CSAT
against allocation ablations, single-habitat ablations, fold-retrained 19-band H33 control,
and the inherited H33-2-B2 incumbent recipe on gems57-pooled-hide-v2 (seeds 20, 21).
"""
from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]

from gems57 import evaluate_holdout, grid as ggrid, holdout  # noqa: E402
from gems84 import csat, paths  # noqa: E402

SEEDS = (20, 21)
D28_SHA256 = "b00a6fb6cab70d0f957308e297695c4032ab97997a41a15ff1295add3df31a26"
B2_SHA256 = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"


def rss_mb() -> float:
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return float(line.split()[1]) / 1024.0
    except OSError:
        pass
    return -1.0


def load_registry_dots(sha256_hex: str, reg_idx: dict, fp: np.ndarray) -> np.ndarray:
    for r in reg_idx["rasters"]:
        if r["sha256"] == sha256_hex:
            with rasterio.open(r["cache_file"]) as src:
                a = src.read(1)
            return np.isfinite(a) & (a > 0) & fp
    raise FileNotFoundError(f"Registry raster {sha256_hex} not found")


def fit_retrained_h19_loqo(
    fp: np.ndarray,
    vis: np.ndarray,
    quad: np.ndarray,
    X_19: np.ndarray,
    d1_fp: np.ndarray,
    seed: int,
) -> np.ndarray:
    """Fold-clean 19-band HGB baseline (no external layers, no transfer features),
    trained strictly out-of-quadrant on visible faults vs >5 px background.
    """
    quad_fp = quad[fp]
    vis_fp = vis[fp]
    pred_fp = np.zeros(X_19.shape[0], dtype=np.float32)
    rng = np.random.default_rng(seed * 701 + 19)
    for q in range(4):
        tr_q = quad_fp != q
        pos_idx = np.flatnonzero(tr_q & vis_fp)
        neg_pool = np.flatnonzero(tr_q & (~vis_fp) & (d1_fp > 5.0))
        neg_idx = rng.choice(neg_pool, size=min(4 * len(pos_idx), len(neg_pool)), replace=False)
        X_tr = np.vstack([X_19[pos_idx], X_19[neg_idx]]).astype(np.float32)
        y_tr = np.concatenate([np.ones(len(pos_idx), dtype=np.int8), np.zeros(len(neg_idx), dtype=np.int8)])
        clf = HistGradientBoostingClassifier(
            max_iter=200,
            learning_rate=0.05,
            max_leaf_nodes=63,
            min_samples_leaf=50,
            l2_regularization=2.0,
            random_state=seed * 37 + q,
        )
        clf.fit(X_tr, y_tr)
        te_idx = np.flatnonzero(quad_fp == q)
        pred_fp[te_idx] = clf.predict_proba(X_19[te_idx].astype(np.float32))[:, 1].astype(np.float32)
    out = np.zeros(fp.shape, dtype=np.float32)
    out[fp] = pred_fp
    return out


def main() -> int:
    t0 = time.time()
    cache_dir = paths.DATA / "cache_csat"
    ev_dir = ROOT / "evidence"
    reg_idx = json.loads((ROOT / "registry" / "registry_index.json").read_text(encoding="utf-8"))
    exp1 = json.loads((ev_dir / "exp84_1_canary_and_surface.json").read_text(encoding="utf-8"))
    str_names = exp1["loqo_full_surface"]["struct_names"]

    g = ggrid.load_grid()
    fp, _ = g.footprint, g.catalogue
    X_phys, phys_names = csat.build_physics_features(fp, cache_path=cache_dir / "X_phys.npz")

    d28_dots = load_registry_dots(D28_SHA256, reg_idx, fp)
    b2_dots = load_registry_dots(B2_SHA256, reg_idx, fp)

    arm_names = [
        "csat_submod",
        "csat_poisson",
        "transfer_only",
        "concealed_only",
        "retrained_h19_control",
        "incumbent_recipe",
        "incumbent_asis",
    ]
    terms: dict[str, list[np.ndarray]] = {k: [] for k in arm_names}
    per_fold_rows = []
    seed_meta = []

    for seed in SEEDS:
        ts0 = time.time()
        print(f"[EXP-84-2] Running LOQO Dual-Habitat holdout on seed={seed} (RSS={rss_mb():.0f}MB)...", flush=True)
        folds, quad = holdout.buffered_component_draw(g, seed=seed, hide_frac=0.20, buffer_px=3)
        vis = folds[0]["visible"]
        assert not (vis & folds[0]["hidden_all"]).any(), "Leakage assertion failed"

        loqo_cache = cache_dir / f"loqo_s{seed}.npz"
        if loqo_cache.exists():
            z = np.load(loqo_cache)
            csat_2d = np.zeros(fp.shape, dtype=np.float32); csat_2d[fp] = z["csat"]
            tr_2d = np.zeros(fp.shape, dtype=np.float32); tr_2d[fp] = z["transfer"]
            co_2d = np.zeros(fp.shape, dtype=np.float32); co_2d[fp] = z["concealed"]
            d1_fp = z["d1"]
            d1_2d = np.zeros(fp.shape, dtype=np.float32); d1_2d[fp] = d1_fp
            loqo = {"csat": csat_2d, "transfer": tr_2d, "concealed": co_2d, "d1": d1_2d}
            del z
        else:
            X_str_s = np.load(cache_dir / f"X_str_s{seed}_f16.npy")
            d1_fp = np.load(cache_dir / f"d1_s{seed}_f32.npy")
            loqo = csat.fit_and_predict_loqo_surface(
                fp, vis, quad, X_phys, phys_names,
                seed=840 + seed, inner_draws=2, inner_hide_frac=0.25,
                w_tr_near=0.72, w_tr_far=0.30, w_con=0.62,
                eval_Struct_cache=(X_str_s, str_names, d1_fp),
            )
            del X_str_s
            gc.collect()
            np.savez(
                loqo_cache,
                csat=loqo["csat"][fp].astype(np.float32),
                transfer=loqo["transfer"][fp].astype(np.float32),
                concealed=loqo["concealed"][fp].astype(np.float32),
                d1=d1_fp.astype(np.float32),
            )

        d1_2d = loqo["d1"]
        allowed_csat = fp & (~vis) & (d1_2d > 2.5)

        em_csat, info_csat = csat.allocate_submodular_dots(
            loqo["csat"], fp, vis, d1_2d, quad,
            collar_px=2.5, pi0=0.0024, max_dots=42_000,
        )
        em_pois = csat.poisson_disk_dots(
            loqo["csat"], allowed_csat, budget=info_csat["n_dots"], sep_px=2.83
        )
        em_tr, info_tr = csat.allocate_submodular_dots(
            loqo["transfer"], fp, vis, d1_2d, quad,
            collar_px=2.5, pi0=0.0024, max_dots=42_000,
        )
        em_co, info_co = csat.allocate_submodular_dots(
            loqo["concealed"], fp, vis, d1_2d, quad,
            collar_px=2.5, pi0=0.0024, max_dots=42_000,
        )

        surf_h19 = fit_retrained_h19_loqo(fp, vis, quad, X_phys[:, :19], d1_fp, seed=seed)
        dvis_exact = ndi.distance_transform_edt(~vis)
        allowed_h19 = fp & (~vis) & (dvis_exact > 2.0)
        em_h19 = csat.poisson_disk_dots(surf_h19, allowed_h19, budget=38_500, sep_px=2.83)

        arms = {
            "csat_submod": em_csat,
            "csat_poisson": em_pois,
            "transfer_only": em_tr,
            "concealed_only": em_co,
            "retrained_h19_control": em_h19,
            "incumbent_recipe": d28_dots & (dvis_exact > 2.0) & (~vis),
            "incumbent_asis": b2_dots.copy(),
        }

        dot_counts = {k: int((v > 0).sum()) for k, v in arms.items()}
        seed_meta.append({
            "seed": seed,
            "csat_alloc": info_csat,
            "transfer_alloc": info_tr,
            "concealed_alloc": info_co,
            "dot_counts_full_map": dot_counts,
            "elapsed_s": round(time.time() - ts0, 2),
        })
        print(f"  [seed={seed}] dots={dot_counts} ({time.time() - ts0:.1f}s, RSS={rss_mb():.0f}MB)", flush=True)

        for f in folds:
            for arm_name, pred in arms.items():
                res, t_arr = evaluate_holdout.evaluate(pred.astype(np.float32), f, fp, block_side=200)
                terms[arm_name].append(t_arr)
                per_fold_rows.append({
                    "seed": seed,
                    "fold": f["name"],
                    "arm": arm_name,
                    "dti": round(float(res["dti"]), 6),
                    "tp": round(float(res["tp"]), 3),
                    "fp": round(float(res["fp"]), 3),
                    "fn": round(float(res["fn"]), 3),
                    "n_truth": int(res["n_truth"]),
                    "n_emitted_in_region": int(res["n_emitted"]),
                })
        del loqo, surf_h19, d1_fp, d1_2d, dvis_exact, allowed_csat, allowed_h19
        del arms, em_csat, em_pois, em_tr, em_co, em_h19, folds, vis
        gc.collect()

    stacked = {k: np.sum(np.stack(v), axis=0) for k, v in terms.items()}
    summary = evaluate_holdout.pooled_summary(stacked, draws=1000, seed=520810, candidate="csat_submod")

    print("\n=== EXP-84-2 POOLED HOLDOUT SUMMARY (gems57-pooled-hide-v2) ===", flush=True)
    for k, sc in summary["scores"].items():
        ci = sc["ci95"]
        print(
            f"  {k:24s}: DTI={sc['dti']:.5f}  95%CI=[{ci[0]:.5f}, {ci[1]:.5f}]  "
            f"(withheld+={sc['withheld_positive_pixels']})",
            flush=True,
        )
    print("\n--- Paired Differences (csat_submod minus comparator) ---", flush=True)
    for k, pd in summary["paired_differences"].items():
        ci = pd["ci95"]
        print(f"  vs {k:24s}: delta={pd['delta']:+.5f}  95%CI=[{ci[0]:+.5f}, {ci[1]:+.5f}]", flush=True)

    inc_diff = summary["paired_differences"]["incumbent_recipe"]
    h19_diff = summary["paired_differences"]["retrained_h19_control"]
    beats_incumbent_recipe = bool(inc_diff["delta"] > 0.0 and inc_diff["ci95"][0] > 0.0)
    beats_retrained_h19 = bool(h19_diff["delta"] > 0.0 and h19_diff["ci95"][0] > 0.0)

    out = {
        "experiment_id": "EXP-84-2",
        "lane": "H84-CSAT",
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": evaluate_holdout.VERSION,
        "implementation_hashes": evaluate_holdout.implementation_hashes(),
        "split": "holdout.buffered_component_draw (whole 8-connected components, 3 px context buffer, 12 px eroded quadrants)",
        "seeds": list(SEEDS),
        "bootstrap_draws": 1000,
        "bootstrap_block_m": 20000,
        "summary": summary,
        "seed_emissions": seed_meta,
        "per_fold": per_fold_rows,
        "gate_checks": {
            "beats_incumbent_recipe_ci95_gt_0": beats_incumbent_recipe,
            "beats_retrained_h19_control_ci95_gt_0": beats_retrained_h19,
        },
        "elapsed_s": round(time.time() - t0, 2),
    }
    out_path = ev_dir / "exp84_2_holdout_eval.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\n[EXP-84-2] Saved {out_path} in {out['elapsed_s']:.1f}s (RSS={rss_mb():.0f}MB).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
