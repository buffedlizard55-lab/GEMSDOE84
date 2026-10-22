"""Interpretable basis maps phi_j(x) for the truth-intensity model.

lambda(x) = exp(theta . phi(x))  on footprint cells that are not mapped faults.

Two kinds of basis:

* **Physics / terrain** (catalogue-blind): rank-transformed to [0,1] inside the
  footprint so every coefficient is on the same scale.  Computed once and cached.
* **Catalogue geometry** (distance bands, local fault density): recomputed from
  whatever catalogue mask is passed in, so the hide-and-recover holdout can use
  the *visible* catalogue only (parallel-run protocol rule 2).

Every source band is named with its official band index/description
(training_features.tif band descriptions, read from the file itself).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

from .paths import EXTERNAL, FEATURES_TIF, WORK

# official band index -> short name (verified against the file's band descriptions)
BANDS = {3: "tmi_hg", 4: "geod_2ndinv", 12: "det_elev", 15: "depth_to_base_surf",
         17: "cond_surf", 18: "iso_grav_anom_hg", 19: "det_elev_slope"}

# distance-to-catalogue bins in pixels (100 m).  Bin 0 (on the catalogue) is excluded
# from the support of lambda; the remaining bins are one-hot with the last as reference.
DIST_EDGES = (0.0, 1.5, 2.5, 4.0, 7.0, 12.0, 20.0, 35.0, np.inf)
REGION_GRID = 3


def _rank01(v: np.ndarray) -> np.ndarray:
    """Average-free rank transform to (0,1]; NaN -> 0 (lowest)."""
    v = np.asarray(v, np.float64)
    out = np.zeros(v.shape, np.float32)
    ok = np.isfinite(v)
    if ok.sum() == 0:
        return out
    order = np.argsort(v[ok], kind="stable")
    r = np.empty(order.size, np.float32)
    r[order] = (np.arange(order.size, dtype=np.float32) + 1) / order.size
    out[ok] = r
    return out


def _read_band(idx: int, footprint: np.ndarray) -> np.ndarray:
    with rasterio.open(FEATURES_TIF) as s:
        a = s.read(idx).astype(np.float32)
        nod = s.nodata
    bad = ~np.isfinite(a) | (a <= -1e30) | ((nod is not None) & (a == np.float32(nod)))
    a[bad] = np.nan
    a[~footprint] = np.nan
    return a


def _fill(a: np.ndarray) -> np.ndarray:
    """Nearest-valid fill so filters do not smear NaN."""
    bad = ~np.isfinite(a)
    if not bad.any():
        return a
    idx = ndi.distance_transform_edt(bad, return_distances=False, return_indices=True)
    return a[tuple(idx)]


def _line_response(a: np.ndarray, sigma: float) -> np.ndarray:
    """Largest-magnitude Hessian eigenvalue (both polarities), scale-normalised."""
    f = _fill(a)
    hyy = ndi.gaussian_filter(f, sigma, order=(2, 0))
    hxx = ndi.gaussian_filter(f, sigma, order=(0, 2))
    hxy = ndi.gaussian_filter(f, sigma, order=(1, 1))
    tr = 0.5 * (hxx + hyy)
    disc = np.sqrt(0.25 * (hxx - hyy) ** 2 + hxy ** 2)
    lam = np.maximum(np.abs(tr + disc), np.abs(tr - disc))
    return (sigma ** 2) * lam


def _grad_mag(a: np.ndarray, sigma: float) -> np.ndarray:
    f = _fill(a)
    gy = ndi.gaussian_filter(f, sigma, order=(1, 0))
    gx = ndi.gaussian_filter(f, sigma, order=(0, 1))
    return np.hypot(gx, gy)


def physics_basis(footprint: np.ndarray, cache: Path | None = None) -> tuple[np.ndarray, list[str]]:
    """(n_footprint, F) float16 matrix of catalogue-blind basis maps, rank-transformed."""
    cache = Path(cache or WORK / "physics_basis.npz")
    if cache.exists():
        z = np.load(cache, allow_pickle=False)
        if int(z["n"]) == int(footprint.sum()):
            return z["X"], [str(s) for s in z["names"]]
    fp = footprint
    cols, names = [], []

    def add(name, arr):
        v = np.where(fp, arr, np.nan)[fp]
        cols.append(_rank01(v).astype(np.float16))
        names.append(name)

    det = _read_band(12, fp)
    add("det_elev_slope", _read_band(19, fp))
    add("det_elev_line_s1p5", _line_response(det, 1.5))
    add("det_elev_line_s4", _line_response(det, 4.0))
    del det
    add("iso_grav_hg", _read_band(18, fp))
    add("tmi_hg", _read_band(3, fp))
    add("basement_depth_grad", _grad_mag(_read_band(15, fp), 2.0))
    add("cond_surf", _read_band(17, fp))
    add("geod_2ndinv", _read_band(4, fp))
    with rasterio.open(EXTERNAL / "topo_10m_derived_100m_u8.tif") as s:
        relief = s.read(5).astype(np.float32); relief[relief == 0] = np.nan
        curv = s.read(6).astype(np.float32); curv[curv == 0] = np.nan
        hsl = s.read(8).astype(np.float32); hsl[hsl == 0] = np.nan
    add("relief_local_10m", relief)
    add("curv_prof_absmax_10m", curv)
    add("hs_lineament_10m", hsl)
    del relief, curv, hsl
    with rasterio.open(EXTERNAL / "lidar_scarp_features_u8.tif") as s:
        ex = s.read(1).astype(np.float32)
        valid = s.read(12) > 0
    ex[~valid] = np.nan
    # scarp strength only where LiDAR exists (others rank lowest); coverage itself is a
    # separate binary basis -- a proxy for where 1 m mapping effort is possible.
    add("lidar_ex_max", ex)
    cols.append(valid[fp].astype(np.float16)); names.append("lidar_valid")
    X = np.stack(cols, axis=1)
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez(cache, X=X, names=np.array(names), n=np.int64(fp.sum()))
    return X, names


def region_basis(footprint: np.ndarray, grid: int = REGION_GRID) -> tuple[np.ndarray, list[str]]:
    """One-hot coarse regions over the footprint bounding box (last block = reference)."""
    yy, xx = np.nonzero(footprint)
    y0, y1, x0, x1 = yy.min(), yy.max() + 1, xx.min(), xx.max() + 1
    ry = np.minimum((yy - y0) * grid // (y1 - y0), grid - 1)
    rx = np.minimum((xx - x0) * grid // (x1 - x0), grid - 1)
    rid = ry * grid + rx
    cols, names = [], []
    for k in range(grid * grid - 1):
        cols.append((rid == k).astype(np.float16)); names.append(f"region_{k // grid}{k % grid}")
    return np.stack(cols, axis=1), names


def catalogue_basis(footprint: np.ndarray, catalogue: np.ndarray) -> tuple[np.ndarray, list[str], np.ndarray]:
    """Distance-band one-hots + log local fault density, from ``catalogue`` only.

    Returns (X, names, on_catalogue) where ``on_catalogue`` marks footprint cells
    that are mapped faults (lambda is forced to zero there).
    """
    cat = np.asarray(catalogue, bool) & footprint
    d = ndi.distance_transform_edt(~cat)[footprint]
    cols, names = [], []
    for lo, hi in zip(DIST_EDGES[:-2], DIST_EDGES[1:-1]):
        cols.append(((d > lo) & (d <= hi)).astype(np.float16))
        names.append(f"dcat_{lo:g}_{hi:g}")
    dens = ndi.gaussian_filter(cat.astype(np.float32), 50.0)[footprint]
    cols.append(_rank01(dens).astype(np.float16)); names.append("cat_density_5km")
    return np.stack(cols, axis=1), names, (d == 0)


def full_basis(footprint, catalogue):
    Xp, np_ = physics_basis(footprint)
    Xr, nr = region_basis(footprint)
    Xc, nc, oncat = catalogue_basis(footprint, catalogue)
    X = np.concatenate([Xp, Xr, Xc], axis=1)
    return X, np_ + nr + nc, oncat


def describe(names):
    return json.dumps(names)
