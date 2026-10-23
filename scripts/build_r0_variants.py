#!/usr/bin/env python3
"""Deterministic rebuild of Parent R0 (h33-h33-2-b2) and single-axis variants (Brief v2).

Steps:
1. Verify all 23 SHA-256 hashes in registry/data_manifest.json.
2. Rebuild Parent R0 (h33-h33-2-b2 from GEMSDOE32, 37,654 unit-mass dots, d_cat > 2.0 px)
   from scored_h19_5 via GEMSDOE24 dot_thin(r_min=2.8) -> d2_8 (44,090 dots) -> prune d_cat <= 2.0 px,
   and verify exact GeoTIFF sha256 against evidence/h33-original-audit.json.
3. Build ledger/raw_paste.txt and ledger/submissions.csv from registry/live_scores.csv
   (collapsing repeat submissions onto canonical entries).
4. Rebuild Parent R0's dot ranking from the recorded GEMSDOE32 recipe (corroboration count +
   H33-A..D multi-physics lineament consensus + 1m LiDAR scarp composite + exact 25-offset
   top-2 kernel marginal DTI gain).
5. Build 3 single-axis variants on AXIS=MASS (or --axis CLI argument), emit releases/<id>.tif
   (NaN outside footprint) and releases/<id>-zeros.tif (0.0 outside footprint), re-read from
   disk, verify all MUST-pass gates, compute REPORT-ONLY diagnostics (catalogue hide-and-recover
   PROXY with n withheld positives and 95% CI, single-feature leakage canary, SGMC off-catalogue
   control), and append BUILT rows to ledger/submissions.csv.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
from collections import deque
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt, label as ndi_label

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT)]

from gems57 import evaluate_holdout, holdout as gems57_holdout  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from research.upstream.src.gems32.h33 import (  # noqa: E402
    H33_BUILDERS,
    lidar_scarp_composite,
    rank_surface,
)

DATE_TAG = "20261023"
PARENT_ID = "h33-h33-2-b2"
PARENT_SCORE_CLAIM = 0.2778
EXPECTED_R0_DOTS = 37654
EXPECTED_D28_DOTS = 44090
EXPECTED_R0_DIGEST8 = "e5eb6e7e"
EXPECTED_R0_ZEROS_SHA256 = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
EXPECTED_R0_NAN_SHA256 = "baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd"

BAND_NAMES = [
    "01_mag_anom",
    "02_rtp",
    "03_tmi_hg",
    "04_geod_2ndinv",
    "05_iso_grav_anom_slope",
    "06_tc",
    "07_geod_shearrate",
    "08_geod_dilaterate",
    "09_tmi_vg",
    "10_deq_n100a15",
    "11_iso_grav_anom_vg",
    "12_det_elev",
    "13_iso_grav_anom",
    "14_tmi",
    "15_depth_to_base_surf",
    "16_ieq_n100a15",
    "17_cond_surf",
    "18_iso_grav_anom_hg",
    "19_det_elev_slope",
]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def verify_manifest(data_dir: Path, manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text())
    verified = {}
    for spec in manifest["files"]:
        key = spec["id"]
        relpath = spec["dest"]
        p = data_dir / relpath
        if not p.exists():
            raise FileNotFoundError(f"Missing manifest file {key}: {p}")
        actual = file_sha256(p)
        expected = spec["sha256"]
        if actual != expected:
            raise RuntimeError(
                f"SHA-256 mismatch for {key} ({p}): expected {expected}, got {actual}"
            )
        verified[key] = {"dest": relpath, "sha256": actual, "bytes": p.stat().st_size}
    return verified


def ensure_unpacked_bands(data_dir: Path) -> Path:
    """Unpack the 19 training bands to per-band .npy files, cleaning the nodata sentinel.

    IR-DEC-07 (found 2026-10-23 in the PRUNE session): ``training_features.tif`` stores
    nodata as the *finite* float32 sentinel -3.4028235e38 (~3,060 px per band inside the
    footprint).  Writing the raw reads through (the previous behaviour) poisons every
    downstream consumer that masks with ``np.isfinite`` only: the upstream
    ``gems32.h33._fill`` keeps the sentinel as data, its Gaussian smears it, and
    ``build_h33a``'s float32 ``np.mean``/``np.std`` overflows to inf/NaN, silently
    zeroing the whole H33-A surface (holdout AUC exactly 0.5000) and turning
    ``rank_surface`` of that constant surface into a row-major ramp inside ``h33_union``.
    With raw bands the committed AXIS=MASS masks are NOT reproducible (720 of 3,765
    boundary dots differ); with sentinel->NaN cleaning at unpack they reproduce to
    within <=12 boundary dots per arm (float-path jitter) and the recorded canary AUCs
    match (h33_union 0.5813, q_posterior 0.6039, seed 20).  The MASS-session run that
    produced the committed masks therefore consumed cleaned bands; this function now
    always produces them, and rewrites any pre-existing sentinel-bearing band files.
    """
    bands_dir = data_dir / "bands"
    bands_dir.mkdir(parents=True, exist_ok=True)

    def _clean(a: np.ndarray) -> np.ndarray:
        return np.where(a <= -1e30, np.nan, a).astype(np.float32)

    def _needs_write(out: Path) -> bool:
        if not out.exists():
            return True
        return bool((np.load(out) <= -1e30).any())

    if all(not _needs_write(bands_dir / f"{name}.npy") for name in BAND_NAMES):
        return bands_dir
    with rasterio.open(data_dir / "training_features.tif") as src:
        for idx, name in enumerate(BAND_NAMES, start=1):
            out = bands_dir / f"{name}.npy"
            if _needs_write(out):
                np.save(out, _clean(src.read(idx).astype(np.float32)))
    return bands_dir


def dot_thin(ridge_mask: np.ndarray, r_min: float) -> np.ndarray:
    """Exact BFS component traversal with Euclidean exclusion disk r_min (GEMSDOE24/src/gems/thinning.py)."""
    H, W = ridge_mask.shape
    rm = ridge_mask.astype(bool)
    labels, n_comp = ndi_label(rm, structure=np.ones((3, 3), dtype=np.int8))
    out = np.zeros((H, W), dtype=bool)
    blocked = np.zeros((H, W), dtype=bool)

    r_int = int(np.floor(r_min))
    dys, dxs = np.mgrid[-r_int : r_int + 1, -r_int : r_int + 1]
    disk = (dys * dys + dxs * dxs) <= (r_min * r_min + 1e-9)
    disk_dy = dys[disk]
    disk_dx = dxs[disk]

    nbr_offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    visited = np.zeros((H, W), dtype=bool)
    ys, xs = np.nonzero(rm)
    order = np.lexsort((xs, ys))
    ys = ys[order]
    xs = xs[order]

    for y0, x0 in zip(ys, xs):
        if visited[y0, x0]:
            continue
        cid = labels[y0, x0]
        q = deque([(int(y0), int(x0))])
        visited[y0, x0] = True
        while q:
            r, c = q.popleft()
            if not blocked[r, c]:
                out[r, c] = True
                ry = r + disk_dy
                rx = c + disk_dx
                valid = (ry >= 0) & (ry < H) & (rx >= 0) & (rx < W)
                blocked[ry[valid], rx[valid]] = True
            for dr, dc in nbr_offsets:
                nr, nc = r + dr, c + dc
                if 0 <= nr < H and 0 <= nc < W and not visited[nr, nc] and labels[nr, nc] == cid:
                    visited[nr, nc] = True
                    q.append((nr, nc))
    return out


def write_submission_pair(
    mask: np.ndarray,
    template_path: Path,
    cat_mask: np.ndarray,
    nan_path: Path,
    zeros_path: Path,
) -> dict:
    """Write both <id>.tif (NaN outside footprint) and <id>-zeros.tif (0.0 outside footprint)."""
    with rasterio.open(template_path) as ref:
        ref_arr = ref.read(1)
        foot = np.isfinite(ref_arr)
        base_profile = ref.profile.copy()

    clean = np.asarray(mask, dtype=bool) & foot & (~cat_mask)
    if int((clean & cat_mask).sum()) != 0:
        raise RuntimeError("Catalogue overlap detected before write")

    digest8 = hashlib.sha256(np.packbits(clean)).hexdigest()[:8]

    base_profile.update(
        driver="GTiff",
        dtype="float32",
        count=1,
        compress="deflate",
        predictor=3,
        zlevel=9,
        tiled=True,
        blockxsize=256,
        blockysize=256,
    )

    nan_path.parent.mkdir(parents=True, exist_ok=True)
    zeros_path.parent.mkdir(parents=True, exist_ok=True)

    arr_nan = np.full(clean.shape, np.nan, dtype=np.float32)
    arr_nan[foot] = clean[foot].astype(np.float32)
    prof_nan = base_profile.copy()
    prof_nan["nodata"] = np.nan
    with rasterio.open(nan_path, "w", **prof_nan) as dst:
        dst.write(arr_nan, 1)

    arr_zeros = np.zeros(clean.shape, dtype=np.float32)
    arr_zeros[foot] = clean[foot].astype(np.float32)
    prof_zeros = base_profile.copy()
    prof_zeros["nodata"] = None
    with rasterio.open(zeros_path, "w", **prof_zeros) as dst:
        dst.write(arr_zeros, 1)

    return {
        "digest8": digest8,
        "nan_path": str(nan_path.relative_to(ROOT)),
        "nan_sha256": file_sha256(nan_path),
        "nan_bytes": nan_path.stat().st_size,
        "zeros_path": str(zeros_path.relative_to(ROOT)),
        "zeros_sha256": file_sha256(zeros_path),
        "zeros_bytes": zeros_path.stat().st_size,
    }


def verify_written_pair_from_disk(
    nan_path: Path,
    zeros_path: Path,
    template_path: Path,
    cat_mask: np.ndarray,
    expected_dots: int,
) -> dict:
    """Re-read both GeoTIFFs from disk and run all MUST-pass format and scientific checks."""
    with rasterio.open(template_path) as ref:
        ref_crs = ref.crs
        ref_shape = (ref.height, ref.width)
        ref_transform = ref.transform
        foot = np.isfinite(ref.read(1))

    out = {}
    for label_key, path, expect_outside_nan in [
        ("nan_tif", nan_path, True),
        ("zeros_tif", zeros_path, False),
    ]:
        with rasterio.open(path) as src:
            arr = src.read(1)
            crs_ok = src.crs == ref_crs
            shape_ok = (src.height, src.width) == ref_shape
            transform_ok = src.transform == ref_transform
            band_ok = src.count == 1
            dtype_ok = src.dtypes[0] == "float32"

        in_foot = arr[foot]
        out_foot = arr[~foot]
        no_nan_in_foot = bool(np.isfinite(in_foot).all())
        in_unit_range = bool(((in_foot >= 0.0) & (in_foot <= 1.0)).all())
        if expect_outside_nan:
            outside_ok = bool(np.isnan(out_foot).all())
        else:
            outside_ok = bool(np.isfinite(out_foot).all() and np.all(out_foot == 0.0))

        dots = int((arr == 1.0).sum())
        cat_mass = float(np.nan_to_num(arr[cat_mask], nan=0.0).sum())
        dots_ok = dots == expected_dots
        cat_ok = cat_mass == 0.0

        passed = all(
            [
                crs_ok,
                shape_ok,
                transform_ok,
                band_ok,
                dtype_ok,
                no_nan_in_foot,
                in_unit_range,
                outside_ok,
                dots_ok,
                cat_ok,
            ]
        )
        if not passed:
            raise RuntimeError(
                f"Gate check failed on {path}: crs={crs_ok}, shape={shape_ok}, "
                f"transform={transform_ok}, band={band_ok}, dtype={dtype_ok}, "
                f"no_nan_in_foot={no_nan_in_foot}, in_unit_range={in_unit_range}, "
                f"outside_ok={outside_ok}, dots={dots} vs {expected_dots}, cat_mass={cat_mass}"
            )
        out[label_key] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": file_sha256(path),
            "crs": str(ref_crs),
            "shape": list(ref_shape),
            "dtype": "float32",
            "count": 1,
            "no_nan_in_footprint": no_nan_in_foot,
            "values_in_0_1": in_unit_range,
            "outside_footprint_encoding_ok": outside_ok,
            "n_dots": dots,
            "catalogue_mass": cat_mass,
            "gate_passed": passed,
        }
    return out


def build_historical_ledger() -> tuple[list[dict], int]:
    """Build ledger/raw_paste.txt and collapse repeat rows into ledger/submissions.csv."""
    import re

    ledger_dir = ROOT / "ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)

    live_csv = ROOT / "registry" / "live_scores.csv"
    raw_paste = ledger_dir / "raw_paste.txt"
    raw_paste.write_text(live_csv.read_text())

    reg_idx = json.loads((ROOT / "registry" / "registry_index.json").read_text())["rasters"]
    by_sha8: dict[str, list[dict]] = {}
    for e in reg_idx:
        for h in e.get("sha8_list", []):
            by_sha8.setdefault(h, []).append(e)

    dots_by_sha = {}
    e3_rows_path = ROOT / "evidence" / "e3_gate_dots_rows.json"
    if e3_rows_path.exists():
        for r in json.loads(e3_rows_path.read_text()):
            dots_by_sha[r["sha256"]] = r["their_dots"]

    raw_rows = list(csv.DictReader(live_csv.open()))
    collapsed: list[dict] = []
    seen_keys: dict[tuple, int] = {}

    for r in raw_rows:
        fname = r["submission_name"]
        stem = fname[:-4] if fname.endswith(".tif") else fname
        tokens = re.findall(r"(?<![0-9a-f])([0-9a-f]{8,16})(?![0-9a-f])", fname.lower())
        cands = []
        for t in tokens:
            cands.extend(by_sha8.get(t[:8], []))
        if not cands:
            for e in reg_idx:
                if any(stem.lower() in p[2].lower() for p in e.get("paths", [])):
                    cands.append(e)

        sha256_val = ""
        n_dots_val = ""
        if cands:
            cands.sort(
                key=lambda e: (
                    0 if any("-zeros" in p[2] for p in e.get("paths", [])) else 1,
                    e.get("sha256", ""),
                )
            )
            c0 = cands[0]
            sha256_val = c0.get("sha256", "")
            if sha256_val in dots_by_sha:
                n_dots_val = str(dots_by_sha[sha256_val])
            else:
                for c in cands:
                    if c.get("sha256") in dots_by_sha:
                        n_dots_val = str(dots_by_sha[c["sha256"]])
                        break

        score = f"{float(r['public_score']):.4f}"
        dedupe_key = (sha256_val if sha256_val else fname, score)
        if dedupe_key in seen_keys:
            row_pos = seen_keys[dedupe_key]
            collapsed[row_pos]["repeat_count"] = str(int(collapsed[row_pos]["repeat_count"]) + 1)
            continue

        parent = ""
        axis = "HISTORICAL"
        value = ""
        pct_changed = ""
        if "h33-h33-2-b2" in stem:
            stem = "h33-h33-2-b2"
            parent = "h27-4-cat-collar-r1-on-d28"
            axis = "PRUNE"
            value = "dcat>2px"
            pct_changed = "6.33"
            n_dots_val = "37654"
            sha256_val = EXPECTED_R0_ZEROS_SHA256
        elif "h27-4-cat-collar-r1-on-d28" in stem:
            parent = "gems24-h25-1-dotted-h19-5-d2-8"
            axis = "PRUNE"
            value = "dcat>1px"
            pct_changed = "8.83"
            n_dots_val = "40199"
        elif "gems24-h25-1-dotted-h19-5-d2-8" in stem:
            parent = "gems19-h19-5-powerlaw-budget-multiline-corroborated"
            axis = "SPACING"
            value = "r_min=2.8px"
            pct_changed = "63.60"
            n_dots_val = "44090"

        date_m = re.search(r"(2026\d{4})", fname)
        date_val = (
            f"{date_m.group(1)[:4]}-{date_m.group(1)[4:6]}-{date_m.group(1)[6:8]}"
            if date_m
            else ""
        )
        seen_keys[dedupe_key] = len(collapsed)
        collapsed.append(
            {
                "id": stem,
                "parent": parent,
                "axis": axis,
                "value": value,
                "n_dots": n_dots_val,
                "pct_changed": pct_changed,
                "sha256": sha256_val,
                "status": "CLAIM",
                "predicted_change": "",
                "receipt_score": score,
                "date": date_val,
                "repeat_count": "1",
                "evidence_label": "CLAIM",
                "filename": fname,
            }
        )

    return collapsed, len(raw_rows)


def write_ledger_csv(rows: list[dict]) -> Path:
    out_path = ROOT / "ledger" / "submissions.csv"
    fieldnames = [
        "id",
        "parent",
        "axis",
        "value",
        "n_dots",
        "pct_changed",
        "sha256",
        "status",
        "predicted_change",
        "receipt_score",
        "date",
        "repeat_count",
        "evidence_label",
        "filename",
    ]
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return out_path


def compute_exact_marginal_gains(
    r0_mask: np.ndarray,
    q: np.ndarray,
    s0: float = PARENT_SCORE_CLAIM,
    alpha: float = 0.2,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[tuple[int, int, float]]]:
    """Compute exact 25-offset top-2 kernel coverage K1, K2 and single-dot marginal DTI gain."""
    H, W = r0_mask.shape
    offs = [
        (dy, dx, float(1.0 - np.hypot(dy, dx) / 3.0))
        for dy in range(-2, 3)
        for dx in range(-2, 3)
        if np.hypot(dy, dx) < 3.0
    ]
    pad = 3
    r0_p = np.pad(r0_mask, pad)
    q_p = np.pad(q, pad)
    K1 = np.zeros((H, W), dtype=np.float32)
    K2 = np.zeros((H, W), dtype=np.float32)
    for dy, dx, kw in offs:
        hit = r0_p[pad - dy : pad - dy + H, pad - dx : pad - dx + W]
        better1 = hit & (kw > K1)
        better2 = hit & (~better1) & (kw > K2)
        K2 = np.where(better1, K1, np.where(better2, kw, K2))
        K1 = np.where(better1, kw, K1)

    K1_p = np.pad(K1, pad)
    K2_p = np.pad(K2, pad)
    dT_r0 = np.zeros((H, W), dtype=np.float32)
    mq_r0 = np.zeros((H, W), dtype=np.float32)
    for dy, dx, kw in offs:
        k1_y = K1_p[pad + dy : pad + dy + H, pad + dx : pad + dx + W]
        k2_y = K2_p[pad + dy : pad + dy + H, pad + dx : pad + dx + W]
        qy = q_p[pad + dy : pad + dy + H, pad + dx : pad + dx + W]
        is_max = np.abs(kw - k1_y) < 1e-6
        dT_r0 += np.where(r0_mask & is_max, qy * (k1_y - k2_y), 0.0)
        mq_r0 = np.maximum(mq_r0, qy * kw)

    gain_r0 = (1.0 - alpha * s0) * dT_r0 - alpha * s0 * (1.0 - mq_r0)
    return gain_r0, K1, K2, offs


def greedy_add_dots(
    r0_mask: np.ndarray,
    cand_pool: np.ndarray,
    q: np.ndarray,
    K1_init: np.ndarray,
    offs: list[tuple[int, int, float]],
    n_add: int,
    r_min: float = 2.8,
    s0: float = PARENT_SCORE_CLAIM,
    alpha: float = 0.2,
) -> tuple[np.ndarray, list[float]]:
    """Select n_add dots from cand_pool with Euclidean spacing >= r_min maximizing exact marginal DTI gain."""
    H, W = r0_mask.shape
    pad = 3
    K1_p = np.pad(K1_init.copy(), pad)
    q_p = np.pad(q, pad)

    dT_add = np.zeros((H, W), dtype=np.float32)
    mq_add = np.zeros((H, W), dtype=np.float32)
    for dy, dx, kw in offs:
        k1_y = K1_p[pad + dy : pad + dy + H, pad + dx : pad + dx + W]
        qy = q_p[pad + dy : pad + dy + H, pad + dx : pad + dx + W]
        dT_add += qy * np.maximum(0.0, kw - k1_y)
        mq_add = np.maximum(mq_add, qy * kw)

    gain_map = (1.0 - alpha * s0) * dT_add - alpha * s0 * (1.0 - mq_add)

    cy, cx = np.nonzero(cand_pool)
    scores = gain_map[cy, cx]
    order = np.argsort(-scores, kind="mergesort")
    cy = cy[order]
    cx = cx[order]
    scores = scores[order]

    r_int = int(np.floor(r_min))
    dys, dxs = np.mgrid[-r_int : r_int + 1, -r_int : r_int + 1]
    disk = (dys * dys + dxs * dxs) <= (r_min * r_min + 1e-9)
    disk_dy = dys[disk]
    disk_dx = dxs[disk]

    blocked = np.zeros((H, W), dtype=bool)
    ry0, rx0 = np.nonzero(r0_mask)
    for dy_b, dx_b in zip(disk_dy, disk_dx):
        yy = np.clip(ry0 + dy_b, 0, H - 1)
        xx = np.clip(rx0 + dx_b, 0, W - 1)
        blocked[yy, xx] = True

    added = np.zeros((H, W), dtype=bool)
    added_gains: list[float] = []
    for r, c in zip(cy, cx):
        if len(added_gains) >= n_add:
            break
        r_i, c_i = int(r), int(c)
        if blocked[r_i, c_i]:
            continue
        # Recompute exact marginal gain against updated K1_p
        pr, pc = r_i + pad, c_i + pad
        dt_val = 0.0
        mq_val = 0.0
        for dy, dx, kw in offs:
            qy_val = float(q_p[pr + dy, pc + dx])
            k1_val = float(K1_p[pr + dy, pc + dx])
            if kw > k1_val:
                dt_val += qy_val * (kw - k1_val)
            if qy_val * kw > mq_val:
                mq_val = qy_val * kw
        g_val = (1.0 - alpha * s0) * dt_val - alpha * s0 * (1.0 - mq_val)
        added[r_i, c_i] = True
        added_gains.append(float(g_val))
        for dy, dx, kw in offs:
            if kw > K1_p[pr + dy, pc + dx]:
                K1_p[pr + dy, pc + dx] = kw
        ry = r_i + disk_dy
        rx = c_i + disk_dx
        valid = (ry >= 0) & (ry < H) & (rx >= 0) & (rx < W)
        blocked[ry[valid], rx[valid]] = True

    if len(added_gains) != n_add:
        raise RuntimeError(f"Requested {n_add} added dots, only found {len(added_gains)}")
    return r0_mask | added, added_gains


def rank_auc(values: np.ndarray, pos_mask: np.ndarray, neg_mask: np.ndarray) -> float:
    p = values[pos_mask]
    n = values[neg_mask]
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
    n1 = float(p.size)
    n0 = float(n.size)
    return float((ranks[lab == 1].sum() - n1 * (n1 + 1.0) / 2.0) / (n1 * n0))


def run_report_only_diagnostics(
    data_dir: Path,
    bands_dir: Path,
    foot: np.ndarray,
    cat: np.ndarray,
    dcat: np.ndarray,
    d28: np.ndarray,
    r0: np.ndarray,
    gain_r0: np.ndarray,
    cand_pool_base: np.ndarray,
    q: np.ndarray,
    K1: np.ndarray,
    offs: list[tuple[int, int, float]],
    surfaces: dict[str, np.ndarray],
    h33_union: np.ndarray,
    lidar: np.ndarray,
    corrob_count: np.ndarray,
    variants: dict[str, np.ndarray],
) -> dict:
    """Compute REPORT-ONLY diagnostics: catalogue hide-and-recover PROXY, leakage canary, SGMC control."""
    grid = load_grid(data_dir)
    folds_20, _ = gems57_holdout.buffered_component_draw(grid, seed=20)
    folds_21, _ = gems57_holdout.buffered_component_draw(grid, seed=21)
    all_folds = [(20, f) for f in folds_20] + [(21, f) for f in folds_21]

    # 1. Leakage canary across all 19 bands + H33 surfaces + composite ranking signals
    pos_20 = np.zeros(foot.shape, dtype=bool)
    neg_20 = np.zeros(foot.shape, dtype=bool)
    for f in folds_20:
        active = foot & f["region"] & (~f["masked_known"])
        pos_20 |= active & f["truth"]
        neg_20 |= active & (~f["truth"])

    pos_21 = np.zeros(foot.shape, dtype=bool)
    neg_21 = np.zeros(foot.shape, dtype=bool)
    for f in folds_21:
        active = foot & f["region"] & (~f["masked_known"])
        pos_21 |= active & f["truth"]
        neg_21 |= active & (~f["truth"])

    canary_features = []
    for bname in BAND_NAMES:
        arr = np.load(bands_dir / f"{bname}.npy")
        a20 = rank_auc(arr, pos_20, neg_20)
        a21 = rank_auc(arr, pos_21, neg_21)
        m = 0.5 * (a20 + a21)
        canary_features.append(
            {
                "feature": bname,
                "auc_seed20": round(a20, 4),
                "auc_seed21": round(a21, 4),
                "auc_mean": round(m, 4),
                "abs_strength": round(max(m, 1.0 - m), 4),
            }
        )

    extra_arrays = {
        "H33-A": surfaces["H33-A"],
        "H33-B": surfaces["H33-B"],
        "H33-C": surfaces["H33-C"],
        "H33-D": surfaces["H33-D"],
        "h33_union": h33_union,
        "lidar_scarp_composite": lidar,
        "corrob_count": corrob_count,
        "q_posterior": q,
    }
    for name, arr in extra_arrays.items():
        a20 = rank_auc(arr, pos_20, neg_20)
        a21 = rank_auc(arr, pos_21, neg_21)
        m = 0.5 * (a20 + a21)
        canary_features.append(
            {
                "feature": name,
                "auc_seed20": round(a20, 4),
                "auc_seed21": round(a21, 4),
                "auc_mean": round(m, 4),
                "abs_strength": round(max(m, 1.0 - m), 4),
            }
        )

    canary_features.sort(key=lambda x: x["abs_strength"], reverse=True)
    max_auc = max(f["abs_strength"] for f in canary_features)
    if max_auc > 0.90:
        raise RuntimeError(f"STOP: Leakage canary exceeded 0.90! max_auc={max_auc}")

    # 2. Catalogue hide-and-recover PROXY (fold-clean recipe and shipped mask, with n withheld positives & 95% CI)
    # In fold-clean mode, only the fold's VISIBLE catalogue is excluded (d_vis > 2.0 px),
    # while the MASS rank retention / addition fractions are applied identically.
    ry, rx = np.nonzero(r0)
    r0_gains = gain_r0[ry, rx]
    cut_drop10 = float(np.percentile(r0_gains, 10.0))
    cut_drop20 = float(np.percentile(r0_gains, 20.0))

    # Precompute fold-clean maps for seed 20 and seed 21 (since visible is shared per seed in buffered_component_draw)
    fold_clean_by_seed: dict[int, dict[str, np.ndarray]] = {}
    for seed_val, seed_folds in [(20, folds_20), (21, folds_21)]:
        vis = seed_folds[0]["visible"]
        dvis = distance_transform_edt(~vis)
        r0_vis = d28 & (dvis > 2.0)
        gain_vis, K1_vis, _, _ = compute_exact_marginal_gains(r0_vis, q)
        v_ry, v_rx = np.nonzero(r0_vis)
        v_gains = gain_vis[v_ry, v_rx]
        v_order = np.argsort(v_gains, kind="mergesort")
        n_drop10_v = int(round(0.10 * v_ry.size))
        n_drop20_v = int(round(0.20 * v_ry.size))
        drop10_vis = r0_vis.copy()
        drop10_vis[v_ry[v_order[:n_drop10_v]], v_rx[v_order[:n_drop10_v]]] = False
        drop20_vis = r0_vis.copy()
        drop20_vis[v_ry[v_order[:n_drop20_v]], v_rx[v_order[:n_drop20_v]]] = False
        cand_vis = cand_pool_base & (dvis >= 3.0) & (~r0_vis)
        add10_vis, _ = greedy_add_dots(
            r0_vis, cand_vis, q, K1_vis, offs, n_add=int(round(0.10 * EXPECTED_R0_DOTS))
        )
        fold_clean_by_seed[seed_val] = {
            "R0": r0_vis,
            "drop10pct": drop10_vis,
            "add10pct": add10_vis,
            "drop20pct": drop20_vis,
        }

    terms_fold_clean: dict[str, np.ndarray] = {}
    terms_shipped: dict[str, np.ndarray] = {}
    shipped_arms = {"R0": r0, **variants}

    for arm_name in shipped_arms:
        acc_clean = None
        acc_ship = None
        for seed_val, fold in all_folds:
            _, t_clean = evaluate_holdout.evaluate(
                fold_clean_by_seed[seed_val][arm_name].astype(np.float32), fold, foot
            )
            _, t_ship = evaluate_holdout.evaluate(
                shipped_arms[arm_name].astype(np.float32), fold, foot
            )
            acc_clean = t_clean if acc_clean is None else (acc_clean + t_clean)
            acc_ship = t_ship if acc_ship is None else (acc_ship + t_ship)
        terms_fold_clean[arm_name] = acc_clean
        terms_shipped[arm_name] = acc_ship

    summary_clean = evaluate_holdout.pooled_summary(
        terms_fold_clean, draws=1000, seed=520810, candidate="add10pct"
    )
    summary_ship = evaluate_holdout.pooled_summary(
        terms_shipped, draws=1000, seed=520810, candidate="add10pct"
    )

    # 3. SGMC off-catalogue control (derived_sgmc_faults_100m_u8.tif at d_cat > 3.0 px)
    with rasterio.open(data_dir / "external" / "derived_sgmc_faults_100m_u8.tif") as ds:
        sgm = (ds.read(1) > 0) & foot
    near_cat = binary_dilation(cat, iterations=3)
    sgmc_truth = sgm & (~cat) & (~near_cat) & foot
    sgmc_coords = np.nonzero(sgmc_truth)
    sgmc_n_truth = int(sgmc_coords[0].size)
    sgmc_dt = distance_transform_edt(~sgmc_truth)
    sgmc_k_dg = np.clip(1.0 - sgmc_dt / 3.0, 0.0, 1.0).astype(np.float32)
    g_lb = 12691.0

    sgmc_results = {}
    for arm_name, mask in shipped_arms.items():
        off_mask = mask & (~cat) & foot
        dp_off = distance_transform_edt(~off_mask)
        k_at_truth = np.clip(1.0 - dp_off[sgmc_coords] / 3.0, 0.0, 1.0)
        tp_sg = float(k_at_truth.sum())
        fn_sg = float(sgmc_n_truth) - tp_sg
        fp_sg = float((1.0 - sgmc_k_dg[off_mask]).sum())
        raw_dti = float(tp_sg / (tp_sg + 0.2 * fp_sg + 0.8 * fn_sg + 1e-6))
        cov_sg = float(tp_sg / sgmc_n_truth)
        tp_cal = cov_sg * g_lb
        fp_cal = max(0.0, float(off_mask.sum()) - tp_cal)
        cal_dti = float(tp_cal / (0.2 * (tp_cal + fp_cal) + 0.8 * g_lb + 1e-6))
        sgmc_results[arm_name] = {
            "evidence_label": "PROXY",
            "sgmc_off_catalogue_truth_pixels": sgmc_n_truth,
            "emitted_dots": int(off_mask.sum()),
            "sgmc_raw_dti": round(raw_dti, 6),
            "sgmc_coverage": round(cov_sg, 6),
            "sgmc_prevalence_calibrated_dti": round(cal_dti, 6),
        }

    return {
        "evidence_label": "PROXY",
        "note": "REPORT ONLY diagnostics (never gates per Brief Section 6).",
        "leakage_canary": {
            "gate": "single_feature_holdout_auc_canary",
            "threshold": 0.90,
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
            "withheld_positive_pixels": summary_clean["scores"]["R0"]["withheld_positive_pixels"],
            "spatial_clusters_20km": summary_clean["bootstrap"]["clusters"],
            "bootstrap_draws": summary_clean["bootstrap"]["draws"],
            "fold_clean_recipe_scores": summary_clean["scores"],
            "fold_clean_paired_differences_vs_add10pct": summary_clean["paired_differences"],
            "shipped_mask_scores": summary_ship["scores"],
        },
        "sgmc_off_catalogue_control": sgmc_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--axis",
        default="MASS",
        choices=["MASS", "CONCENTRATION", "SNAP", "PRUNE", "RELIEF", "SPACING", "TRACKB"],
        help="Single experimental axis to execute this session (default: MASS per SLOT_PLAN.md).",
    )
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "gems_data")
    parser.add_argument("--manifest", type=Path, default=ROOT / "registry" / "data_manifest.json")
    args = parser.parse_args()

    t0 = time.time()
    print("[1/6] Verifying all 23 SHA-256 hashes in registry/data_manifest.json ...")
    manifest_verified = verify_manifest(args.data_dir, args.manifest)
    bands_dir = ensure_unpacked_bands(args.data_dir)
    print(f"      Verified {len(manifest_verified)} manifest files and 19 unpacked bands.")

    print("[2/6] Rebuilding Parent R0 (h33-h33-2-b2) from scored_h19_5 and verifying SHA-256 ...")
    template_path = args.data_dir / "sample_submission.tif"
    with rasterio.open(template_path) as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(args.data_dir / "existing_faults.tif") as ds:
        cat = (ds.read(1) > 0) & foot
    dcat = distance_transform_edt(~cat)

    def read_scored(relname: str) -> np.ndarray:
        with rasterio.open(args.data_dir / "scored" / relname) as ds:
            return (ds.read(1) > 0) & foot

    h19_5 = read_scored("gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif")
    h19_4 = read_scored("gems19-h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan.tif")
    h16_1 = read_scored("gems16-h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan.tif")
    d15 = read_scored("gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif")
    d28_pinned = read_scored("gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif")
    tgc = read_scored("gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif")
    ens12 = read_scored("gemsdoe-ens12-adopted-7f00890a.tif")

    d28_rebuilt = dot_thin(h19_5, 2.8)
    if not np.array_equal(d28_rebuilt, d28_pinned):
        raise RuntimeError("Rebuilt d2_8 does not match pinned d2_8 raster")
    r0 = d28_rebuilt & (dcat > 2.0)
    if int(r0.sum()) != EXPECTED_R0_DOTS:
        raise RuntimeError(f"Expected {EXPECTED_R0_DOTS} dots in R0, got {int(r0.sum())}")

    r0_check_dir = args.data_dir / "rebuilt_r0"
    r0_pair = write_submission_pair(
        r0,
        template_path,
        cat,
        r0_check_dir / "h33-h33-2-b2-nan.tif",
        r0_check_dir / "h33-h33-2-b2-zeros.tif",
    )
    if (
        r0_pair["digest8"] != EXPECTED_R0_DIGEST8
        or r0_pair["zeros_sha256"] != EXPECTED_R0_ZEROS_SHA256
        or r0_pair["nan_sha256"] != EXPECTED_R0_NAN_SHA256
    ):
        raise RuntimeError(f"Parent R0 SHA-256 verification failed: {r0_pair}")
    print(
        f"      Parent R0 verified bit-for-bit: {EXPECTED_R0_DOTS} dots, "
        f"digest8={r0_pair['digest8']}, zeros_sha256={r0_pair['zeros_sha256'][:16]}..."
    )

    print("[3/6] Building ledger/raw_paste.txt and ledger/submissions.csv ...")
    ledger_rows, raw_count = build_historical_ledger()
    existing_shas = {r["sha256"] for r in ledger_rows if r["sha256"]}
    existing_pairs = {(r["parent"], r["axis"], r["value"]) for r in ledger_rows}
    print(f"      Collapsed {raw_count} raw rows into {len(ledger_rows)} canonical historical rows.")

    print("[4/6] Rebuilding Parent R0 ranking (GEMSDOE32 recipe + exact 25-offset marginal DTI gain) ...")
    surfaces = {hid: builder(bands_dir, args.data_dir, foot) for hid, builder in H33_BUILDERS.items()}
    h33_union = np.mean([rank_surface(v, foot) for v in surfaces.values()], axis=0).astype(np.float32)
    lidar = np.nan_to_num(lidar_scarp_composite(args.data_dir, foot), nan=0.0).astype(np.float32)

    corrob_count = (
        h19_5.astype(np.float32)
        + h19_4.astype(np.float32)
        + h16_1.astype(np.float32)
        + tgc.astype(np.float32)
        + d15.astype(np.float32)
        + ens12.astype(np.float32)
    )
    base_mult = (
        1.0
        + 0.45 * corrob_count
        + 0.70 * ens12.astype(np.float32)
        + 0.50 * d15.astype(np.float32)
        + 0.35 * lidar
    )
    ridge_union = (h19_5 | h19_4 | h16_1 | tgc) & foot
    raw_q = (
        (0.65 * ridge_union.astype(np.float32) + 0.35 * h33_union)
        * base_mult
        * (0.50 + 0.50 * h33_union)
    )
    q_scale = float(np.percentile(raw_q[ridge_union], 99.5))
    q = np.clip(raw_q / max(q_scale, 1e-6), 0.0, 1.0).astype(np.float32)
    q[~foot] = 0.0

    gain_r0, K1, K2, offs = compute_exact_marginal_gains(r0, q)
    ry, rx = np.nonzero(r0)
    r0_gains = gain_r0[ry, rx]
    r0_order_asc = np.argsort(r0_gains, kind="mergesort")

    # Candidate addition pool: corroborated ridge pixels thinned at r_min=2.8 px
    # Live emission filters by dcat >= 3.0 px; fold-clean holdout filters by dvis >= 3.0 px.
    cand_pool_base = dot_thin(ridge_union, 2.8)
    cand_pool = cand_pool_base & (~r0) & (dcat >= 3.0)

    if args.axis != "MASS":
        raise NotImplementedError(
            f"Session is configured for AXIS=MASS per SLOT_PLAN.md; got --axis={args.axis}"
        )

    print("[5/6] Building 3 single-axis variants on AXIS=MASS ...")
    n_delta_10 = int(round(0.10 * EXPECTED_R0_DOTS))  # 3,765 dots
    n_delta_20 = int(round(0.20 * EXPECTED_R0_DOTS))  # 7,531 dots

    # Variant 1: drop lowest-ranked 10% of R0 (-3,765 dots -> 33,889 dots)
    mask_drop10 = r0.copy()
    mask_drop10[ry[r0_order_asc[:n_delta_10]], rx[r0_order_asc[:n_delta_10]]] = False

    # Variant 2: add next-ranked 10% corroborated ridge dots (+3,765 dots -> 41,419 dots, d_cat >= 3.0 px)
    mask_add10, added_gains_10 = greedy_add_dots(
        r0, cand_pool, q, K1, offs, n_add=n_delta_10, r_min=2.8
    )

    # Variant 3: drop lowest-ranked 20% of R0 (-7,531 dots -> 30,123 dots)
    mask_drop20 = r0.copy()
    mask_drop20[ry[r0_order_asc[:n_delta_20]], rx[r0_order_asc[:n_delta_20]]] = False

    variant_specs = [
        {
            "key": "drop10pct",
            "axis": "MASS",
            "value": "-10pct",
            "slug_value": "-drop10pct",
            "mask": mask_drop10,
            "predicted_change": "+0.0020 to +0.0045 DTI (MODEL: prunes 3,765 lowest-marginal-gain dots where FP penalty outweighs marginal coverage)",
            "form_note": "h33-h33-2-b2; MASS -10% (drop 3765 lowest-rank dots -> 33889); pred +0.002 to +0.005 DTI",
            "mechanism_card": {
                "hypothesis": "Removing the lowest-ranked 10% (3,765 dots) of R0 increases live DTI because those tail dots sit on single-channel topographic/geophysical noise or already-covered fault segments where marginal truth credit dT < 0.0719 px-equiv (the break-even bar at s0 = 0.2778).",
                "mechanism": "Under DTI = T / (0.2*T + 0.2*(S - M) + 0.8*|G|), each unit-mass dot adds 0.2*(1 - m_q(x)) to the denominator and (1 - 0.2*s0)*dT(x) to the numerator. Dots ranked in the bottom decile of R0 have minimum multi-channel corroboration (corrob_count <= 1) and weak H33 multi-physics strike consensus (H33-A..D), contributing excess false-positive mass (S - M) without expanding the 300 m max-coverage envelope.",
                "non_fault_mimic": "Erosional pediment dissection scarps, alluvial-fan channel margins, and volcanic flow-lobe edges that trigger a single DEM/openness ridge channel (h19_5) without magnetic (RTP/TMI), gravity (isostatic HGM), MT conductivity, or 1 m LiDAR en-echelon scarplet corroboration.",
                "predicted_sign_and_size": "Positive: +0.0020 to +0.0045 DTI on public test (MODEL; fold-clean hide-and-recover PROXY delta reported separately).",
                "falsifier": "A live score < 0.2768 (drop >= 0.0010 below R0's 0.2778 CLAIM) falsifies the hypothesis that R0's bottom decile is net-FP-dominated and proves hidden test faults populate low-corroboration DEM ridges.",
            },
        },
        {
            "key": "add10pct",
            "axis": "MASS",
            "value": "+10pct",
            "slug_value": "-add10pct",
            "mask": mask_add10,
            "predicted_change": "-0.0030 to +0.0025 DTI (MODEL: adds 3,765 next-ranked corroborated ridge dots at r>=2.8px, d_cat>=3px; tests if G_test > 15k)",
            "form_note": "h33-h33-2-b2; MASS +10% (add 3765 top-rank dots at dcat>=3px -> 41419); pred -0.003 to +0.003",
            "mechanism_card": {
                "hypothesis": "Adding the next-ranked 10% (+3,765 dots -> 41,419 dots) from multi-channel corroborated ridge extensions (h19_4 | h16_1 | tgc_v2_d15 | h19_5) at r_min = 2.8 px and d_cat >= 3.0 px increases DTI if and only if off-catalogue fault prevalence in those secondary ridges exceeds the 7.2% break-even coverage bar.",
                "mechanism": "Selects 3,765 candidate dots outside R0's 300 m kernel shadow by lazy greedy maximization of exact marginal DTI gain weighted by H33-A..D multi-physics lineament consensus and 1 m LiDAR scarp step height, strictly >= 300 m from all existing_faults.tif pixels.",
                "non_fault_mimic": "Intrabasinal playette desiccation cracks, lithologic dike swarms in TMI, and range-parallel strandline terraces that form collinear geophysical/topographic ridges >300 m off mapped Quaternary faults.",
                "predicted_sign_and_size": "Bracketing sign: -0.0030 to +0.0025 DTI (MODEL). Paired with MASS -10%, the two points bracket the exact optimal mass S* on the R0 ranking curve in one week.",
                "falsifier": "A live score < 0.2735 while MASS -10% scores > 0.2785 falsifies under-allocation and proves the R0 ridge family is already over-budgeted past S* <= 37,654.",
            },
        },
        {
            "key": "drop20pct",
            "axis": "MASS",
            "value": "-20pct",
            "slug_value": "-drop20pct",
            "mask": mask_drop20,
            "predicted_change": "+0.0010 to +0.0065 DTI (MODEL: prunes 7,531 lowest-ranked 20% of R0 -> 30,123 dots; tests steeper precision-recall regime)",
            "form_note": "h33-h33-2-b2; MASS -20% (drop 7531 lowest-rank dots -> 30123); pred +0.001 to +0.007 DTI",
            "mechanism_card": {
                "hypothesis": "Pruning the bottom 20% (7,531 dots -> 30,123 dots) of R0 tests whether true unmapped test fault prevalence |G| is sparse enough (< 10,000 px) that aggressive denominator compression (-1,506 units in 0.2*S) outweighs the loss of second-decile ridge coverage.",
                "mechanism": "Retains only the top 80% (30,123 dots) of R0 where multi-channel ridge corroboration (h19_5 + h19_4 + h16_1 + tgc + d15 + ens12) and H33-A..D strike alignment both exceed the 20th-percentile marginal DTI gain threshold.",
                "non_fault_mimic": "Secondary tributary drainage alignments and low-relief piedmont slope breaks that pass 2-channel corroboration but lack deep basement (depth_to_base_surf / MT conductivity) or 1 m LiDAR scarplet step support.",
                "predicted_sign_and_size": "Positive if MASS -10% is positive: +0.0010 to +0.0065 DTI (MODEL). Determines curvature d^2(DTI)/dS^2 of the live score with respect to total dot mass.",
                "falsifier": "A live score < MASS -10% and < 0.2760 falsifies aggressive pruning and bounds optimal R0 mass firmly inside [33,889, 37,654].",
            },
        },
    ]

    releases_dir = ROOT / "releases"
    releases_dir.mkdir(parents=True, exist_ok=True)
    variant_records = []
    variant_masks_by_key = {}

    for spec in variant_specs:
        pair_key = (PARENT_ID, spec["axis"], spec["value"])
        if pair_key in existing_pairs:
            raise RuntimeError(f"Duplicate (parent, axis, value) in ledger: {pair_key}")

        mask = spec["mask"]
        n_dots = int(mask.sum())
        dots_added = int((mask & (~r0)).sum())
        dots_removed = int((r0 & (~mask)).sum())
        sym_diff = dots_added + dots_removed
        pct_changed = 100.0 * sym_diff / float(EXPECTED_R0_DOTS)
        if not (1.0 <= pct_changed <= 50.0):
            raise RuntimeError(
                f"Variant {spec['key']} changed {pct_changed:.2f}% of R0 dots (must be in [1%, 50%])"
            )

        # Write to temporary files first to compute exact GeoTIFF sha8 for the filename
        tmp_nan = releases_dir / f"_tmp_{spec['key']}.tif"
        tmp_zeros = releases_dir / f"_tmp_{spec['key']}-zeros.tif"
        tmp_info = write_submission_pair(mask, template_path, cat, tmp_nan, tmp_zeros)
        sha8 = tmp_info["nan_sha256"][:8]
        var_id = f"{PARENT_ID}-{spec['axis'].lower()}{spec['slug_value']}-{DATE_TAG}-{sha8}"

        final_nan = releases_dir / f"{var_id}.tif"
        final_zeros = releases_dir / f"{var_id}-zeros.tif"
        tmp_nan.replace(final_nan)
        tmp_zeros.replace(final_zeros)

        if file_sha256(final_nan) in existing_shas or file_sha256(final_zeros) in existing_shas:
            raise RuntimeError(f"SHA-256 already present in ledger for {var_id}")

        disk_check = verify_written_pair_from_disk(
            final_nan, final_zeros, template_path, cat, expected_dots=n_dots
        )

        dcat_vals = dcat[mask]
        added_dcat_min = float(dcat[mask & (~r0)].min()) if dots_added > 0 else None
        if added_dcat_min is not None and added_dcat_min < 3.0:
            raise RuntimeError(f"Added dots violated d_cat >= 3.0 px: min={added_dcat_min}")

        if len(spec["form_note"]) > 140:
            raise RuntimeError(f"Form note exceeds 140 chars: {len(spec['form_note'])}")

        rec = {
            "id": var_id,
            "key": spec["key"],
            "parent": PARENT_ID,
            "axis": spec["axis"],
            "value": spec["value"],
            "n_dots": n_dots,
            "dots_added": dots_added,
            "dots_removed": dots_removed,
            "symmetric_diff_dots": sym_diff,
            "pct_changed_vs_r0": round(pct_changed, 2),
            "jaccard_vs_r0": round(float((mask & r0).sum()) / float((mask | r0).sum()), 6),
            "d_cat_min_px": round(float(dcat_vals.min()), 4),
            "d_cat_median_px": round(float(np.median(dcat_vals)), 4),
            "d_cat_p90_px": round(float(np.percentile(dcat_vals, 90.0)), 4),
            "added_dots_d_cat_min_px": round(added_dcat_min, 4) if added_dcat_min is not None else None,
            "digest8_mask": tmp_info["digest8"],
            "nan_tif": disk_check["nan_tif"],
            "zeros_tif": disk_check["zeros_tif"],
            "form_note": spec["form_note"],
            "predicted_change": spec["predicted_change"],
            "mechanism_card": spec["mechanism_card"],
        }
        variant_records.append(rec)
        variant_masks_by_key[spec["key"]] = mask

        ledger_rows.append(
            {
                "id": var_id,
                "parent": PARENT_ID,
                "axis": spec["axis"],
                "value": spec["value"],
                "n_dots": str(n_dots),
                "pct_changed": f"{pct_changed:.2f}",
                "sha256": disk_check["nan_tif"]["sha256"],
                "status": "BUILT",
                "predicted_change": spec["predicted_change"],
                "receipt_score": "",
                "date": "",
                "repeat_count": "1",
                "evidence_label": "MODEL",
                "filename": f"{var_id}.tif",
            }
        )
        existing_shas.add(disk_check["nan_tif"]["sha256"])
        existing_shas.add(disk_check["zeros_tif"]["sha256"])
        existing_pairs.add(pair_key)
        print(
            f"      Built {var_id}: n_dots={n_dots} ({pct_changed:.2f}% changed vs R0), "
            f"nan_sha8={disk_check['nan_tif']['sha256'][:8]}, zeros_sha8={disk_check['zeros_tif']['sha256'][:8]}"
        )

    ledger_csv_path = write_ledger_csv(ledger_rows)
    print(f"      Updated {ledger_csv_path.relative_to(ROOT)} ({len(ledger_rows)} total rows).")

    print("[6/6] Running REPORT-ONLY diagnostics (hide-and-recover PROXY, leakage canary, SGMC control) ...")
    diagnostics = run_report_only_diagnostics(
        args.data_dir,
        bands_dir,
        foot,
        cat,
        dcat,
        d28_rebuilt,
        r0,
        gain_r0,
        cand_pool_base,
        q,
        K1,
        offs,
        surfaces,
        h33_union,
        lidar,
        corrob_count,
        variant_masks_by_key,
    )

    report = {
        "generated_utc": "2026-10-23T04:15:00Z",
        "git_head_sha": git_head_sha(),
        "seed": 520810,
        "axis": args.axis,
        "manifest_files_verified": len(manifest_verified),
        "parent_r0": {
            "id": PARENT_ID,
            "source_repo": "buffedlizard55-lab/GEMSDOE32",
            "live_score": PARENT_SCORE_CLAIM,
            "evidence_label": "CLAIM",
            "n_dots": EXPECTED_R0_DOTS,
            "d_cat_min_px": round(float(dcat[r0].min()), 4),
            "d_cat_median_px": round(float(np.median(dcat[r0])), 4),
            "d_cat_p90_px": round(float(np.percentile(dcat[r0], 90.0)), 4),
            "d_cat_gt_3px_dots": int((r0 & (dcat > 3.0)).sum()),
            "d_cat_eq_3px_dots": int((r0 & (dcat == 3.0)).sum()),
            "d_cat_between_2_and_3px_dots": int((r0 & (dcat > 2.0) & (dcat < 3.0)).sum()),
            "digest8": r0_pair["digest8"],
            "nan_sha256": r0_pair["nan_sha256"],
            "zeros_sha256": r0_pair["zeros_sha256"],
            "exact_rebuild_verified": True,
        },
        "variants": variant_records,
        "report_only_diagnostics": diagnostics,
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    out_json = ROOT / "evidence" / "r0_mass_variants_20261023.json"
    out_json.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Done in {report['elapsed_seconds']}s -> {out_json.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
