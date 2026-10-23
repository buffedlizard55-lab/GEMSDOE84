#!/usr/bin/env python3
"""Deterministic rebuild of Parent R0 (h33-h33-2-b2) and AXIS=PRUNE single-axis variants (Brief v2).

AXIS was not assigned by the human this session (clarifying question skipped); PRUNE is the
next unbuilt axis in the brief's default plan and subsumes the COLLAR_REFILL experiment
proposed in SLOT_PLAN.md.  MASS (-10pct/+10pct/-20pct) and SNAP (3 variants) were built in
the 2026-10-23 session and are NOT rebuilt here (each (AXIS, value) pair is built once).

Steps (Brief v2 section 5 start sequence):
1. Verify all SHA-256 hashes in registry/data_manifest.json.
2. Rebuild Parent R0 exactly as scripts/build_r0_variants.py does (scored_h19_5 ->
   dot_thin(r_min=2.8) -> d2_8 44,090 dots, asserted bit-identical to the pinned raster ->
   prune d_cat <= 2.0 px -> 37,654 dots) and match the pinned -zeros/-nan SHA-256.
   If the parent cannot be rebuilt bit-for-bit this script stops; it never approximates R0.
3. Rebuild the parent's own ranking with the recorded GEMSDOE32 recipe (same code path as
   the MASS session: corroboration count + H33-A..D consensus + 1 m LiDAR scarp composite
   + exact 25-offset top-2 kernel marginal DTI gain at s0 = 0.2778 CLAIM).
4. Build 3 variants differing ONLY in catalogue-collar geometry, count fixed at 37,654:
     - dgt1in    : collar in to d_cat > 1 px -- add every d2_8 dot in 1 < d_cat <= 2,
                   drop the same number of lowest-marginal-gain R0 dots.
     - dge3refill: collar out to d_cat >= 3 px -- drop R0 dots in 2 < d_cat < 3, refill the
                   same count from the corroborated ridge pool at d_cat >= 3.0 px.
     - dgt3refill: collar out to d_cat > 3 px -- drop R0 dots in 2 < d_cat <= 3, refill the
                   same count from the corroborated ridge pool at d_cat > 3.0 px.
   Emit releases/<id>.tif (NaN outside footprint) + <id>-zeros.tif, re-read from disk,
   run every MUST-pass gate (Brief section 6), record parent-diff statistics.
5. REPORT-ONLY diagnostics (never gates): fold-clean catalogue hide-and-recover PROXY
   (n withheld positives, 95% CI), single-feature leakage canary (AUC > 0.90 stops the
   build per Brief section 6), SGMC off-catalogue control.
6. Write ledger/_prune_rows.json (consumed by scripts/build_ledger.py) and
   evidence/r0_prune_variants_20261023.json with one mechanism card per variant.

Usage:  python scripts/build_prune_variants.py [--data-dir .cache/gems_data]
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
from gems84.prune import drop_collar_band, swap_in_near_collar  # noqa: E402
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

DATE_TAG = "20261023"
PARENT_ID = "h33-h33-2-b2"
AXIS = "PRUNE"


def git_head_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def read_ledger_dedupe() -> tuple[set[str], set[tuple[str, str, str]]]:
    """All sha256/sha256_zeros and (parent, axis, value) pairs already in the ledger."""
    path = ROOT / "ledger" / "submissions.csv"
    shas: set[str] = set()
    pairs: set[tuple[str, str, str]] = set()
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            for key in ("sha256", "sha256_zeros"):
                if row.get(key):
                    shas.add(row[key])
            if row.get("parent") and row.get("axis"):
                pairs.add((row["parent"], row["axis"], row.get("value", "")))
    return shas, pairs


def build_variant_masks(r0, d28, dcat, gain_r0, cand_pool_base, q):
    """The three fixed-count collar masks.  Returns [(key, value, mask, extra_stats)]."""
    out = []

    # --- collar IN to d_cat > 1 px: swap the whole (1, 2] ring of d2_8 back in
    near_pool = d28 & (dcat > 1.0) & (dcat <= 2.0) & (~r0)
    mask_in, st_in = swap_in_near_collar(r0, near_pool, gain_r0)
    out.append(("dgt1in", "dcat>1px-swapin", mask_in, {"swap": st_in,
                                                      "near_pool_dots": int(near_pool.sum())}))

    # --- collar OUT to d_cat >= 3 px (SLOT_PLAN COLLAR_REFILL): drop 2 < d_cat < 3, refill
    base_ge3, removed_ge3 = drop_collar_band(r0, dcat, lo=2.0, hi=3.0, hi_inclusive=False)
    _, k1_ge3, _, offs = compute_exact_marginal_gains(base_ge3, q)
    cand_ge3 = cand_pool_base & (~base_ge3) & (dcat >= 3.0)
    mask_ge3, gains_ge3 = greedy_add_dots(base_ge3, cand_ge3, q, k1_ge3, offs,
                                          n_add=int(removed_ge3.sum()), r_min=2.8)
    out.append(("dge3refill", "dcat>=3px-refill", mask_ge3,
                {"removed_band_dots": int(removed_ge3.sum()),
                 "refill_pool_dots": int(cand_ge3.sum()),
                 "refill_gain_min": float(min(gains_ge3)),
                 "refill_gain_median": float(np.median(gains_ge3))}))

    # --- collar OUT to d_cat > 3 px (brief PRUNE <=3 point): drop 2 < d_cat <= 3, refill
    base_gt3, removed_gt3 = drop_collar_band(r0, dcat, lo=2.0, hi=3.0, hi_inclusive=True)
    _, k1_gt3, _, offs = compute_exact_marginal_gains(base_gt3, q)
    cand_gt3 = cand_pool_base & (~base_gt3) & (dcat > 3.0)
    mask_gt3, gains_gt3 = greedy_add_dots(base_gt3, cand_gt3, q, k1_gt3, offs,
                                          n_add=int(removed_gt3.sum()), r_min=2.8)
    out.append(("dgt3refill", "dcat>3px-refill", mask_gt3,
                {"removed_band_dots": int(removed_gt3.sum()),
                 "refill_pool_dots": int(cand_gt3.sum()),
                 "refill_gain_min": float(min(gains_gt3)),
                 "refill_gain_median": float(np.median(gains_gt3))}))
    return out


# Per-variant collar predicate every emitted dot must satisfy (gate, re-checked on disk masks).
COLLAR_RULE = {
    "dgt1in": ("d_cat > 1.0 px", lambda d: float(d.min()) > 1.0),
    "dge3refill": ("d_cat >= 3.0 px", lambda d: float(d.min()) >= 3.0),
    "dgt3refill": ("d_cat > 3.0 px", lambda d: float(d.min()) > 3.0),
}

MECHANISM_CARDS = {
    "dgt1in": {
        "hypothesis": "Moving the collar in from d_cat > 2 px to d_cat > 1 px at fixed count "
                      "(swap all 2,545 pre-prune d2_8 dots in the 100-200 m ring back in, drop "
                      "the 2,545 lowest-marginal-gain R0 dots) lowers live DTI, because the "
                      "organizer masks known-fault pixels pixel-exactly and scores neighbours "
                      "against new-fault truth only, so the 100-200 m halo of a mapped trace is "
                      "where 'already captured' geometry concentrates.",
        "mechanism": "Under alpha = 0.2, a dot 1-2 px from a catalogue trace spends most of its "
                     "300 m triangular kernel on the masked trace and its immediate hanging-wall/"
                     "footwall sliver; its residual new-fault credit must still clear the "
                     "~0.056 x (denominator) bar at DTI 0.28. The historical CLAIM ladder "
                     "(d>1: 0.2708 at 40,199 dots -> d>2: 0.2778 at 37,654) credits this ring "
                     "with net-negative value, but mass fell at the same time; this variant "
                     "holds mass at 37,654 so the receipt prices the ring alone.",
        "non_fault_mimic": "The mapped trace itself, misregistered by 100-200 m in the source "
                           "compilations (USGS/INGENIOUS linework vs 100 m grid), plus "
                           "fault-parallel erosional benches and colluvial aprons at the scarp "
                           "base that the h19_5 ridge detector follows.",
        "predicted_sign_and_size": "Negative: -0.002 to -0.006 DTI vs R0 (MODEL).",
        "falsifier": "A live receipt >= 0.2778 for dgt1in (at identical count) falsifies the "
                     "collar story: the 0.2708 -> 0.2778 step was then a pure mass effect, and "
                     "unmapped splays do populate the 100-200 m ring.",
    },
    "dge3refill": {
        "hypothesis": "R0's 1,611 dots at diagonal distances sqrt(5)/sqrt(8) px (224-283 m) are "
                      "the last remnant of the >2.0 px (not >=3 px) prune; replacing them with "
                      "the top-ranked corroborated ridge dots at d_cat >= 3.0 px, count fixed, "
                      "raises live DTI slightly.",
        "mechanism": "A dot at 2.24 px from a mapped trace still overlaps the masked trace's "
                     "300 m kernel footprint; moving that mass one kernel radius out places it "
                     "on independent ridge pixels whose max-cover credit is not shadowed by "
                     "catalogue geometry. Refill ranking is the parent's own exact 25-offset "
                     "marginal-gain order (greedy, r_min = 2.8 px), so only position changes.",
        "non_fault_mimic": "True en-echelon relay steps and sub-parallel hanging-wall splays "
                           "220-290 m off a master fault -- real new-fault pixels the organizer "
                           "explicitly allows within 300 m of known traces.",
        "predicted_sign_and_size": "Positive, small: 0.000 to +0.003 DTI vs R0 (MODEL).",
        "falsifier": "A live drop > 0.001 vs R0 at matched count proves the (2, 3) px ring "
                     "carries real unmapped test splays and the collar should move in, not out.",
    },
    "dgt3refill": {
        "hypothesis": "Extending the collar past the full kernel radius (drop the 2,171 R0 dots "
                      "at 2 < d_cat <= 3 px, refill at d_cat > 3.0 px) is the brief's PRUNE "
                      "<=3 px point; it tests whether ANY dot whose kernel touches a mapped "
                      "trace is net-negative once count is held fixed.",
        "mechanism": "At d_cat = 3.0 px a dot's triangular kernel just reaches the catalogue "
                     "pixel with weight 0; dots inside that ring share kernel support with "
                     "masked pixels. If new-fault truth avoids the 0-300 m halo (mapped "
                     "systems already captured there), the refilled off-halo dots win; if "
                     "truth is halo-rich (new geometry of existing systems), they lose.",
        "non_fault_mimic": "Newly mapped strands of existing systems -- explicitly included "
                           "in the organizer's 'new fault' definition -- which by construction "
                           "sit inside the 300 m halo this variant vacates.",
        "predicted_sign_and_size": "Bracketed: -0.001 to +0.003 DTI vs R0 (MODEL); ordered "
                                   "with dge3refill it measures the marginal value of the "
                                   "exact-3.0 px ring (560 dots).",
        "falsifier": "dgt3refill scoring below dge3refill by > 0.001 shows the =3.0 px ring "
                     "itself carries truth credit, capping the optimal collar at >= 3.0 px "
                     "inclusive rather than exclusive.",
    },
}

FORM_NOTES = {
    "dgt1in": "h33-h33-2-b2; PRUNE collar >1px swap-in 2545 ring dots, count 37654; pred -0.002..-0.006",
    "dge3refill": "h33-h33-2-b2; PRUNE collar >=3px, replace 1611 diag dots refilled, 37654; pred 0..+0.003",
    "dgt3refill": "h33-h33-2-b2; PRUNE collar >3px, replace 2171 ring dots refilled, 37654; pred -0.001..+0.003",
}

PREDICTED = {
    "dgt1in": "-0.002 to -0.006 DTI (MODEL: prices the 100-200 m catalogue ring at fixed count 37,654)",
    "dge3refill": "0.000 to +0.003 DTI (MODEL: removes (2,3)px diagonal-collar remnant, ranked refill at d_cat>=3px)",
    "dgt3refill": "-0.001 to +0.003 DTI (MODEL: full kernel-radius collar d_cat>3px, ranked refill, count fixed)",
}


def run_report_only_diagnostics(data_dir, bands_dir, foot, cat, d28, r0, cand_pool_base, q,
                                surfaces, h33_union, lidar, corrob_count, variants):
    """REPORT ONLY (Brief section 6): hide-and-recover PROXY, leakage canary, SGMC control."""
    grid = load_grid(data_dir)
    folds_20, _ = gems57_holdout.buffered_component_draw(grid, seed=20)
    folds_21, _ = gems57_holdout.buffered_component_draw(grid, seed=21)
    all_folds = [(20, f) for f in folds_20] + [(21, f) for f in folds_21]

    # --- leakage canary (identical construction to the MASS session) -------------------
    def pos_neg(folds):
        pos = np.zeros(foot.shape, dtype=bool)
        neg = np.zeros(foot.shape, dtype=bool)
        for f in folds:
            active = foot & f["region"] & (~f["masked_known"])
            pos |= active & f["truth"]
            neg |= active & (~f["truth"])
        return pos, neg

    pos20, neg20 = pos_neg(folds_20)
    pos21, neg21 = pos_neg(folds_21)
    canary = []
    arrays = {b: np.load(bands_dir / f"{b}.npy") for b in BAND_NAMES}
    arrays.update({"H33-A": surfaces["H33-A"], "H33-B": surfaces["H33-B"],
                   "H33-C": surfaces["H33-C"], "H33-D": surfaces["H33-D"],
                   "h33_union": h33_union, "lidar_scarp_composite": lidar,
                   "corrob_count": corrob_count, "q_posterior": q})
    for name, arr in arrays.items():
        a20, a21 = rank_auc(arr, pos20, neg20), rank_auc(arr, pos21, neg21)
        m = 0.5 * (a20 + a21)
        canary.append({"feature": name, "auc_seed20": round(a20, 4), "auc_seed21": round(a21, 4),
                       "auc_mean": round(m, 4), "abs_strength": round(max(m, 1.0 - m), 4)})
    canary.sort(key=lambda x: x["abs_strength"], reverse=True)
    max_auc = max(f["abs_strength"] for f in canary)
    if max_auc > 0.90:
        raise RuntimeError(f"STOP: leakage canary exceeded 0.90 (max_auc={max_auc})")

    # --- fold-clean hide-and-recover: same collar recipe against each fold's VISIBLE cat
    fold_clean_by_seed = {}
    for seed_val, seed_folds in [(20, folds_20), (21, folds_21)]:
        vis = seed_folds[0]["visible"]
        dvis = distance_transform_edt(~vis)
        r0_vis = d28 & (dvis > 2.0)
        gain_vis, _, _, offs = compute_exact_marginal_gains(r0_vis, q)
        arms = {"R0": r0_vis}
        near_vis = d28 & (dvis > 1.0) & (dvis <= 2.0) & (~r0_vis)
        arms["dgt1in"], _ = swap_in_near_collar(r0_vis, near_vis, gain_vis)
        for key, hi_incl, refill_ok in [
            ("dge3refill", False, dvis >= 3.0),
            ("dgt3refill", True, dvis > 3.0),
        ]:
            base_v, removed_v = drop_collar_band(r0_vis, dvis, lo=2.0, hi=3.0,
                                                 hi_inclusive=hi_incl)
            _, k1_v, _, _ = compute_exact_marginal_gains(base_v, q)
            cand_v = cand_pool_base & (~base_v) & refill_ok
            arms[key], _g = greedy_add_dots(base_v, cand_v, q, k1_v, offs,
                                            n_add=int(removed_v.sum()), r_min=2.8)
        fold_clean_by_seed[seed_val] = arms

    shipped_arms = {"R0": r0, **variants}
    terms_clean, terms_ship = {}, {}
    for arm in shipped_arms:
        acc_c = acc_s = None
        for seed_val, fold in all_folds:
            _, t_c = evaluate_holdout.evaluate(
                fold_clean_by_seed[seed_val][arm].astype(np.float32), fold, foot)
            _, t_s = evaluate_holdout.evaluate(
                shipped_arms[arm].astype(np.float32), fold, foot)
            acc_c = t_c if acc_c is None else acc_c + t_c
            acc_s = t_s if acc_s is None else acc_s + t_s
        terms_clean[arm], terms_ship[arm] = acc_c, acc_s

    summary_clean = evaluate_holdout.pooled_summary(terms_clean, draws=1000, seed=520810,
                                                    candidate="dge3refill")
    summary_ship = evaluate_holdout.pooled_summary(terms_ship, draws=1000, seed=520810,
                                                   candidate="dge3refill")
    paired_vs_r0 = {}
    for arm in variants:
        s = evaluate_holdout.pooled_summary(
            {"R0": terms_clean["R0"], arm: terms_clean[arm]},
            draws=1000, seed=520810, candidate=arm)
        paired_vs_r0[arm] = s.get("paired_differences", {})

    # --- SGMC off-catalogue control (same construction as the MASS session) ------------
    with rasterio.open(data_dir / "external" / "derived_sgmc_faults_100m_u8.tif") as ds:
        sgm = (ds.read(1) > 0) & foot
    near_cat = binary_dilation(cat, iterations=3)
    sgmc_truth = sgm & (~cat) & (~near_cat) & foot
    sgmc_coords = np.nonzero(sgmc_truth)
    n_truth = int(sgmc_coords[0].size)
    sgmc_k = np.clip(1.0 - distance_transform_edt(~sgmc_truth) / 3.0, 0.0, 1.0).astype(np.float32)
    g_lb = 12691.0
    sgmc_results = {}
    for arm, mask in shipped_arms.items():
        off = mask & (~cat) & foot
        dp = distance_transform_edt(~off)
        tp = float(np.clip(1.0 - dp[sgmc_coords] / 3.0, 0.0, 1.0).sum())
        fn = float(n_truth) - tp
        fp = float((1.0 - sgmc_k[off]).sum())
        raw = float(tp / (tp + 0.2 * fp + 0.8 * fn + 1e-6))
        cov = tp / n_truth
        tp_cal = cov * g_lb
        fp_cal = max(0.0, float(off.sum()) - tp_cal)
        cal = float(tp_cal / (0.2 * (tp_cal + fp_cal) + 0.8 * g_lb + 1e-6))
        sgmc_results[arm] = {"evidence_label": "PROXY",
                             "sgmc_off_catalogue_truth_pixels": n_truth,
                             "emitted_dots": int(off.sum()),
                             "sgmc_raw_dti": round(raw, 6), "sgmc_coverage": round(cov, 6),
                             "sgmc_prevalence_calibrated_dti": round(cal, 6)}

    return {
        "evidence_label": "PROXY",
        "note": "REPORT ONLY diagnostics (never gates per Brief Section 6).",
        "leakage_canary": {"gate": "single_feature_holdout_auc_canary", "threshold": 0.90,
                           "n_features_checked": len(canary),
                           "max_single_feature_auc": round(max_auc, 4),
                           "passed": bool(max_auc <= 0.90),
                           "withheld_positives_seed20": int(pos20.sum()),
                           "withheld_positives_seed21": int(pos21.sum()),
                           "total_withheld_positive_pixels": int(pos20.sum() + pos21.sum()),
                           "top_10_features": canary[:10]},
        "catalogue_hide_and_recover_proxy": {
            "evidence_label": "PROXY",
            "withheld_positive_pixels": summary_clean["scores"]["R0"]["withheld_positive_pixels"],
            "spatial_clusters_20km": summary_clean["bootstrap"]["clusters"],
            "bootstrap_draws": summary_clean["bootstrap"]["draws"],
            "fold_clean_recipe_scores": summary_clean["scores"],
            "fold_clean_paired_differences_vs_R0": paired_vs_r0,
            "shipped_mask_scores": summary_ship["scores"],
        },
        "sgmc_off_catalogue_control": sgmc_results,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--manifest", type=Path, default=ROOT / "registry" / "data_manifest.json")
    args = ap.parse_args()
    t0 = time.time()

    print("[1/6] Verifying SHA-256 hashes in registry/data_manifest.json ...")
    verified = verify_manifest(args.data_dir, args.manifest)
    bands_dir = ensure_unpacked_bands(args.data_dir)
    print(f"      Verified {len(verified)} manifest files and 19 unpacked bands.")

    print("[2/6] Rebuilding Parent R0 (h33-h33-2-b2) and matching pinned SHA-256 ...")
    template_path = args.data_dir / "sample_submission.tif"
    with rasterio.open(template_path) as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(args.data_dir / "existing_faults.tif") as ds:
        cat = (ds.read(1) > 0) & foot
    dcat = distance_transform_edt(~cat)

    def read_scored(name: str) -> np.ndarray:
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
        raise RuntimeError("STOP: rebuilt d2_8 does not match the pinned d2_8 raster")
    r0 = d28 & (dcat > 2.0)
    if int(r0.sum()) != EXPECTED_R0_DOTS:
        raise RuntimeError(f"STOP: expected {EXPECTED_R0_DOTS} R0 dots, got {int(r0.sum())}")
    r0_pair = write_submission_pair(r0, template_path, cat,
                                    args.data_dir / "rebuilt_r0_prune" / "h33-h33-2-b2-nan.tif",
                                    args.data_dir / "rebuilt_r0_prune" / "h33-h33-2-b2-zeros.tif")
    if (r0_pair["digest8"] != EXPECTED_R0_DIGEST8
            or r0_pair["zeros_sha256"] != EXPECTED_R0_ZEROS_SHA256
            or r0_pair["nan_sha256"] != EXPECTED_R0_NAN_SHA256):
        raise RuntimeError(f"STOP: Parent R0 SHA-256 verification failed: {r0_pair}")
    print(f"      R0 rebuilt bit-for-bit: {EXPECTED_R0_DOTS} dots, digest8={r0_pair['digest8']}.")

    # Lineage cross-check: the 0.2708 solo base must equal d2_8 pruned at d_cat > 1 px.
    with rasterio.open(args.data_dir / "parent" / "gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif") as ds:
        a = ds.read(1)
        solo_base = np.isfinite(a) & (a > 0)
    solo_eq_dgt1 = bool(np.array_equal(solo_base & foot, d28 & (dcat > 1.0)))
    print(f"      solo 0.2708 base == d2_8 & (d_cat>1): {solo_eq_dgt1} "
          f"({int(solo_base.sum())} dots)")

    print("[3/6] Checking ledger for duplicate hashes / (parent, axis, value) pairs ...")
    ledger_shas, ledger_pairs = read_ledger_dedupe()
    print(f"      Ledger holds {len(ledger_shas)} hashes, {len(ledger_pairs)} (parent,axis,value) pairs.")

    print("[4/6] Rebuilding the parent ranking (recorded GEMSDOE32 recipe, as in MASS session) ...")
    surfaces = {hid: b(bands_dir, args.data_dir, foot) for hid, b in H33_BUILDERS.items()}
    h33_union = np.mean([rank_surface(v, foot) for v in surfaces.values()], axis=0).astype(np.float32)
    lidar = np.nan_to_num(lidar_scarp_composite(args.data_dir, foot), nan=0.0).astype(np.float32)
    corrob_count = (h19_5.astype(np.float32) + h19_4.astype(np.float32) + h16_1.astype(np.float32)
                    + tgc.astype(np.float32) + d15.astype(np.float32) + ens12.astype(np.float32))
    base_mult = (1.0 + 0.45 * corrob_count + 0.70 * ens12.astype(np.float32)
                 + 0.50 * d15.astype(np.float32) + 0.35 * lidar)
    ridge_union = (h19_5 | h19_4 | h16_1 | tgc) & foot
    raw_q = (0.65 * ridge_union.astype(np.float32) + 0.35 * h33_union) * base_mult * (0.50 + 0.50 * h33_union)
    q = np.clip(raw_q / max(float(np.percentile(raw_q[ridge_union], 99.5)), 1e-6), 0.0, 1.0).astype(np.float32)
    q[~foot] = 0.0
    gain_r0, _k1, _k2, _offs = compute_exact_marginal_gains(r0, q)
    cand_pool_base = dot_thin(ridge_union, 2.8)

    print("[5/6] Building 3 AXIS=PRUNE variants (count fixed at 37,654) ...")
    specs = build_variant_masks(r0, d28, dcat, gain_r0, cand_pool_base, q)
    releases_dir = ROOT / "releases"
    records, ledger_rows, masks_by_key = [], [], {}
    for key, value, mask, extra in specs:
        pair = (PARENT_ID, AXIS, value)
        if pair in ledger_pairs:
            raise RuntimeError(f"Duplicate (parent, axis, value) in ledger: {pair}")
        n_dots = int(mask.sum())
        if n_dots != EXPECTED_R0_DOTS:
            raise RuntimeError(f"{key}: count {n_dots} != parent {EXPECTED_R0_DOTS} (PRUNE holds count)")
        added = int((mask & ~r0).sum())
        removed = int((r0 & ~mask).sum())
        pct_changed = 100.0 * (added + removed) / EXPECTED_R0_DOTS
        if not (1.0 <= pct_changed <= 50.0):
            raise RuntimeError(f"{key}: {pct_changed:.2f}% changed outside [1%, 50%]")
        rule_text, rule_ok = COLLAR_RULE[key][0], COLLAR_RULE[key][1](dcat[mask])
        if not rule_ok:
            raise RuntimeError(f"{key}: collar rule violated ({rule_text})")
        if int((mask & cat).sum()) != 0:
            raise RuntimeError(f"{key}: mass on catalogue pixels")

        tmp_nan, tmp_zeros = releases_dir / f"_tmp_{key}.tif", releases_dir / f"_tmp_{key}-zeros.tif"
        tmp_info = write_submission_pair(mask, template_path, cat, tmp_nan, tmp_zeros)
        sha8 = tmp_info["nan_sha256"][:8]
        var_id = f"{PARENT_ID}-prune-{key}-{DATE_TAG}-{sha8}"
        final_nan, final_zeros = releases_dir / f"{var_id}.tif", releases_dir / f"{var_id}-zeros.tif"
        tmp_nan.replace(final_nan)
        tmp_zeros.replace(final_zeros)
        if file_sha256(final_nan) in ledger_shas or file_sha256(final_zeros) in ledger_shas:
            raise RuntimeError(f"SHA-256 already present in ledger for {var_id}")
        disk = verify_written_pair_from_disk(final_nan, final_zeros, template_path, cat,
                                             expected_dots=n_dots)
        if len(FORM_NOTES[key]) > 140:
            raise RuntimeError(f"Form note exceeds 140 chars for {key}")

        rec = {"id": var_id, "key": key, "parent": PARENT_ID, "axis": AXIS, "value": value,
               "n_dots": n_dots, "dots_added": added, "dots_removed": removed,
               "pct_changed_vs_r0": round(pct_changed, 2),
               "jaccard_vs_r0": round(float((mask & r0).sum()) / float((mask | r0).sum()), 6),
               "collar_rule": rule_text,
               "d_cat_min_px": round(float(dcat[mask].min()), 4),
               "d_cat_median_px": round(float(np.median(dcat[mask])), 4),
               "d_cat_p90_px": round(float(np.percentile(dcat[mask], 90.0)), 4),
               "added_dots_d_cat_min_px": round(float(dcat[mask & ~r0].min()), 4) if added else None,
               "build_stats": extra,
               "nan_tif": disk["nan_tif"], "zeros_tif": disk["zeros_tif"],
               "form_note": FORM_NOTES[key], "predicted_change": PREDICTED[key],
               "mechanism_card": MECHANISM_CARDS[key]}
        records.append(rec)
        masks_by_key[key] = mask
        ledger_rows.append({
            "id": var_id, "site": "GEMSDOE84", "name": var_id, "score": "",
            "evidence_class": "BUILT (unscored)", "encoding": "nan+zeros",
            "n_dots": str(n_dots), "pct_changed": f"{pct_changed:.2f}", "sha8": sha8,
            "sha256": disk["nan_tif"]["sha256"], "sha256_zeros": disk["zeros_tif"]["sha256"],
            "parent": PARENT_ID, "axis": AXIS, "value": value, "status": "BUILT",
            "receipt": "N", "receipt_score": "", "predicted_change": PREDICTED[key],
            "date": "", "form_note": FORM_NOTES[key],
            "notes": f"collar {rule_text} at fixed count 37,654 "
                     f"(+{added} / -{removed} dots vs R0)",
        })
        ledger_shas.update({disk["nan_tif"]["sha256"], disk["zeros_tif"]["sha256"]})
        ledger_pairs.add(pair)
        print(f"      Built {var_id}: {n_dots} dots, {pct_changed:.2f}% changed, "
              f"collar {rule_text}, gates passed on disk re-read.")

    (ROOT / "ledger" / "_prune_rows.json").write_text(json.dumps(ledger_rows, indent=2) + "\n")
    print("      Wrote ledger/_prune_rows.json (run scripts/build_ledger.py to fold into submissions.csv).")

    print("[6/6] REPORT-ONLY diagnostics (hide-and-recover PROXY, canary, SGMC) ...")
    diagnostics = run_report_only_diagnostics(args.data_dir, bands_dir, foot, cat, d28, r0,
                                              cand_pool_base, q, surfaces, h33_union, lidar,
                                              corrob_count, masks_by_key)

    report = {
        "generated_utc": "2026-10-23",
        "git_head_sha": git_head_sha(),
        "seed": 520810,
        "axis": AXIS,
        "axis_assignment": "not assigned by human (clarifying question skipped 2026-10-23); "
                           "PRUNE chosen as next unbuilt axis in the brief default plan; "
                           "subsumes SLOT_PLAN COLLAR_REFILL",
        "manifest_files_verified": len(verified),
        "parent_r0": {
            "id": PARENT_ID, "source_repo": "buffedlizard55-lab/GEMSDOE32",
            "live_score": 0.2778, "evidence_label": "CLAIM", "n_dots": EXPECTED_R0_DOTS,
            "digest8": r0_pair["digest8"], "nan_sha256": r0_pair["nan_sha256"],
            "zeros_sha256": r0_pair["zeros_sha256"], "exact_rebuild_verified": True,
            "d2_8_dots": int(d28.sum()),
            "solo_base_equals_d28_pruned_dgt1": solo_eq_dgt1,
            "ring_1lt_d_le2_in_d28": int((d28 & (dcat > 1.0) & (dcat <= 2.0)).sum()),
            "r0_dots_2lt_d_lt3": int((r0 & (dcat > 2.0) & (dcat < 3.0)).sum()),
            "r0_dots_d_eq3": int((r0 & (dcat == 3.0)).sum()),
            "historical_collar_ladder_claim": [
                {"file": "dotted-h19-5-d2-8 (no collar prune)", "n_dots": int(d28.sum()), "score": 0.2600},
                {"file": "h27-4-r1-solo-d2-8 (d_cat>1)", "n_dots": int(solo_base.sum()), "score": 0.2708},
                {"file": "h33-h33-2-b2 (d_cat>2) = R0", "n_dots": EXPECTED_R0_DOTS, "score": 0.2778},
            ],
        },
        "variants": records,
        "report_only_diagnostics": diagnostics,
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    out = ROOT / "evidence" / "r0_prune_variants_20261023.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Done in {report['elapsed_seconds']}s -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
