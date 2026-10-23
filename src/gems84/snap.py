"""AXIS=SNAP: relocate parent dots onto the strongest verified edge response, <= L px away.

Hypothesis (structural-geologist reading)
-----------------------------------------
The parent R0 dot set is the output of a purely *geometric* operator: a deterministic BFS
Poisson-disk thinning of the H19-5 lineament field at 2.8 px spacing
(``GEMSDOE24/src/gems/thinning.py:dot_thin``).  Which pixel of a ridge survives the thinning
is decided by raster traversal order, not by where the physical discontinuity actually is,
so a dot can sit one or two pixels off the geophysical edge that nominated the lineament in
the first place.  Under the official DTI kernel (triangular, R = 300 m = 3 px) the credit a
dot earns from a truth pixel is ``1 - d/3``: a 1 px misplacement costs up to one third of the
credit available from that truth pixel, and the 400 m GeoDAWN line spacing means lineament
positions are uncertain by roughly the kernel radius
(https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7).

Mechanism
---------
Each dot may move to the pixel of highest normalised *edge response* within a disc of radius
L pixels, provided (a) the response there is higher by at least ``margin``, (b) the target is
inside the footprint, (c) the target keeps >= 3 px from the catalogue (brief hard constraint
4 -- no mass on catalogue pixels and none within the exclusion ring), and (d) the target is
not already claimed by another dot.  Count, mass and exclusions are therefore unchanged; only
positions move.  The move is deterministic (fixed candidate order, no RNG).

The response is the OR-fusion (pixel-wise maximum) of the two competition bands that are
literal edge detectors, per the brief's SNAP specification ("provided TMI/gravity gradient
bands"): band 3 ``tmi_hg`` (TMI horizontal gradient) and band 18 ``iso_grav_anom_hg``
(isostatic gravity anomaly horizontal gradient), both from the sha256-pinned
``training_features.tif``.  Each band is nodata-filled, lightly smoothed (sigma = 1 px, the
upstream ``_fill`` convention), robust-standardised (median/IQR z) and scaled so 1.0 is the
99.5th percentile inside the footprint -- the upstream ``robust_unit`` convention, so the two
bands are comparable before fusion.  LiDAR-derived scarps are deliberately NOT used: the
brief restricts them to human-supplied rasters.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter

# (1-based rasterio band index, band name) -- verified against training_features.tif
# descriptions in registry/data_manifest.json.
EDGE_BANDS: tuple[tuple[int, str], ...] = ((3, "tmi_hg"), (18, "iso_grav_anom_hg"))
SMOOTH_SIGMA_PX = 1.0
ROBUST_PCT = 99.5
CLIP = 6.0


def robust_unit(a: np.ndarray, foot: np.ndarray, pct: float = ROBUST_PCT,
                clip: float = CLIP) -> np.ndarray:
    """Footprint-normalised non-negative score in [0, 1] (median/IQR z scaled at ``pct``).

    Same convention as the parent lineage's ``GEMSDOE32/src/gems32/h33.py:robust_unit`` so the
    two gradient bands are on a common scale before fusion.
    """
    out = np.zeros(a.shape, dtype=np.float32)
    v = foot & np.isfinite(a)
    if not v.any():
        return out
    vals = a[v]
    med = float(np.median(vals))
    q25, q75 = np.percentile(vals, [25.0, 75.0])
    scale = max(float(q75 - q25) / 1.349, 1e-9)
    z = (a - med) / scale
    hi = max(float(np.percentile(z[v], pct)), 1e-6)
    out[v] = np.clip(z[v] / hi, 0.0, clip) / clip
    return out


def _read_band(path, band: int, foot: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(band).astype(np.float32)
    return np.where(foot & np.isfinite(a) & (a > -1e30), a, np.nan)


def edge_response(features_tif, grid, bands: tuple[tuple[int, str], ...] = EDGE_BANDS,
                  sigma: float = SMOOTH_SIGMA_PX) -> tuple[np.ndarray, dict]:
    """Fused edge-response surface in [0, 1] plus per-band diagnostics."""
    per_band: dict[str, np.ndarray] = {}
    diag: dict = {"bands": [], "sigma_px": sigma, "robust_pct": ROBUST_PCT}
    for idx, name in bands:
        raw = _read_band(features_tif, idx, grid.foot)
        v = grid.foot & np.isfinite(raw)
        med = float(np.median(raw[v])) if v.any() else 0.0
        filled = np.where(v, raw, med).astype(np.float32)
        if sigma:
            filled = gaussian_filter(filled, sigma, mode="nearest").astype(np.float32)
        n = robust_unit(filled, grid.foot)
        per_band[name] = n
        diag["bands"].append({
            "index": idx, "name": name, "nodata_fraction":
            float(1.0 - v.sum() / max(int(grid.foot.sum()), 1)),
            "mean_in_footprint": float(n[grid.foot].mean()),
            "p99_in_footprint": float(np.percentile(n[grid.foot], 99.0)),
        })
    fused = np.maximum.reduce([per_band[n] for _i, n in bands]).astype(np.float32)
    fused[~grid.foot] = 0.0
    diag["fused_mean_in_footprint"] = float(fused[grid.foot].mean())
    return fused, {"response": diag, "per_band": per_band}


def _offsets(max_shift: float) -> list[tuple[int, int, float]]:
    """Candidate displacements with 0 < |d| <= ``max_shift`` (Euclidean px).

    Ordered by decreasing distance is *not* used: the order is by increasing distance, then
    ``dy``, then ``dx``, so tie-breaking is deterministic and independent of the data.
    """
    r = int(np.ceil(max_shift))
    out = []
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d = float(np.hypot(dy, dx))
            if 0.0 < d <= max_shift + 1e-9:
                out.append((dy, dx, d))
    return sorted(out, key=lambda t: (round(t[2], 6), t[0], t[1]))


@dataclass
class SnapResult:
    mask: np.ndarray
    moves: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def snap_dots(dots: np.ndarray, resp: np.ndarray, allowed: np.ndarray,
              max_shift: float, margin: float = 0.0) -> SnapResult:
    """Relocate dots onto higher-response pixels within ``max_shift`` px.

    Parameters
    ----------
    dots : bool array -- parent dot mask (one dot per pixel).
    resp : float array -- edge-response surface (higher = stronger edge).
    allowed : bool array -- pixels a dot may occupy (footprint, >= 3 px off catalogue).
    max_shift : maximum Euclidean displacement in pixels.
    margin : required response gain ``resp[target] - resp[current] >= margin``.  A strictly
        positive gain is always required, so ``margin=0`` means "move only if the target is
        genuinely stronger", not "move to any equal-valued pixel".

    Returns a ``SnapResult`` whose mask has exactly ``dots.sum()`` pixels, one dot per pixel.
    """
    dots = np.asarray(dots, bool)
    min_gain = max(float(margin), 1e-9)
    offs = _offsets(float(max_shift))
    if not offs:
        raise ValueError("max_shift admits no displacement")
    claimed = dots.copy()
    ys, xs = np.nonzero(dots)
    new = dots.copy()
    moves: list[tuple[int, int, int, int, float, float, float]] = []
    gains: list[float] = []
    n_blocked_feasibility = 0
    n_blocked_claim = 0

    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        r0 = float(resp[y0, x0])
        best = None
        for dy, dx, dist in offs:
            y1, x1 = y0 + dy, x0 + dx
            if not (0 <= y1 < resp.shape[0] and 0 <= x1 < resp.shape[1]):
                continue
            if not allowed[y1, x1]:
                n_blocked_feasibility += 1
                continue
            r1 = float(resp[y1, x1])
            if r1 - r0 < min_gain:
                continue
            if best is None or r1 > best[3] + 1e-12:
                best = (y1, x1, dist, r1)
        if best is None:
            continue
        y1, x1, dist, r1 = best
        if claimed[y1, x1]:
            n_blocked_claim += 1
            continue
        claimed[y0, x0] = False
        claimed[y1, x1] = True
        new[y0, x0] = False
        new[y1, x1] = True
        moves.append((int(y0), int(x0), int(y1), int(x1), r0, r1, dist))
        gains.append(r1 - r0)

    disp = np.array([m[6] for m in moves], dtype=np.float64) if moves else np.zeros(0)
    stats = {
        "max_shift_px": float(max_shift),
        "margin": float(margin),
        "min_gain_applied": float(min_gain),
        "candidate_offsets": len(offs),
        "dots_in": int(dots.sum()),
        "dots_out": int(new.sum()),
        "count_preserved": bool(new.sum() == dots.sum()),
        "dots_moved": int(len(moves)),
        "pct_dots_moved": round(100.0 * len(moves) / max(int(dots.sum()), 1), 3),
        "mean_displacement_px": float(disp.mean()) if disp.size else 0.0,
        "median_displacement_px": float(np.median(disp)) if disp.size else 0.0,
        "max_displacement_px": float(disp.max()) if disp.size else 0.0,
        "mean_response_gain": float(np.mean(gains)) if gains else 0.0,
        "median_response_gain": float(np.median(gains)) if gains else 0.0,
        "candidate_pixels_rejected_infeasible": int(n_blocked_feasibility),
        "candidate_pixels_rejected_already_claimed": int(n_blocked_claim),
    }
    return SnapResult(mask=new, moves=moves, stats=stats)


def density_cv(mask: np.ndarray, footprint: np.ndarray, block_px: int = 10) -> float:
    """Coefficient of variation of dot density over ``block_px``-pixel blocks (1 km at 10 px).

    Reported so a SNAP variant can be shown *not* to have changed the spatial concentration of
    mass (that is the CONCENTRATION axis, not this one).
    """
    h, w = mask.shape
    nb_y, nb_x = h // block_px, w // block_px
    m = mask[: nb_y * block_px, : nb_x * block_px].reshape(nb_y, block_px, nb_x, block_px)
    f = footprint[: nb_y * block_px, : nb_x * block_px].reshape(nb_y, block_px, nb_x, block_px)
    counts = m.sum(axis=(1, 3)).astype(np.float64)
    avail = f.sum(axis=(1, 3)).astype(np.float64)
    keep = avail > 0
    dens = counts[keep] / avail[keep]
    mu = float(dens.mean())
    return float(dens.std() / mu) if mu > 0 else 0.0
