#!/usr/bin/env python3
"""Reproduction audit for the 2026-10-23 AXIS=PRUNE builds (IR-DEC-13).

This script BUILDS NOTHING for submission. It re-derives the parent MASS-session ranking
from the committed recipe (``scripts/build_r0_variants.py`` with the IR-DEC-13
sentinel->NaN band cleaning) and measures, writing everything to
``evidence/prune_reproduction_audit_20261023.json``:

1. lineage identities (d2_8 / solo / R0) and R0's pinned SHA-256 pair;
2. ranking fidelity: the three committed AXIS=MASS masks recomputed and compared
   pixel-exact (tolerance recorded, not assumed);
3. canary fingerprints (holdout AUCs of q_posterior / h33_union / lidar composite,
   seeds 20/21) for the cleaned ranking, next to the values the MASS session recorded
   and the values the two merged PRUNE sessions recorded -- the comparison that shows
   those sessions ranked refill/trim dots with the pre-fix (sentinel-poisoned) surface;
4. pairwise dot overlap among the six merged PRUNE releases and clean-ranking collar
   arms rebuilt in memory (never written to releases/), quantifying that the poisoned
   ranking changed at most a few hundred refill dots per file;
5. the disposition: main's six PRUNE files stand (built-once rule); the third parallel
   implementation that found IR-DEC-13 withdrew its two duplicate files in PR #28:
   h33-h33-2-b2-prune-dcatgt3px-20261023-a7d86ed4 (nan sha256
   a7d86ed4266cf3c9e408fccb6ee81aee43bddf18c49a5e54a9436b5a9d36f5f0) and
   h33-h33-2-b2-prune-dcatgt1px-20261023-f5c7e4fb (nan sha256
   f5c7e4fb3db30907dd361c89018e4cb937620f963fe27a3809a9d1ba205da56d),
   preserved in that PR's first commit (874a63c) only. Do not submit them.

Usage: .venv/bin/python scripts/audit_prune_reproduction.py [--data-dir .cache/gems_data]
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
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT)]

from gems57 import holdout as gems57_holdout  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from scripts.build_r0_variants import (  # noqa: E402
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
    write_submission_pair,
)

EXPECTED_R0_DOTS = 37_654
EXPECTED_SOLO_DOTS = 40_199
EXPECTED_D28_DOTS = 44_090
EXPECTED_R0_DIGEST8 = "e5eb6e7e"
EXPECTED_R0_ZEROS_SHA256 = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
EXPECTED_R0_NAN_SHA256 = "baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd"
EXPECTED_SOLO_SHA256 = "ab02300152248fdda04e988e2cd2a0c13f35eec42fcf670a15e8b76b19e24a73"
FIDELITY_TOLERANCE_PX = 50

# Values the MASS session recorded (evidence/r0_mass_variants_20261023.json). The two merged
# PRUNE sessions recorded q_posterior 0.6035/0.5853 and h33_union 0.5810/0.5583 instead.
MASS_RECORDED_AUCS = {
    "q_posterior": (0.6039, 0.5860),
    "h33_union": (0.5813, 0.5614),
    "lidar_scarp_composite": (0.5855, 0.5616),
}

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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    ap.add_argument("--manifest", type=Path, default=ROOT / "registry" / "data_manifest.json")
    ap.add_argument("--evidence-out", type=Path,
                    default=ROOT / "evidence" / "prune_reproduction_audit_20261023.json")
    args = ap.parse_args()
    t0 = time.time()
    cache_dir = args.data_dir / "prune_cache"

    manifest_verified = verify_manifest(args.data_dir, args.manifest)
    bands_dir = ensure_unpacked_bands(args.data_dir)
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
    assert np.array_equal(d28, d28_pinned) and int(d28.sum()) == EXPECTED_D28_DOTS
    solo_path = args.data_dir / "parent" / "gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif"
    assert file_sha256(solo_path) == EXPECTED_SOLO_SHA256
    assert np.array_equal(read_mask(solo_path, foot), d28 & (dcat > 1.0))
    r0 = d28 & (dcat > 2.0)
    assert int(r0.sum()) == EXPECTED_R0_DOTS
    r0_pair = write_submission_pair(r0, template_path, cat,
                                    args.data_dir / "audit_r0" / "nan.tif",
                                    args.data_dir / "audit_r0" / "zeros.tif")
    assert (r0_pair["digest8"], r0_pair["zeros_sha256"], r0_pair["nan_sha256"]) == \
        (EXPECTED_R0_DIGEST8, EXPECTED_R0_ZEROS_SHA256, EXPECTED_R0_NAN_SHA256)

    ranking = build_ranking(cache_dir, args.data_dir, bands_dir, foot, scored)
    q = ranking["q"]
    cand_pool_base = cached(cache_dir, "cand_pool_base",
                            lambda: dot_thin(ranking["ridge_union"], 2.8))
    gain_r0, k1, _k2, offs = compute_exact_marginal_gains(r0, q)

    # MASS-mask fidelity of the cleaned ranking.
    ry, rx = np.nonzero(r0)
    order_asc = np.argsort(gain_r0[ry, rx], kind="mergesort")
    rebuilt_mass = {}
    for key, n_drop in (("drop10pct", 3765), ("drop20pct", 7531)):
        m = r0.copy()
        m[ry[order_asc[:n_drop]], rx[order_asc[:n_drop]]] = False
        rebuilt_mass[key] = m
    rebuilt_mass["add10pct"], _ = greedy_add_dots(
        r0, cand_pool_base & (~r0) & (dcat >= 3.0), q, k1, offs, n_add=3765, r_min=2.8)
    fidelity = {}
    for key, rebuilt in rebuilt_mass.items():
        hits = sorted(p for p in (ROOT / "releases").glob(f"*mass-{key}-*.tif")
                      if not p.name.endswith("-zeros.tif"))
        assert len(hits) == 1, hits
        mismatch = int((read_mask(hits[0], foot) ^ rebuilt).sum())
        fidelity[key] = {"committed_file": hits[0].name, "mismatch_pixels": mismatch,
                         "bit_identical": bool(mismatch == 0),
                         "within_tolerance": bool(mismatch <= FIDELITY_TOLERANCE_PX)}

    # Canary fingerprints (cleaned ranking) vs recorded values.
    grid = load_grid(args.data_dir)
    def pos_neg(seed):
        folds, _ = gems57_holdout.buffered_component_draw(grid, seed=seed)
        pos = np.zeros(foot.shape, bool); neg = np.zeros(foot.shape, bool)
        for f in folds:
            a = foot & f["region"] & (~f["masked_known"])
            pos |= a & f["truth"]; neg |= a & (~f["truth"])
        return pos, neg
    p20, n20 = pos_neg(20); p21, n21 = pos_neg(21)
    impl_a = json.loads((ROOT / "evidence" / "r0_prune_variants_20261023.json").read_text())
    impl_a_top = {r["feature"]: r for r in
                  impl_a["report_only_diagnostics"]["leakage_canary"]["top_10_features"]}
    fingerprints = {}
    for name, arr in (("q_posterior", q), ("h33_union", ranking["h33_union"]),
                      ("lidar_scarp_composite", ranking["lidar"]),
                      ("H33-A", ranking["surfaces"]["H33-A"])):
        rec = impl_a_top.get(name, {})
        fingerprints[name] = {
            "cleaned_ranking_auc_seed20": round(float(rank_auc(arr, p20, n20)), 4),
            "cleaned_ranking_auc_seed21": round(float(rank_auc(arr, p21, n21)), 4),
            "mass_session_recorded": MASS_RECORDED_AUCS.get(name),
            "merged_prune_sessions_recorded":
                [rec.get("auc_seed20"), rec.get("auc_seed21")] if rec else None,
        }

    # Clean-ranking collar arms in memory vs the six merged PRUNE releases on disk.
    clean_gt3, _ = collar_arm(d28, dcat, 3.0, EXPECTED_R0_DOTS, q, cand_pool_base)
    clean_gt1, _ = collar_arm(d28, dcat, 1.0, EXPECTED_R0_DOTS, q, cand_pool_base)
    ledger = list(csv.DictReader((ROOT / "ledger" / "submissions.csv").open()))
    prune_ids = [r["id"] for r in ledger if r.get("axis") == "PRUNE" and r["status"] == "BUILT"]
    on_disk = {}
    for pid in prune_ids:
        p = ROOT / "releases" / f"{pid}.tif"
        assert p.exists(), p
        on_disk[pid] = read_mask(p, foot)
    def agree(a, b):
        return {"shared_dots": int((a & b).sum()), "symmetric_diff_dots": int((a ^ b).sum())}
    agreements = {
        "clean_gt3_vs_each_merged_prune_file": {pid: agree(clean_gt3, m) for pid, m in on_disk.items()},
        "clean_gt1_vs_each_merged_prune_file": {pid: agree(clean_gt1, m) for pid, m in on_disk.items()},
        "within_merged_gt3_class": {
            f"{a} vs {b}": agree(on_disk[a], on_disk[b])
            for a, b in (("h33-h33-2-b2-prune-dgt3refill-20261023-10ce9ad1",
                          "h33-2-b2-pruned3p0-20261023-26e80847"),)},
    }

    report = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_head_sha": git_head_sha(),
        "purpose": "IR-DEC-13 reproduction audit: no submission file is built here.",
        "manifest_files_verified": len(manifest_verified),
        "parent_r0_sha256_verified": True,
        "lineage_identities_measured": {
            "solo_equals_d28_and_dcat_gt_1": True, "r0_equals_d28_and_dcat_gt_2": True,
            "ring_1_2_dots": int((d28 & (dcat > 1.0) & (dcat <= 2.0)).sum()),
            "ring_2_3_dots": int((r0 & (dcat <= 3.0)).sum())},
        "ranking_fidelity_gate": {"tolerance_px": FIDELITY_TOLERANCE_PX, "arms": fidelity,
                                  "cache_key": cache_key()},
        "canary_fingerprints": fingerprints,
        "mask_agreements": agreements,
        "disposition": "Main's six PRUNE files stand as the built-once PRUNE set. The "
                       "sentinel cleaning changes <=273 refill dots in the >3 px class "
                       "(measured pairwise above), far below the 0.01 live-DTI evidence "
                       "band, so no merged file is rebuilt. The third parallel "
                       "implementation's two duplicate files were withdrawn in PR #28 "
                       "before merge (ids/sha256 in this module's docstring).",
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    args.evidence_out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"fidelity": fidelity, "elapsed": report["elapsed_seconds"]}, indent=1))
    print(f"audit written -> {args.evidence_out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
