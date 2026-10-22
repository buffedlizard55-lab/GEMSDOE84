#!/usr/bin/env python3
"""Build the GEMSDOE84 candidate submission GeoTIFF(s) from the fused H84-1/H84-3 field,
run the full format validator, and write the receipt. See README.md / docs/ for why this
artifact is labelled NOT RECOMMENDED FOR SCORED SUBMISSION (it is shipped for audit and
continuity only -- it did not beat the uniform-random control on our own holdout, see
evidence/h84_holdout.json and RUN_CARD.json)."""
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems84 import features as F
from gems84.submission import write_submission_tif, validate_submission

BUDGET = 44_090
NAME = "gemsdoe84-h84-fused-demag-cond-corridor-20261022T000000Z-auditonly"


def top_k_emission(field, valid, k):
    flat = np.where(valid, field, -np.inf).ravel()
    n_finite = np.isfinite(flat).sum()
    k = min(k, int(n_finite))
    idx = np.argpartition(flat, -k)[-k:]
    out = np.zeros_like(field, dtype=np.float32)
    vals = flat[idx]
    order = np.argsort(vals)
    ranks = np.empty_like(order)
    ranks[order] = np.arange(len(order))
    out.ravel()[idx] = 0.5 + 0.5 * (ranks / max(len(ranks) - 1, 1))
    return out.reshape(field.shape)


def main():
    t0 = time.time()
    bands, feat_valid, _ = F.load_stack()
    fault, label_valid, _ = F.load_labels()
    valid = F.footprint(feat_valid, label_valid)
    print(f"[{time.time()-t0:.1f}s] loaded, footprint={valid.sum()} px")

    h1 = F.h84_1_demagnetized_conductive_corridor(bands, valid)
    h3 = F.h84_3_conductivity_basement_discordance(bands, valid)
    fused = F.minmax01(np.maximum(h1, h3), valid)
    dotted = top_k_emission(fused, valid, BUDGET)
    print(f"[{time.time()-t0:.1f}s] field + emission built, budget={BUDGET} px, "
          f"mass={dotted.sum():.1f}")

    template = ROOT / "data" / "sample_submission.tif"
    out_dir = ROOT / "docs" / "downloads"

    receipts = {}
    for variant, outside in [("zeros", 0.0), ("nan", float("nan"))]:
        path = out_dir / f"{NAME}-{variant}.tif"
        w = write_submission_tif(path, dotted, valid, template, outside_value=outside)
        v = validate_submission(path, template)
        receipts[variant] = {"write": w, "validate": v}
        print(f"[{time.time()-t0:.1f}s] wrote {variant}: sha256={w['sha256'][:16]}... "
              f"all_pass={v['all_pass']} min={v['min']} max={v['max']} "
              f"n_nonfinite={v['n_nonfinite_px']}")

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{NAME}-receipts.json").write_text(json.dumps(receipts, indent=2))
    (ROOT / "registry" / "submission_receipts.json").write_text(json.dumps({
        "name": NAME, "budget_px": BUDGET, "built_utc": "2026-10-22T00:00:00Z",
        "variants": receipts,
    }, indent=2))
    print(f"\nDone in {time.time()-t0:.1f}s. Receipts: registry/submission_receipts.json")


if __name__ == "__main__":
    main()
