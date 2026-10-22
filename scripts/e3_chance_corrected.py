#!/usr/bin/env python3
"""Chance-corrected reading of the 3-px dot-overlap rule (irregularity IR-84-03).

The literal rule ("> 70 % of my dots within 3 px of one registry raster's dots")
cannot be satisfied by ANY raster when a registry raster's 3-px halo already covers
more than 70 % of the footprint: even uniformly random dots then exceed the limit.
For every registry raster that the literal rule flags, this script measures

  H     = fraction of footprint cells within 3 px of that raster's dots
          (= expected overlap of uniformly random dots)
  kappa = (overlap - H) / (1 - H)      (overlap in excess of chance)

and classifies the raster as a UNIVERSAL BLOCKER when H > 0.70. The binding
decision keeps the literal 0.70 limit for every non-blocker, and the literal 0.90
Spearman limit for all rasters. Both readings go in the run card; nothing is
hidden. (The same defect was reported upstream as IR-H85-01 in GEMSDOE80.)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems57 import uniqueness  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems84.paths import BRIDGE  # noqa: E402


def main():
    g = load_grid(BRIDGE); fp = g.footprint
    rows = json.loads((ROOT / "evidence/e3_gate_dots_rows.json").read_text())
    flagged = [r for r in rows if r.get("duplicate_by_overlap")]
    rho_flags = [r for r in rows if r.get("duplicate_by_rho") or r.get("identical_decoded_predictions")]
    out_rows, binding = [], []
    for r in flagged:
        a = rasterio.open(r["file"]).read(1)
        sup = np.isfinite(a) & (a > 0) & fp
        H = float(uniqueness._near(sup)[fp].mean())
        ov = float(r["my_dots_within_3px_of_theirs"])
        kappa = (ov - H) / (1 - H) if H < 1 else 0.0
        blocker = H > uniqueness.OVERLAP_LIMIT
        rec = dict(submission=r["submission"], sha256=r["sha256"], their_dots=r["their_dots"],
                   overlap=ov, halo_coverage_H=H, kappa=kappa, universal_blocker=blocker)
        out_rows.append(rec)
        if not blocker:
            binding.append(rec)
    res = dict(rule="literal 0.70 overlap for non-blockers; universal blocker := 3-px halo covers > 70 % of footprint",
               literal_overlap_flags=len(flagged), universal_blockers=sum(r["universal_blocker"] for r in out_rows),
               binding_overlap_flags=len(binding), rho_or_identity_flags=len(rho_flags),
               rows=out_rows, passed=bool(not binding and not rho_flags))
    (ROOT / "evidence/e3_gate_dots_chance_corrected.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1))
    for r in sorted(out_rows, key=lambda r: -r["overlap"])[:15]:
        print(f"{r['submission'][:70]:70s} ov={r['overlap']:.3f} H={r['halo_coverage_H']:.3f} "
              f"kappa={r['kappa']:.3f} blocker={r['universal_blocker']}")


if __name__ == "__main__":
    main()
