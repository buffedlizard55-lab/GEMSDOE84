#!/usr/bin/env python3
"""REPORT-ONLY instruments (brief v2 section 6): catalogue hide-and-recover
PROXY and SGMC control for R0 and this session's releases.  Never gates.

Hide-and-recover here scores each static dot set as-is against the pooled
gems57 two-seed whole-segment folds (seeds 20/21, mode=all).  Known bias:
the R0 lineage computed catalogue distances from the FULL catalogue, so its
dots also avoid the withheld segments -- the PROXY understates near-trace
recovery for pruned files and historically correlates only -0.87..+0.54 with
live scores (brief s3).  Read it as an instrument check, not evidence about
which variant to submit.  No features are fitted in this session, so the
single-feature AUC leakage canary is not applicable (no feature exists).

Usage: python scripts/proxy_report.py   (needs $GEMS84_DATA parent inputs)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import metric  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.holdout import build_holdout  # noqa: E402

DATA = Path(os.environ.get("GEMS84_DATA", "/home/user/gemsdata"))
SGMC_SHA = "643cbe992ef4ba37588fb469163ed8291e3ceb23d6c1f78a3cfaa462430c2da0"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_dots(p: Path) -> np.ndarray:
    with rasterio.open(p) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0)


def pooled(cell_terms: list[tuple[float, float, float]]) -> float:
    tp = sum(t[0] for t in cell_terms)
    fp = sum(t[1] for t in cell_terms)
    fn = sum(t[2] for t in cell_terms)
    return metric.dti_from_components(tp, fp, fn)


def main() -> None:
    grid = load_grid(ROOT / "data" / "bridge")
    ctx = build_holdout(grid, seeds=(20, 21), modes=("all",))
    cells = ctx.cells_of("all")
    cands: dict[str, np.ndarray] = {"R0": load_dots(DATA / "parent" / "r0-zeros.tif")}
    for p in sorted((ROOT / "releases").glob("*.tif")):
        if not p.name.endswith("-zeros.tif"):
            cands[p.stem] = load_dots(p)
    terms: dict[str, list[tuple[float, float, float]]] = {}
    n_truth = 0
    for name, dots_mask in cands.items():
        terms[name] = []
        for c in cells:
            pred = dots_mask[c.bbox]
            truth = np.zeros(pred.shape, dtype=bool)
            truth[c.truth_yx] = True
            r = metric.dti_binary(pred, truth, valid=c.active)
            terms[name].append((r["tp"], r["fp"], r["fn"]))
            if name == "R0":
                n_truth += int(truth[c.active].sum())
    rng = np.random.default_rng(20261023)
    out: dict = {
        "class": "PROXY (local holdout) -- report only, never a gate, never a score",
        "evaluator": "vendor/gems57 pooled hide-and-recover, seeds=[20,21], mode=all, static dots as-is",
        "n_withheld_positives": n_truth,
        "bias_note": "lineage prune used the full catalogue incl. withheld segments; PROXY understates pruned files",
        "candidates": {},
    }
    for name in cands:
        base = pooled(terms[name])
        diffs = []
        if name != "R0":
            idx = np.arange(len(cells))
            for _ in range(1000):
                pick = rng.choice(idx, size=len(idx), replace=True)
                diffs.append(pooled([terms[name][i] for i in pick])
                             - pooled([terms["R0"][i] for i in pick]))
        out["candidates"][name] = {
            "holdout_dti_PROXY": base,
            "paired_diff_vs_R0_PROXY": None if name == "R0" else {
                "mean": float(np.mean(diffs)),
                "ci95_cell_bootstrap": [float(np.percentile(diffs, 2.5)),
                                        float(np.percentile(diffs, 97.5))]},
        }
    sgmc_path = DATA / "external" / "derived_sgmc_faults_100m_u8.tif"
    if sgmc_path.is_file() and sha256(sgmc_path) == SGMC_SHA:
        with rasterio.open(sgmc_path) as ds:
            sg = ds.read(1)
        truth = (sg > 0) & grid.footprint & ~grid.catalogue
        out["sgmc_control_PROXY"] = {
            "n_sgmc_off_catalogue_px": int(truth.sum()),
            **{name: metric.dti_binary(mask, truth, valid=grid.footprint,
                                        known=grid.catalogue)["dti"]
               for name, mask in cands.items()},
            "note": "SGMC geologic-map faults are a control surface, not scored truth",
        }
    else:
        out["sgmc_control_PROXY"] = "UNVERIFIED (pinned SGMC raster absent or hash mismatch)"
    dest = ROOT / "ledger" / "proxy_report_20261023.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
