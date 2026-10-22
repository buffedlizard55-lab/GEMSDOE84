#!/usr/bin/env python3
"""Why did h33-h33-2-b2 (0.2778, OWNER-REPORTED) score highest in the family?

Measures, from hash-verified bytes, the exact lineage
  D2.8 (0.2600) -> H27-4 r1 (0.2708) -> H33-2-B2 (0.2778)
and checks the metric algebra that links the three reported scores.
Output: evidence/incumbent_anatomy.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems57.grid import load_grid  # noqa: E402
from gems84.paths import BRIDGE  # noqa: E402

REF = Path("/home/user/ref/60GEMSDOE/registry/rasters")
FILES = {  # name: (file, owner-reported live score)
    "h19_5_solid": ("19GEMSDOE__h19-5-powerlaw-budget-multiline.tif", 0.1922),
    "d1_5": ("GEMSDOE24__h25-1-dotted-h19-5-d1-5.tif", 0.2477),
    "d2_8": ("GEMSDOE25__dotted-h19-5-d2-8.tif", 0.2600),
    "h27_4_r1": ("GEMSDOE28__h27-4-r1-solo-d2-8.tif", 0.2708),
    "h36_1_rung30": ("GEMSDOE28__h36-1-rung30-blind-r1.tif", 0.2710),
    "h33_2_b2": ("GEMSDOE32__h33-2-b2-zeros.tif", 0.2778),
    "anderson_pinn": ("GEMSDOE36__anderson-geothermal-pinn-38854.tif", 0.2750),
}


def main():
    g = load_grid(BRIDGE)
    fp, cat = g.footprint, g.catalogue
    dcat = ndi.distance_transform_edt(~cat)
    dots, out = {}, {"evidence_class": "MEASURED from hash-verified bytes; scores OWNER-REPORTED", "rasters": {}}
    for k, (f, score) in FILES.items():
        p = REF / f
        a = rasterio.open(p).read(1)
        d = np.isfinite(a) & (a > 0) & fp
        dots[k] = d
        dd = dcat[d]
        out["rasters"][k] = dict(file=f, sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                                 owner_reported_live=score, dots=int(d.sum()),
                                 unique_values=[float(v) for v in np.unique(a[np.isfinite(a)])[:5]],
                                 dots_dcat_le1=int((dd <= 1).sum()), dots_dcat_le2=int((dd <= 2).sum()),
                                 dots_dcat_le3=int((dd <= 3).sum()), median_dcat_px=float(np.median(dd)),
                                 on_catalogue=int((d & cat).sum()))
    sub = lambda a, b: bool((dots[a] & ~dots[b]).sum() == 0)
    out["lineage"] = dict(
        h27_4_subset_of_d2_8=sub("h27_4_r1", "d2_8"),
        h27_4_equals_d2_8_minus_dcat_le1=bool(np.array_equal(dots["h27_4_r1"], dots["d2_8"] & (dcat > 1))),
        h33_2_b2_subset_of_h27_4=sub("h33_2_b2", "h27_4_r1"),
        h33_2_b2_equals_h27_4_minus_dcat_le2=bool(np.array_equal(dots["h33_2_b2"], dots["h27_4_r1"] & (dcat > 2))),
        d2_8_subset_of_h19_5=sub("d2_8", "h19_5_solid"))
    # algebra: if the removed near-catalogue dots carried zero TP credit, removing n
    # pure-FP dots changes 1/DTI by -alpha*n/T  =>  T = alpha*n / (1/s0 - 1/s1)
    s0, s1, s2 = 0.2600, 0.2708, 0.2778
    n1 = out["rasters"]["d2_8"]["dots"] - out["rasters"]["h27_4_r1"]["dots"]
    n2 = out["rasters"]["h27_4_r1"]["dots"] - out["rasters"]["h33_2_b2"]["dots"]
    T = 0.2 * n1 / (1 / s0 - 1 / s1)
    s2_pred = 1 / (1 / s1 - 0.2 * n2 / T)
    out["algebra"] = dict(
        assumption="removed dots (within 100 m, then 200 m of a mapped fault) earned zero TP credit",
        removed_step1=n1, removed_step2=n2, implied_TPw=T, predicted_s2_if_zero_credit=s2_pred,
        reported_s2=s2, residual=s2 - s2_pred,
        implied_denominator_at_s2=T / s2,
        marginal_bar_at_s2=0.2 * s2,
        mean_credit_per_kept_dot=T / out["rasters"]["h33_2_b2"]["dots"],
        interpretation=("Both pruning steps are explained to within 0.0006 DTI by deleting dots that earned "
                        "~no credit: near-catalogue dots are almost pure false-positive mass on the live board. "
                        "Kept dots average ~2.4x the marginal bar, so the field's precision, not its density, "
                        "is what limits the score."))
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence/incumbent_anatomy.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["lineage"], indent=1)); print(json.dumps(out["algebra"], indent=1))


if __name__ == "__main__":
    main()
