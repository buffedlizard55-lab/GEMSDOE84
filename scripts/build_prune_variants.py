#!/usr/bin/env python3
"""AXIS = PRUNE: collar-width sweep on Parent R0 (``h33-h33-2-b2``), count held fixed.

Brief v2 section 5 (PRUNE): *remove dots <= 1, <= 2 (R0), <= 3 px from the catalogue; refill to
hold the count.*  R0 already excludes every dot at ``d_cat <= 2 px``, so the <= 1 px and <= 2 px
values are empty sets for this parent (documented in the receipt).  The informative values are the
ones that cut *into* R0's collar, so this session sweeps the collar width upward and keeps the dot
count at exactly 37,654 by refilling from the parent's own recorded ranking.

Why this is the highest-value remaining axis
--------------------------------------------
The R0 lineage's only demonstrated live gain is a catalogue-collar prune (d2.8 -> d_cat > 2 px:
0.2708 -> 0.2778 CLAIM).  The scoring kernel is 3 px wide, so R0 still emits 2,171 dots inside the
3 px kernel footprint of a masked known-catalogue pixel (1,611 strictly between 2 and 3 px, 560 at
exactly 3.0 px; ``evidence/r0_mass_variants_20261023.json``).  Known USGS/INGENIOUS pixels are
masked pixel-exactly out of the label set, so a dot whose kernel disc is dominated by masked
catalogue pays false-positive mass without collecting credit; the counter-case is new-fault truth
lying within 300 m of a known trace (organizer forum answer 11516).  This sweep measures which
side dominates.

Design
------
* Parent: rebuilt byte-identically from the pinned recipe (SHA-256 ``c55bafc4...``) and verified.
* One change only: the catalogue collar width (2.5 / 3.0 / 4.0 px).  Everything else -- ranking,
  refill pool, spacing gate (2.8 px), d_cat >= 3.0 px on added dots, emission writer -- is held at
  the parent's recorded setting.
* Count held at 37,654: every pruned collar dot is replaced by the highest exact-marginal-DTI-gain
  candidate from the parent's own pool, so the variants isolate *location*, not mass.
* Gates, then REPORT-ONLY diagnostics (hide-and-recover PROXY, leakage canary, SGMC control).

Usage
-----
    python scripts/build_prune_variants.py [--data-dir .cache/gems_data]
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
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
from gems57.grid import load_grid as load_grid57  # noqa: E402
from gems84.parent import (  # noqa: E402
    R0_ZEROS_SHA256,
    emit_dots,
    load_grid,
    rebuild_r0_mask,
    sha256_file,
    verify_r0_file,
)

AXIS = "PRUNE"
PARENT_ID = "h33-2-b2"
DATE_TAG = "20261023"
PARENT_SCORE_CLAIM = 0.2778
EXPECTED_R0_DOTS = 37654
SEED = 520810
# Live-anchor denominator (recorded in scripts/build_snap_variants.py: LIVE_ANCHOR_DENOMINATOR):
# DTI denominator at the 0.2708 anchor, i.e. 0.2T + 0.2(S-M) + 0.8|G|.  Used only to convert a
# marginal-gain sum into a DTI-scale MODEL projection; never a score.
LIVE_ANCHOR_DENOMINATOR = 18734.44

# Collar widths (px) of the catalogue exclusion for the *pruned* mask.  R0 = 2.0 px.
VARIANTS = (
    {
        "value": "d2p5",
        "collar_px": 2.5,
        "hypothesis": (
            "Cutting the collar from 2.0 to 2.5 px removes only the 941 R0 dots in the innermost "
            "diagonal shell (d_cat in (2.0, 2.5]); at that distance a dot's 3 px triangular kernel "
            "is >83% dominated by masked catalogue pixels, so those dots should pay false-positive "
            "mass with little collectable credit. Refilling them from the off-catalogue ridge pool "
            "should be weakly positive."
        ),
        "falsifier": (
            "A live score below 0.2768 (>= 0.0010 under R0's 0.2778 CLAIM) falsifies the claim that "
            "the innermost diagonal shell is net false-positive dominated."
        ),
    },
    {
        "value": "d3p0",
        "collar_px": 3.0,
        "hypothesis": (
            "Removing every R0 dot within one full kernel radius (300 m) of masked catalogue "
            "pixels (2,171 dots, 5.77% of R0) and refilling at matched count with off-catalogue "
            "corroborated ridge dots removes mass that can earn almost no credit, because the "
            "catalogue pixels underneath are masked out of the label set."
        ),
        "falsifier": (
            "A live score below 0.2768 falsifies the collar-false-positive hypothesis and would "
            "show that unmapped new-fault truth sits inside 300 m of the known traces (as the "
            "organizer allowed), making the collar a productive band."
        ),
    },
    {
        "value": "d4p0",
        "collar_px": 4.0,
        "hypothesis": (
            "If the collar penalty is monotone, a 4 px exclusion (3,825 dots, 10.16% of R0) should "
            "beat the 3 px variant. Along-strike continuations and relay splays of mapped faults "
            "live in this band, so the sign is genuinely uncertain: this point measures where the "
            "collar-vs-continuation trade turns over."
        ),
        "falsifier": (
            "A live score below the 3 px variant falsifies monotonicity of the collar penalty and "
            "bounds the optimum collar width at or below 3 px."
        ),
    },
)


def load_r0_pipeline():
    """Import the recorded R0-ranking recipe (scripts/build_r0_variants.py) as a module."""
    spec = importlib.util.spec_from_file_location("gems_r0_variants", ROOT / "scripts" / "build_r0_variants.py")
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError("cannot import scripts/build_r0_variants.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:  # pragma: no cover
        return "unknown"


def read_ledger(path: Path) -> tuple[dict[str, set[str]], list[dict], list[str]]:
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    hashes: dict[str, set[str]] = {}
    for r in rows:
        for key in ("sha256", "sha256_zeros"):
            if r.get(key):
                hashes.setdefault(r[key], set()).add(r["id"])
        if r.get("sha8"):
            hashes.setdefault(r["sha8"], set()).add(r["id"])
    return hashes, rows, fieldnames


def write_ledger(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    tmp = path.with_suffix(".csv.tmp")
    with tmp.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\r\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    tmp.replace(path)


def check_format(path: Path, grid, template: Path, mode: str) -> dict:
    """Re-read a written GeoTIFF and run every MUST-pass format gate from Brief v2 section 6."""
    with rasterio.open(template) as ref:
        ref_crs = ref.crs
        ref_shape = (ref.height, ref.width)
        ref_transform = ref.transform
        foot = np.isfinite(ref.read(1))
    with rasterio.open(path) as src:
        arr = src.read(1)
        crs, shape, transform = src.crs, (src.height, src.width), src.transform
        dtype, count = src.dtypes[0], src.count
    in_foot, out_foot = arr[foot], arr[~foot]
    checks = {
        "crs_epsg32611": str(crs) == str(ref_crs) == "EPSG:32611",
        "shape_matches_template": shape == ref_shape,
        "transform_matches_template": transform == ref_transform,
        "single_band": count == 1,
        "float32": dtype == "float32",
        "no_nan_in_footprint": bool(np.isfinite(in_foot).all()),
        "values_in_0_1": bool(((in_foot >= 0.0) & (in_foot <= 1.0)).all()),
        "outside_is_nan" if mode == "nan" else "outside_is_zero": bool(
            np.isnan(out_foot).all() if mode == "nan" else (np.isfinite(out_foot).all() and np.all(out_foot == 0.0))
        ),
    }
    return {
        "checks": checks,
        "all_passed": all(checks.values()),
        "dots": int((arr == 1.0).sum()),
        "catalogue_mass": float(np.nan_to_num(arr[grid.catalogue], nan=0.0).sum()),
        "sha256": sha256_file(path),
    }


def rank_auc(values: np.ndarray, pos: np.ndarray, neg: np.ndarray) -> float:
    p = values[pos]
    n = values[neg]
    p = p[np.isfinite(p)]
    n = n[np.isfinite(n)]
    if p.size == 0 or n.size == 0:
        return 0.5
    s = np.concatenate([p, n]).astype(np.float64)
    lab = np.concatenate([np.ones(p.size), np.zeros(n.size)])
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(s.size, dtype=np.float64)
    ranks[order] = np.arange(1, s.size + 1, dtype=np.float64)
    _, inv, cnt = np.unique(s, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=ranks)
    ranks = (sums / cnt)[inv]
    n1, n0 = float(p.size), float(n.size)
    return float((ranks[lab == 1].sum() - n1 * (n1 + 1.0) / 2.0) / (n1 * n0))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", default=str(ROOT / ".cache" / "gems_data"))
    ap.add_argument("--releases", default=str(ROOT / "releases"))
    ap.add_argument("--ledger", default=str(ROOT / "ledger" / "submissions.csv"))
    ap.add_argument("--receipt", default=str(ROOT / "evidence" / "prune_variants_receipt.json"))
    args = ap.parse_args()

    t0 = time.time()
    data_dir = Path(args.data_dir)
    releases = Path(args.releases)
    releases.mkdir(parents=True, exist_ok=True)
    template = data_dir / "sample_submission.tif"
    brv = load_r0_pipeline()

    print("[1/6] Verifying pinned inputs (registry/data_manifest.json) ...")
    manifest_verified = brv.verify_manifest(data_dir, ROOT / "registry" / "data_manifest.json")
    bands_dir = brv.ensure_unpacked_bands(data_dir)
    print(f"      {len(manifest_verified)} manifest hashes and 19 unpacked bands verified.")

    print("[2/6] Rebuilding Parent R0 and matching its SHA-256 ...")
    grid = load_grid(data_dir)
    r0, base = rebuild_r0_mask(data_dir)
    if int(r0.sum()) != EXPECTED_R0_DOTS:
        raise SystemExit(f"parent dot count {int(r0.sum())} != {EXPECTED_R0_DOTS}")
    if int((r0 & grid.catalogue).sum()) != 0:
        raise SystemExit("parent emits mass on catalogue pixels")
    parent_check = verify_r0_file(
        data_dir / "parent" / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif", grid
    )
    if parent_check["sha256"] != R0_ZEROS_SHA256:
        raise SystemExit("parent R0 file does not match its pin; refusing to build variants")
    print(f"      R0 = {int(r0.sum()):,} dots, sha256 {R0_ZEROS_SHA256[:16]}... verified.")

    print("[3/6] Rebuilding the parent's own ranking (recorded GEMSDOE32 recipe) ...")
    from research.upstream.src.gems32.h33 import (  # noqa: E402
        H33_BUILDERS,
        lidar_scarp_composite,
        rank_surface,
    )

    def read_scored(relname: str) -> np.ndarray:
        with rasterio.open(data_dir / "scored" / relname) as ds:
            return (ds.read(1) > 0) & grid.foot

    h19_5 = read_scored("gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif")
    h19_4 = read_scored("gems19-h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan.tif")
    h16_1 = read_scored("gems16-h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan.tif")
    d15 = read_scored("gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif")
    tgc = read_scored("gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif")
    ens12 = read_scored("gemsdoe-ens12-adopted-7f00890a.tif")

    surfaces = {hid: builder(bands_dir, data_dir, grid.foot) for hid, builder in H33_BUILDERS.items()}
    h33_union = np.mean([rank_surface(v, grid.foot) for v in surfaces.values()], axis=0).astype(np.float32)
    lidar = np.nan_to_num(lidar_scarp_composite(data_dir, grid.foot), nan=0.0).astype(np.float32)

    corrob_count = (
        h19_5.astype(np.float32) + h19_4.astype(np.float32) + h16_1.astype(np.float32)
        + tgc.astype(np.float32) + d15.astype(np.float32) + ens12.astype(np.float32)
    )
    base_mult = 1.0 + 0.45 * corrob_count + 0.70 * ens12.astype(np.float32) \
        + 0.50 * d15.astype(np.float32) + 0.35 * lidar
    ridge_union = (h19_5 | h19_4 | h16_1 | tgc) & grid.foot
    raw_q = (0.65 * ridge_union.astype(np.float32) + 0.35 * h33_union) * base_mult \
        * (0.50 + 0.50 * h33_union)
    q_scale = float(np.percentile(raw_q[ridge_union], 99.5))
    q = np.clip(raw_q / max(q_scale, 1e-6), 0.0, 1.0).astype(np.float32)
    q[~grid.foot] = 0.0
    cand_pool_base = brv.dot_thin(ridge_union, 2.8)
    # Refill pool: off-catalogue corroborated ridge dots, spaced at the parent's 2.8 px, and never
    # inside the 3 px kernel footprint of the catalogue (held constant across all three variants).
    refill_pool = cand_pool_base & (~r0) & (grid.d_cat >= 3.0)
    print(f"      refill pool = {int(refill_pool.sum()):,} off-catalogue dots "
          f"(d_cat >= 3.0 px, r_min = 2.8 px)")

    ledger_hashes, ledger_rows, fieldnames = read_ledger(Path(args.ledger))
    existing_pairs = {(r.get("parent", ""), r.get("axis", ""), r.get("value", "")) for r in ledger_rows}
    pair_shas = {(r.get("parent", ""), r.get("axis", ""), r.get("value", "")): (r.get("sha256") or "")
                 for r in ledger_rows}

    print("[4/6] Building PRUNE variants (collar sweep, count held at 37,654) ...")
    r0_gain, _, _, _ = brv.compute_exact_marginal_gains(r0, q)
    records: list[dict] = []
    arms: dict[str, np.ndarray] = {"R0": r0}
    for spec in VARIANTS:
        collar = float(spec["collar_px"])
        pruned = r0 & (grid.d_cat > collar)
        removed = int((r0 & ~pruned).sum())
        if removed == 0:
            raise SystemExit(f"{spec['value']}: collar {collar} px removes no R0 dots")
        gain_v, K1_v, _, offs = brv.compute_exact_marginal_gains(pruned, q)
        mask, added_gains = brv.greedy_add_dots(
            pruned, refill_pool, q, K1_v, offs, n_add=removed, r_min=2.8
        )
        n_dots = int(mask.sum())
        dots_added = int((mask & ~r0).sum())
        dots_removed = int((r0 & ~mask).sum())
        sym = dots_added + dots_removed
        pct_changed = 100.0 * sym / float(EXPECTED_R0_DOTS)
        if not (1.0 <= pct_changed <= 50.0):
            raise SystemExit(f"{spec['value']}: {pct_changed:.2f}% changed is outside [1, 50]%")

        # MODEL projection.  The exact-marginal-gain sum is a *ranking* quantity: q is a continuous
        # ridge posterior, not an indicator truth field, so its absolute value is not commensurate
        # with the live-anchor DTI denominator (summing it directly would project +0.17 DTI from
        # 2,171 dots, which is impossible at this truth prevalence).  It is therefore used for its
        # SIGN only, and the DTI-scale projection comes from the one measured collar move in the
        # lineage: d_cat <= 2 px prune of 6,436 dots -> +0.0070 live (0.2708 -> 0.2778, both CLAIM),
        # i.e. 1.088e-6 DTI per removed collar dot.  Refilling 1:1 at the top of the parent's own
        # pool is assumed net-neutral; the upper bound allows each refill dot to be worth as much
        # as a collar dot, i.e. double the anchor slope.
        cy, cx = np.nonzero(r0 & ~pruned)
        collar_gain_lost = float(r0_gain[cy, cx].sum())
        refill_gain = float(np.sum(added_gains))
        ranking_sign = "negative" if refill_gain < collar_gain_lost else "positive"
        anchor_slope = 0.0070 / 6436.0
        model_delta = removed * anchor_slope
        model_lo, model_hi = 0.0, 2.0 * model_delta

        nan_path = releases / f"_tmp_{spec['value']}.tif"
        zeros_path = releases / f"_tmp_{spec['value']}-zeros.tif"
        emit_dots(mask, grid, nan_path, mode="nan")
        emit_dots(mask, grid, zeros_path, mode="zeros")
        nan_chk = check_format(nan_path, grid, template, "nan")
        zeros_chk = check_format(zeros_path, grid, template, "zeros")
        sha8 = nan_chk["sha256"][:8]
        file_id = f"{PARENT_ID}-prune{spec['value']}-{DATE_TAG}-{sha8}"
        final_nan = releases / f"{file_id}.tif"
        final_zeros = releases / f"{file_id}-zeros.tif"
        nan_path.replace(final_nan)
        zeros_path.replace(final_zeros)

        pair = (PARENT_ID, AXIS, spec["value"])
        # Hashes owned by this very (parent, axis, value) row are an idempotent rebuild, not a dup.
        own_ids = {r["id"] for r in ledger_rows
                   if (r.get("parent"), r.get("axis"), r.get("value")) == pair}
        dup = sorted({f for h in (nan_chk["sha256"], zeros_chk["sha256"])
                      for f in ledger_hashes.get(h, set())} - own_ids)
        gates = {
            "nan_format": nan_chk["all_passed"],
            "zeros_format": zeros_chk["all_passed"],
            "count_held": n_dots == nan_chk["dots"] == zeros_chk["dots"] == EXPECTED_R0_DOTS,
            "zero_catalogue_mass": nan_chk["catalogue_mass"] == 0.0 and zeros_chk["catalogue_mass"] == 0.0,
            "inside_footprint": int((mask & ~grid.foot).sum()) == 0,
            "added_dots_d_cat_ge_3": int((mask & ~r0).sum()) == dots_added
            and float(grid.d_cat[mask & ~r0].min()) >= 3.0,
            "differs_from_parent": not np.array_equal(mask, r0),
            "sha256_not_in_ledger": not dup,
            # A repeated (parent, axis, value) is allowed only as a byte-identical rebuild of the
            # row already in the ledger; anything else is a real duplicate experiment.
            "pair_not_repeated_or_identical": pair not in existing_pairs
            or pair_shas.get(pair) == nan_chk["sha256"],
        }
        if not all(gates.values()):
            raise SystemExit(f"gate failure for {file_id}: {gates}")

        added_dcat = grid.d_cat[mask & ~r0]
        rec = {
            "id": file_id,
            "parent": PARENT_ID,
            "axis": AXIS,
            "value": spec["value"],
            "collar_px": collar,
            "n_dots": n_dots,
            "dots_removed_collar": dots_removed,
            "dots_added_refill": dots_added,
            "pct_changed_vs_r0": round(pct_changed, 2),
            "jaccard_vs_r0": round(float((mask & r0).sum()) / float((mask | r0).sum()), 6),
            "removed_d_cat_max_px": round(float(grid.d_cat[r0 & ~pruned].max()), 4),
            "added_d_cat_min_px": round(float(added_dcat.min()), 4),
            "added_d_cat_median_px": round(float(np.median(added_dcat)), 4),
            "model_delta_dti": round(model_delta, 5),
            "model_delta_components": {
                "lineage_anchor_central_dti": round(model_delta, 5),
                "predicted_band_dti": [round(model_lo, 5), round(model_hi, 5)],
                "anchor_slope_dti_per_removed_dot": anchor_slope,
                "ranking_arithmetic_sign": ranking_sign,
                "ranking_units_refill_gain_sum": round(refill_gain, 3),
                "ranking_units_collar_gain_lost_sum": round(collar_gain_lost, 3),
                "ranking_units_note": (
                    "ranking units only (q is a continuous posterior, not indicator truth); "
                    "not commensurate with the live DTI denominator, used for sign alone"
                ),
                "live_anchor_denominator_reference": LIVE_ANCHOR_DENOMINATOR,
            },
            "nan_tif": {"path": str(final_nan.relative_to(ROOT)), "sha256": nan_chk["sha256"],
                        "dots": nan_chk["dots"], "checks": nan_chk["checks"]},
            "zeros_tif": {"path": str(final_zeros.relative_to(ROOT)), "sha256": zeros_chk["sha256"],
                          "dots": zeros_chk["dots"], "checks": zeros_chk["checks"]},
            "form_note": (
                f"{PARENT_ID}; PRUNE collar {collar:g}px ({dots_removed} dots out, {dots_added} "
                f"refill at dcat>=3px); pred {model_delta:+.3f} DTI"
            ),
            "predicted_change": (
                f"MODEL {model_lo:+.4f}..{model_hi:+.4f} DTI (lineage-anchored {model_delta:+.4f} "
                f"central, refill assumed neutral); ranking arithmetic favors {ranking_sign}"
            ),
            "mechanism_card": {
                "hypothesis": spec["hypothesis"],
                "mechanism": (
                    f"Under DTI = T / (0.2T + 0.2(S-M) + 0.8|G|) each unit-mass dot adds "
                    f"0.2(1 - m_q) to the denominator and (1 - 0.2s)dT to the numerator. Known "
                    f"USGS/INGENIOUS pixels are masked pixel-exactly out of the label set, so a dot "
                    f"inside the 3 px (300 m) kernel footprint of a masked catalogue pixel can only "
                    f"collect credit from *new-fault* truth. Collar dots are swapped 1:1 for the "
                    f"highest exact-marginal-gain off-catalogue ridge dots (d_cat >= 3.0 px, "
                    f"r_min = 2.8 px) from the parent's own ranked pool, so total mass and mean "
                    f"spacing are held and only collar geometry changes."
                ),
                "non_fault_mimic": (
                    "Alluvial-fan head-cut scarps, pediment slope breaks and playa margins that "
                    "parallel mapped range-front faults at 200-400 m; these mimic an unmapped splay "
                    "and would make collar dots productive rather than wasteful."
                ),
                "predicted_sign_and_size": (
                    f"MODEL {model_lo:+.4f}..{model_hi:+.4f} DTI (central {model_delta:+.4f} from "
                    f"1.088e-6 DTI per removed collar dot x {removed} dots, refill assumed neutral). "
                    f"Note the disagreement: the parent's own masking-blind ranking arithmetic prices "
                    f"the collar dots higher than the refill pool ({ranking_sign}), yet the lineage's "
                    f"one measured collar prune (0.2708 -> 0.2778 CLAIM) moved the other way, which is "
                    f"exactly why this axis is worth a slot. Live changes under 0.010 count as no "
                    f"evidence (public chunks only)."
                ),
                "falsifier": spec["falsifier"],
            },
        }
        records.append(rec)
        arms[spec["value"]] = mask
        print(f"      {file_id}: collar {collar:g}px, {dots_removed} out + {dots_added} in "
              f"({pct_changed:.2f}% changed), MODEL {model_delta:+.4f} DTI, sha8 {sha8}")

    print("[5/6] REPORT-ONLY diagnostics (hide-and-recover PROXY, leakage canary, SGMC control) ...")
    diag_grid = load_grid57(data_dir)
    folds_20, _ = gems57_holdout.buffered_component_draw(diag_grid, seed=20)
    folds_21, _ = gems57_holdout.buffered_component_draw(diag_grid, seed=21)
    all_folds = [(20, f) for f in folds_20] + [(21, f) for f in folds_21]

    pos20 = np.zeros(grid.foot.shape, bool)
    neg20 = np.zeros(grid.foot.shape, bool)
    pos21 = np.zeros(grid.foot.shape, bool)
    neg21 = np.zeros(grid.foot.shape, bool)
    for f in folds_20:
        active = grid.foot & f["region"] & (~f["masked_known"])
        pos20 |= active & f["truth"]
        neg20 |= active & (~f["truth"])
    for f in folds_21:
        active = grid.foot & f["region"] & (~f["masked_known"])
        pos21 |= active & f["truth"]
        neg21 |= active & (~f["truth"])

    canary = []
    for bname in brv.BAND_NAMES:
        arr = np.load(bands_dir / f"{bname}.npy")
        m = 0.5 * (rank_auc(arr, pos20, neg20) + rank_auc(arr, pos21, neg21))
        canary.append({"feature": bname, "auc_mean": round(m, 4), "abs_strength": round(max(m, 1 - m), 4)})
    for name, arr in {**surfaces, "h33_union": h33_union, "lidar_scarp_composite": lidar,
                      "corrob_count": corrob_count, "q_posterior": q}.items():
        m = 0.5 * (rank_auc(arr, pos20, neg20) + rank_auc(arr, pos21, neg21))
        canary.append({"feature": name, "auc_mean": round(m, 4), "abs_strength": round(max(m, 1 - m), 4)})
    canary.sort(key=lambda x: x["abs_strength"], reverse=True)
    max_auc = canary[0]["abs_strength"]
    if max_auc > 0.90:
        raise SystemExit(f"STOP: leakage canary exceeded 0.90 (max_auc={max_auc})")

    terms: dict[str, np.ndarray] = {}
    for name, mask in arms.items():
        acc = None
        for _, fold in all_folds:
            _, t = evaluate_holdout.evaluate(mask.astype(np.float32), fold, diag_grid.footprint)
            acc = t if acc is None else acc + t
        terms[name] = acc
    summary = evaluate_holdout.pooled_summary(
        terms, draws=1000, seed=SEED, candidate=VARIANTS[1]["value"]
    )

    with rasterio.open(data_dir / "external" / "derived_sgmc_faults_100m_u8.tif") as ds:
        sgm = (ds.read(1) > 0) & grid.foot
    near_cat = binary_dilation(grid.catalogue, iterations=3)
    sgmc_truth = sgm & (~grid.catalogue) & (~near_cat) & grid.foot
    sgmc_coords = np.nonzero(sgmc_truth)
    n_sg = int(sgmc_coords[0].size)
    sgmc_dt = distance_transform_edt(~sgmc_truth)
    k_dg = np.clip(1.0 - sgmc_dt / 3.0, 0.0, 1.0).astype(np.float32)
    g_lb = 12691.0
    sgmc = {}
    for name, mask in arms.items():
        off = mask & (~grid.catalogue) & grid.foot
        dp = distance_transform_edt(~off)
        tp = float(np.clip(1.0 - dp[sgmc_coords] / 3.0, 0.0, 1.0).sum())
        fn = float(n_sg) - tp
        fp = float((1.0 - k_dg[off]).sum())
        raw = float(tp / (tp + 0.2 * fp + 0.8 * fn + 1e-6))
        cov = float(tp / n_sg)
        tp_cal = cov * g_lb
        fp_cal = max(0.0, float(off.sum()) - tp_cal)
        cal = float(tp_cal / (0.2 * (tp_cal + fp_cal) + 0.8 * g_lb + 1e-6))
        sgmc[name] = {"sgmc_raw_dti": round(raw, 6), "sgmc_coverage": round(cov, 6),
                      "sgmc_prevalence_calibrated_dti": round(cal, 6)}

    print("[6/6] Appending BUILT rows to the ledger ...")
    for rec in records:
        new_row = ({
            "id": rec["id"], "site": "GEMSDOE84", "name": rec["id"], "score": "",
            "evidence_class": "BUILT (unscored)", "encoding": "nan+zeros", "n_dots": str(rec["n_dots"]),
            "pct_changed": f"{rec['pct_changed_vs_r0']:.2f}", "sha8": rec["nan_tif"]["sha256"][:8],
            "sha256": rec["nan_tif"]["sha256"], "sha256_zeros": rec["zeros_tif"]["sha256"],
            "parent": PARENT_ID, "axis": AXIS, "value": rec["value"], "status": "BUILT",
            "receipt": "N", "receipt_score": "", "predicted_change": rec["predicted_change"],
            "date": "", "form_note": rec["form_note"],
            "notes": (f"collar {rec['collar_px']:g} px; {rec['dots_removed_collar']} collar dots out, "
                      f"{rec['dots_added_refill']} refill in at d_cat >= 3.0 px; MODEL "
                      f"{rec['model_delta_dti']:+.4f} DTI lineage-anchored; ranking arithmetic "
                      f"{rec['model_delta_components']['ranking_arithmetic_sign']}"),
        })
        for i, row in enumerate(ledger_rows):
            if (row.get("parent"), row.get("axis"), row.get("value")) == (PARENT_ID, AXIS, rec["value"]):
                ledger_rows[i] = new_row
                break
        else:
            ledger_rows.append(new_row)
    write_ledger(Path(args.ledger), ledger_rows, fieldnames)
    print(f"      ledger now has {len(ledger_rows)} rows ({len(records)} PRUNE rows written/replaced).")

    receipt = {
        "schema_version": 1,
        "axis": AXIS,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_sha": git_sha(),
        "seed": SEED,
        "manifest_files_verified": len(manifest_verified),
        "parent": {
            "id": PARENT_ID,
            "n_dots": int(r0.sum()),
            "zeros_sha256": R0_ZEROS_SHA256,
            "rebuild_byte_identical": True,
            "claimed_live": PARENT_SCORE_CLAIM,
            "claimed_live_evidence_class": "CLAIM",
            "collar_px": 2.0,
            "d_cat_min_px": round(float(grid.d_cat[r0].min()), 4),
            "dots_within_2p5_px": int((grid.d_cat[r0] <= 2.5).sum()),
            "dots_within_3p0_px": int((grid.d_cat[r0] <= 3.0).sum()),
            "dots_within_4p0_px": int((grid.d_cat[r0] <= 4.0).sum()),
        },
        "brief_values_not_buildable": {
            "<=": "1 px and <= 2 px collars remove 0 dots from R0 because R0 already excludes "
                 "every dot at d_cat <= 2 px; recorded rather than emitted as empty variants."
        },
        "refill_rule": "pool = dot_thin(h19_5|h19_4|h16_1|tgc, 2.8) & ~R0 & d_cat >= 3.0; "
                       "1:1 replacement by descending exact marginal DTI gain at s0 = 0.2778",
        "variants": records,
        "report_only_diagnostics": {
            "evidence_label": "PROXY",
            "note": "REPORT ONLY (Brief v2 section 6): never gates.",
            "leakage_canary": {
                "threshold": 0.90, "n_features_checked": len(canary), "max_single_feature_auc": max_auc,
                "passed": bool(max_auc <= 0.90),
                "withheld_positives_seed20": int(pos20.sum()), "withheld_positives_seed21": int(pos21.sum()),
                "total_withheld_positive_pixels": int(pos20.sum() + pos21.sum()),
                "top_10_features": canary[:10],
            },
            "catalogue_hide_and_recover_proxy": {
                "withheld_positive_pixels": summary["scores"]["R0"]["withheld_positive_pixels"],
                "bootstrap_draws": summary["bootstrap"]["draws"],
                "shipped_mask_scores": summary["scores"],
                "shipped_mask_paired_differences_vs_d3p0": summary["paired_differences"],
            },
            "sgmc_off_catalogue_control": sgmc,
        },
        "parent_marginal_gain_sum": round(float(r0_gain.sum()), 3),
        "elapsed_s": round(time.time() - t0, 1),
    }
    Path(args.receipt).write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"      receipt -> {args.receipt} ({receipt['elapsed_s']}s)")
    print(f"      canary max AUC = {max_auc:.4f}; PROXY holdout (shipped): "
          + ", ".join(f"{k}={v['dti']:.4f}" for k, v in summary["scores"].items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
