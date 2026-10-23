#!/usr/bin/env python3
"""EXP-84-1: Build/cache 38 physics + 20 transfer channels, run 58-feature leakage canary,
fit full-catalogue LOQO H84-CSAT surface, and audit pre-placement surface uniqueness across
all 1,160 SHA-256-verified registry rasters.
"""
from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]

from gems57 import grid as ggrid, holdout  # noqa: E402
from gems57.uniqueness import RHO_LIMIT, records_from_index  # noqa: E402
from gems84 import csat, paths  # noqa: E402


def rss_mb() -> float:
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return float(line.split()[1]) / 1024.0
    except OSError:
        pass
    return -1.0


def exact_full_footprint_spearman_scan(surface_2d: np.ndarray, fp: np.ndarray, reg_idx_path: Path) -> dict:
    """Exact full-footprint Spearman rank correlation of pre-placement surface vs all 1,160 rasters."""
    t0 = time.time()
    idx = json.loads(reg_idx_path.read_text(encoding="utf-8"))
    records, complete, source_errors = records_from_index(idx)
    vals = surface_2d[fp].astype(np.float32)
    ranks = rankdata(vals).astype(np.float64)
    ranks -= ranks.mean()
    norm = float(np.linalg.norm(ranks))
    n = len(vals)
    if norm <= 0.0:
        raise RuntimeError("Degenerate zero-variance pre-placement surface")

    rows = []
    errors = []
    for i, rec in enumerate(records):
        p = Path(rec["file"])
        if not p.is_absolute():
            p = ROOT / p
        try:
            with rasterio.open(p) as src:
                theirs = src.read(1).astype(np.float32)
            theirs = np.where(np.isfinite(theirs), theirs, 0.0)
            tv = theirs[fp]
            if np.ptp(tv) == 0:
                rho = None
            elif np.all((tv == 0.0) | (tv == 1.0)):
                tb = tv > 0.0
                nt = int(tb.sum())
                rho = float(ranks[tb].sum() / (norm * np.sqrt(nt * (n - nt) / n)))
            else:
                tr = rankdata(tv).astype(np.float64)
                tr -= tr.mean()
                rho = float(np.dot(ranks, tr) / (norm * np.linalg.norm(tr)))
            rows.append({
                "repo": rec.get("repo"),
                "submission": rec.get("submission"),
                "sha256": rec.get("sha256"),
                "their_dots": int((tv > 0).sum()),
                "spearman_full_footprint": rho,
                "abs_spearman": abs(rho) if rho is not None else None,
            })
        except Exception as exc:
            errors.append({"submission": rec.get("submission"), "error": str(exc)})
        if (i + 1) % 300 == 0:
            print(f"  [surface-scan] {i + 1}/{len(records)} rasters ({time.time() - t0:.1f}s, RSS={rss_mb():.0f}MB)", flush=True)

    valid_rows = [r for r in rows if r["spearman_full_footprint"] is not None]
    worst_pos = max(valid_rows, key=lambda r: r["spearman_full_footprint"])
    worst_abs = max(valid_rows, key=lambda r: r["abs_spearman"])
    top10 = sorted(valid_rows, key=lambda r: r["abs_spearman"], reverse=True)[:10]
    passed = (
        complete
        and len(errors) == 0
        and len(source_errors) == 0
        and len(rows) == len(records)
        and worst_abs["abs_spearman"] <= RHO_LIMIT
    )
    return {
        "evidence_class": "REGISTRY-MEASUREMENT",
        "stage": "pre_placement_surface",
        "rasters_expected": len(records),
        "rasters_checked": len(rows),
        "errors": errors,
        "complete_accessible_scan": bool(complete and not errors and not source_errors),
        "rho_limit": RHO_LIMIT,
        "worst_spearman_full_footprint": float(worst_pos["spearman_full_footprint"]),
        "worst_spearman_submission": worst_pos["submission"],
        "worst_abs_spearman": float(worst_abs["abs_spearman"]),
        "worst_abs_spearman_submission": worst_abs["submission"],
        "top_10_by_abs_spearman": top10,
        "passed": bool(passed),
        "elapsed_s": round(time.time() - t0, 2),
    }


def main() -> int:
    t0 = time.time()
    data_dir = paths.DATA
    cache_dir = data_dir / "cache_csat"
    cache_dir.mkdir(parents=True, exist_ok=True)
    ev_dir = ROOT / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)

    print(f"[EXP-84-1] Loading grid & footprint from {data_dir} (RSS={rss_mb():.0f}MB)...", flush=True)
    g = ggrid.load_grid()
    fp = g.footprint
    cat = g.catalogue
    quad = holdout.quadrant_ids(fp)

    # 1. Build & cache 38 catalogue-blind physics channels
    print(f"[EXP-84-1] Building 38 catalogue-blind physics channels (RSS={rss_mb():.0f}MB)...", flush=True)
    tp0 = time.time()
    X_phys, phys_names = csat.build_physics_features(fp, cache_path=cache_dir / "X_phys.npz")
    print(f"  X_phys shape={X_phys.shape} dtype={X_phys.dtype} built in {time.time() - tp0:.1f}s (RSS={rss_mb():.0f}MB)", flush=True)

    # 2. Build & cache transfer features for holdout seeds (20, 21) and run 58-column leakage canary
    rng = np.random.default_rng(20261022)
    pos_rows_all = []
    neg_rows_all = []
    str_names_ref: list[str] = []

    fp_idx_2d = np.full(fp.shape, -1, dtype=np.int32)
    fp_idx_2d[fp] = np.arange(int(fp.sum()), dtype=np.int32)

    for seed in (20, 21):
        ts0 = time.time()
        folds, _ = holdout.buffered_component_draw(g, seed=seed, hide_frac=0.20, buffer_px=3)
        vis_s = folds[0]["visible"]
        for q_chk in range(1, 4):
            assert np.array_equal(vis_s, folds[q_chk]["visible"]), "Expected identical visible map across folds of seed"
        assert not (vis_s & folds[0]["hidden_all"]).any(), "Leakage check failed: visible intersects hidden_all"

        X_str_s, str_names, d1_s = csat.build_transfer_features(vis_s, fp, X_phys, phys_names)
        str_names_ref = str_names
        np.save(cache_dir / f"X_str_s{seed}_f16.npy", X_str_s)
        np.save(cache_dir / f"d1_s{seed}_f32.npy", d1_s)
        print(f"  X_str seed={seed} shape={X_str_s.shape} built in {time.time() - ts0:.1f}s (RSS={rss_mb():.0f}MB)", flush=True)

        for fold in folds:
            scored = fold["region"] & fp & (~fold["masked_known"])
            pos_m = scored & fold["truth"]
            neg_m = scored & (~fold["truth"])
            p_ids = fp_idx_2d[pos_m]
            n_pool = fp_idx_2d[neg_m]
            n_sub = rng.choice(n_pool, size=min(31250, len(n_pool)), replace=False)
            pos_rows_all.append(np.hstack([X_phys[p_ids], X_str_s[p_ids]]))
            neg_rows_all.append(np.hstack([X_phys[n_sub], X_str_s[n_sub]]))
        del X_str_s, d1_s
        gc.collect()

    X_pos = np.vstack(pos_rows_all).astype(np.float32)
    X_neg = np.vstack(neg_rows_all).astype(np.float32)
    del pos_rows_all, neg_rows_all
    y_can = np.concatenate([np.ones(len(X_pos), dtype=np.int8), np.zeros(len(X_neg), dtype=np.int8)])
    X_can = np.vstack([X_pos, X_neg])
    all_names = phys_names + str_names_ref
    assert X_can.shape[1] == 58 and len(all_names) == 58

    canary_rows = []
    for j, name in enumerate(all_names):
        col = X_can[:, j]
        auc = float(roc_auc_score(y_can, col))
        disc = max(auc, 1.0 - auc)
        canary_rows.append({
            "index": j,
            "feature": name,
            "group": "physics_blind" if j < 38 else "visible_transfer",
            "auc": round(auc, 5),
            "discriminability": round(disc, 5),
        })
    del X_can, X_pos, X_neg
    gc.collect()

    worst_canary = max(canary_rows, key=lambda r: r["discriminability"])
    canary_passed = worst_canary["discriminability"] <= 0.90
    print(
        f"[EXP-84-1] 58-feature leakage canary: max_disc={worst_canary['discriminability']:.5f} "
        f"({worst_canary['feature']}) passed={canary_passed}",
        flush=True,
    )
    if not canary_passed:
        raise RuntimeError(f"FAIL-CLOSED LEAKAGE CANARY TRIGGERED: {worst_canary}")

    # 3. Fit full-catalogue LOQO H84-CSAT surface
    print(f"[EXP-84-1] Fitting full-catalogue LOQO Dual-Habitat surface (RSS={rss_mb():.0f}MB)...", flush=True)
    tl0 = time.time()
    loqo_full = csat.fit_and_predict_loqo_surface(
        fp, cat, quad, X_phys, phys_names,
        seed=84, inner_draws=2, inner_hide_frac=0.25,
        w_tr_near=0.72, w_tr_far=0.30, w_con=0.62,
    )
    csat_full_2d = loqo_full["csat"]
    np.save(cache_dir / "csat_full_surf_f32.npy", csat_full_2d[fp].astype(np.float32))
    np.save(cache_dir / "ptr_full_surf_f32.npy", loqo_full["transfer"][fp].astype(np.float32))
    np.save(cache_dir / "pco_full_surf_f32.npy", loqo_full["concealed"][fp].astype(np.float32))
    np.save(cache_dir / "d1_full_f32.npy", loqo_full["d1"][fp].astype(np.float32))
    print(
        f"  Full-catalogue LOQO fit completed in {time.time() - tl0:.1f}s "
        f"(mean={float(csat_full_2d[fp].mean()):.4f}, max={float(csat_full_2d[fp].max()):.4f}, RSS={rss_mb():.0f}MB)",
        flush=True,
    )

    # 4. Pre-placement surface uniqueness audit across all 1,160 registry rasters
    print("[EXP-84-1] Scanning pre-placement surface Spearman against 1,160 registry rasters...", flush=True)
    surf_audit = exact_full_footprint_spearman_scan(
        csat_full_2d, fp, ROOT / "registry" / "registry_index.json"
    )
    print(
        f"[EXP-84-1] Pre-placement surface scan: checked={surf_audit['rasters_checked']}, "
        f"worst_abs_rho={surf_audit['worst_abs_spearman']:.5f} ({surf_audit['worst_abs_spearman_submission']}), "
        f"passed={surf_audit['passed']}",
        flush=True,
    )
    if not surf_audit["passed"]:
        raise RuntimeError(f"FAIL-CLOSED PRE-PLACEMENT SURFACE UNIQUENESS TRIGGERED: {surf_audit['worst_abs_spearman_submission']}")

    top_phys = sorted([r for r in canary_rows if r["group"] == "physics_blind"], key=lambda r: r["discriminability"], reverse=True)[:10]
    top_str = sorted([r for r in canary_rows if r["group"] == "visible_transfer"], key=lambda r: r["discriminability"], reverse=True)[:10]

    report = {
        "experiment_id": "EXP-84-1",
        "lane": "H84-CSAT",
        "evidence_class": "CANARY-AND-REGISTRY-MEASUREMENT",
        "footprint_pixels": int(fp.sum()),
        "n_physics_features": len(phys_names),
        "n_transfer_features": len(str_names_ref),
        "n_total_features": len(all_names),
        "leakage_canary": {
            "evaluator": "gems57-pooled-hide-v2-domain",
            "seeds": [20, 21],
            "withheld_positives_scored": int(y_can.sum()),
            "sampled_negatives_scored": int((y_can == 0).sum()),
            "auc_ceiling": 0.90,
            "max_discriminability": worst_canary["discriminability"],
            "max_feature": worst_canary["feature"],
            "passed": canary_passed,
            "top_10_physics_blind": top_phys,
            "top_10_visible_transfer": top_str,
            "all_features": canary_rows,
        },
        "loqo_full_surface": {
            "struct_names": loqo_full["struct_names"],
            "mean_in_footprint": float(csat_full_2d[fp].mean()),
            "p95_in_footprint": float(np.percentile(csat_full_2d[fp], 95)),
            "p99_in_footprint": float(np.percentile(csat_full_2d[fp], 99)),
            "max_in_footprint": float(csat_full_2d[fp].max()),
        },
        "pre_placement_surface_uniqueness": surf_audit,
        "elapsed_s": round(time.time() - t0, 2),
    }
    out_path = ev_dir / "exp84_1_canary_and_surface.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[EXP-84-1] Saved {out_path} in {report['elapsed_s']:.1f}s (RSS={rss_mb():.0f}MB).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
