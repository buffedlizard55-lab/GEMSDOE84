"""Exact transcription of the competition's distance-weighted Tversky index (DTI).

Formula source (OFFICIAL, verbatim from
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ , section
"Performance metric", fetched 2026-10-22):

    k(d) = max(1 - d/R, 0)                              triangular kernel, R = 300 m

    TP_w = sum_{g in G} max_{x : d(x,g) <= R} p(x) * k(d(x,g))
    FP_w = sum_{x : p(x) > 0} p(x) * [1 - max_{g in G} k(d(x,g))]
    FN_w = sum_{g in G} [1 - max_{x : d(x,g) <= R} p(x) * k(d(x,g))]

    DTI(alpha, beta) = TP_w / (TP_w + alpha*FP_w + beta*FN_w + eps)

with alpha = 0.2, beta = 0.8 for this competition.

This module ships two implementations of TP_w/FP_w/FN_w:
  * `dti_bruteforce`  -- literal O(N_truth * N_pixels-within-R) loop, used ONLY to unit-test
    the fast version on small synthetic rasters (see tests/test_metric.py). Never run on the
    full 3730x3292 grid.
  * `dti_fast`        -- vectorised using scipy distance transforms + a small (2R+1)^2 kernel
    max-filter, exact (not an approximation) for this kernel because the triangular kernel
    has finite support R=3 px.

Algebraic identity used by `dti_fast` (re-derived and checked against the brute-force
version in tests/test_metric.py to < 1e-9):
    Let M(y) = max_{o : |o| <= R} p(y + o) * k(|o|)      (a weighted grey dilation of p)
    Then TP_w = sum_{g in G} M(g), and FN_w = |G| - TP_w exactly (each truth pixel
    contributes exactly one unit to the FN_w sum before weighting: 1 - M(g)).
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt

PIXEL_M = 100.0   # official: 100 m resolution
R_M = 300.0       # official: 300 m triangular-kernel support
ALPHA = 0.2       # official
BETA = 0.8        # official
EPS = 1e-9


def _kernel_offsets(pixel_m: float = PIXEL_M, r_m: float = R_M):
    r_px = int(np.ceil(r_m / pixel_m))
    offs = []
    for dy in range(-r_px, r_px + 1):
        for dx in range(-r_px, r_px + 1):
            d = np.hypot(dy, dx) * pixel_m
            if d <= r_m:
                w = max(1.0 - d / r_m, 0.0)
                offs.append((dy, dx, w))
    return offs


_OFFSETS = _kernel_offsets()


def _weighted_dilation(p: np.ndarray) -> np.ndarray:
    """M(y) = max over offsets o (|o|<=R) of p(y+o) * k(|o|). Zero-padded at borders."""
    h, w = p.shape
    M = np.zeros_like(p, dtype=np.float32)
    for dy, dx, wgt in _OFFSETS:
        if wgt == 0.0:
            continue
        shifted = np.zeros_like(p, dtype=np.float32)
        ys0, ys1 = max(0, dy), h + min(0, dy)
        xs0, xs1 = max(0, dx), w + min(0, dx)
        yd0, yd1 = max(0, -dy), h - max(0, dy)
        xd0, xd1 = max(0, -dx), w - max(0, dx)
        shifted[yd0:yd1, xd0:xd1] = p[ys0:ys1, xs0:xs1] * wgt
        np.maximum(M, shifted, out=M)
    return M


def dti_fast(p: np.ndarray, truth: np.ndarray, valid: np.ndarray | None = None,
             alpha: float = ALPHA, beta: float = BETA, crop_margin_px: int = 4) -> dict:
    """Exact (finite-kernel) vectorised DTI. p in [0,1], truth boolean, valid boolean mask
    of pixels that are inside the scoring footprint (both p and truth are treated as 0 /
    False outside `valid`).

    Performance note (exact, not an approximation): because the triangular kernel has
    finite support R=300 m=3 px, both the TP_w weighted-dilation term and the FP_w
    kernel-weight correction are identically zero more than `crop_margin_px` pixels away
    from the nearest truth pixel. FP_w is therefore computed as
    `sum(p) - sum(p * kweight)` with `kweight` built only inside a cropped bounding box
    around the (usually spatially localized, per-fold) truth mask -- this is algebraically
    identical to running on the full raster, just far cheaper when truth is sparse/local,
    which matters because this function is called ~dozens of times per holdout run on a
    3730x3292 grid in a 3.8 GB sandbox.
    """
    p = np.asarray(p, dtype=np.float32)
    truth = np.asarray(truth, dtype=bool)
    if valid is not None:
        p = np.where(valid, p, 0.0)
        truth = truth & valid
    p = np.clip(np.nan_to_num(p, nan=0.0), 0.0, 1.0)

    n_truth = int(truth.sum())
    S_total = float(p.sum())
    if n_truth == 0:
        return {"TPw": 0.0, "FPw": S_total, "FNw": 0.0, "n_truth": 0,
                "DTI": 0.0 if S_total > 0 else 1.0}

    ys, xs = np.where(truth)
    r_px = int(np.ceil(R_M / PIXEL_M))
    pad = r_px + crop_margin_px
    h, w = p.shape
    y0, y1 = max(0, ys.min() - pad), min(h, ys.max() + pad + 1)
    x0, x1 = max(0, xs.min() - pad), min(w, xs.max() + pad + 1)

    p_c = p[y0:y1, x0:x1]
    truth_c = truth[y0:y1, x0:x1]

    M_c = _weighted_dilation(p_c)
    TPw = float(M_c[truth_c].sum())

    dist_px = distance_transform_edt(~truth_c)
    dist_m = dist_px * PIXEL_M
    kweight_c = np.maximum(1.0 - dist_m / R_M, 0.0)
    fp_correction = float((p_c * kweight_c).sum())
    FPw = S_total - fp_correction  # = sum_x p(x)*(1-kweight_full(x)) exactly
    FNw = float(n_truth - TPw)

    denom = TPw + alpha * FPw + beta * FNw + EPS
    DTI = TPw / denom
    return {"TPw": TPw, "FPw": FPw, "FNw": FNw, "n_truth": n_truth, "DTI": DTI}


def dti_bruteforce(p: np.ndarray, truth: np.ndarray, alpha: float = ALPHA,
                    beta: float = BETA, pixel_m: float = PIXEL_M, r_m: float = R_M) -> dict:
    """Literal O(pixels x pixels-within-R) transcription of the organizer's formula, for
    unit-testing the fast path on small rasters only."""
    p = np.clip(np.nan_to_num(np.asarray(p, dtype=np.float32), nan=0.0), 0.0, 1.0)
    truth = np.asarray(truth, dtype=bool)
    h, w = p.shape
    g_idx = np.argwhere(truth)
    n_truth = len(g_idx)
    if n_truth == 0:
        return {"TPw": 0.0, "FPw": float(p.sum()), "FNw": 0.0, "n_truth": 0}

    TPw = 0.0
    best_k_per_pixel = np.zeros((h, w), dtype=np.float32)
    for (gy, gx) in g_idx:
        best = 0.0
        for y in range(h):
            for x in range(w):
                d = np.hypot(y - gy, x - gx) * pixel_m
                if d <= r_m:
                    k = max(1.0 - d / r_m, 0.0)
                    val = p[y, x] * k
                    if val > best:
                        best = val
                    if k > best_k_per_pixel[y, x]:
                        best_k_per_pixel[y, x] = k
        TPw += best
    FPw = float((p * (1.0 - best_k_per_pixel)).sum())
    FNw = float(n_truth - TPw)
    denom = TPw + alpha * FPw + beta * FNw + EPS
    return {"TPw": TPw, "FPw": FPw, "FNw": FNw, "n_truth": n_truth, "DTI": TPw / denom}
