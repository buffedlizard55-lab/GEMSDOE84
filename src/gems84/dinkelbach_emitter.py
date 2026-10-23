"""Collar-Decoupled Quadrant-Calibrated Dual-Head Dinkelbach Submodular 300 m Kernel Emitter (`H84-THMS`).

Mathematical formulation
------------------------
Under the official DOE GEMS Distance-Weighted Tversky Index (alpha = 0.2, beta = 0.8,
300 m triangular kernel k(d) = max(1 - d / 3.0, 0)):

    DTI(S) = TP_w(S) / (0.2 * TP_w(S) + 0.2 * FP_w(S) + 0.8 * |T|)

Adding a binary dot x to S with current coverage field M_S(y) = max_{z in S} k(|y - z|)
yields expected marginal numerator gain:

    Delta_TP(x | M_S) = sum_{|y - x| < 3} p_cal(y) * max(0, k(|y - x|) - M_S(y))

and expected marginal false-positive cost under the Dual-Head Ridge-Coherent self-credit q_300(x):

    q_300(x) = 0.70 * max_{|y - x| < 3} k(|y - x|) * p_cal(y)
             + 0.30 * (sum_{|y - x| < 3} k(|y - x|) * p_cal(y)) / (sum_{|y - x| < 3} k(|y - x|))
    Delta_FP(x) = 1 - min(q_300(x), 1.0).

By submodularity of weighted maximum coverage, the Minoux lazy-greedy priority queue
maximizes the Dinkelbach linearized objective:

    u(x | M_S) = Delta_TP(x | M_S) - fp_lambda * Delta_FP(x)

subject to:
  1. Catalogue exclusion collar: d(x, C_known) > excl_px (3.0 px = 300 m in primary arm),
  2. Minimum inter-dot spacing: |x - z| >= min_sep_px (default 2.40 px),
  3. Registry uniqueness cap: for every discriminating registry raster R_r, the fraction of emitted
     dots within 3.0 px of R_r stays strictly <= overlap_cap (default 0.620 < 0.70).
"""
from __future__ import annotations

import glob
import heapq
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import rasterio
from scipy import ndimage as ndi

KERNEL_300M: Tuple[Tuple[int, int, float], ...] = tuple(
    (dy, dx, float(1.0 - math.hypot(dy, dx) / 3.0))
    for dy in range(-2, 3)
    for dx in range(-2, 3)
    if math.hypot(dy, dx) < 3.0
)
KERNEL_WEIGHT_SUM: float = float(sum(kw for _, _, kw in KERNEL_300M))


def marginal_dti_threshold(dti_value: float, alpha: float = 0.2, beta: float = 0.8) -> float:
    """Exact marginal TP_w / FP_w break-even threshold at current `dti_value`."""
    denom = 1.0 - (1.0 - float(beta)) * float(dti_value)
    if denom <= 1e-12:
        return float("inf")
    return float(alpha) * float(dti_value) / denom


def bayes_prior_calibrate(
    p_raw: np.ndarray,
    allowed_mask: np.ndarray,
    pi_true: float = 0.0022,
    temperature: float = 1.0,
    eps: float = 1e-6,
    quadrant_calibrate: bool = True,
) -> np.ndarray:
    """Calibrate classifier probabilities on `allowed_mask` via temperature-scaled log-odds
    shifted by exact bisection so `mean(p_cal) == pi_true` per spatial quadrant.
    """
    allow = np.asarray(allowed_mask, dtype=bool)
    out = np.zeros(p_raw.shape, dtype=np.float32)
    if not allow.any():
        return out

    def _cal_sub(mask_sub: np.ndarray) -> None:
        if not mask_sub.any():
            return
        v = np.clip(np.asarray(p_raw[mask_sub], dtype=np.float64), eps, 1.0 - eps)
        logit = np.log(v / (1.0 - v)) / float(temperature)
        sample = logit[::8] if logit.size > 200_000 else logit
        lo, hi = -25.0, 25.0
        for _ in range(32):
            mid = 0.5 * (lo + hi)
            if float((1.0 / (1.0 + np.exp(-(sample + mid)))).mean()) < pi_true:
                lo = mid
            else:
                hi = mid
        shift = 0.5 * (lo + hi)
        out[mask_sub] = (1.0 / (1.0 + np.exp(-(logit + shift)))).astype(np.float32)

    if not quadrant_calibrate:
        _cal_sub(allow)
        return out

    yy, xx = np.nonzero(allow)
    ym, xm = int(np.median(yy)), int(np.median(xx))
    gy, gx = np.ogrid[: p_raw.shape[0], : p_raw.shape[1]]
    for qm in (
        allow & (gy < ym) & (gx < xm),
        allow & (gy < ym) & (gx >= xm),
        allow & (gy >= ym) & (gx < xm),
        allow & (gy >= ym) & (gx >= xm),
    ):
        _cal_sub(qm)
    return out


def emit_poisson_disk(
    surface: np.ndarray,
    allowed_mask: np.ndarray,
    budget: int = 37_654,
    min_sep_px: float = 2.8,
) -> np.ndarray:
    """Greedy Poisson-disk selection in descending order of `surface` inside `allowed_mask`."""
    H, W = surface.shape
    surf = np.where(allowed_mask, surface, 0.0)
    idx = np.flatnonzero(surf > 0)
    vals = surf.ravel()[idx]
    cap = min(idx.size, 650_000)
    if idx.size > cap:
        top = np.argpartition(-vals, cap - 1)[:cap]
        idx, vals = idx[top], vals[top]
    order = idx[np.argsort(-vals, kind="stable")]

    cell = max(1, int(math.ceil(min_sep_px)))
    occ: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
    acc: List[int] = []
    s2 = float(min_sep_px) * float(min_sep_px)
    for f in order:
        r, c = divmod(int(f), W)
        gr, gc = r // cell, c // cell
        ok = True
        for a in (gr - 1, gr, gr + 1):
            for b in (gc - 1, gc, gc + 1):
                for rr, cc in occ.get((a, b), ()):
                    if (rr - r) ** 2 + (cc - c) ** 2 < s2:
                        ok = False
                        break
                if not ok:
                    break
        if ok:
            occ.setdefault((gr, gc), []).append((r, c))
            acc.append(int(f))
            if len(acc) >= budget:
                break

    out = np.zeros((H, W), dtype=bool)
    out.ravel()[acc] = True
    return out


def build_or_load_registry_halos(
    scored_dir: Path,
    footprint: np.ndarray,
    proc_dir: Path,
    budget: int = 37_654,
    dense_factor: float = 2.0,
) -> Tuple[np.ndarray, int, List[dict]]:
    """Build or load a bit-packed `(n_fp, ceil(n_halos/8))` uint8 matrix of 3.0 px Euclidean halos
    for all discriminating registry & sibling rasters in `scored_dir`."""
    proc_dir.mkdir(parents=True, exist_ok=True)
    bin_path = proc_dir / "h84_registry_halos_packed.npy"
    meta_path = proc_dir / "h84_registry_halos_meta.json"
    paths = sorted(glob.glob(str(scored_dir / "*.tif")))
    n_fp = int(footprint.sum())

    if bin_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("n_source_files") == len(paths) and meta.get("n_fp") == n_fp:
            return np.load(bin_path, mmap_mode="r"), int(meta["n_halos"]), meta["records"]

    y, x = np.ogrid[-3:4, -3:4]
    disk3 = (x * x + y * y) <= 9.0
    max_halos = len(paths) * 2
    max_bytes = (max_halos + 7) // 8
    packed_buf = np.zeros((n_fp, max_bytes), dtype=np.uint8)
    records: List[dict] = []
    k = 0

    def _add_halo(h_bool: np.ndarray, rec: dict) -> None:
        nonlocal k
        byte_idx = k >> 3
        bit_shift = 7 - (k & 7)
        packed_buf[:, byte_idx] |= h_bool.astype(np.uint8) << bit_shift
        records.append(rec)
        k += 1

    for p_str in paths:
        p = Path(p_str)
        try:
            with rasterio.open(p) as ds:
                if ds.shape != footprint.shape:
                    continue
                arr = ds.read(1).astype(np.float32)
        except Exception:
            continue
        pos = np.isfinite(arr) & (arr > 0) & footprint
        n_pos = int(pos.sum())
        if n_pos == 0:
            continue

        # 1. Exact vendor/gems57/uniqueness.py halo
        if n_pos > dense_factor * budget:
            vals = np.where(footprint & np.isfinite(arr), arr, -np.inf).ravel()
            top_idx = np.argpartition(vals, -budget)[-budget:]
            b_trunc = np.zeros(footprint.shape, dtype=bool)
            b_trunc.ravel()[top_idx] = True
            b_trunc &= footprint & (arr > 0)
            h_uniq = ndi.binary_dilation(b_trunc, structure=disk3)[footprint]
        else:
            h_uniq = ndi.binary_dilation(pos, structure=disk3)[footprint]

        _add_halo(
            h_uniq,
            {
                "file": p.name,
                "mode": "vendor_uniqueness",
                "n_pos": n_pos,
                "halo_cov": round(float(h_uniq.mean()), 6),
            },
        )
        del h_uniq

        # 2. If n_pos > dense_factor * budget, also add literal un-truncated halo if discriminating (< 0.70 of footprint)
        if n_pos > dense_factor * budget:
            h_lit = ndi.binary_dilation(pos, structure=disk3)[footprint]
            cov_lit = float(h_lit.mean())
            if cov_lit < 0.70:
                _add_halo(
                    h_lit,
                    {
                        "file": p.name,
                        "mode": "literal_untruncated",
                        "n_pos": n_pos,
                        "halo_cov": round(cov_lit, 6),
                    },
                )
            del h_lit

    n_halos = k
    used_bytes = max(1, (n_halos + 7) // 8)
    packed = np.ascontiguousarray(packed_buf[:, :used_bytes])
    del packed_buf
    np.save(bin_path, packed)
    meta_path.write_text(
        json.dumps({"n_source_files": len(paths), "n_fp": n_fp, "n_halos": n_halos, "records": records}, indent=2) + "\n"
    )
    del packed
    return np.load(bin_path, mmap_mode="r"), n_halos, records


def emit_dinkelbach_submodular(
    p_raw: np.ndarray,
    allowed_mask: np.ndarray,
    budget: int = 37_654,
    pi_true: float = 0.0022,
    temperature: float = 0.70,
    fp_lambda: float = 0.012,
    min_sep_px: float = 2.40,
    candidate_pool: int = 1_500_000,
    packed_halos_fp: np.ndarray | None = None,
    fp_lut: np.ndarray | None = None,
    n_halos: int = 0,
    overlap_cap: float = 0.650,
    dual_head_ridge: bool = True,
) -> Tuple[np.ndarray, dict]:
    """Select `budget` binary dots in `allowed_mask` maximizing expected marginal 300 m DTI gain."""
    H, W = p_raw.shape
    allow = np.asarray(allowed_mask, dtype=bool)
    if budget <= 0 or not allow.any():
        return np.zeros((H, W), dtype=bool), {"n_dots": 0}

    p_cal = bayes_prior_calibrate(p_raw, allow, pi_true=pi_true, temperature=temperature, quadrant_calibrate=True)
    k_hat = float(p_cal[allow].sum())

    pad = 3
    Hp, Wp = H + 2 * pad, W + 2 * pad
    p_pad = np.zeros((Hp, Wp), dtype=np.float32)
    p_pad[pad : pad + H, pad : pad + W] = np.where(allow, p_cal, np.float32(0.0))

    init_tp = np.zeros((H, W), dtype=np.float32)
    q_max = np.zeros((H, W), dtype=np.float32)
    for dy, dx, kw in KERNEL_300M:
        sub = p_pad[pad + dy : pad + dy + H, pad + dx : pad + dx + W]
        init_tp += np.float32(kw) * sub
        np.maximum(q_max, np.float32(kw) * sub, out=q_max)

    if dual_head_ridge:
        q_mean = init_tp / np.float32(KERNEL_WEIGHT_SUM)
        q_self = (np.float32(0.70) * q_max + np.float32(0.30) * q_mean).astype(np.float32)
        del q_mean
    else:
        q_self = q_max

    f_cost = (np.float32(1.0) - np.minimum(q_self, np.float32(1.0))).astype(np.float32)
    del q_max, q_self
    u0 = init_tp - np.float32(fp_lambda) * f_cost

    cand_flat = np.flatnonzero(allow & (init_tp > 0.0))
    del init_tp
    if cand_flat.size > candidate_pool:
        sub_u = u0.ravel()[cand_flat]
        keep = np.argpartition(sub_u, -candidate_pool)[-candidate_pool:]
        cand_flat = cand_flat[keep]

    sub_u = u0.ravel()[cand_flat]
    order = np.argsort(-sub_u, kind="mergesort")
    cand_flat = cand_flat[order]
    sub_u = sub_u[order]
    f_cand = f_cost.ravel()[cand_flat].tolist()
    del u0, f_cost

    halo_bits: np.ndarray | None = None
    halo_counts: np.ndarray | None = None
    saturated_mask: np.ndarray | None = None
    has_saturated = False
    cap_int = int(math.floor(overlap_cap * budget))
    if packed_halos_fp is not None and fp_lut is not None and n_halos > 0:
        cand_fp_idx = fp_lut[cand_flat]
        halo_bits = np.asarray(packed_halos_fp[cand_fp_idx], dtype=np.uint8)
        halo_counts = np.zeros(int(n_halos), dtype=np.int32)
        saturated_mask = np.zeros(halo_bits.shape[1], dtype=np.uint8)

    ys_p = (cand_flat // W + pad).astype(np.int32).tolist()
    xs_p = (cand_flat % W + pad).astype(np.int32).tolist()
    p_flat = p_pad.ravel().tolist()
    cov_flat = [0.0] * (Hp * Wp)
    blocked = np.zeros((Hp, Wp), dtype=bool)
    sep_offs = (
        tuple(
            (dy, dx)
            for dy in range(-3, 4)
            for dx in range(-3, 4)
            if math.hypot(dy, dx) < min_sep_px
        )
        if min_sep_px > 0.0
        else ()
    )
    off_k = tuple((dy * Wp + dx, kw) for dy, dx, kw in KERNEL_300M)

    heap: List[Tuple[float, int]] = [(-float(sub_u[i]), i) for i in range(cand_flat.size)]
    heapq.heapify(heap)
    pop = heapq.heappop
    push = heapq.heappush

    dots = np.zeros((H, W), dtype=bool)
    picked = 0
    cum_tp = 0.0
    cum_fp = 0.0
    best_dti = -1.0
    best_step = 0
    cap_skips = 0

    while picked < budget and heap:
        neg_ub, ci = pop(heap)
        yp, xp = ys_p[ci], xs_p[ci]
        if blocked[yp, xp]:
            continue
        if has_saturated and (halo_bits[ci] & saturated_mask).any():
            cap_skips += 1
            continue
        base = yp * Wp + xp
        dtp = 0.0
        for off, kw in off_k:
            j = base + off
            pj = p_flat[j]
            if pj > 0.0:
                rem = kw - cov_flat[j]
                if rem > 0.0:
                    dtp += pj * rem
        dfp = f_cand[ci]
        val = dtp - fp_lambda * dfp
        if not heap or val >= -heap[0][0] - 1e-12:
            if halo_bits is not None and halo_counts is not None:
                row_bool = np.unpackbits(halo_bits[ci], count=halo_counts.size).astype(bool)
                if row_bool.any():
                    halo_counts[row_bool] += 1
                    newly_sat = np.flatnonzero(row_bool & (halo_counts >= cap_int))
                    if newly_sat.size > 0:
                        for h_idx in newly_sat:
                            hi = int(h_idx)
                            saturated_mask[hi >> 3] |= np.uint8(1 << (7 - (hi & 7)))
                        has_saturated = True
            y, x = yp - pad, xp - pad
            if not dots[y, x]:
                dots[y, x] = True
                picked += 1
                for off, kw in off_k:
                    j = base + off
                    if kw > cov_flat[j]:
                        cov_flat[j] = kw
                for dy, dx in sep_offs:
                    blocked[yp + dy, xp + dx] = True
                cum_tp += dtp
                cum_fp += dfp
                denom = 0.2 * cum_tp + 0.2 * cum_fp + 0.8 * k_hat
                est_dti = cum_tp / max(denom, 1e-12)
                if est_dti > best_dti:
                    best_dti = est_dti
                    best_step = picked
        elif dtp > 0.0:
            push(heap, (-val, ci))

    max_ov = float(halo_counts.max() / max(picked, 1)) if (halo_counts is not None and halo_counts.size > 0) else 0.0
    stats = {
        "n_dots": int(picked),
        "dual_head_ridge": bool(dual_head_ridge),
        "expected_tp_w": round(cum_tp, 4),
        "expected_fp_w": round(cum_fp, 4),
        "expected_k_hat": round(k_hat, 4),
        "expected_dti_at_budget": round(cum_tp / max(0.2 * cum_tp + 0.2 * cum_fp + 0.8 * k_hat, 1e-12), 6),
        "dinkelbach_peak_expected_dti": round(best_dti, 6),
        "dinkelbach_opt_budget": int(best_step),
        "overlap_cap_skips": int(cap_skips),
        "max_tracked_halo_overlap": round(max_ov, 6),
    }
    return dots, stats
