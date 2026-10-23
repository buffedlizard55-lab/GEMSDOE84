#!/usr/bin/env python3
"""REPORT-ONLY measurements for the AXIS=SNAP variants.  Nothing here is a gate.

Three instruments, all on the repo's own shared tooling (``vendor/gems57``, whose module
hashes are recorded in the receipt so a reader can tell which evaluator produced the numbers):

1. **Catalogue hide-and-recover PROXY** -- withhold whole fault segments per spatial quadrant
   (seeds 20 and 21), mask the visible catalogue pixel-exactly, score pooled DTI
   (alpha 0.2, beta 0.8, 300 m triangular kernel).  Reported with the number of withheld
   positive pixels and a Wilson 95% CI on coverage.  The brief is explicit that this proxy
   correlated -0.87..+0.54 with live scores over 12-14 files: it is a PROXY, never a gate, and
   it is never written as a score.
2. **Leakage canary** -- single-feature AUC of each response band against the withheld
   positives.  AUC > 0.90 means stop and investigate (the brief's rule), because a band that
   separates withheld catalogue pixels almost perfectly is being fed by the catalogue itself.
3. **SGMC control** -- DTI of each emission against off-catalogue USGS SGMC map faults
   (proxy truth, prevalence not calibrated).  A control, not a target.

Usage:  python scripts/measure_snap_reports.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import evaluate_holdout as shared_eval  # noqa: E402
from gems57 import grid as shared_grid  # noqa: E402
from gems57 import holdout as shared_holdout  # noqa: E402
from gems57.metric import ALPHA, BETA, EPS, kernel  # noqa: E402
from gems84.parent import load_grid as load_parent_grid  # noqa: E402
from gems84.parent import rebuild_r0_mask  # noqa: E402
from gems84.snap import edge_response  # noqa: E402

CANARY_AUC_LIMIT = 0.90


def sgmc_control(mask: np.ndarray, truth: np.ndarray) -> dict:
    """Official-formula DTI of a binary emission against a proxy truth mask."""
    p = np.asarray(mask, bool)
    if not truth.any() or not p.any():
        return {"dti": 0.0, "tp": 0.0, "fp": float(p.sum()), "fn": float(truth.sum()),
                "n_truth": int(truth.sum()), "n_emitted": int(p.sum())}
    dp = distance_transform_edt(~p)
    tp = float(kernel(dp[truth]).sum())
    dg = distance_transform_edt(~truth)
    fp = float((1.0 - kernel(dg[p])).sum())
    fn = float(truth.sum()) - tp
    return {"dti": float(tp / (tp + ALPHA * fp + BETA * fn + EPS)), "tp": tp, "fp": fp,
            "fn": fn, "n_truth": int(truth.sum()), "n_emitted": int(p.sum())}


def auc(values: np.ndarray, y: np.ndarray) -> float:
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, values))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", default=str(ROOT / ".cache" / "gems_data"))
    ap.add_argument("--releases", default=str(ROOT / "releases"))
    ap.add_argument("--receipt", default=str(ROOT / "evidence" / "snap_reports.json"))
    args = ap.parse_args()

    t0 = time.time()
    data_dir = Path(args.data_dir)
    releases = Path(args.releases)

    # Shared-tooling grid (existing_faults.tif + sample_submission.tif, hash-checked by gems57).
    g = shared_grid.load_grid(data_dir)
    pgrid = load_parent_grid(data_dir)
    r0, _ = rebuild_r0_mask(data_dir)
    resp, diag = edge_response(data_dir / "training_features.tif", pgrid)
    per_band = diag["per_band"]

    import rasterio
    with rasterio.open(data_dir / "external" / "derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = ds.read(1) > 0
    sgmc_truth = sgmc & ~g.catalogue & ~binary_dilation(g.catalogue, iterations=3) & g.footprint

    print("[reports] building hide-and-recover folds (seeds 20, 21; mode all)", flush=True)
    ctx = shared_holdout.build_holdout(g, seeds=(20, 21), modes=("all",))

    arms: dict[str, np.ndarray] = {"R0_parent": r0}
    for receipt in sorted(releases.glob("*-snap*.json")):
        meta = json.loads(receipt.read_text())
        tif = ROOT / meta["files"]["zeros"]["path"]
        with rasterio.open(tif) as ds:
            arr = ds.read(1)
        arms[meta["id"]] = (arr > 0.5)

    proxy: dict[str, dict] = {}
    for name, mask in arms.items():
        res = shared_holdout.evaluate(mask, ctx, cell_mode="all")
        lo, hi = shared_holdout.wilson_ci(res["pooled_tp"], float(res["pooled_n_truth"]))
        proxy[name] = {
            "pooled_dti": res["pooled_dti"],
            "pooled_coverage": res["pooled_coverage"],
            "coverage_wilson95": [lo, hi],
            "withheld_positive_pixels": res["pooled_n_truth"],
            "emitted_pixels": res["emitted_pixels"],
            "on_visible_catalogue": res["on_visible_catalogue"],
            "mean_fold_dti": res["mean_fold_dti"],
            "std_fold_dti": res["std_fold_dti"],
            "per_fold_dti": res["per_fold_dti"],
            "per_quadrant_dti": res["per_quadrant_dti"],
        }
        print(f"[reports] {name:44s} PROXY pooled-DTI {res['pooled_dti']:.5f} "
              f"coverage {res['pooled_coverage']:.5f} [{lo:.5f},{hi:.5f}] "
              f"n_withheld {res['pooled_n_truth']:,}", flush=True)

    # ---- leakage canary -------------------------------------------------------------
    rng = np.random.default_rng(84)
    canary_rows = []
    features = {**{f"band:{k}": v for k, v in per_band.items()}, "fused:max(tmi_hg,grav_hg)": resp}
    for cell in ctx.cells:
        hidden = ctx.hidden_by_cell[cell.key][cell.bbox]
        active = cell.active
        pos = np.flatnonzero(hidden & active)
        neg = np.flatnonzero(active & ~hidden)
        if pos.size == 0 or neg.size == 0:
            continue
        neg = rng.choice(neg, min(len(neg), 100_000), replace=False)
        ids = np.r_[pos, neg]
        y = np.r_[np.ones(pos.size), np.zeros(neg.size)]
        for fname, arr in features.items():
            a = auc(arr[cell.bbox].ravel()[ids], y)
            canary_rows.append({
                "fold": cell.key, "feature": fname, "auc": max(a, 1.0 - a),
                "withheld_positives": int(pos.size),
                "passed": bool(max(a, 1.0 - a) <= CANARY_AUC_LIMIT),
            })
    canary_worst = max((r["auc"] for r in canary_rows), default=0.0)
    canary_pass = all(r["passed"] for r in canary_rows)
    print(f"[reports] canary worst max(AUC,1-AUC) = {canary_worst:.4f} "
          f"({'PASS' if canary_pass else 'STOP AND INVESTIGATE'})", flush=True)

    # ---- SGMC control ---------------------------------------------------------------
    sgmc_rows = {name: sgmc_control(mask, sgmc_truth) for name, mask in arms.items()}
    for name, r in sgmc_rows.items():
        print(f"[reports] {name:44s} SGMC-control DTI {r['dti']:.5f} "
              f"(proxy truth {r['n_truth']:,} px)", flush=True)

    receipt = {
        "schema_version": 1,
        "evidence_class": "PROXY (local holdout) + MODEL controls. NOT scores.",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evaluator_version": shared_eval.VERSION,
        "implementation_hashes": shared_eval.implementation_hashes(),
        "caveat": ("The catalogue hide-and-recover proxy is reported only. The brief records that "
                   "it correlated -0.87..+0.54 with live scores over 12-14 files; a file that "
                   "passed it (lidar03) scored 0.1152 live. No number here is a leaderboard "
                   "score and none of these instruments gates a slot."),
        "arms": {
            name: {
                "holdout_proxy": proxy[name],
                "sgmc_control": sgmc_rows[name],
            } for name in arms
        },
        "leakage_canary": {
            "limit": CANARY_AUC_LIMIT,
            "worst_max_auc": canary_worst,
            "passed": canary_pass,
            "rows": canary_rows,
        },
        "elapsed_s": round(time.time() - t0, 1),
    }
    Path(args.receipt).write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"[reports] receipt -> {args.receipt}  ({receipt['elapsed_s']}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
