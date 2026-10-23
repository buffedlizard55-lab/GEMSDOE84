#!/usr/bin/env python3
"""AXIS=CONCENTRATION single-axis variants of Parent R0 (``h33-h33-2-b2``), Brief v2 s5.

Blocks are 50x50 px (5x5 km) squares from origin (0,0); a block is eligible when >=50%
of it lies inside the footprint (2,046 blocks).  The block prior is the mean of the
parent ranking surface ``q`` (recorded GEMSDOE32 recipe, rebuilt exactly as in the
MASS/PRUNE sessions) over footprint pixels.  Count is held at 37,654; spacing
(r_min = 2.8 px), collar (retained R0 dots unchanged, refills at d_cat >= 3 px) and the
per-dot ranking are held fixed -- only the km-scale geography of the dot set moves:

    conc-t50-m3765   move 3,765 dots (10.00%): drop lowest-gain R0 dots in bottom-half
                     prior blocks, greedy-refill in top-half blocks.
    conc-t25-m2400   move 2,400 dots ( 6.37%): bottom-half -> top-quartile blocks
                     (stronger contrast; 2,496-dot greedy capacity measured pre-build).
    spread-m2400     move 2,400 dots ( 6.37%): top-quartile -> bottom-half blocks
                     (reverse / falsification arm; capacity 2,494).

Capacity note (measured, recorded in the receipt): R0 is a maximal 2.8 px packing, so
high-prior blocks accept few extra on-ridge dots -- the canonical thinned candidate
pool places at most 4,287 / 2,496 extra dots in top-half / top-quartile 5 km blocks.
Move sizes above are the largest round doses inside that envelope; no off-ridge pool
was invented to force larger moves.

Also asserted here (fail-closed): the rebuilt ranking's bottom-2,545 R0 dots equal the
removal set of the merged PRUNE arm ``prune-dgt1in`` bit-for-bit (canonical-ranking
identity), and the shipped MASS drop masks' concordance with this ranking is measured
and recorded (they are NOT bit-reproducible from the recorded recipe; see IR-DEC-13).
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT)]

from gems57 import evaluate_holdout, holdout as gems57_holdout  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems84.concentration import (  # noqa: E402
    BLOCK_PX,
    block_dot_shares,
    block_prior,
    donor_recipient_masks,
    lowest_gain_dots,
)
from gems84.snap import density_cv  # noqa: E402
from research.upstream.src.gems32.h33 import (  # noqa: E402
    H33_BUILDERS,
    lidar_scarp_composite,
    rank_surface,
)
from scripts.build_r0_variants import (  # noqa: E402
    BAND_NAMES,
    EXPECTED_R0_DIGEST8,
    EXPECTED_R0_DOTS,
    EXPECTED_R0_NAN_SHA256,
    EXPECTED_R0_ZEROS_SHA256,
    PARENT_SCORE_CLAIM,
    compute_exact_marginal_gains,
    dot_thin,
    ensure_unpacked_bands,
    file_sha256,
    greedy_add_dots,
    rank_auc,
    verify_manifest,
    verify_written_pair_from_disk,
    write_submission_pair,
)

DATE_TAG = time.strftime("%Y%m%d", time.gmtime())
PARENT_ID = "h33-h33-2-b2"
AXIS = "CONCENTRATION"
SEED = 520810
ANCHOR_D = 18262.37421006327  # evidence/incumbent_anatomy.json:algebra (MODEL anchor)


def scenario(n_move: int, c_in: tuple, c_out: tuple) -> dict:
    """Fixed-count swap scenario dDTI ~= (1-0.2s)*n*(c_in-c_out)/D (MODEL, never a score)."""
    f = (1.0 - 0.2 * PARENT_SCORE_CLAIM) * n_move / ANCHOR_D
    return {
        "n_move": n_move,
        "assumed_mean_live_credit_in": list(c_in),
        "assumed_mean_live_credit_out": list(c_out),
        "predicted_live_change": [round(f * (c_in[0] - c_out[1]), 4),
                                  round(f * (c_in[1] - c_out[0]), 4)],
        "basis": "credit-scenario on incumbent_anatomy anchor (D=18262.37 at s=0.2778 "
                 "CLAIM; marginal bar 0.0556); c ranges bracket second-tier refill dots "
                 "vs weakest retained-class dots. No ranking-unit sum is divided by D "
                 "(IR-DEC-11).",
    }


ARMS = [
    {
        "key": "t50m3765", "value": "5km-t50-move3765", "slug": "conc5km-t50-m3765",
        "donor": "bot50", "recip": "top50", "n_move": 3765,
        "model": scenario(3765, (0.035, 0.085), (0.020, 0.055)),
        "form_note": "h33-h33-2-b2; CONC 5km move 3765 (10%) low->high prior blocks, 37654; pred -0.004..+0.013",
        "mechanism_card": {
            "hypothesis": "Shifting 10% of R0's dots from the bottom-half 5 km blocks (by "
                          "mean parent field q) into the top half at fixed count gains DTI "
                          "because Basin-and-Range faulting is clustered at km scale "
                          "(systems, relays, step-overs): blocks where independent physics "
                          "already agree host denser unmapped structure per ridge pixel.",
            "mechanism": "Per-dot ranking saturates locally (maximal 2.8 px packing); the "
                         "remaining allocation question is geographic. Donor dots are the "
                         "lowest exact-gain R0 dots in low-prior blocks; refills are the "
                         "greedy top-gain canonical-pool dots in high-prior blocks at "
                         "d_cat>=3 px, so only block membership changes.",
            "non_fault_mimic": "Block q tracks data, not faults: GeoDAWN Area 1 vs Area 2 "
                               "line spacing, lidar/radiometric coverage edges, and "
                               "lineament-rich volcanic/caldera terrains raise mean q "
                               "without raising throughgoing-fault density.",
            "predicted_sign_and_size": "Bracketing, positive center: -0.004 to +0.013 DTI "
                                       "(MODEL credit scenario).",
            "falsifier": "Live <= R0 CLAIM - 0.002 while spread-m2400 >= R0 falsifies the "
                         "clustering prior at 5 km: high-q blocks are then "
                         "catalogue-complete (already mapped), and residual truth sits "
                         "in quiet blocks.",
        },
    },
    {
        "key": "t25m2400", "value": "5km-t25-move2400", "slug": "conc5km-t25-m2400",
        "donor": "bot50", "recip": "top25", "n_move": 2400,
        "model": scenario(2400, (0.040, 0.090), (0.020, 0.055)),
        "form_note": "h33-h33-2-b2; CONC 5km move 2400 (6.4%) low->top-quartile blocks, 37654; pred -0.002..+0.009",
        "mechanism_card": {
            "hypothesis": "Same mechanism, stronger per-dot contrast: refills only into "
                          "the top-quartile prior blocks. If the km prior is real, this "
                          "arm should match or beat conc-t50 per receipt despite moving "
                          "36% fewer dots; if capacity-driven second-tier placements "
                          "dominate, it will not.",
            "mechanism": "Top-quartile blocks are the most packing-saturated (greedy "
                         "capacity 2,496 dots measured), so dose is capacity-limited to "
                         "2,400; the arm therefore also prices saturation: refills must "
                         "use residual ridge gaps between retained dots.",
            "non_fault_mimic": "Saturated blocks are saturated because ridge detectors "
                               "fire densely on non-fault lineament swarms (joint sets, "
                               "flow banding, yardang/dune lineations).",
            "predicted_sign_and_size": "Bracketing: -0.002 to +0.009 DTI (MODEL). "
                                       "Pre-registered >= spread-m2400; unordered vs t50 "
                                       "(contrast vs dose).",
            "falsifier": "Live < conc-t50 receipt by >=0.002 with conc-t50 > R0: "
                         "concentration helps only before saturation; top-quartile "
                         "infill is kernel-redundant with retained dots.",
        },
    },
    {
        "key": "spreadm2400", "value": "spread5km-move2400", "slug": "spread5km-b50-m2400",
        "donor": "top25", "recip": "bot50", "n_move": 2400,
        "model": scenario(2400, (0.015, 0.050), (0.030, 0.065)),
        "form_note": "h33-h33-2-b2; SPREAD 5km move 2400 (6.4%) high->low prior blocks, 37654; pred -0.006..+0.003",
        "mechanism_card": {
            "hypothesis": "Reverse arm: spreading mass into low-prior blocks loses DTI "
                          "under the clustering hypothesis. It wins only if the "
                          "completeness mechanism dominates -- high-q blocks are "
                          "already captured by USGS/INGENIOUS mapping (masked from "
                          "labels), so undiscovered faults disproportionately remain "
                          "where the field and the catalogue are quiet.",
            "mechanism": "Mirror construction of conc-t25 (same donor/recipient block "
                         "sets, roles swapped, same pool/selector/spacing), giving a "
                         "signed dose pair at equal moved count.",
            "non_fault_mimic": "Low-q blocks may be low because thick Quaternary cover "
                               "hides scarps (blind faults present but field-blind) -- "
                               "the genuine signal this arm hopes for if it wins; "
                               "mimicked by playa/evaporite lineaments in the same "
                               "basins.",
            "predicted_sign_and_size": "Negative center: -0.006 to +0.003 DTI (MODEL).",
            "falsifier": "Live >= both CONC receipts: the km block prior is "
                         "anti-informative for NEW-fault labels; allocation should "
                         "flatten or invert the prior (completeness beats clustering).",
        },
    },
]


def conc_arm(base, donor_reg, recip_reg, dist, gain_base, cand_pool_base, q, offs,
             n_move, require_exact=True):
    """One fixed-count block move.  Returns (mask, info).  Fold-clean calls pass
    ``require_exact=False`` and accept the measured greedy capacity."""
    n_move = min(n_move, int((base & donor_reg).sum()))
    drop = lowest_gain_dots(base, donor_reg, gain_base, n_move)
    kept = base & ~drop
    _, k1, _, _ = compute_exact_marginal_gains(kept, q)
    cand = cand_pool_base & recip_reg & (dist >= 3.0) & (~kept)
    try:
        out, gains = greedy_add_dots(kept, cand, q, k1, offs, n_add=n_move, r_min=2.8)
    except RuntimeError as exc:
        if require_exact:
            raise
        cap = int(str(exc).split("only found ")[1])
        drop = lowest_gain_dots(base, donor_reg, gain_base, cap)
        kept = base & ~drop
        _, k1, _, _ = compute_exact_marginal_gains(kept, q)
        cand = cand_pool_base & recip_reg & (dist >= 3.0) & (~kept)
        out, gains = greedy_add_dots(kept, cand, q, k1, offs, n_add=cap, r_min=2.8)
        n_move = cap
    if int(out.sum()) != int(base.sum()):
        raise RuntimeError("CONC arm count drift")
    return out, {"n_moved": n_move,
                 "removed_gain_mean": round(float(gain_base[drop].mean()), 6),
                 "refill_gain_mean": round(float(np.mean(gains)), 6),
                 "refill_gain_min": round(float(np.min(gains)), 6),
                 "cand_pool_in_recip": int(cand.sum())}


def run_report_only(data_dir, bands_dir, foot, cat, d28, r0, cand_pool_base, q,
                    surfaces, h33_union, lidar, corrob_count, regions, live_masks):
    """REPORT-ONLY: fold-clean hide-and-recover PROXY, leakage canary, SGMC control."""
    grid = load_grid(data_dir)
    folds_20, _ = gems57_holdout.buffered_component_draw(grid, seed=20)
    folds_21, _ = gems57_holdout.buffered_component_draw(grid, seed=21)
    all_folds = [(20, f) for f in folds_20] + [(21, f) for f in folds_21]
    offs = [(dy, dx, float(1.0 - np.hypot(dy, dx) / 3.0))
            for dy in range(-2, 3) for dx in range(-2, 3) if np.hypot(dy, dx) < 3.0]

    pos, neg = {}, {}
    for seed_val, folds in ((20, folds_20), (21, folds_21)):
        p = np.zeros(foot.shape, bool)
        n = np.zeros(foot.shape, bool)
        for f in folds:
            active = foot & f["region"] & (~f["masked_known"])
            p |= active & f["truth"]
            n |= active & (~f["truth"])
        pos[seed_val], neg[seed_val] = p, n
    feats = {b: np.load(bands_dir / f"{b}.npy") for b in BAND_NAMES}
    feats.update({"H33-A": surfaces["H33-A"], "H33-B": surfaces["H33-B"],
                  "H33-C": surfaces["H33-C"], "H33-D": surfaces["H33-D"]})
    feats.update({"h33_union": h33_union, "lidar_scarp_composite": lidar,
                  "corrob_count": corrob_count, "q_posterior": q})
    canary = []
    for name, arr in feats.items():
        a20, a21 = rank_auc(arr, pos[20], neg[20]), rank_auc(arr, pos[21], neg[21])
        m = 0.5 * (a20 + a21)
        canary.append({"feature": name, "auc_seed20": round(a20, 4),
                       "auc_seed21": round(a21, 4), "auc_mean": round(m, 4),
                       "abs_strength": round(max(m, 1.0 - m), 4)})
    del feats
    canary.sort(key=lambda x: x["abs_strength"], reverse=True)
    max_auc = max(f["abs_strength"] for f in canary)
    if max_auc > 0.90:
        raise RuntimeError(f"STOP: leakage canary {max_auc} > 0.90 -- investigate")

    fold_clean, fold_moves = {}, {}
    for seed_val, folds in ((20, folds_20), (21, folds_21)):
        vis = folds[0]["visible"]
        dvis = distance_transform_edt(~vis)
        r0_vis = d28 & (dvis > 2.0)
        gain_vis, _, _, _ = compute_exact_marginal_gains(r0_vis, q)
        arms = {"R0": r0_vis}
        fold_moves[seed_val] = {}
        for spec in ARMS:
            n_scaled = int(round(spec["n_move"] * int(r0_vis.sum()) / EXPECTED_R0_DOTS))
            arms[spec["key"]], info = conc_arm(
                r0_vis, regions[spec["donor"]], regions[spec["recip"]], dvis, gain_vis,
                cand_pool_base, q, offs, n_scaled, require_exact=False)
            fold_moves[seed_val][spec["key"]] = info["n_moved"]
        fold_clean[seed_val] = arms

    shipped = {"R0": r0, **live_masks}
    terms_clean, terms_ship = {}, {}
    for arm in shipped:
        acc_c = acc_s = None
        for seed_val, fold in all_folds:
            _, t = evaluate_holdout.evaluate(
                fold_clean[seed_val][arm].astype(np.float32), fold, foot)
            acc_c = t if acc_c is None else acc_c + t
            _, t = evaluate_holdout.evaluate(shipped[arm].astype(np.float32), fold, foot)
            acc_s = t if acc_s is None else acc_s + t
        terms_clean[arm], terms_ship[arm] = acc_c, acc_s
    summ_clean = evaluate_holdout.pooled_summary(terms_clean, draws=1000, seed=SEED,
                                                 candidate="t50m3765")
    summ_ship = evaluate_holdout.pooled_summary(terms_ship, draws=1000, seed=SEED,
                                                candidate="t50m3765")

    with rasterio.open(data_dir / "external" / "derived_sgmc_faults_100m_u8.tif") as ds:
        sgm = (ds.read(1) > 0) & foot
    truth = sgm & (~cat) & (~binary_dilation(cat, iterations=3)) & foot
    sy, sx = np.nonzero(truth)
    n_t = int(sy.size)
    k_dg = np.clip(1.0 - distance_transform_edt(~truth) / 3.0, 0, 1).astype(np.float32)
    sgmc = {}
    for arm, mask in shipped.items():
        tp = float(np.clip(1.0 - distance_transform_edt(~mask)[sy, sx] / 3.0, 0, 1).sum())
        fp = float((1.0 - k_dg[mask]).sum())
        cov = tp / n_t
        sgmc[arm] = {"evidence_label": "PROXY",
                     "sgmc_off_catalogue_truth_pixels": n_t,
                     "emitted_dots": int(mask.sum()),
                     "sgmc_raw_dti": round(tp / (tp + 0.2 * fp + 0.8 * (n_t - tp) + 1e-6), 6),
                     "sgmc_coverage": round(cov, 6),
                     "sgmc_prevalence_calibrated_dti": round(
                         cov * 12691.0 / (0.2 * int(mask.sum()) + 0.8 * 12691.0 + 1e-6), 6)}
    return {
        "evidence_label": "PROXY",
        "note": "REPORT ONLY (never gates, Brief s6). Fold-clean arms rebuild each CONC "
                "move against the fold VISIBLE catalogue (d_vis>=3 refills), same block "
                "prior (q is catalogue-masked only via emission rules, as in MASS/PRUNE), "
                "move counts scaled by |R0_vis|/37654 and capped at greedy capacity.",
        "fold_clean_moved_dots": {str(k): v for k, v in fold_moves.items()},
        "leakage_canary": {
            "gate": "single_feature_holdout_auc_canary", "threshold": 0.90,
            "n_features_checked": len(canary), "max_single_feature_auc": round(max_auc, 4),
            "passed": bool(max_auc <= 0.90),
            "withheld_positives_seed20": int(pos[20].sum()),
            "withheld_positives_seed21": int(pos[21].sum()),
            "total_withheld_positive_pixels": int(pos[20].sum() + pos[21].sum()),
            "top_10_features": canary[:10]},
        "catalogue_hide_and_recover_proxy": {
            "evidence_label": "PROXY",
            "withheld_positive_pixels": summ_clean["scores"]["R0"]["withheld_positive_pixels"],
            "spatial_clusters_20km": summ_clean["bootstrap"]["clusters"],
            "bootstrap_draws": summ_clean["bootstrap"]["draws"],
            "fold_clean_recipe_scores": summ_clean["scores"],
            "fold_clean_paired_differences_vs_t50m3765": summ_clean["paired_differences"],
            "shipped_mask_scores": summ_ship["scores"],
            "warning": "Withheld truth is catalogue-derived and clustered where the "
                       "catalogue is dense; this PROXY is structurally kind to "
                       "concentration into mapped-fault neighbourhoods. Report only."},
        "sgmc_off_catalogue_control": sgmc,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--manifest", type=Path, default=ROOT / "registry" / "data_manifest.json")
    ap.add_argument("--skip-diagnostics", action="store_true")
    args = ap.parse_args()
    t0 = time.time()

    print("[1/7] Verifying SHA-256 manifest ...")
    verified = verify_manifest(args.data_dir, args.manifest)
    bands_dir = ensure_unpacked_bands(args.data_dir)
    print(f"      {len(verified)} manifest files verified.")

    print("[2/7] Rebuilding R0 + ledger duplicate pre-checks ...")
    template_path = args.data_dir / "sample_submission.tif"
    with rasterio.open(template_path) as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(args.data_dir / "existing_faults.tif") as ds:
        cat = (ds.read(1) > 0) & foot
    dcat = distance_transform_edt(~cat)

    def read_scored(name):
        with rasterio.open(args.data_dir / "scored" / name) as ds:
            return (ds.read(1) > 0) & foot

    h19_5 = read_scored("gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif")
    h19_4 = read_scored("gems19-h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan.tif")
    h16_1 = read_scored("gems16-h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan.tif")
    d15 = read_scored("gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif")
    d28_pinned = read_scored("gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif")
    tgc = read_scored("gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif")
    ens12 = read_scored("gemsdoe-ens12-adopted-7f00890a.tif")
    d28 = dot_thin(h19_5, 2.8)
    if not np.array_equal(d28, d28_pinned):
        raise RuntimeError("STOP: rebuilt d2_8 != pinned")
    r0 = d28 & (dcat > 2.0)
    if int(r0.sum()) != EXPECTED_R0_DOTS:
        raise RuntimeError("STOP: R0 dot count")
    r0_pair = write_submission_pair(
        r0, template_path, cat,
        args.data_dir / "rebuilt_r0_conc" / "h33-h33-2-b2-nan.tif",
        args.data_dir / "rebuilt_r0_conc" / "h33-h33-2-b2-zeros.tif")
    if (r0_pair["digest8"] != EXPECTED_R0_DIGEST8
            or r0_pair["zeros_sha256"] != EXPECTED_R0_ZEROS_SHA256
            or r0_pair["nan_sha256"] != EXPECTED_R0_NAN_SHA256):
        raise RuntimeError(f"STOP: R0 SHA-256 mismatch {r0_pair}")
    with (ROOT / "ledger" / "submissions.csv").open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    ledger_shas = {r[c] for r in rows for c in ("sha256", "sha256_zeros") if r[c]}
    ledger_pairs = {(r["parent"], r["axis"], r["value"]) for r in rows if r["axis"]}
    for spec in ARMS:
        if (PARENT_ID, AXIS, spec["value"]) in ledger_pairs:
            raise RuntimeError(f"STOP: (parent,axis,value) already built {spec['value']}")
    print(f"      R0 byte-identical; ledger {len(rows)} rows, no CONC duplicates.")

    print("[3/7] Rebuilding parent ranking; canonical-ranking audit ...")
    surfaces = {h: b(bands_dir, args.data_dir, foot) for h, b in H33_BUILDERS.items()}
    h33_union = np.mean([rank_surface(v, foot) for v in surfaces.values()],
                        axis=0).astype(np.float32)
    lidar = np.nan_to_num(lidar_scarp_composite(args.data_dir, foot), nan=0.0).astype(np.float32)
    corrob_count = (h19_5.astype(np.float32) + h19_4.astype(np.float32)
                    + h16_1.astype(np.float32) + tgc.astype(np.float32)
                    + d15.astype(np.float32) + ens12.astype(np.float32))
    base_mult = (1.0 + 0.45 * corrob_count + 0.70 * ens12.astype(np.float32)
                 + 0.50 * d15.astype(np.float32) + 0.35 * lidar)
    ridge_union = (h19_5 | h19_4 | h16_1 | tgc) & foot
    raw_q = ((0.65 * ridge_union.astype(np.float32) + 0.35 * h33_union)
             * base_mult * (0.50 + 0.50 * h33_union))
    q = np.clip(raw_q / max(float(np.percentile(raw_q[ridge_union], 99.5)), 1e-6),
                0.0, 1.0).astype(np.float32)
    q[~foot] = 0.0
    del raw_q, base_mult
    gain_r0, _k1, _k2, offs = compute_exact_marginal_gains(r0, q)
    ry, rx = np.nonzero(r0)
    order_asc = np.argsort(gain_r0[ry, rx], kind="mergesort")

    def bottom(n):
        m = np.zeros_like(r0)
        m[ry[order_asc[:n]], rx[order_asc[:n]]] = True
        return m

    def shipped_mask(fname):
        with rasterio.open(ROOT / "releases" / fname) as ds:
            return ds.read(1) == 1.0

    prune_removed = r0 & ~shipped_mask("h33-h33-2-b2-prune-dgt1in-20261023-02ad0d5c.tif")
    canonical_ok = bool(np.array_equal(bottom(2545), prune_removed))
    if not canonical_ok:
        raise RuntimeError("STOP: canonical ranking != merged PRUNE removal set")
    ranking_audit = {"canonical_ranking_reproduces_prune_dgt1in_removals": canonical_ok,
                     "mass_concordance": {}}
    for n, fname in ((3765, "h33-h33-2-b2-mass-drop10pct-20261023-2cde51f3.tif"),
                     (7531, "h33-h33-2-b2-mass-drop20pct-20261023-62bfc392.tif")):
        dropped = r0 & ~shipped_mask(fname)
        mine = bottom(n)
        ranking_audit["mass_concordance"][f"drop{n}"] = {
            "overlap_dots": int((mine & dropped).sum()), "of_n": n,
            "overlap_frac": round(float((mine & dropped).sum()) / n, 4),
            "shipped_dropped_mean_canonical_gain": round(float(gain_r0[dropped].mean()), 4),
            "canonical_bottom_mean_gain": round(float(gain_r0[mine].mean()), 4)}
    print(f"      canonical ranking OK (PRUNE removals bit-identical); "
          f"MASS concordance {ranking_audit['mass_concordance']}")
    cand_pool_base = dot_thin(ridge_union, 2.8)
    del h19_4, h16_1, tgc, d15, ens12, ridge_union, d28_pinned

    print("[4/7] Block prior (5 km) + building arms ...")
    prior, eligible = block_prior(q, foot, BLOCK_PX)
    regions = donor_recipient_masks(prior, eligible, foot.shape, BLOCK_PX)
    pv = prior[eligible]
    block_info = {
        "block_px": BLOCK_PX, "block_km": BLOCK_PX / 10.0,
        "eligible_blocks": int(eligible.sum()),
        "prior_percentiles": {str(p): round(float(np.percentile(pv, p)), 5)
                               for p in (0, 10, 25, 50, 75, 90, 100)},
        "prior_mean_bot50": round(float(np.nanmean(
            np.where(eligible & (prior <= regions["p50"]), prior, np.nan))), 5),
        "prior_mean_top50": round(float(np.nanmean(
            np.where(eligible & (prior > regions["p50"]), prior, np.nan))), 5),
        "prior_mean_top25": round(float(np.nanmean(
            np.where(eligible & (prior >= regions["p75"]), prior, np.nan))), 5),
        "r0_shares": block_dot_shares(r0, regions, foot),
        "density_cv_definition": "gems84.snap.density_cv: std/mean of dots-per-footprint-"
                                 "pixel over blocks with any footprint (10px grid crop)",
        "r0_density_cv": {"1km_10px": round(density_cv(r0, foot, 10), 4),
                          "5km_50px": round(density_cv(r0, foot, 50), 4),
                          "10km_100px": round(density_cv(r0, foot, 100), 4)},
        "brief_reported_best_cv": "0.51-0.59 (UNVERIFIED: definition/block size unstated; "
                                  "R0 measures 1.88/0.96/0.80 at 1/5/10 km under the "
                                  "definition above, so the reported range is not "
                                  "comparable and is not used as a target)",
    }
    print(f"      blocks {block_info['eligible_blocks']}, "
          f"CV R0 {block_info['r0_density_cv']}, shares {block_info['r0_shares']}")
    live_masks, arm_info = {}, {}
    for spec in ARMS:
        m, info = conc_arm(r0, regions[spec["donor"]], regions[spec["recip"]], dcat,
                           gain_r0, cand_pool_base, q, offs, spec["n_move"])
        if info["n_moved"] != spec["n_move"]:
            raise RuntimeError(f"{spec['key']}: moved {info['n_moved']} != {spec['n_move']}")
        live_masks[spec["key"]], arm_info[spec["key"]] = m, info
        print(f"      {spec['key']}: moved {info['n_moved']}")

    print("[5/7] Emitting + gating release pairs ...")
    records, conc_rows = [], []
    for spec in ARMS:
        key, mask = spec["key"], live_masks[spec["key"]]
        n_dots = int(mask.sum())
        added, removed = int((mask & ~r0).sum()), int((r0 & ~mask).sum())
        pct = 100.0 * (added + removed) / EXPECTED_R0_DOTS
        if n_dots != EXPECTED_R0_DOTS or added != removed or not (1.0 <= pct <= 50.0):
            raise RuntimeError(f"{key}: bad diff n={n_dots} +{added}/-{removed}")
        if int((mask & cat).sum()) or float(dcat[mask & ~r0].min()) < 3.0:
            raise RuntimeError(f"{key}: catalogue/collar violation")
        if len(spec["form_note"]) > 140:
            raise RuntimeError(f"{key}: form note >140")
        tmp_nan = ROOT / "releases" / f"_tmp_{key}.tif"
        tmp_z = ROOT / "releases" / f"_tmp_{key}-zeros.tif"
        tmp_info = write_submission_pair(mask, template_path, cat, tmp_nan, tmp_z)
        sha8 = tmp_info["nan_sha256"][:8]
        var_id = f"{PARENT_ID}-{spec['slug']}-{DATE_TAG}-{sha8}"
        fin_nan = ROOT / "releases" / f"{var_id}.tif"
        fin_z = ROOT / "releases" / f"{var_id}-zeros.tif"
        if fin_nan.exists() or fin_z.exists():
            raise RuntimeError(f"release exists {var_id}")
        tmp_nan.replace(fin_nan)
        tmp_z.replace(fin_z)
        if file_sha256(fin_nan) in ledger_shas or file_sha256(fin_z) in ledger_shas:
            raise RuntimeError(f"SHA already in ledger {var_id}")
        disk = verify_written_pair_from_disk(fin_nan, fin_z, template_path, cat,
                                             expected_dots=n_dots)
        pred = spec["model"]["predicted_live_change"]
        pred_txt = (f"{pred[0]:+.3f} to {pred[1]:+.3f} DTI (MODEL: 5km-block move of "
                    f"{spec['n_move']} dots at fixed count; credit scenario in receipt)")
        rec = {
            "id": var_id, "key": key, "parent": PARENT_ID, "axis": AXIS,
            "value": spec["value"], "n_dots": n_dots, "dots_added": added,
            "dots_removed": removed, "dots_moved": spec["n_move"],
            "pct_moved_vs_r0": round(100.0 * spec["n_move"] / EXPECTED_R0_DOTS, 2),
            "pct_changed_vs_r0": round(pct, 2),
            "pct_changed_definition": "symmetric-difference dots / 37654 * 100 (a move "
                                      "of k dots counts 2k), as in MASS/PRUNE rows",
            "jaccard_vs_r0": round(float((mask & r0).sum()) / float((mask | r0).sum()), 6),
            "donor_blocks": spec["donor"], "recipient_blocks": spec["recip"],
            "d_cat_min_px": round(float(dcat[mask].min()), 4),
            "added_dots_d_cat_min_px": round(float(dcat[mask & ~r0].min()), 4),
            "density_cv": {"1km_10px": round(density_cv(mask, foot, 10), 4),
                           "5km_50px": round(density_cv(mask, foot, 50), 4),
                           "10km_100px": round(density_cv(mask, foot, 100), 4)},
            "block_shares": block_dot_shares(mask, regions, foot),
            "build_stats": arm_info[key],
            "digest8_mask": tmp_info["digest8"],
            "nan_tif": disk["nan_tif"], "zeros_tif": disk["zeros_tif"],
            "form_note": spec["form_note"], "predicted_change": pred_txt,
            "model_scenario": spec["model"], "mechanism_card": spec["mechanism_card"],
        }
        records.append(rec)
        conc_rows.append({
            "id": var_id, "site": "GEMSDOE84", "name": var_id, "score": "",
            "evidence_class": "BUILT (unscored)", "encoding": "nan+zeros",
            "n_dots": str(n_dots), "pct_changed": f"{pct:.2f}", "sha8": sha8,
            "sha256": disk["nan_tif"]["sha256"],
            "sha256_zeros": disk["zeros_tif"]["sha256"],
            "parent": PARENT_ID, "axis": AXIS, "value": spec["value"],
            "status": "BUILT", "receipt": "N", "receipt_score": "",
            "predicted_change": pred_txt, "date": "", "form_note": spec["form_note"],
            "notes": f"5km blocks; move {spec['n_move']} dots {spec['donor']}->"
                     f"{spec['recip']} (+{added}/-{removed}), count 37,654; "
                     f"CV5km {block_info['r0_density_cv']['5km_50px']}->"
                     f"{rec['density_cv']['5km_50px']}",
        })
        sidecar = {"schema_version": 1, "evidence_class": "BUILT (unscored)",
                   "parent_score": "0.2778 (CLAIM: owner-reported; no receipt in ledger/)",
                   "no_evidence_threshold": 0.01, "block_info": block_info, **rec}
        (ROOT / "releases" / f"{var_id}.json").write_text(json.dumps(sidecar, indent=2) + "\n")
        print(f"      {var_id}: moved {spec['n_move']} ({pct:.2f}% sym) "
              f"CV5km->{rec['density_cv']['5km_50px']}")

    (ROOT / "ledger" / "_concentration_rows.json").write_text(
        json.dumps(conc_rows, indent=2) + "\n")

    print("[6/7] REPORT-ONLY diagnostics ...")
    diagnostics = None
    if not args.skip_diagnostics:
        diagnostics = run_report_only(args.data_dir, bands_dir, foot, cat, d28, r0,
                                      cand_pool_base, q, surfaces, h33_union, lidar,
                                      corrob_count, regions, live_masks)
    try:
        git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                          text=True).strip()
    except Exception:
        git_sha = "unknown"
    print("[7/7] Writing receipt ...")
    report = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_head_sha": git_sha, "seed": SEED, "axis": AXIS,
        "axis_assignment": "not assigned by human (clarifying questions skipped "
                           "2026-10-23, third consecutive session); CONCENTRATION is "
                           "the next unbuilt axis on merged main after MASS/SNAP/PRUNE "
                           "(IR-DEC-08 names CONCENTRATION and RELIEF as unbuilt)",
        "manifest_files_verified": len(verified),
        "parent_r0": {"id": PARENT_ID, "live_score": PARENT_SCORE_CLAIM,
                      "evidence_label": "CLAIM", "n_dots": EXPECTED_R0_DOTS,
                      "digest8": r0_pair["digest8"],
                      "nan_sha256": r0_pair["nan_sha256"],
                      "zeros_sha256": r0_pair["zeros_sha256"],
                      "exact_rebuild_verified": True},
        "ranking_audit": ranking_audit,
        "block_design": block_info,
        "pre_registered_ordering": "conc arms >= R0 >= spread (MODEL); t50 vs t25 "
                                   "unordered; every |change| may be <0.01 = no evidence "
                                   "singly (brief s5); the signed t25-vs-spread pair at "
                                   "equal dose is the primary contrast",
        "variants": records,
        "report_only_diagnostics": diagnostics,
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    out = ROOT / "evidence" / f"r0_concentration_variants_{DATE_TAG}.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Done {report['elapsed_seconds']}s -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
