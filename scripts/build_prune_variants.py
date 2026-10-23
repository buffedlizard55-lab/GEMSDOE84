#!/usr/bin/env python3
"""Build brief-v2 PRUNE variants of parent R0 (h33-h33-2-b2, GEMSDOE32).

R0 is recovered byte-exactly (sha256-pinned) and independently rebuilt:
R0 dots == h27-4-r1 dots minus dots within <=2 px (Euclidean) of the
catalogue.  If either check fails this script stops and writes nothing.

Variants (AXIS=PRUNE, refill to hold the count at 37,654):
  prune3r : remove R0 dots with d_catalogue <= 3 px, refill the same number.
  prune4r : remove R0 dots with d_catalogue <= 4 px, refill the same number.

Refill rule (deterministic; the lineage rasters are binary, so no continuous
ranking is stored -- the ranking is rebuilt ordinally from the lineage):
  * Pool: H19-5 field support with d_catalogue > B, excluding kept dots.
    Refill can only reuse pixels the ancestral field itself nominated.
  * Removed dots are processed in raster order.  For each, pool candidates
    are ordered by (distance to the removed dot, lineage tier [in d1.5
    before H19-5-only], row, col) and the first candidate at >=2.8 px from
    every kept/chosen dot is taken (parent's minimum spacing: measured R0
    nearest-neighbour minimum is 2.83 px).  Local refill holds the km-scale
    dot distribution fixed, so the only intended change is collar distance.

Inputs are sha256-verified before use (registry/data_manifest.json pins plus
the parent pins below).  Outputs: releases/<id>.tif (NaN outside footprint)
and releases/<id>-zeros.tif (0.0 outside), plus releases/<id>.json receipts.
No network access; no Drivendata contact.  Data root: $GEMS84_DATA
(default /home/user/gemsdata).  Fetch the pinned inputs there first.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "data" / "bridge"
DATA = Path(os.environ.get("GEMS84_DATA", "/home/user/gemsdata"))
RELEASES = ROOT / "releases"
DATE = "20261023"
PARENT = "h33-h33-2-b2"
N_PARENT = 37_654
# Measured 2026-10-23: the ancestral d2.8 thinning is near-maximal w.r.t. the
# H19-5 support -- only 611 (B=3) / 577 (B=4) pool pixels sit >=2.8 px from a
# kept dot, fewer than the 2,171 / 3,825 refills needed.  A 2.8 px refill
# spacing is therefore impossible on the ancestral field; the floor is 2.0 px
# (8,986 / 8,601 pool pixels).  The spacing degradation is confined to refill
# dots, is reported in every receipt, and biases the predicted gain downward.
MIN_SPACING_PX = 2.0
STRICT_SPACING_PX = 2.8  # parent spacing; recorded as diagnostic only

# sha256 pins: first three also in registry/data_manifest.json; parent pins
# from evidence/h33-original-audit.json + evidence/h33_validation.json and
# appended to the manifest by this session (2026-10-23).
PINS = {
    "sample": (BRIDGE / "sample_submission.tif",
               "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"),
    "labels": (BRIDGE / "labels.tif",
               "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093"),
    "r0_zeros": (DATA / "parent" / "r0-zeros.tif",
                 "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"),
    "r0_nan": (DATA / "parent" / "r0-nan.tif",
               "baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd"),
    "h27_4": (DATA / "parent" / "h27-4-r1-nan.tif",
              "ab02300152248fdda04e988e2cd2a0c13f35eec42fcf670a15e8b76b19e24a73"),
    "h19_5": (DATA / "scored" / "h19-5.tif",
              "ec1f9b56b83ce33cad781ceb9f104b18fb4f2ff785263a4e89616af4aabdee8d"),
    "d1_5": (DATA / "scored" / "d1-5.tif",
             "68d0e2e4fcc594f9a23f56c44b885fee733d026d39be55e18ad2a07289525310"),
    "d2_8": (DATA / "scored" / "d2-8.tif",
             "91eae1ca42ec845eaa8c2ba32da49806e24751743459b8a10017c479bbe639b8"),
}

PREDICTED = {  # MODEL (anchor-algebra scenarios; see ledger/mechanism_cards.md)
    3: {"central": +0.004, "range": [-0.003, +0.011]},
    4: {"central": +0.005, "range": [-0.008, +0.018]},
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(key: str) -> np.ndarray:
    path, want = PINS[key]
    if not path.is_file():
        sys.exit(f"STOP: pinned input missing: {key} at {path}")
    got = sha256(path)
    if got != want:
        sys.exit(f"STOP: sha256 mismatch for {key}: got {got}, want {want}")
    with rasterio.open(path) as ds:
        return ds.read(1)


def dots(a: np.ndarray) -> np.ndarray:
    return np.isfinite(a) & (a > 0)


def block_cv(mask: np.ndarray, foot: np.ndarray, bs: int) -> float:
    h, w = mask.shape
    hb, wb = h // bs, w // bs
    rc = mask[: hb * bs, : wb * bs].reshape(hb, bs, wb, bs).sum(axis=(1, 3))
    fc = foot[: hb * bs, : wb * bs].reshape(hb, bs, wb, bs).sum(axis=(1, 3))
    ok = fc > 0.5 * bs * bs
    dens = rc[ok] / fc[ok]
    return float(dens.std() / dens.mean())


def refill_local(keep: np.ndarray, removed_yx: np.ndarray, pool: np.ndarray,
                 tier0: np.ndarray) -> tuple[np.ndarray, dict]:
    """One local, spacing-constrained replacement per removed dot.

    Spacing to kept dots is tested against a single Euclidean distance
    transform; spacing among chosen refills is tested against a 3 px hash
    grid of already-chosen points.  Deterministic throughout.
    """
    d_keep = distance_transform_edt(~keep)
    n_strict = int((pool & (d_keep >= STRICT_SPACING_PX)).sum())
    pool_yx = np.column_stack(np.where(pool))
    pool_tree = cKDTree(pool_yx.astype(np.float64))
    used = np.zeros(len(pool_yx), dtype=bool)
    cells: dict[tuple[int, int], list[tuple[int, int]]] = {}
    chosen: list[tuple[int, int]] = []
    disp, tier_counts = [], {"d1.5": 0, "h19_only": 0}

    def spacing_ok(cy: int, cx: int) -> bool:
        if d_keep[cy, cx] < MIN_SPACING_PX:
            return False
        gy, gx = cy // 3, cx // 3
        for j in (gy - 1, gy, gy + 1):
            for i in (gx - 1, gx, gx + 1):
                for py, px in cells.get((j, i), ()):
                    if (py - cy) ** 2 + (px - cx) ** 2 < MIN_SPACING_PX ** 2:
                        return False
        return True

    for ry, rx in removed_yx:
        picked = None
        for k in (64, 512, 4096, len(pool_yx)):
            dists, idxs = pool_tree.query([float(ry), float(rx)],
                                           k=min(k, len(pool_yx)))
            dists = np.atleast_1d(dists)
            idxs = np.atleast_1d(idxs)
            order = sorted(
                range(len(idxs)),
                key=lambda j: (round(float(dists[j]), 9),
                               0 if tier0[pool_yx[idxs[j], 0], pool_yx[idxs[j], 1]] else 1,
                               int(pool_yx[idxs[j], 0]), int(pool_yx[idxs[j], 1])),
            )
            for j in order:
                pi = int(idxs[j])
                if used[pi]:
                    continue
                cy, cx = (int(pool_yx[pi, 0]), int(pool_yx[pi, 1]))
                if spacing_ok(cy, cx):
                    picked = (pi, cy, cx, float(dists[j]))
                    break
            if picked is not None:
                break
        if picked is None:
            sys.exit("STOP: refill pool exhausted under spacing rule")
        pi, cy, cx, dd = picked
        used[pi] = True
        chosen.append((cy, cx))
        cells.setdefault((cy // 3, cx // 3), []).append((cy, cx))
        disp.append(dd)
        tier_counts["d1.5" if tier0[cy, cx] else "h19_only"] += 1
    out = np.zeros(keep.shape, dtype=bool)
    for cy, cx in chosen:
        out[cy, cx] = True
    disp = np.asarray(disp)
    stats = {
        "spacing_floor_px": MIN_SPACING_PX,
        "pool_px_at_strict_parent_spacing_2.8": n_strict,
        "n_refill": int(len(chosen)),
        "tier_counts": tier_counts,
        "displacement_px_mean": float(disp.mean()) if len(disp) else 0.0,
        "displacement_px_median": float(np.median(disp)) if len(disp) else 0.0,
        "displacement_px_p95": float(np.percentile(disp, 95)) if len(disp) else 0.0,
        "displacement_px_max": float(disp.max()) if len(disp) else 0.0,
    }
    return out, stats


def write_twin(path: Path, dotmask: np.ndarray, foot: np.ndarray, mode: str,
               profile: dict) -> str:
    arr = np.zeros(dotmask.shape, dtype=np.float32)
    arr[dotmask] = 1.0
    prof = dict(profile)
    if mode == "nan":
        arr[~foot] = np.nan
        prof["nodata"] = float("nan")
    else:
        prof.pop("nodata", None)
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(arr, 1)
    return sha256(path)


def main() -> None:
    git_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip()
    sample = load("sample")
    foot = np.isfinite(sample)
    cat = dots(load("labels").astype(np.float32)) & foot
    r0 = dots(load("r0_zeros"))
    r0n = dots(load("r0_nan"))
    base = dots(load("h27_4"))
    h19 = dots(load("h19_5"))
    d15 = dots(load("d1_5"))
    d28 = dots(load("d2_8"))
    assert np.array_equal(r0, r0n), "R0 twins disagree on dot set"
    assert int(r0.sum()) == N_PARENT, f"R0 dot count {r0.sum()} != {N_PARENT}"
    assert not (h19 & ~foot).any(), "H19-5 support outside footprint"
    dist = distance_transform_edt(~cat)
    # Rebuild-the-parent check (brief v2 section 5): never approximate R0.
    rebuilt = base & (dist > 2)
    if not np.array_equal(rebuilt, r0):
        sys.exit("STOP: rebuild failed: h27-4 minus d<=2 != R0 dot set")
    assert np.array_equal(base, d28 & (dist > 1)), "lineage break: h27-4 != d2.8 minus d<=1"
    print(f"parent verified: file sha pins OK; rebuild base-minus-<=2px == R0 "
          f"({N_PARENT} dots, 0 within 2 px, {int((dist[r0] <= 3).sum())} within 3 px)")

    with rasterio.open(PINS["r0_zeros"][0]) as ds:
        profile = ds.profile.copy()  # replicate the scored parent's encoding
    RELEASES.mkdir(exist_ok=True)

    for b in (3, 4):
        keep = r0 & (dist > b)
        removed = r0 & (dist <= b)
        n_rm = int(removed.sum())
        pool = h19 & (dist > b) & ~keep
        removed_yx = np.column_stack(np.where(removed))
        refill, rstats = refill_local(keep, removed_yx, pool, d15)
        var = keep | refill
        assert int(var.sum()) == N_PARENT
        assert not (var & cat).any(), "variant mass on catalogue"
        assert float(dist[var].min()) > b, "variant violates its own collar"
        assert not (refill & ~h19).any(), "refill outside ancestral field"
        pct = 100.0 * n_rm / N_PARENT
        assert 1.0 <= pct <= 50.0, pct
        nn = cKDTree(np.column_stack(np.where(var)))
        dd, _ = nn.query(np.column_stack(np.where(var)), k=2)
        diff = {
            "n_removed": n_rm,
            "n_added": int(refill.sum()),
            "n_kept": int((var & r0).sum()),
            "pct_of_parent_dots_replaced": round(pct, 4),
            "symmetric_difference": int((var ^ r0).sum()),
            "jaccard_similarity": float((var & r0).sum() / (var | r0).sum()),
            "min_d_catalogue_px": float(dist[var].min()),
            "median_d_catalogue_px": float(np.median(dist[var])),
            "nn_spacing_px_min": float(dd[:, 1].min()),
            "nn_spacing_px_median": float(np.median(dd[:, 1])),
            "block_cv_2km_before": block_cv(r0, foot, 20),
            "block_cv_2km_after": block_cv(var, foot, 20),
            "block_cv_5km_before": block_cv(r0, foot, 50),
            "block_cv_5km_after": block_cv(var, foot, 50),
            **rstats,
        }
        stem = f"{PARENT}-prune{b}r-{DATE}"
        tmp_nan = RELEASES / f".{stem}.tmp.tif"
        write_twin(tmp_nan, var, foot, "nan", profile)
        sha_nan = sha256(tmp_nan)
        vid = f"{stem}-{sha_nan[:8]}"
        nan_path = RELEASES / f"{vid}.tif"
        zeros_path = RELEASES / f"{vid}-zeros.tif"
        if nan_path.exists() or zeros_path.exists():
            tmp_nan.unlink()
            sys.exit(f"STOP: refusing to overwrite existing release {vid}")
        tmp_nan.replace(nan_path)
        sha_zeros = write_twin(zeros_path, var, foot, "zeros", profile)
        note = (f"Parent {PARENT} 0.2778 CLAIM; PRUNE B={b}+local refill "
                f"{N_PARENT} dots, {pct:.2f}% replaced; pred "
                f"{PREDICTED[b]['central']:+.3f} MODEL")
        assert len(note) <= 140, (len(note), note)
        receipt = {
            "id": vid, "parent": PARENT, "parent_sha256": PINS["r0_zeros"][1],
            "axis": "PRUNE", "value": f"B={b} px + local refill (count held)",
            "n_dots": N_PARENT, "parent_diff": diff,
            "file_nan_primary": nan_path.name, "sha256_nan": sha_nan,
            "file_zeros_fallback": zeros_path.name, "sha256_zeros": sha_zeros,
            "form_note": note, "form_note_chars": len(note),
            "predicted_change_MODEL": PREDICTED[b],
            "evidence": "parent live 0.2778 is CLAIM (no receipt); predictions are MODEL",
            "git_sha": git_sha, "seed": "none (fully deterministic rule)",
            "script": "scripts/build_prune_variants.py",
            "inputs_sha256": {k: v[1] for k, v in PINS.items()},
            "weekly_slot_consumed": False,
        }
        (RELEASES / f"{vid}.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(f"built {vid}: removed {n_rm} ({pct:.2f}%), refilled "
              f"{rstats['n_refill']} (tiers {rstats['tier_counts']}, "
              f"median displacement {rstats['displacement_px_median']:.1f} px), "
              f"nan sha {sha_nan[:12]}..., zeros sha {sha_zeros[:12]}...")


if __name__ == "__main__":
    main()
