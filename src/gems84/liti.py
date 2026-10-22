"""Leaderboard-Inverted Truth Intensity (LITI).

Idea
----
Every live-scored raster r is one noisy measurement of the *hidden* new-fault set.
Model the hidden truth as cells drawn with per-cell probability

    lambda(x) = exp(theta . phi(x))      (0 on mapped-catalogue cells)

Because the official TP_w is a sum over truth cells, its expectation is linear in
lambda:

    E[TP_w](r) = sum_x lambda(x) * c_r(x),   c_r(x) = max_o p_r(x+o) k(|o|)
    E[|G|]     = sum_x lambda(x)
    FP_w(r)    = S_r - sum_dots p * max_g k  ~=  S_r - eta * sum_x lambda(x) m_r(x),
                 m_r(x) = sum_o p_r(x+o) k(|o|)      (eta in (0,1) absorbs the
                 sum->max saturation for line-shaped truth)

and the predicted score is the official formula on those expectations:

    s_hat_r = A_r / (0.2 A_r + 0.2 F_r + 0.8 G)       (alpha=0.2, beta=0.8, R=300 m)

Sums are Monte-Carlo estimates on a fixed uniform sample of footprint cells.
theta and eta are fitted to the owner-reported live scores by penalised least
squares with an analytic gradient.  This is a *model*, never a score: every
number it produces is labelled MODEL-PROJECTION.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from gems57.metric import ALPHA, BETA, OFF_DX, OFF_DY, OFF_K


def coverage_at(p: np.ndarray, ys: np.ndarray, xs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """c(x)=max_o p(x+o)k(o) and m(x)=sum_o p(x+o)k(o) at sample cells (exact offsets)."""
    H, W = p.shape
    c = np.zeros(ys.size, np.float32)
    m = np.zeros(ys.size, np.float32)
    for j, i, k in zip(OFF_DY, OFF_DX, OFF_K):
        ny, nx = ys + j, xs + i
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        v = np.zeros(ys.size, np.float32)
        v[ok] = p[ny[ok], nx[ok]] * np.float32(k)
        np.maximum(c, v, out=c)
        m += v
    return c, m


def decoded_prediction(path, footprint):
    """In-footprint prediction with NaN->0 (the support the scorer can credit)."""
    import rasterio
    with rasterio.open(path) as s:
        a = s.read(1).astype(np.float32)
        ok = (s.count == 1 and s.shape == footprint.shape)
    if not ok:
        raise ValueError("not a single-band grid raster")
    a = np.where(np.isfinite(a) & footprint, a, 0).astype(np.float32)
    if (a < 0).any() or (a > 1).any():
        raise ValueError("values outside [0,1]: the portal would have rejected it")
    return a


def decoded_sha(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a, np.float32).tobytes()).hexdigest()


@dataclass
class Design:
    Phi: np.ndarray        # (n, F) float32 basis at sample cells (incl. intercept col 0)
    support: np.ndarray    # (n,) bool, lambda>0 allowed (not on catalogue)
    C: np.ndarray          # (R, n) float32 max-kernel coverage
    Mm: np.ndarray         # (R, n) float32 sum-kernel coverage
    S: np.ndarray          # (R,) emitted mass
    w: float               # footprint cells per sample cell
    names: list


def predict(theta, eta_logit, D: Design, rows=None):
    rows = np.arange(D.C.shape[0]) if rows is None else np.asarray(rows)
    lam = (np.exp(np.clip(D.Phi @ np.asarray(theta, np.float32), -30, 0.0)) * D.support).astype(np.float32)
    eta = 1.0 / (1.0 + np.exp(-eta_logit))
    A = D.w * (D.C[rows] @ lam).astype(np.float64)
    B = D.w * (D.Mm[rows] @ lam).astype(np.float64)
    G = D.w * float(lam.sum(dtype=np.float64))
    F = np.maximum(D.S[rows] - eta * B, 0.0)
    den = ALPHA * A + ALPHA * F + BETA * G
    return A / den, dict(A=A, B=B, G=G, F=F, eta=eta, lam=lam)


def fit(D: Design, y: np.ndarray, rows: np.ndarray, reg: float = 1e-3,
        theta0=None, maxiter: int = 400):
    """Penalised least squares on live scores; analytic gradient; intercept unpenalised."""
    Fdim = D.Phi.shape[1]
    if theta0 is None:
        theta0 = np.zeros(Fdim + 1)
        theta0[0] = np.log(12000.0 / (D.w * D.support.sum()))  # ~1.2e4 truth cells prior start
    yv = y[rows]
    Cr, Mr, Sr = D.C[rows], D.Mm[rows], D.S[rows]
    pen = np.ones(Fdim); pen[0] = 0.0

    def fun(z):
        th, el = z[:Fdim], z[Fdim]
        e = D.Phi @ th.astype(np.float32)
        clipmask = (e > -30) & (e < 0.0)
        lam = (np.exp(np.clip(e, -30, 0.0)) * D.support).astype(np.float32)
        eta = 1.0 / (1.0 + np.exp(-el))
        A = D.w * (Cr @ lam).astype(np.float64); B = D.w * (Mr @ lam).astype(np.float64)
        G = D.w * float(lam.sum(dtype=np.float64))
        Fp = Sr - eta * B
        pos = Fp > 0
        Fp = np.where(pos, Fp, 0.0)
        den = ALPHA * A + ALPHA * Fp + BETA * G
        s = A / den
        r = s - yv
        loss = float(r @ r) + reg * float(pen @ (th * th))
        L = (lam * clipmask)[:, None] * D.Phi           # d lam / d theta (float32)
        dA = D.w * (Cr @ L).astype(np.float64); dB = D.w * (Mr @ L).astype(np.float64)
        dG = D.w * L.sum(0, dtype=np.float64)
        dF = np.where(pos[:, None], -eta * dB, 0.0)
        dden = ALPHA * dA + ALPHA * dF + BETA * dG[None, :]
        ds = (dA * den[:, None] - A[:, None] * dden) / (den[:, None] ** 2)
        g_th = 2 * (r @ ds) + 2 * reg * pen * th
        dF_eta = np.where(pos, -B * eta * (1 - eta), 0.0)
        ds_eta = -A * ALPHA * dF_eta / den ** 2
        g_el = 2 * float(r @ ds_eta)
        return loss, np.concatenate([g_th, [g_el]])

    res = minimize(fun, theta0, jac=True, method="L-BFGS-B", options=dict(maxiter=maxiter))
    return res.x[:Fdim], float(res.x[Fdim]), res


def full_lambda(theta, Phi_full, support_full):
    """lambda on every footprint cell (chunked to bound memory)."""
    out = np.zeros(Phi_full.shape[0], np.float32)
    step = 500_000
    for a in range(0, Phi_full.shape[0], step):
        e = Phi_full[a:a + step].astype(np.float32) @ theta[1:].astype(np.float32) + np.float32(theta[0])
        out[a:a + step] = np.exp(np.clip(e, -30, 0.0))
    out[~support_full] = 0
    return out


def git_blob_sha(path) -> str:
    from pathlib import Path
    b = Path(path).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def load_scored(matches, footprint, ys, xs, registry_dir):
    """Decode, verify and de-duplicate every live-scored raster; coverage at the sample.

    A score row is kept only if all its matched blobs exist, pass the git-blob
    SHA-1 check, are valid [0,1] grid rasters, and decode to ONE prediction.
    Rows that decode to an already-seen prediction are merged (scores averaged).
    """
    from pathlib import Path
    rows, C, Mm, S, dropped, seen = [], [], [], [], [], {}
    for r in matches:
        decoded, problems = {}, []
        for repo, blob, path in r["matches"]:
            f = Path(registry_dir) / f"{blob}.tif"
            if not f.exists():
                problems.append(f"missing blob {blob}"); continue
            if git_blob_sha(f) != blob:
                problems.append(f"blob hash mismatch {blob}"); continue
            try:
                a = decoded_prediction(f, footprint)
            except Exception as e:
                problems.append(f"{blob}: {e}"); continue
            decoded.setdefault(decoded_sha(a), (a, blob, path))
        if len(decoded) != 1:
            dropped.append(dict(name=r["name"], score=r["score"], reason=(
                "ambiguous: matched rasters decode to %d different predictions" % len(decoded)
                if decoded else "; ".join(problems) or "no raster")))
            continue
        dsha, (a, blob, path) = next(iter(decoded.items()))
        if dsha in seen:
            rows[seen[dsha]]["scores"].append(r["score"]); rows[seen[dsha]]["names"].append(r["name"])
            continue
        c, m = coverage_at(a, ys, xs)
        seen[dsha] = len(rows)
        rows.append(dict(site=r["site"], names=[r["name"]], scores=[r["score"]], blob=blob, path=path,
                         decoded_sha256=dsha, emitted=int((a > 0).sum()), mass=float(a.sum())))
        C.append(c); Mm.append(m); S.append(float(a.sum()))
    return rows, np.stack(C), np.stack(Mm), np.array(S), dropped
