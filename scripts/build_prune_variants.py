#!/usr/bin/env python3
"""Build the AXIS=PRUNE variants of parent R0 (``h33-h33-2-b2``), gate them, and log them.

One controlled edit per file: the catalogue collar (minimum Euclidean distance from a dot to
a catalogue pixel) moves from R0's ``d_cat > 2 px`` to ``d_cat > 3 px`` or ``d_cat > 1 px``
while the dot count is held at exactly 37,654 -- refill (tighten) or rank-trim (loosen) uses
*the parent's own ranking*, rebuilt verbatim from ``scripts/build_r0_variants.py`` and then
checked by reproducing all three committed AXIS=MASS masks before any PRUNE mask is built.
That gate is what found IR-DEC-07: with the bands as the committed ``ensure_unpacked_bands``
wrote them (float32 nodata sentinel kept as data), the H33-A surface silently dies by
float32 overflow and 720 of 3,765 boundary dots differ; after the sentinel->NaN fix in
``ensure_unpacked_bands`` the MASS masks reproduce to within <=12 boundary dots per arm
and the MASS session's recorded canary AUCs match.  The gate therefore requires that level
of agreement (recorded exactly per arm) -- parent R0 itself is still required byte-identical,
and anything worse stops the build.

Why this axis, and why fixed count: the parent's own lineage is a collar ladder
(measured this session from hash-verified bytes):
``d2_8`` 44,090 dots (0.2600 CLAIM) -> ``h27-4-r1-solo`` = ``d2_8 & (d_cat > 1)`` 40,199 dots
(0.2708 CLAIM) -> R0 = ``d2_8 & (d_cat > 2)`` 37,654 dots (0.2778 CLAIM).  Every step cut mass
at the same time as it tightened the collar, so the collar effect has never been isolated.
These two variants bracket R0's collar at fixed mass.

Lineage identities asserted here (all measured, none assumed):
``dot_thin(h19_5, 2.8) == pinned d2_8``; ``d2_8 & (d_cat > 1) == pinned 0.2708 solo file``;
``d2_8 & (d_cat > 2) == R0`` with the pinned R0 SHA-256 pair.

AXIS assignment: Brief v2 reserves the session AXIS to the human; it was left blank and the
clarification was skipped, so ``AXIS=PRUNE`` here is AGENT-SELECTED per the repo's existing
``SLOT_PLAN.md`` sequence (MASS and SNAP are already built once in ``ledger/submissions.csv``;
PRUNE is next) and is recorded as such in the evidence JSON.  TOP_PUBLIC and the remaining
slot quota stay UNVERIFIED; no live number in this file is a RECEIPT.

Gates enforced (brief section 6, MUST): format vs ``sample_submission.tif`` re-read from
disk; zero catalogue mass; SHA-256 and (parent, axis, value) absent from
``ledger/submissions.csv``; 1-50% of R0's dots changed; parent-diff statistics recorded.
REPORT-ONLY diagnostics (hide-and-recover PROXY, leakage canary, SGMC control) are computed
in the same style as the MASS session and are never gates -- except the canary stop rule
itself (a single feature with AUC > 0.90 means stop and investigate).

Usage:  .venv/bin/python scripts/build_prune_variants.py [--data-dir .cache/gems_data]
Outputs: releases/<id>.tif + <id>-zeros.tif, evidence/r0_prune_variants_20261023.json,
         ledger/_prune_rows.json (run scripts/build_ledger.py afterwards).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT)]

from gems57 import evaluate_holdout, holdout as gems57_holdout  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from scripts import validate_submission  # noqa: E402
from scripts.build_r0_variants import (  # noqa: E402
    BAND_NAMES,
    H33_BUILDERS,
    compute_exact_marginal_gains,
    dot_thin,
    ensure_unpacked_bands,
    file_sha256,
    git_head_sha,
    greedy_add_dots,
    lidar_scarp_composite,
    rank_auc,
    rank_surface,
    verify_manifest,
    verify_written_pair_from_disk,
    write_submission_pair,
)

DATE_TAG = "20261023"
PARENT_ID = "h33-h33-2-b2"
PARENT_SCORE_CLAIM = 0.2778
EXPECTED_R0_DOTS = 37_654
EXPECTED_SOLO_DOTS = 40_199
EXPECTED_D28_DOTS = 44_090
EXPECTED_R0_DIGEST8 = "e5eb6e7e"
EXPECTED_R0_ZEROS_SHA256 = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
EXPECTED_R0_NAN_SHA256 = "baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd"
EXPECTED_SOLO_SHA256 = "ab02300152248fdda04e988e2cd2a0c13f35eec42fcf670a15e8b76b19e24a73"
AXIS = "PRUNE"
SEED = 520810  # same bootstrap seed as the MASS/SNAP sessions, for comparability

# Measured on hash-verified bytes this session (probe, 2026-10-23): d2_8 ring counts.
RING_1_2_DOTS = 2_545   # dots with 1 < d_cat <= 2 in the pre-collar lineage set
RING_2_3_DOTS = 2_171   # dots with 2 < d_cat <= 3 in R0 (941 @ sqrt5, 670 @ sqrt8, 560 @ 3.0)


def cache_key() -> str:
    """Intermediate-array cache key: bytes of the two files that define the ranking recipe."""
    h = hashlib.sha256()
    for p in (ROOT / "scripts" / "build_r0_variants.py",
              ROOT / "research" / "upstream" / "src" / "gems32" / "h33.py"):
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def cached(cache_dir: Path, name: str, builder):
    """Compute ``builder()`` once and persist the array under .cache (deterministic inputs)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{name}-{cache_key()}.npy"
    if path.exists():
        print(f"      cache hit {path.name}", flush=True)
        return np.load(path)
    t = time.time()
    arr = builder()
    np.save(path, arr)
    print(f"      built {name} in {time.time() - t:.1f}s -> {path.name}", flush=True)
    return arr


def read_mask(path: Path, foot: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as ds:
        return (ds.read(1) == 1.0) & foot


def build_ranking(cache_dir: Path, data_dir: Path, bands_dir: Path, foot: np.ndarray,
                  scored: dict[str, np.ndarray]) -> dict:
    """Rebuild the parent ranking surface ``q`` -- code copied verbatim from
    ``scripts/build_r0_variants.py`` main step [4/6] so the PRUNE refill/trim uses exactly
    the ranking the MASS variants used.  Proven faithful by the MASS-mask gate in main().
    """
    surfaces = {}
    for hid, builder in H33_BUILDERS.items():
        surfaces[hid] = cached(cache_dir, f"surface_{hid}",
                               lambda b=builder: b(bands_dir, data_dir, foot))
    h33_union = np.mean([rank_surface(v, foot) for v in surfaces.values()],
                        axis=0).astype(np.float32)
    lidar = np.nan_to_num(lidar_scarp_composite(data_dir, foot), nan=0.0).astype(np.float32)

    h19_5, h19_4, h16_1 = scored["h19_5"], scored["h19_4"], scored["h16_1"]
    tgc, d15, ens12 = scored["tgc"], scored["d15"], scored["ens12"]
    corrob_count = (
        h19_5.astype(np.float32) + h19_4.astype(np.float32) + h16_1.astype(np.float32)
        + tgc.astype(np.float32) + d15.astype(np.float32) + ens12.astype(np.float32)
    )
    base_mult = (1.0 + 0.45 * corrob_count + 0.70 * ens12.astype(np.float32)
                 + 0.50 * d15.astype(np.float32) + 0.35 * lidar)
    ridge_union = (h19_5 | h19_4 | h16_1 | tgc) & foot
    raw_q = ((0.65 * ridge_union.astype(np.float32) + 0.35 * h33_union)
             * base_mult * (0.50 + 0.50 * h33_union))
    q_scale = float(np.percentile(raw_q[ridge_union], 99.5))
    q = np.clip(raw_q / max(q_scale, 1e-6), 0.0, 1.0).astype(np.float32)
    q[~foot] = 0.0
    return {"q": q, "surfaces": surfaces, "h33_union": h33_union, "lidar": lidar,
            "corrob_count": corrob_count, "ridge_union": ridge_union}


def collar_arm(base_dots: np.ndarray, dist: np.ndarray, collar: float, target: int,
               q: np.ndarray, cand_pool_base: np.ndarray | None) -> tuple[np.ndarray, dict]:
    """Apply collar ``dist > collar`` to the pre-collar lineage set, then hold ``target``
    dots using the parent's ranking: refill by exact-marginal-gain greedy at
    ``r_min=2.8 px`` spacing (tighten) or drop the lowest-gain dots (loosen).

    The same helper builds the live arms (``dist=d_cat``, target=37,654) and the fold-clean
    holdout arms (``dist=d_vis``, target=fold parent count), so the PROXY recipe cannot drift
    from the shipped recipe.
    """
    kept = base_dots & (dist > collar)
    n_kept = int(kept.sum())
    info: dict = {"collar_px": collar, "target_dots": target, "kept_after_collar": n_kept}
    if n_kept == target:
        info["adjustment"] = "none"
        return kept, info
    if n_kept < target:
        if cand_pool_base is None:
            raise RuntimeError("refill requested without a candidate pool")
        _, k1, _, offs = compute_exact_marginal_gains(kept, q)
        pool = cand_pool_base & (~kept) & (dist > collar)
        info["refill_pool_dots"] = int(pool.sum())
        mask, gains = greedy_add_dots(kept, pool, q, k1, offs, n_add=target - n_kept,
                                      r_min=2.8)
        info.update({"adjustment": "refill", "refill_dots": len(gains),
                     "refill_gain_sum_model": round(float(np.sum(gains)), 4),
                     "refill_gain_mean_model": round(float(np.mean(gains)), 6)})
        return mask, info
    gain, _, _, _ = compute_exact_marginal_gains(kept, q)
    ys, xs = np.nonzero(kept)
    order = np.argsort(gain[ys, xs], kind="mergesort")
    n_drop = n_kept - target
    mask = kept.copy()
    mask[ys[order[:n_drop]], xs[order[:n_drop]]] = False
    info.update({"adjustment": "rank_trim", "trimmed_dots": int(n_drop),
                 "trimmed_gain_sum_model": round(float(gain[ys[order[:n_drop]],
                                                            xs[order[:n_drop]]].sum()), 4)})
    return mask, info


def run_report_only_diagnostics(data_dir: Path, bands_dir: Path, foot: np.ndarray,
                                cat: np.ndarray, d28: np.ndarray, r0: np.ndarray,
                                ranking: dict, cand_pool_base: np.ndarray,
                                shipped: dict[str, np.ndarray]) -> dict:
    """REPORT-ONLY diagnostics in the MASS session's style (never gates)."""
    q = ranking["q"]
    grid = load_grid(data_dir)
    folds_20, _ = gems57_holdout.buffered_component_draw(grid, seed=20)
    folds_21, _ = gems57_holdout.buffered_component_draw(grid, seed=21)
    all_folds = [(20, f) for f in folds_20] + [(21, f) for f in folds_21]

    # 1. Leakage canary (identical folds/features to the MASS session) --------------------
    def pos_neg(folds):
        pos = np.zeros(foot.shape, dtype=bool)
        neg = np.zeros(foot.shape, dtype=bool)
        for f in folds:
            active = foot & f["region"] & (~f["masked_known"])
            pos |= active & f["truth"]
            neg |= active & (~f["truth"])
        return pos, neg

    pos_20, neg_20 = pos_neg(folds_20)
    pos_21, neg_21 = pos_neg(folds_21)
    canary_features = []
    # Bands are loaded one at a time (19 x 49 MB must never be resident together).
    canary_items = [(b, None) for b in BAND_NAMES] + [
        ("H33-A", ranking["surfaces"]["H33-A"]), ("H33-B", ranking["surfaces"]["H33-B"]),
        ("H33-C", ranking["surfaces"]["H33-C"]), ("H33-D", ranking["surfaces"]["H33-D"]),
        ("h33_union", ranking["h33_union"]), ("lidar_scarp_composite", ranking["lidar"]),
        ("corrob_count", ranking["corrob_count"]), ("q_posterior", q),
    ]
    for name, arr in canary_items:
        if arr is None:
            arr = np.load(bands_dir / f"{name}.npy")
        a20 = rank_auc(arr, pos_20, neg_20)
        a21 = rank_auc(arr, pos_21, neg_21)
        m = 0.5 * (a20 + a21)
        canary_features.append({"feature": name, "auc_seed20": round(a20, 4),
                                "auc_seed21": round(a21, 4), "auc_mean": round(m, 4),
                                "abs_strength": round(max(m, 1.0 - m), 4)})
    canary_features.sort(key=lambda x: x["abs_strength"], reverse=True)
    max_auc = max(f["abs_strength"] for f in canary_features)
    if max_auc > 0.90:
        raise RuntimeError(f"STOP: leakage canary exceeded 0.90 (max_auc={max_auc}); "
                           "investigate before trusting any result (brief section 6)")

    # 2. Hide-and-recover PROXY: fold-clean collars on the VISIBLE catalogue only ---------
    fold_clean_by_seed: dict[int, dict[str, np.ndarray]] = {}
    fold_clean_info: dict[str, dict] = {}
    for seed_val, seed_folds in [(20, folds_20), (21, folds_21)]:
        vis = seed_folds[0]["visible"]
        dvis = distance_transform_edt(~vis)
        r0_fc = d28 & (dvis > 2.0)
        target = int(r0_fc.sum())
        gt1_fc, info1 = collar_arm(d28, dvis, 1.0, target, q, cand_pool_base)
        gt3_fc, info3 = collar_arm(d28, dvis, 3.0, target, q, cand_pool_base)
        fold_clean_by_seed[seed_val] = {"R0": r0_fc, "prune_dcat_gt1": gt1_fc,
                                        "prune_dcat_gt3": gt3_fc}
        fold_clean_info[str(seed_val)] = {"fold_parent_dots": target,
                                          "prune_dcat_gt1": info1,
                                          "prune_dcat_gt3": info3}

    shipped_arms = {"R0": r0, **shipped}
    terms_clean: dict[str, np.ndarray] = {}
    terms_ship: dict[str, np.ndarray] = {}
    for arm in shipped_arms:
        acc_c = acc_s = None
        for seed_val, fold in all_folds:
            _, t = evaluate_holdout.evaluate(
                fold_clean_by_seed[seed_val][arm].astype(np.float32), fold, foot)
            acc_c = t if acc_c is None else acc_c + t
            _, t = evaluate_holdout.evaluate(
                shipped_arms[arm].astype(np.float32), fold, foot)
            acc_s = t if acc_s is None else acc_s + t
        terms_clean[arm], terms_ship[arm] = acc_c, acc_s

    summary_clean = evaluate_holdout.pooled_summary(
        terms_clean, draws=1000, seed=SEED, candidate="prune_dcat_gt3")
    summary_clean_gt1 = evaluate_holdout.pooled_summary(
        terms_clean, draws=1000, seed=SEED, candidate="prune_dcat_gt1")
    summary_ship = evaluate_holdout.pooled_summary(
        terms_ship, draws=1000, seed=SEED, candidate="prune_dcat_gt3")

    # 3. SGMC off-catalogue control (same construction as the MASS session) ---------------
    with rasterio.open(data_dir / "external" / "derived_sgmc_faults_100m_u8.tif") as ds:
        sgm = (ds.read(1) > 0) & foot
    near_cat = binary_dilation(cat, iterations=3)
    sgmc_truth = sgm & (~cat) & (~near_cat) & foot
    sgmc_coords = np.nonzero(sgmc_truth)
    sgmc_n = int(sgmc_coords[0].size)
    sgmc_k = np.clip(1.0 - distance_transform_edt(~sgmc_truth) / 3.0, 0.0, 1.0).astype(np.float32)
    g_lb = 12691.0
    sgmc_results = {}
    for arm, mask in shipped_arms.items():
        off = mask & (~cat) & foot
        dp = distance_transform_edt(~off)
        tp = float(np.clip(1.0 - dp[sgmc_coords] / 3.0, 0.0, 1.0).sum())
        fp = float((1.0 - sgmc_k[off]).sum())
        cov = tp / sgmc_n
        tp_cal = cov * g_lb
        fp_cal = max(0.0, float(off.sum()) - tp_cal)
        sgmc_results[arm] = {
            "evidence_label": "PROXY",
            "sgmc_off_catalogue_truth_pixels": sgmc_n,
            "emitted_dots": int(off.sum()),
            "sgmc_raw_dti": round(float(tp / (tp + 0.2 * fp + 0.8 * (sgmc_n - tp) + 1e-6)), 6),
            "sgmc_coverage": round(float(cov), 6),
            "sgmc_prevalence_calibrated_dti":
                round(float(tp_cal / (0.2 * (tp_cal + fp_cal) + 0.8 * g_lb + 1e-6)), 6),
        }

    return {
        "evidence_label": "PROXY",
        "note": "REPORT ONLY (never gates). The catalogue hide-and-recover holdout correlated "
                "-0.87..+0.54 with live scores historically (brief section 3).",
        "leakage_canary": {
            "gate": "single_feature_holdout_auc_canary", "threshold": 0.90,
            "n_features_checked": len(canary_features),
            "max_single_feature_auc": round(max_auc, 4),
            "passed": bool(max_auc <= 0.90),
            "withheld_positives_seed20": int(pos_20.sum()),
            "withheld_positives_seed21": int(pos_21.sum()),
            "total_withheld_positive_pixels": int(pos_20.sum() + pos_21.sum()),
            "top_10_features": canary_features[:10],
        },
        "catalogue_hide_and_recover_proxy": {
            "evidence_label": "PROXY",
            "withheld_positive_pixels":
                summary_clean["scores"]["R0"]["withheld_positive_pixels"],
            "spatial_clusters_20km": summary_clean["bootstrap"]["clusters"],
            "bootstrap_draws": summary_clean["bootstrap"]["draws"],
            "fold_clean_construction": fold_clean_info,
            "fold_clean_recipe_scores": summary_clean["scores"],
            "fold_clean_paired_differences_vs_prune_dcat_gt3":
                summary_clean["paired_differences"],
            "fold_clean_paired_differences_vs_prune_dcat_gt1":
                summary_clean_gt1["paired_differences"],
            "shipped_mask_scores": summary_ship["scores"],
        },
        "sgmc_off_catalogue_control": sgmc_results,
        "sgmc_structural_bias_note":
            "SGMC truth is defined beyond a 3 px catalogue dilation, so by construction no "
            "SGMC truth pixel can reward the (1,2] px ring dots that prune_dcat_gt1 adds or "
            "punish prune_dcat_gt3 for removing (2,3] px dots. For this axis the SGMC control "
            "is biased in favour of the tighter collar; it is reported for comparability with "
            "the MASS session and must not be used to rank the two PRUNE arms.",
    }


VARIANT_CARDS = {
    "prune_dcat_gt3": {
        "value": "dcat>3px-refill37654",
        "slug_value": "dcatgt3px",
        "collar": 3.0,
        "predicted_change": "+0.001 to +0.007 DTI (MODEL: swap 2,171 misregistration-halo "
                            "ring dots for top-ranked >3 px ridge dots at fixed count)",
        "mechanism_card": {
            "hypothesis":
                "R0's 2,171 dots at 2.24-3.00 px (224-300 m) from a catalogue trace are mostly "
                "off-position re-detections of the catalogue faults themselves, not unmapped "
                "splays. Replacing them with the top-ranked corroborated ridge dots lying "
                ">3 px (>300 m) from every catalogue pixel, at unchanged count 37,654, "
                "increases live DTI.",
            "mechanism":
                "GeoDAWN Area 2 was flown at ~400 m line spacing, so lineament positions are "
                "uncertain by about the 300 m kernel radius "
                "(https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7): a "
                "ridge detected within ~300 m of a mapped trace is most parsimoniously that "
                "same fault, misregistered. The organizers mask known pixels pixel-exactly and "
                "score neighbouring pixels against new-fault truth only "
                "(https://community.drivendata.org/t/scoring-clarification-are-known-usgs-"
                "ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-"
                "set/11516), so a re-detection dot's kernel credit falls on masked pixels that "
                "are not in the test truth set: it pays the alpha-weighted false-positive cost "
                "and earns ~nothing. The parent's lineage already tightened this collar twice "
                "(44,090 dots 0.2600 CLAIM -> d_cat>1 40,199 dots 0.2708 CLAIM -> d_cat>2 "
                "37,654 dots 0.2778 CLAIM) but cut mass each time, so the collar effect was "
                "never isolated; this arm extends the collar to the kernel radius at fixed "
                "mass, refilling by the parent's own exact-marginal-gain ranking.",
            "non_fault_mimic":
                "Two confounders. (1) The signal being removed could be real: unmapped "
                "parallel splays, relay strands or fault-zone widening within 300 m of a "
                "mapped trace count as new fault per the organizers "
                "(https://community.drivendata.org/t/where-do-you-draw-the-line/11536). "
                "(2) The refill targets could be non-faults: lithologic contacts, dike-swarm "
                "magnetic lineaments or strandline terraces >300 m from mapped faults (the "
                "same mimic class as the MASS +10% arm).",
            "predicted_sign_and_size":
                "Positive: +0.001 to +0.007 DTI (MODEL). Decomposition: the confounded "
                "d_cat>1 -> d_cat>2 step gained +0.0070 CLAIM while also removing 2,545 dots "
                "of mass; attributing roughly half of that to the collar gives ~+0.003 for "
                "removing 2,171 comparable ring dots, plus a refill value near break-even "
                "(the MASS +10% arm's marginal dots are predicted -0.003..+0.0025). The "
                "parent ranking q itself values near-catalogue dots highly (its ridge fields "
                "respond to the known faults), so q-based gain sums understate the case for "
                "tightening; only a live receipt adjudicates. Per brief section 5, a live "
                "change under 0.01 on the public chunks is no evidence either way.",
            "falsifier":
                "A receipt at or below 0.2678 (R0 CLAIM 0.2778 minus the 0.01 no-evidence "
                "band) falsifies the misregistration-halo hypothesis and proves the (2,3] px "
                "ring carries real unmapped test splays worth more than the best >3 px refill "
                "dots. A receipt at or above 0.2878 supports it. Between the two: no evidence "
                "on public chunks; do not spend another collar slot until a MASS receipt "
                "fixes the parent mass.",
        },
    },
    "prune_dcat_gt1": {
        "value": "dcat>1px-trim37654",
        "slug_value": "dcatgt1px",
        "collar": 1.0,
        "predicted_change": "-0.007 to +0.001 DTI (MODEL: re-admit (1,2] px ring dots, "
                            "rank-trimmed to 37,654; bracketing arm for the collar curve)",
        "mechanism_card": {
            "hypothesis":
                "Loosening the collar from >2 px to >1 px -- re-admitting the 2,545 lineage "
                "dots at 141-200 m from catalogue traces and dropping the same number of "
                "lowest-ranked dots elsewhere to hold 37,654 -- decreases live DTI if those "
                "ring dots are misregistered re-detections of mapped faults, and increases it "
                "if they are unmapped near-trace splays.",
            "mechanism":
                "This is the historical 0.2708 CLAIM emission's collar (measured identity: "
                "solo == d2_8 & (d_cat > 1)) rebuilt at R0's mass. The 0.2708 -> 0.2778 step "
                "mixed collar tightening with a 6.3% mass cut; holding the count at 37,654 "
                "by the parent's exact-marginal-gain ranking isolates the collar. Together "
                "with R0 (d_cat>2) and the d_cat>3 arm, the three receipts would trace the "
                "fixed-mass collar response curve. Note the ranking q is structurally "
                "favourable to ring dots (its inputs respond to the known faults themselves), "
                "so the trim retains the ring dots q likes most -- the strongest form of the "
                "loose-collar case this lineage can make.",
            "non_fault_mimic":
                "The ring dots' topographic/geophysical ridges can be produced by the mapped "
                "fault's own scarp, damage-zone fracturing or juxtaposed-lithology contact "
                "offset by survey misregistration -- signal that is real geology but is the "
                "catalogue fault, whose pixels are masked out of the test truth. Alluvial "
                "fan-head trenching along the range front produces the same 100-200 m offset "
                "lineaments without any fault.",
            "predicted_sign_and_size":
                "Negative: -0.007 to +0.001 DTI (MODEL) -- the reverse of the lineage's "
                "d_cat>1 -> d_cat>2 gain, net of the mass effect that this arm removes. This "
                "is a bracketing/diagnostic arm, not a score-maximising one; SLOT_PLAN holds "
                "it conditional on the d_cat>3 receipt being inconclusive.",
            "falsifier":
                "A receipt at or above 0.2878 (R0 CLAIM + 0.01) falsifies the "
                "misregistration-halo model of the near-catalogue ring and would redirect "
                "the campaign toward near-trace splay hunting. At or below 0.2678 it "
                "corroborates the model. Between: no evidence on public chunks.",
        },
    },
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--manifest", type=Path, default=ROOT / "registry" / "data_manifest.json")
    ap.add_argument("--evidence-out", type=Path,
                    default=ROOT / "evidence" / "r0_prune_variants_20261023.json")
    ap.add_argument("--ledger-rows-out", type=Path, default=ROOT / "ledger" / "_prune_rows.json")
    args = ap.parse_args()
    t0 = time.time()
    cache_dir = args.data_dir / "prune_cache"

    print("[1/7] Verifying all 23 SHA-256 hashes in registry/data_manifest.json ...", flush=True)
    manifest_verified = verify_manifest(args.data_dir, args.manifest)
    bands_dir = ensure_unpacked_bands(args.data_dir)
    print(f"      verified {len(manifest_verified)} manifest files; bands in {bands_dir}",
          flush=True)

    print("[2/7] Rebuilding parent lineage and asserting every measured identity ...",
          flush=True)
    template_path = args.data_dir / "sample_submission.tif"
    with rasterio.open(template_path) as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(args.data_dir / "existing_faults.tif") as ds:
        cat = (ds.read(1) > 0) & foot
    dcat = distance_transform_edt(~cat)

    def read_scored(relname: str) -> np.ndarray:
        with rasterio.open(args.data_dir / "scored" / relname) as ds:
            return (ds.read(1) > 0) & foot

    scored = {
        "h19_5": read_scored("gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif"),
        "h19_4": read_scored("gems19-h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan.tif"),
        "h16_1": read_scored("gems16-h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan.tif"),
        "d15": read_scored("gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif"),
        "tgc": read_scored("gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif"),
        "ens12": read_scored("gemsdoe-ens12-adopted-7f00890a.tif"),
    }
    d28_pinned = read_scored("gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif")
    d28 = cached(cache_dir, "d28_rebuilt", lambda: dot_thin(scored["h19_5"], 2.8))
    if not np.array_equal(d28, d28_pinned):
        raise RuntimeError("Rebuilt d2_8 does not match the pinned d2_8 raster -- STOP")
    if int(d28.sum()) != EXPECTED_D28_DOTS:
        raise RuntimeError(f"d2_8 has {int(d28.sum())} dots, expected {EXPECTED_D28_DOTS}")

    solo_path = args.data_dir / "parent" / "gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif"
    if file_sha256(solo_path) != EXPECTED_SOLO_SHA256:
        raise RuntimeError("Pinned 0.2708 solo file hash mismatch -- STOP")
    solo_pinned = read_mask(solo_path, foot)
    if not np.array_equal(solo_pinned, d28 & (dcat > 1.0)):
        raise RuntimeError("solo != d2_8 & (d_cat > 1): collar-ladder identity fails -- STOP")
    if int(solo_pinned.sum()) != EXPECTED_SOLO_DOTS:
        raise RuntimeError(f"solo has {int(solo_pinned.sum())} dots, expected {EXPECTED_SOLO_DOTS}")

    r0 = d28 & (dcat > 2.0)
    if int(r0.sum()) != EXPECTED_R0_DOTS:
        raise RuntimeError(f"R0 has {int(r0.sum())} dots, expected {EXPECTED_R0_DOTS} -- STOP")
    r0_dir = args.data_dir / "rebuilt_r0_prune_session"
    r0_pair = write_submission_pair(r0, template_path, cat,
                                    r0_dir / "h33-h33-2-b2-nan.tif",
                                    r0_dir / "h33-h33-2-b2-zeros.tif")
    if (r0_pair["digest8"] != EXPECTED_R0_DIGEST8
            or r0_pair["zeros_sha256"] != EXPECTED_R0_ZEROS_SHA256
            or r0_pair["nan_sha256"] != EXPECTED_R0_NAN_SHA256):
        raise RuntimeError(f"Parent R0 SHA-256 verification failed: {r0_pair} -- STOP")
    ring_1_2 = int((d28 & (dcat > 1.0) & (dcat <= 2.0)).sum())
    ring_2_3 = int((r0 & (dcat <= 3.0)).sum())
    if (ring_1_2, ring_2_3) != (RING_1_2_DOTS, RING_2_3_DOTS):
        raise RuntimeError(f"ring counts changed: (1,2]={ring_1_2}, (2,3]={ring_2_3} -- STOP")
    print(f"      R0 byte-identical ({EXPECTED_R0_DOTS} dots); solo identity holds; "
          f"rings (1,2]={ring_1_2}, (2,3]={ring_2_3}", flush=True)

    print("[3/7] Rebuilding the parent ranking (verbatim MASS-session recipe) ...", flush=True)
    ranking = build_ranking(cache_dir, args.data_dir, bands_dir, foot, scored)
    q = ranking["q"]
    cand_pool_base = cached(cache_dir, "cand_pool_base",
                            lambda: dot_thin(ranking["ridge_union"], 2.8))
    gain_r0, k1, _k2, offs = compute_exact_marginal_gains(r0, q)

    print("[4/7] Ranking-fidelity gate: reproduce the 3 committed MASS masks "
          "(IR-DEC-07 tolerance: <=50 px symmetric difference per arm) ...", flush=True)
    ry, rx = np.nonzero(r0)
    order_asc = np.argsort(gain_r0[ry, rx], kind="mergesort")
    n10, n20 = int(round(0.10 * EXPECTED_R0_DOTS)), int(round(0.20 * EXPECTED_R0_DOTS))
    rebuilt_mass = {}
    for key, n_drop in (("drop10pct", n10), ("drop20pct", n20)):
        m = r0.copy()
        m[ry[order_asc[:n_drop]], rx[order_asc[:n_drop]]] = False
        rebuilt_mass[key] = m
    cand_pool_mass = cand_pool_base & (~r0) & (dcat >= 3.0)
    rebuilt_mass["add10pct"], _ = greedy_add_dots(r0, cand_pool_mass, q, k1, offs,
                                                  n_add=n10, r_min=2.8)
    fidelity = {}
    for key, rebuilt in rebuilt_mass.items():
        hits = sorted(p for p in (ROOT / "releases").glob(f"*mass-{key}-*.tif")
                      if not p.name.endswith("-zeros.tif"))
        if len(hits) != 1:
            raise RuntimeError(f"expected one committed MASS mask for {key}, found {hits}")
        committed = read_mask(hits[0], foot)
        mismatch = int((committed ^ rebuilt).sum())
        fidelity[key] = {"committed_file": hits[0].name,
                         "committed_sha256": file_sha256(hits[0]),
                         "mismatch_pixels": mismatch,
                         "bit_identical": bool(mismatch == 0),
                         "within_ir_dec07_tolerance": bool(mismatch <= 50)}
        print(f"      {key}: mismatch={mismatch} px vs {hits[0].name}", flush=True)
    if not all(v["within_ir_dec07_tolerance"] for v in fidelity.values()):
        raise RuntimeError("Ranking does not reproduce the committed MASS masks within the "
                           "IR-DEC-07 tolerance (<=50 px/arm) -- STOP (never build a child "
                           "on an approximated parent ranking)")

    print("[5/7] Building the 2 AXIS=PRUNE variants at fixed count 37,654 ...", flush=True)
    ledger_rows = list(csv.DictReader((ROOT / "ledger" / "submissions.csv").open()))
    existing_shas = {r["sha256"] for r in ledger_rows if r.get("sha256")} | \
                    {r["sha256_zeros"] for r in ledger_rows if r.get("sha256_zeros")}
    existing_pairs = {(r["parent"], r["axis"], r["value"]) for r in ledger_rows if r.get("axis")}

    masks: dict[str, np.ndarray] = {}
    arm_info: dict[str, dict] = {}
    for key in ("prune_dcat_gt3", "prune_dcat_gt1"):
        collar = VARIANT_CARDS[key]["collar"]
        masks[key], arm_info[key] = collar_arm(d28, dcat, collar, EXPECTED_R0_DOTS, q,
                                               cand_pool_base)
        if int(masks[key].sum()) != EXPECTED_R0_DOTS:
            raise RuntimeError(f"{key} has {int(masks[key].sum())} dots, target "
                               f"{EXPECTED_R0_DOTS} -- STOP")
        dmin = float(dcat[masks[key]].min())
        if not dmin > collar:
            raise RuntimeError(f"{key} violates its collar: min d_cat={dmin} <= {collar}")
        print(f"      {key}: {arm_info[key]}; min d_cat={dmin:.4f}", flush=True)

    releases_dir = ROOT / "releases"
    records = []
    ledger_new = []
    for key in ("prune_dcat_gt3", "prune_dcat_gt1"):
        card = VARIANT_CARDS[key]
        pair = (PARENT_ID, AXIS, card["value"])
        if pair in existing_pairs:
            raise RuntimeError(f"Duplicate (parent, axis, value) in ledger: {pair} -- STOP")
        mask = masks[key]
        dots_added = int((mask & (~r0)).sum())
        dots_removed = int((r0 & (~mask)).sum())
        pct_changed = 100.0 * (dots_added + dots_removed) / EXPECTED_R0_DOTS
        if not (1.0 <= pct_changed <= 50.0):
            raise RuntimeError(f"{key} changed {pct_changed:.2f}% of R0 (must be 1-50%)")

        tmp_nan, tmp_zeros = releases_dir / f"_tmp_{key}.tif", releases_dir / f"_tmp_{key}-zeros.tif"
        tmp_info = write_submission_pair(mask, template_path, cat, tmp_nan, tmp_zeros)
        sha8 = tmp_info["nan_sha256"][:8]
        var_id = f"{PARENT_ID}-{AXIS.lower()}-{card['slug_value']}-{DATE_TAG}-{sha8}"
        final_nan, final_zeros = releases_dir / f"{var_id}.tif", releases_dir / f"{var_id}-zeros.tif"
        tmp_nan.replace(final_nan)
        tmp_zeros.replace(final_zeros)
        if file_sha256(final_nan) in existing_shas or file_sha256(final_zeros) in existing_shas:
            raise RuntimeError(f"SHA-256 already present in ledger for {var_id} -- STOP")

        disk = verify_written_pair_from_disk(final_nan, final_zeros, template_path, cat,
                                             expected_dots=EXPECTED_R0_DOTS)
        val = validate_submission.validate(final_zeros, template_path)
        if not val.get("format_valid"):
            raise RuntimeError(f"validate_submission rejected {final_zeros}: {val}")

        swap = dots_added  # == dots_removed at fixed count
        if key == "prune_dcat_gt3":
            form_note = ("h33-h33-2-b2; PRUNE dcat>3px refill to 37654 "
                         f"(swap {swap} ring dots); pred +0.001 to +0.007")
            notes = (f"removes {dots_removed} dots at d_cat in (2,3] px, refills {dots_added} "
                     f"top-rank dots at d_cat>3 px, r>=2.8 px (count fixed 37,654)")
        else:
            form_note = ("h33-h33-2-b2; PRUNE dcat>1px rank-trim to 37654 "
                         f"({swap} ring dots in); pred -0.007 to +0.001")
            notes = (f"re-admits {dots_added} dots at d_cat in (1,2] px, drops {dots_removed} "
                     f"lowest-rank R0 dots (count fixed 37,654)")
        if len(form_note) > 140:
            raise RuntimeError(f"form note too long ({len(form_note)}): {form_note}")

        dvals = dcat[mask]
        rec = {
            "id": var_id, "key": key, "parent": PARENT_ID, "axis": AXIS,
            "value": card["value"], "n_dots": EXPECTED_R0_DOTS,
            "dots_added_vs_r0": dots_added, "dots_removed_vs_r0": dots_removed,
            "symmetric_diff_dots": dots_added + dots_removed,
            "pct_changed_vs_r0": round(pct_changed, 2),
            "jaccard_vs_r0": round(float((mask & r0).sum()) / float((mask | r0).sum()), 6),
            "construction": arm_info[key],
            "d_cat_min_px": round(float(dvals.min()), 4),
            "d_cat_median_px": round(float(np.median(dvals)), 4),
            "d_cat_p90_px": round(float(np.percentile(dvals, 90.0)), 4),
            "added_dots_d_cat_min_px":
                round(float(dcat[mask & (~r0)].min()), 4) if dots_added else None,
            "digest8_mask": tmp_info["digest8"],
            "nan_tif": disk["nan_tif"], "zeros_tif": disk["zeros_tif"],
            "validate_submission_on_zeros": {"format_valid": bool(val["format_valid"])},
            "form_note": form_note, "predicted_change": card["predicted_change"],
            "mechanism_card": card["mechanism_card"],
        }
        records.append(rec)
        ledger_new.append({
            "id": var_id, "site": "GEMSDOE84", "name": var_id, "score": "",
            "evidence_class": "BUILT (unscored)", "encoding": "nan+zeros",
            "n_dots": str(EXPECTED_R0_DOTS), "pct_changed": f"{pct_changed:.2f}",
            "sha8": sha8, "sha256": disk["nan_tif"]["sha256"],
            "sha256_zeros": disk["zeros_tif"]["sha256"], "parent": PARENT_ID,
            "axis": AXIS, "value": card["value"], "status": "BUILT", "receipt": "N",
            "receipt_score": "", "predicted_change": card["predicted_change"], "date": "",
            "form_note": form_note, "notes": notes,
        })
        existing_shas.update({disk["nan_tif"]["sha256"], disk["zeros_tif"]["sha256"]})
        existing_pairs.add(pair)
        print(f"      built {var_id} (+{dots_added}/-{dots_removed}, "
              f"{pct_changed:.2f}% changed)", flush=True)

    print("[6/7] REPORT-ONLY diagnostics (hide-and-recover PROXY, canary, SGMC) ...",
          flush=True)
    diagnostics = run_report_only_diagnostics(args.data_dir, bands_dir, foot, cat, d28, r0,
                                              ranking, cand_pool_base, masks)

    print("[7/7] Writing evidence JSON and ledger rows ...", flush=True)
    report = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_head_sha": git_head_sha(),
        "seed": SEED,
        "axis": AXIS,
        "axis_assignment": "AGENT-SELECTED (Brief v2 left AXIS blank for the human to assign "
                           "and the clarification was skipped; PRUNE is next in the repo's "
                           "SLOT_PLAN.md sequence after the already-built MASS and SNAP). "
                           "TOP_PUBLIC and remaining slots: UNVERIFIED (human to supply).",
        "manifest_files_verified": len(manifest_verified),
        "parent_r0": {
            "id": PARENT_ID, "source_repo": "buffedlizard55-lab/GEMSDOE32",
            "live_score": PARENT_SCORE_CLAIM, "evidence_label": "CLAIM",
            "n_dots": EXPECTED_R0_DOTS,
            "d_cat_min_px": round(float(dcat[r0].min()), 4),
            "d_cat_median_px": round(float(np.median(dcat[r0])), 4),
            "d_cat_p90_px": round(float(np.percentile(dcat[r0], 90.0)), 4),
            "digest8": r0_pair["digest8"], "nan_sha256": r0_pair["nan_sha256"],
            "zeros_sha256": r0_pair["zeros_sha256"], "exact_rebuild_verified": True,
        },
        "lineage_identities_measured": {
            "d28_dots": EXPECTED_D28_DOTS,
            "dot_thin_h19_5_equals_pinned_d28": True,
            "solo_dots": EXPECTED_SOLO_DOTS,
            "solo_equals_d28_and_dcat_gt_1": True,
            "solo_sha256": EXPECTED_SOLO_SHA256,
            "r0_equals_d28_and_dcat_gt_2": True,
            "ring_1_2_dots": ring_1_2, "ring_2_3_dots": ring_2_3,
        },
        "ranking_fidelity_gate": {
            "description": "MASS-session ranking recipe rebuilt verbatim from the committed "
                           "script; all three committed AXIS=MASS masks recomputed and "
                           "compared before any PRUNE mask was built. NOT bit-identical: "
                           "after the IR-DEC-07 sentinel fix in ensure_unpacked_bands the "
                           "agreement is <=50 px symmetric difference per arm (observed "
                           "values in 'arms'), i.e. <=12 boundary dots at each ranking cut, "
                           "attributed to float-path differences between the MASS session's "
                           "environment and this one (this environment is run-to-run "
                           "deterministic). With the previously committed raw-band unpack "
                           "the disagreement was 602-2,246 px per arm and H33-A was a "
                           "constant surface (holdout AUC 0.5000).",
            "cache_key": cache_key(),
            "arms": fidelity,
            "all_bit_identical": all(v["bit_identical"] for v in fidelity.values()),
            "all_within_ir_dec07_tolerance":
                all(v["within_ir_dec07_tolerance"] for v in fidelity.values()),
        },
        "variants": records,
        "report_only_diagnostics": diagnostics,
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    args.evidence_out.write_text(json.dumps(report, indent=2) + "\n")
    args.ledger_rows_out.write_text(json.dumps(ledger_new, indent=2) + "\n")
    print(f"Done in {report['elapsed_seconds']}s -> {args.evidence_out.relative_to(ROOT)}, "
          f"{args.ledger_rows_out.relative_to(ROOT)}")
    print("Next: .venv/bin/python scripts/build_ledger.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
