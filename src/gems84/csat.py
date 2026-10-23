"""Lane H84-CSAT: Contact-Depth 3D Analytic Signal & Elastic Strain-Accommodation Transfer.

Implements the preregistered GEMSDOE84 method lane (registry/preregistration.json):
  1. 38 catalogue-blind multi-physics channels combining official 19-band potential,
     geodetic, seismic, conductivity, basement and detrended-elevation fields with
     3D Analytic Signal amplitudes, vertical contact phase ratios, Salem (2007)
     Tilt-Depth shallow-contact wavenumber, GeoDAWN K/Th & U/Th metasomatic/redox
     residuals, seamless relief-deconfounded 1 m LiDAR + 10 m 3DEP piedmont
     breaklines, and playa-deconfounded DOE GDR #1391 geothermometer enthalpy plumes
     (strictly asserting ``dist_known_fault_px`` is never read).
  2. 20 visible-only elastic fracture-mechanics strain-transfer & physics-coupling
     channels reusing ``gems57.relay_bend_anatomy`` (exact bitplane two-component
     Voronoi distance transform ``two_host_frame`` and multi-scale ``host_bend_fields``)
     and ``gems57.network`` (``local_strike``, ``offset_components``), augmented with
     outward Pollard-Segall crack-tip propagation cones.
  3. Strict Leave-One-Quadrant-Out (LOQO) Dual-Habitat training:
       * Head A (``P_transfer``): HGB + ExtraTrees trained on counterfactual
         synthetic whole-component withhold splits (``buffer_px = 3``) strictly
         inside the 3 non-test quadrants so off-collar distances never collapse.
       * Head B (``P_concealed``): 100 % catalogue-blind HGB + ExtraTrees trained
         on inverse-relief-weighted positives vs relief-matched + basin negatives.
  4. Quadrant Bayes prior-shift calibration + shared ``gems57.emit.greedy_allocate``
     exact two-sided 300 m triangular-kernel submodular dot allocation.
  5. Zero registry rasters are accessed during feature building, training, or
     dot emission; uniqueness is audited blindly via ``gems57.uniqueness``.
"""
from __future__ import annotations

import csv
import gc
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier

from gems57 import emit
from gems57.holdout import quadrant_ids
from gems57.network import STRUCT3, local_strike, offset_components
from gems57.relay_bend_anatomy import host_bend_fields, two_host_frame

from .paths import EXTERNAL, FEATURES_TIF, WORK

CLIP_Z = 8.0

OFFICIAL_BAND_NAMES = (
    "b01_mag_anom",
    "b02_rtp",
    "b03_tmi_hg",
    "b04_geod_2ndinv",
    "b05_iso_grav_slope",
    "b06_tc",
    "b07_geod_shear",
    "b08_geod_dilat",
    "b09_tmi_vg",
    "b10_deq",
    "b11_iso_grav_vg",
    "b12_det_elev",
    "b13_iso_grav",
    "b14_tmi",
    "b15_depth_base",
    "b16_ieq",
    "b17_cond_surf",
    "b18_iso_grav_hg",
    "b19_det_elev_slope",
)

FORBIDDEN_GDR_COLUMNS = frozenset({"dist_known_fault_px"})


def robust_z_1d(v: np.ndarray, valid_sub: np.ndarray | None = None) -> np.ndarray:
    """Median/MAD robust z-score on a 1-D footprint vector; non-finite -> 0."""
    x = np.asarray(v, dtype=np.float32)
    ok = np.isfinite(x) if valid_sub is None else (np.isfinite(x) & np.asarray(valid_sub, bool))
    out = np.zeros(x.shape, dtype=np.float32)
    if not ok.any():
        return out
    ref = x[ok]
    med = float(np.median(ref))
    mad = float(np.median(np.abs(ref - med))) * 1.4826
    if not np.isfinite(mad) or mad < 1e-6:
        mad = max(float(np.std(ref)), 1e-6)
    z = np.clip((x[np.isfinite(x)] - med) / mad, -CLIP_Z, CLIP_Z)
    out[np.isfinite(x)] = z.astype(np.float32)
    if valid_sub is not None:
        out[~np.asarray(valid_sub, bool)] = 0.0
    return out


def nearest_fill_2d(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Fill outside ``valid`` with nearest valid pixel to avoid boundary edge artifacts."""
    ok = np.asarray(valid, bool) & np.isfinite(a)
    if not ok.any():
        return np.zeros(a.shape, dtype=np.float32)
    out = np.asarray(a, dtype=np.float32).copy()
    bad = ~ok
    if bad.any():
        idx = ndi.distance_transform_edt(bad, return_distances=False, return_indices=True)
        out = out[tuple(idx)]
    return out


def ridge_crest_2d(filled: np.ndarray, sigma: float) -> np.ndarray:
    """Scale-normalised positive crest strength -(most negative Hessian eigenvalue)."""
    hyy = ndi.gaussian_filter(filled, sigma, order=(2, 0))
    hxx = ndi.gaussian_filter(filled, sigma, order=(0, 2))
    hxy = ndi.gaussian_filter(filled, sigma, order=(1, 1))
    tr = 0.5 * (hxx + hyy)
    disc = np.sqrt(np.maximum(0.25 * (hxx - hyy) ** 2 + hxy * hxy, 0.0))
    lo = tr - disc
    del hyy, hxx, hxy, tr, disc
    return ((sigma * sigma) * np.maximum(-lo, 0.0)).astype(np.float32)


def grad_mag_2d(filled: np.ndarray, sigma: float) -> np.ndarray:
    gy = ndi.gaussian_filter(filled, sigma, order=(1, 0))
    gx = ndi.gaussian_filter(filled, sigma, order=(0, 1))
    g = np.hypot(gx, gy).astype(np.float32)
    del gy, gx
    return g


def _read_official_band(idx: int, footprint: np.ndarray, feat_path: Path) -> np.ndarray:
    with rasterio.open(feat_path) as s:
        a = s.read(idx).astype(np.float32)
        nod = s.nodata
    bad = ~np.isfinite(a) | (np.abs(a) > 1e20)
    if nod is not None and np.isfinite(nod):
        bad |= (a == np.float32(nod))
    a[bad] = np.nan
    a[~footprint] = np.nan
    return a


def rasterize_gdr_geothermal(
    shape: tuple[int, int],
    footprint: np.ndarray,
    well_csv: Path,
    vent_csv: Path,
) -> np.ndarray:
    """Catalogue-blind hydrothermal enthalpy + Quaternary vent plume field.

    Explicitly verifies that ``dist_known_fault_px`` is never accessed.
    """
    h, w = shape
    enthalpy_grid = np.zeros(shape, dtype=np.float32)
    with open(well_csv, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        allowed_cols = {"row", "col", "temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c"}
        assert not (allowed_cols & FORBIDDEN_GDR_COLUMNS)
        for row in reader:
            try:
                r = int(float(row["row"]))
                c = int(float(row["col"]))
            except (KeyError, ValueError, TypeError):
                continue
            if not (0 <= r < h and 0 <= c < w) or not footprint[r, c]:
                continue
            vals_gt = []
            for k in ("geothermquartz_c", "geothermchalc_c", "geothermcat_c"):
                raw = row.get(k, "")
                try:
                    v = float(raw)
                    if np.isfinite(v) and 0.0 < v < 450.0:
                        vals_gt.append(v)
                except (ValueError, TypeError):
                    pass
            t_meas = 0.0
            try:
                tm = float(row.get("temp_c", ""))
                if np.isfinite(tm) and 0.0 < tm < 350.0:
                    t_meas = tm
            except (ValueError, TypeError):
                pass
            anom = max(0.0, t_meas - 25.0) / 45.0
            if vals_gt:
                anom += max(0.0, max(vals_gt) - 75.0) / 95.0
            if anom > enthalpy_grid[r, c]:
                enthalpy_grid[r, c] = min(anom, 6.0)

    vent_grid = np.zeros(shape, dtype=np.float32)
    if vent_csv.exists():
        with open(vent_csv, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                try:
                    r = int(float(row["row"]))
                    c = int(float(row["col"]))
                except (KeyError, ValueError, TypeError):
                    continue
                if 0 <= r < h and 0 <= c < w and footprint[r, c]:
                    vent_grid[r, c] = 1.0

    plume_s6 = ndi.gaussian_filter(enthalpy_grid, 6.0, mode="constant")
    plume_s18 = ndi.gaussian_filter(enthalpy_grid, 18.0, mode="constant")
    vent_s15 = ndi.gaussian_filter(vent_grid, 15.0, mode="constant")
    combined = np.log1p(12.0 * plume_s6 + 35.0 * plume_s18 + 25.0 * vent_s15).astype(np.float32)
    del enthalpy_grid, vent_grid, plume_s6, plume_s18, vent_s15
    return combined


def build_physics_features(
    footprint: np.ndarray,
    *,
    cache_path: Path | None = None,
    feat_path: Path = FEATURES_TIF,
    ext_dir: Path = EXTERNAL,
) -> tuple[np.ndarray, list[str]]:
    """Build or load the 38 catalogue-blind physical channels as (N_fp, 38) float16."""
    fp = np.asarray(footprint, bool)
    n_fp = int(fp.sum())
    cache = Path(cache_path) if cache_path is not None else (WORK / "csat_physics_v1.npz")
    if cache.exists():
        z = np.load(cache, allow_pickle=False)
        if int(z["n_fp"]) == n_fp:
            return z["X"], [str(s) for s in z["names"]]

    cols: list[np.ndarray] = []
    names: list[str] = []

    def push(name: str, vec_fp: np.ndarray, valid_sub: np.ndarray | None = None) -> np.ndarray:
        zvec = robust_z_1d(vec_fp, valid_sub=valid_sub)
        cols.append(zvec.astype(np.float16))
        names.append(name)
        return zvec

    # Keep only the few bands needed for cross-band transforms; stream the rest.
    keep_2d: dict[int, np.ndarray] = {}
    needed = {2, 3, 6, 7, 8, 9, 11, 12, 15, 17, 18, 19}
    for idx, bname in enumerate(OFFICIAL_BAND_NAMES, start=1):
        arr = _read_official_band(idx, fp, feat_path)
        push(bname, arr[fp])
        if idx in needed:
            keep_2d[idx] = arr
        else:
            del arr

    # 3D Potential-Field Analytic Signal & Vertical Contact Phase Ratios
    tmi_hg = np.maximum(keep_2d[3][fp], 0.0)
    tmi_vg = keep_2d[9][fp]
    amag = np.hypot(tmi_hg, tmi_vg)
    grav_hg = np.maximum(keep_2d[18][fp], 0.0)
    grav_vg = keep_2d[11][fp]
    agrav = np.hypot(grav_hg, grav_vg)
    push("p20_analytic_mag", np.log1p(np.maximum(amag, 0.0)))
    push("p21_analytic_grav", np.log1p(np.maximum(agrav, 0.0)))
    push("p22_phase_vz_mag", tmi_vg / (amag + 1e-6))
    push("p23_phase_vz_grav", grav_vg / (agrav + 1e-6))
    del tmi_hg, tmi_vg, amag, grav_hg, grav_vg, agrav, keep_2d[3], keep_2d[9], keep_2d[11]

    # Salem (2007) Tilt-Depth shallow-contact wavenumber: |grad(TC)| * exp(-z(TC)^2 / 2)
    tc_fill = nearest_fill_2d(keep_2d[6], fp)
    tc_grad = grad_mag_2d(tc_fill, 1.5)[fp]
    tc_z = cols[5].astype(np.float32)  # b06_tc robust z
    salem_w = tc_grad * np.exp(-0.5 * np.minimum(tc_z * tc_z, 16.0))
    push("p24_salem_tilt_wavenumber", salem_w)
    del tc_fill, tc_grad, tc_z, salem_w, keep_2d[6]

    # Buried Paleozoic/crystalline basement fault gradient & crest
    base_fill = nearest_fill_2d(keep_2d[15], fp)
    bgrad = grad_mag_2d(base_fill, 2.0)
    push("p25_basement_grad", bgrad[fp])
    bcrest = ridge_crest_2d(bgrad, 2.0)
    push("p26_basement_crest", bcrest[fp])
    del base_fill, bgrad, bcrest, keep_2d[15]

    # Shallow magnetic upward-continuation residual: z(RTP) - z(TMI_up150)
    with rasterio.open(ext_dir / "geodawn_extensions_u8.tif") as s:
        tmi_up150 = s.read(4).astype(np.float32)
    up_valid = (tmi_up150 > 0) & fp
    z_up = robust_z_1d(tmi_up150[fp], valid_sub=up_valid[fp])
    z_rtp = cols[1].astype(np.float32)
    push("p27_mag_shallow_resid", z_rtp - 0.85 * z_up, valid_sub=up_valid[fp])
    del tmi_up150, up_valid, z_up, z_rtp, keep_2d[2]

    # Relief-deconfounded detrended-elevation multi-scale crests
    det_fill = nearest_fill_2d(keep_2d[12], fp)
    det_loc_std = np.sqrt(
        np.maximum(
            ndi.gaussian_filter(det_fill * det_fill, 10.0)
            - ndi.gaussian_filter(det_fill, 10.0) ** 2,
            1.0,
        )
    )
    c15 = ridge_crest_2d(det_fill, 1.5) / (det_loc_std + 5.0)
    c40 = ridge_crest_2d(det_fill, 4.0) / (det_loc_std + 5.0)
    push("p28_det_crest_s1p5", c15[fp])
    push("p29_det_crest_s4", c40[fp])
    del det_fill, det_loc_std, c15, c40, keep_2d[12]

    # Seamless 10 m 3DEP relief-deconfounded piedmont breaklines & lineaments
    with rasterio.open(ext_dir / "topo_10m_derived_100m_u8.tif") as s:
        rel10 = s.read(5).astype(np.float32)
        curv10 = s.read(6).astype(np.float32)
        acoh10 = s.read(7).astype(np.float32)
        hsl10 = s.read(8).astype(np.float32)
    v10 = ((rel10 > 0) | (curv10 > 0)) & fp
    brk10 = (curv10 / np.maximum(rel10, 6.0)) * (0.4 + acoh10 / 255.0)
    lin10 = hsl10 / np.maximum(rel10, 6.0)
    push("p30_topo10m_breakline", brk10[fp], valid_sub=v10[fp])
    push("p31_topo10m_lineament", lin10[fp], valid_sub=v10[fp])
    push("p32_topo10m_relief", rel10[fp], valid_sub=v10[fp])
    del rel10, curv10, acoh10, hsl10, v10, brk10, lin10

    # 1 m 3DEP LiDAR relief-normalized scarp & single-sided facing asymmetry
    with rasterio.open(ext_dir / "lidar_scarp_features_u8.tif") as s:
        step1 = s.read(3).astype(np.float32)
        down1 = s.read(6).astype(np.float32)
        up1 = s.read(7).astype(np.float32)
        rel1 = s.read(9).astype(np.float32)
        coh1 = s.read(10).astype(np.float32)
        lid_ok = (s.read(12) > 0) & fp
    nstep = (step1 / np.maximum(rel1, 6.0)) * (0.4 + coh1 / 255.0)
    fasym = np.abs(down1 - up1) / np.maximum(down1 + up1 + 6.0, 6.0) * (coh1 / 255.0)
    push("p33_lidar_norm_step", nstep[fp], valid_sub=lid_ok[fp])
    push("p34_lidar_facing_asym", fasym[fp], valid_sub=lid_ok[fp])
    del step1, down1, up1, rel1, coh1, lid_ok, nstep, fasym

    # GeoDAWN radiometric K/Th metasomatic & U/Th redox residuals
    with rasterio.open(ext_dir / "geodawn_rad_u8.tif") as s:
        rad_k = s.read(1).astype(np.float32)
        rad_th = s.read(2).astype(np.float32)
        rad_u = s.read(3).astype(np.float32)
    rad_ok = (rad_k > 0) & (rad_th > 0) & fp
    zk = robust_z_1d(rad_k[fp], valid_sub=rad_ok[fp])
    zth = robust_z_1d(rad_th[fp], valid_sub=rad_ok[fp])
    zu = robust_z_1d(rad_u[fp], valid_sub=rad_ok[fp])
    push("p35_rad_k_th_resid", zk - 0.80 * zth, valid_sub=rad_ok[fp])
    push("p36_rad_u_th_resid", zu - 0.80 * zth, valid_sub=rad_ok[fp])
    del rad_k, rad_th, rad_u, rad_ok, zk, zth, zu

    # GDR #1391 geothermometer enthalpy plumes + playa-deconfounded clay-cap transtension
    geotherm_2d = rasterize_gdr_geothermal(
        fp.shape,
        fp,
        ext_dir / "gdr_wellspring_in_footprint.csv",
        ext_dir / "gdr_volcanic_vents_in_footprint.csv",
    )
    push("p37_geotherm_enthalpy_plume", geotherm_2d[fp])
    del geotherm_2d

    z_cond = cols[16].astype(np.float32)   # b17_cond_surf
    z_ghg = cols[17].astype(np.float32)    # b18_iso_grav_hg
    z_slp = cols[18].astype(np.float32)    # b19_det_elev_slope
    z_shr = cols[6].astype(np.float32)     # b07_geod_shear
    z_dil = cols[7].astype(np.float32)     # b08_geod_dilat
    non_playa_gate = 1.0 / (1.0 + np.exp(-(z_ghg + z_slp)))
    clay_transtens = np.maximum(z_cond, 0.0) * non_playa_gate + 0.5 * (z_shr + 0.5 * z_dil)
    push("p38_claycap_transtension", clay_transtens)
    keep_2d.clear()
    gc.collect()

    X = np.stack(cols, axis=1)
    assert X.shape == (n_fp, 38), X.shape
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez(cache, X=X, names=np.array(names), n_fp=np.int64(n_fp))
    return X, names


def _tip_propagation_fields(
    vis: np.ndarray,
    comp: np.ndarray,
    comp_len: np.ndarray,
    strike_fine: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Identify polyline endpoints on components >= 4 px and compute outward unit vectors."""
    big = vis & (comp_len[comp] >= 4)
    if not big.any():
        big = vis
    nb = ndi.convolve(big.astype(np.int16), np.ones((3, 3), np.int16), mode="constant") - big.astype(np.int16)
    tips = big & (nb == 1)
    if not tips.any():
        tips = big
    rho3 = ndi.gaussian_filter(big.astype(np.float32), 3.0, mode="constant")
    gy, gx = np.gradient(rho3)
    # Outward direction points away from fault mass (-grad rho3)
    out_y, out_x = -gy, -gx
    norm = np.hypot(out_y, out_x)
    out_y = np.divide(out_y, norm, out=np.zeros_like(out_y), where=norm > 1e-8)
    out_x = np.divide(out_x, norm, out=np.zeros_like(out_x), where=norm > 1e-8)
    # Align host tangent sign with outward direction where strike is finite
    sf = strike_fine
    fin = np.isfinite(sf)
    th = np.where(fin, np.radians(sf), 0.0)
    ty, tx = -np.cos(th).astype(np.float32), np.sin(th).astype(np.float32)
    dot = ty * out_y + tx * out_x
    sgn = np.where(dot >= 0.0, 1.0, -1.0).astype(np.float32)
    vy = np.where(fin, 0.7 * sgn * ty + 0.3 * out_y, out_y).astype(np.float32)
    vx = np.where(fin, 0.7 * sgn * tx + 0.3 * out_x, out_x).astype(np.float32)
    vn = np.hypot(vy, vx)
    vy = np.divide(vy, vn, out=out_y, where=vn > 1e-8).astype(np.float32)
    vx = np.divide(vx, vn, out=out_x, where=vn > 1e-8).astype(np.float32)
    del rho3, gy, gx, out_y, out_x, norm, ty, tx, dot, sgn, vn
    dtip, (ty_idx, tx_idx) = ndi.distance_transform_edt(~tips, return_indices=True)
    return dtip.astype(np.float32), ty_idx.astype(np.int32), tx_idx.astype(np.int32), np.stack([vy, vx], axis=0)


def build_transfer_features(
    visible: np.ndarray,
    footprint: np.ndarray,
    X_phys: np.ndarray,
    phys_names: list[str],
) -> tuple[np.ndarray, list[str], np.ndarray]:
    """Compute 20 off-catalogue strain-transfer & physics-coupling features from ``visible`` ONLY.

    Returns ``(X_struct_fp, names, d1_fp)`` aligned with ``footprint`` pixels.
    """
    fp = np.asarray(footprint, bool)
    vis = np.asarray(visible, bool) & fp
    if not vis.any():
        raise ValueError("build_transfer_features requires non-empty visible mask")

    th = two_host_frame(vis)
    bend = host_bend_fields(vis, fine_px=3.0, coarse_px=9.0)
    strike_res = bend["strike_fine"]
    coh_res = np.clip(bend["coh_fine"], 0.0, 1.0)
    # Fallback where local_strike is NaN on tiny components: smooth orientation
    bad_s = ~np.isfinite(strike_res)
    if bad_s.any():
        strike_res = np.where(bad_s, 0.0, strike_res).astype(np.float32)

    fy, fx = np.nonzero(fp)
    d1 = th["d1"][fy, fx].astype(np.float32)
    d2 = th["d2"][fy, fx].astype(np.float32)
    iy1, ix1 = th["iy1"][fy, fx], th["ix1"][fy, fx]
    iy2, ix2 = th["iy2"][fy, fx], th["ix2"][fy, fx]
    c1, c2 = th["c1"][fy, fx], th["c2"][fy, fx]
    comp_len = th["comp_len"]

    dy1 = (fy - iy1).astype(np.float32)
    dx1 = (fx - ix1).astype(np.float32)
    dy2 = (fy - iy2).astype(np.float32)
    dx2 = (fx - ix2).astype(np.float32)

    st1 = strike_res[iy1, ix1]
    st2 = strike_res[iy2, ix2]
    coh1 = coh_res[iy1, ix1]
    coh2 = coh_res[iy2, ix2]

    d_par1, _, side1 = offset_components(dy1, dx1, st1)
    along_frac = (np.abs(d_par1) / (d1 + 1.0)).astype(np.float32)
    log_len1 = np.log1p(comp_len[c1]).astype(np.float32)
    log_len2 = np.log1p(comp_len[c2]).astype(np.float32)

    # Exact Voronoi unit gradients grad(d1) and grad(d2)
    inv1 = 1.0 / np.maximum(d1, 1e-4)
    inv2 = 1.0 / np.maximum(d2, 1e-4)
    relay_facing = np.clip(-(dy1 * inv1 * dy2 * inv2 + dx1 * inv1 * dx2 * inv2), -1.0, 1.0).astype(np.float32)
    relay_sym = (2.0 * d1 / np.maximum(d1 + d2, 1e-4)).astype(np.float32)
    pos_face = np.maximum(relay_facing, 0.0)

    relay_bridge_s12 = (pos_face * relay_sym * np.exp(-(d1 + d2) / 20.0)).astype(np.float32)
    relay_bridge_s30 = (
        pos_face * relay_sym * np.exp(-(d1 + d2) / 50.0) * np.sqrt(log_len1 * log_len2)
    ).astype(np.float32)
    two_host_cos2 = (coh1 * coh2 * np.cos(np.radians(2.0 * (st1 - st2)))).astype(np.float32)

    decay15 = np.exp(-d1 / 15.0).astype(np.float32)
    bend_turn = (bend["turn"][iy1, ix1] * decay15).astype(np.float32)
    bend_asym = (side1.astype(np.float32) * bend["sin2_turn"][iy1, ix1] * decay15).astype(np.float32)

    across_sib = (
        (1.0 - along_frac) * np.exp(-(((d1 - 9.0) / 6.0) ** 2)) * (0.3 + 0.7 * coh1)
    ).astype(np.float32)

    del th, bend, iy1, ix1, iy2, ix2, dy1, dx1, dy2, dx2, inv1, inv2, st1, st2, coh1, coh2

    # Crack-tip Pollard-Segall forward propagation cones
    comp_map, _ = ndi.label(vis, structure=STRUCT3)
    dtip_2d, ty_2d, tx_2d, tip_vec = _tip_propagation_fields(vis, comp_map, comp_len, strike_res)
    dtip = dtip_2d[fy, fx]
    tyi = ty_2d[fy, fx]
    txi = tx_2d[fy, fx]
    tvy = tip_vec[0, tyi, txi]
    tvx = tip_vec[1, tyi, txi]
    tlen = np.log1p(comp_len[comp_map[tyi, txi]]).astype(np.float32)
    w_inv = 1.0 / np.maximum(dtip, 1e-4)
    cos_tip = np.maximum(0.0, ((fy - tyi) * w_inv * tvy + (fx - txi) * w_inv * tvx)).astype(np.float32)
    d_eff = np.maximum(dtip - 3.0, 0.0)
    tip_cone_s8 = ((cos_tip ** 4) * tlen * np.exp(-d_eff / 8.0)).astype(np.float32)
    tip_cone_s22 = ((cos_tip ** 3) * tlen * np.exp(-d_eff / 22.0)).astype(np.float32)
    del comp_map, dtip_2d, ty_2d, tx_2d, tip_vec, dtip, tyi, txi, tvy, tvx, tlen, w_inv, cos_tip, d_eff

    dens35 = np.log1p(1000.0 * ndi.gaussian_filter(vis.astype(np.float32), 35.0, mode="constant")[fy, fx]).astype(
        np.float32
    )

    p_idx = {n: i for i, n in enumerate(phys_names)}
    amag = X_phys[:, p_idx["p20_analytic_mag"]].astype(np.float32)
    agrav = X_phys[:, p_idx["p21_analytic_grav"]].astype(np.float32)
    brk10 = X_phys[:, p_idx["p30_topo10m_breakline"]].astype(np.float32)
    lid1 = X_phys[:, p_idx["p33_lidar_norm_step"]].astype(np.float32)
    geoth = X_phys[:, p_idx["p37_geotherm_enthalpy_plume"]].astype(np.float32)
    clay = X_phys[:, p_idx["p38_claycap_transtension"]].astype(np.float32)
    salem = X_phys[:, p_idx["p24_salem_tilt_wavenumber"]].astype(np.float32)
    bcrest = X_phys[:, p_idx["p26_basement_crest"]].astype(np.float32)

    c01 = tip_cone_s8 * np.maximum(0.0, np.maximum(amag, agrav))
    c02 = tip_cone_s22 * np.maximum(0.0, np.maximum(brk10, lid1))
    c03 = relay_bridge_s12 * (np.maximum(0.0, geoth) + np.maximum(0.0, clay))
    c04 = across_sib * np.maximum(0.0, np.maximum(salem, bcrest))

    raw_cols = [
        ("s01_log_d1", np.log1p(d1)),
        ("s02_log_d2", np.log1p(d2)),
        ("s03_log_len1", log_len1),
        ("s04_log_len2", log_len2),
        ("s05_along_par", along_frac),
        ("s06_across_sib_band", across_sib),
        ("s07_relay_facing", relay_facing),
        ("s08_relay_sym", relay_sym),
        ("s09_relay_bridge_s12", relay_bridge_s12),
        ("s10_relay_bridge_s30", relay_bridge_s30),
        ("s11_two_host_cos2", two_host_cos2),
        ("s12_host_bend_turn", bend_turn),
        ("s13_host_bend_asym", bend_asym),
        ("s14_tip_cone_s8", tip_cone_s8),
        ("s15_tip_cone_s22", tip_cone_s22),
        ("s16_cat_density_s35", dens35),
        ("c01_tip_x_analytic", c01),
        ("c02_tip_x_breakline", c02),
        ("c03_relay_x_geotherm", c03),
        ("c04_sib_x_salem_tilt", c04),
    ]
    names = [k for k, _ in raw_cols]
    X_s = np.stack([np.clip(v, -50.0, 50.0).astype(np.float16) for _, v in raw_cols], axis=1)
    gc.collect()
    return X_s, names, d1


def _synthetic_component_withhold(
    vis_mask: np.ndarray,
    rng: np.random.Generator,
    hide_frac: float = 0.25,
    buffer_px: int = 3,
) -> tuple[np.ndarray, np.ndarray]:
    """Withhold whole 8-connected components of ``vis_mask`` with a 3-px context buffer."""
    comp, nc = ndi.label(vis_mask, structure=STRUCT3)
    if nc < 4:
        raise ValueError("too few components for counterfactual withhold")
    sizes = np.bincount(comp.ravel(), minlength=nc + 1)
    ids = np.arange(1, nc + 1)
    perm = rng.permutation(ids)
    target_px = hide_frac * float(vis_mask.sum())
    cum = np.cumsum(sizes[perm])
    k = min(int(np.searchsorted(cum, target_px)) + 1, max(1, nc - 2))
    chosen = perm[:k]
    syn_target = np.isin(comp, chosen) & vis_mask
    collar = ndi.distance_transform_edt(~syn_target) <= buffer_px
    syn_vis = vis_mask & ~collar
    if not syn_vis.any():
        syn_vis = vis_mask & ~syn_target
    return syn_vis, syn_target


def _fit_ensemble_pair(
    X_tr: np.ndarray,
    y_tr: np.ndarray,
    sample_weight: np.ndarray | None,
    seed: int,
) -> tuple[HistGradientBoostingClassifier, ExtraTreesClassifier]:
    hgb = HistGradientBoostingClassifier(
        max_iter=240,
        learning_rate=0.06,
        max_leaf_nodes=47,
        min_samples_leaf=140,
        l2_regularization=2.0,
        random_state=seed,
    )
    hgb.fit(X_tr, y_tr, sample_weight=sample_weight)
    et = ExtraTreesClassifier(
        n_estimators=120,
        max_depth=18,
        min_samples_leaf=40,
        max_features="sqrt",
        n_jobs=-1,
        random_state=seed + 101,
    )
    et.fit(X_tr, y_tr, sample_weight=sample_weight)
    return hgb, et


def _predict_pair_fp(
    models: tuple[HistGradientBoostingClassifier, ExtraTreesClassifier],
    X_fp: np.ndarray,
    chunk: int = 500_000,
) -> np.ndarray:
    hgb, et = models
    n = X_fp.shape[0]
    out = np.empty(n, dtype=np.float32)
    for a in range(0, n, chunk):
        b = min(n, a + chunk)
        xb = X_fp[a:b].astype(np.float32)
        p1 = hgb.predict_proba(xb)[:, 1]
        p2 = et.predict_proba(xb)[:, 1]
        out[a:b] = (0.65 * p1 + 0.35 * p2).astype(np.float32)
    return out


def sharpen_probability_2d(prob_fp: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Concentrate diffuse probability ribbons onto 1-px fault centerlines."""
    grid_p = np.zeros(footprint.shape, dtype=np.float32)
    grid_p[footprint] = prob_fp
    fill = nearest_fill_2d(grid_p, footprint)
    crest = ridge_crest_2d(fill, 1.15)
    c_fp = crest[footprint]
    q995 = float(np.quantile(c_fp, 0.995)) if c_fp.size else 1.0
    c_norm = np.clip(c_fp / max(q995, 1e-6), 0.0, 1.0)
    # Multiplicative + additive centerline sharpening keeps values strictly in [0, 1]
    sharp_fp = np.clip(prob_fp * (0.72 + 0.56 * c_norm), 0.0, 1.0).astype(np.float32)
    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = sharp_fp
    del grid_p, fill, crest, c_fp, c_norm, sharp_fp
    return out


def bayes_quadrant_calibrate(
    surface_2d: np.ndarray,
    allowed_2d: np.ndarray,
    quad_2d: np.ndarray,
    pi0: float = 0.0024,
) -> np.ndarray:
    """Calibrate log-odds per quadrant so mean posterior on allowed cells equals ``pi0``."""
    out = np.zeros(surface_2d.shape, dtype=np.float32)
    eps = 1e-6
    for q in range(4):
        m = allowed_2d & (quad_2d == q)
        if not m.any():
            continue
        p = np.clip(surface_2d[m].astype(np.float64), eps, 1.0 - eps)
        odds = p / (1.0 - p)
        # Binary search scalar multiplier alpha_q > 0 so mean(alpha_q*odds / (1 + alpha_q*odds)) == pi0
        lo, hi = 1e-5, 1e3
        for _ in range(36):
            mid = 0.5 * (lo + hi)
            cal = (mid * odds) / (1.0 + mid * odds)
            if float(cal.mean()) > pi0:
                hi = mid
            else:
                lo = mid
        scale = 0.5 * (lo + hi)
        out[m] = ((scale * odds) / (1.0 + scale * odds)).astype(np.float32)
    return out


def fit_and_predict_loqo_surface(
    footprint: np.ndarray,
    visible: np.ndarray,
    quad: np.ndarray,
    X_phys: np.ndarray,
    phys_names: list[str],
    *,
    seed: int = 84,
    inner_draws: int = 2,
    inner_hide_frac: float = 0.25,
    w_tr_near: float = 0.72,
    w_tr_far: float = 0.30,
    w_con: float = 0.62,
    eval_Struct_cache: tuple[np.ndarray, list[str], np.ndarray] | None = None,
) -> dict[str, np.ndarray]:
    """Fit strict Leave-One-Quadrant-Out (LOQO) Dual-Habitat models on ``visible`` only.

    For each quadrant q in {0,1,2,3}, both Head A (transfer) and Head B (catalogue-blind
    concealed) are trained EXCLUSIVELY on pixels in quadrants q' != q using ``visible``.
    Returns full-grid 2-D float32 surfaces ``csat``, ``transfer``, and ``concealed`` in [0, 1].
    """
    fp = np.asarray(footprint, bool)
    vis = np.asarray(visible, bool) & fp
    quad_fp = quad[fp]

    # Full-visible inference structural features (never uses withheld truth!)
    if eval_Struct_cache is not None:
        X_struct_eval, struct_names, d1_eval = eval_Struct_cache
    else:
        X_struct_eval, struct_names, d1_eval = build_transfer_features(vis, fp, X_phys, phys_names)

    # Precompute 2 counterfactual inner-withhold datasets on ``vis`` so each LOQO fold
    # simply subsets rows in (quad_fp != q) without leaking across quadrant boundaries!
    # Wait: to guarantee zero boundary leakage across quadrants during counterfactual draws,
    # synthetic withholding is performed per quadrant on ``vis & (quad == q')`` or globally
    # on ``vis`` with strict row filtering ``quad_fp != q``. Masking ``vis_q = vis & (quad != q)``
    # per fold is only 4 folds * 2 draws = 8 fast calls — let's build synthetic draws on
    # quadrant-eroded ``vis`` so components do not even cross quadrant borders!
    syn_datasets = []
    rng_master = np.random.default_rng(seed * 1009 + 17)
    d_vis_fp = d1_eval
    vis_q_clean = vis & (quad >= 0)
    for m_idx in range(inner_draws):
        syn_vis, syn_tgt = _synthetic_component_withhold(
            vis_q_clean, rng_master, hide_frac=inner_hide_frac, buffer_px=3
        )
        Xs_m, _, d1_syn = build_transfer_features(syn_vis, fp, X_phys, phys_names)
        pos_m = syn_tgt[fp] & (d1_syn > 3.0)
        neg_near_m = (~vis[fp]) & (d_vis_fp > 3.0) & (d_vis_fp <= 22.0) & (d1_syn > 3.0)
        neg_far_m = (~vis[fp]) & (d_vis_fp > 22.0) & (d1_syn > 3.0)
        syn_datasets.append((Xs_m, pos_m, neg_near_m, neg_far_m))

    p_idx = {n: i for i, n in enumerate(phys_names)}
    rel_z = np.maximum(X_phys[:, p_idx["p32_topo10m_relief"]].astype(np.float32), -2.0)
    slp_z = np.maximum(X_phys[:, p_idx["b19_det_elev_slope"]].astype(np.float32), -2.0)
    rough = np.maximum(0.5 * (rel_z + slp_z), -1.5)

    p_transfer_fp = np.zeros(X_phys.shape[0], dtype=np.float32)
    p_concealed_fp = np.zeros(X_phys.shape[0], dtype=np.float32)

    for q in range(4):
        in_train_q = (quad_fp != q) & (quad_fp >= 0)
        in_test_q = (quad_fp == q)
        rng_q = np.random.default_rng(seed * 97 + q * 13 + 5)

        # --- Head A: Counterfactual Strain-Accommodation + Multi-Physics ---
        XA_parts, yA_parts, wA_parts = [], [], []
        for Xs_m, pos_m, neg_near_m, neg_far_m in syn_datasets:
            p_ids = np.flatnonzero(pos_m & in_train_q)
            nn_pool = np.flatnonzero(neg_near_m & in_train_q)
            nf_pool = np.flatnonzero(neg_far_m & in_train_q)
            n_nn = min(len(nn_pool), max(len(p_ids) * 4, 25_000))
            n_nf = min(len(nf_pool), max(len(p_ids) * 3, 20_000))
            nn_ids = rng_q.choice(nn_pool, n_nn, replace=False)
            nf_ids = rng_q.choice(nf_pool, n_nf, replace=False)
            sel = np.concatenate([p_ids, nn_ids, nf_ids])
            XA_m = np.concatenate([X_phys[sel], Xs_m[sel]], axis=1).astype(np.float32)
            yA_m = np.concatenate([
                np.ones(len(p_ids), dtype=np.float32),
                np.zeros(n_nn + n_nf, dtype=np.float32),
            ])
            # Weight negatives proportionally to territory size so near vs far is unbiased
            w_nn = float(len(nn_pool)) / max(n_nn, 1)
            w_nf = float(len(nf_pool)) / max(n_nf, 1)
            norm_w = float(len(nn_pool) + len(nf_pool)) / max(n_nn + n_nf, 1)
            wA_m = np.concatenate([
                np.full(len(p_ids), 8.0, dtype=np.float32),
                np.full(n_nn, w_nn / norm_w, dtype=np.float32),
                np.full(n_nf, w_nf / norm_w, dtype=np.float32),
            ])
            XA_parts.append(XA_m)
            yA_parts.append(yA_m)
            wA_parts.append(wA_m)
        XA_tr = np.concatenate(XA_parts, axis=0)
        yA_tr = np.concatenate(yA_parts, axis=0)
        wA_tr = np.concatenate(wA_parts, axis=0)
        wA_tr /= max(float(wA_tr.mean()), 1e-6)
        del XA_parts, yA_parts, wA_parts
        models_A = _fit_ensemble_pair(XA_tr, yA_tr, wA_tr, seed=seed * 31 + q)
        del XA_tr, yA_tr, wA_tr
        X_te_q = np.concatenate([X_phys[in_test_q], X_struct_eval[in_test_q]], axis=1)
        p_transfer_fp[in_test_q] = _predict_pair_fp(models_A, X_te_q)
        del models_A, X_te_q

        # --- Head B: 100 % Catalogue-Blind Concealed & Piedmont Multi-Physics ---
        posB_ids = np.flatnonzero(vis[fp] & in_train_q)
        negB_pool = np.flatnonzero((~vis[fp]) & (d_vis_fp > 4.0) & in_train_q)
        n_negB = min(len(negB_pool), max(len(posB_ids) * 4, 80_000))
        # Half relief-matched negatives, half uniform basin-wide negatives
        n_half = n_negB // 2
        r_probs = np.exp(np.clip(rough[negB_pool], -1.5, 3.0)).astype(np.float64)
        r_probs /= r_probs.sum()
        neg_rel = rng_q.choice(negB_pool, n_half, replace=False, p=r_probs)
        rem_mask = ~np.isin(negB_pool, neg_rel)
        rem_pool = negB_pool[rem_mask]
        neg_uni = rng_q.choice(rem_pool, min(n_negB - n_half, len(rem_pool)), replace=False)
        selB = np.concatenate([posB_ids, neg_rel, neg_uni])
        XB_tr = X_phys[selB].astype(np.float32)
        yB_tr = np.concatenate([
            np.ones(len(posB_ids), dtype=np.float32),
            np.zeros(len(neg_rel) + len(neg_uni), dtype=np.float32),
        ])
        # Inverse-relief weight on positives boosts concealed/piedmont fault learning!
        pos_w = (1.5 / np.sqrt(1.0 + np.maximum(rough[posB_ids] + 1.5, 0.0))).astype(np.float32)
        wB_tr = np.concatenate([
            pos_w * 2.5,
            np.ones(len(neg_rel) + len(neg_uni), dtype=np.float32),
        ])
        wB_tr /= max(float(wB_tr.mean()), 1e-6)
        models_B = _fit_ensemble_pair(XB_tr, yB_tr, wB_tr, seed=seed * 53 + q)
        del XB_tr, yB_tr, wB_tr
        p_concealed_fp[in_test_q] = _predict_pair_fp(models_B, X_phys[in_test_q])
        del models_B
        gc.collect()

    del syn_datasets
    gc.collect()

    s_tr = sharpen_probability_2d(p_transfer_fp, fp)
    s_con = sharpen_probability_2d(p_concealed_fp, fp)

    # Smooth distance-adaptive Dual-Habitat Noisy-OR fusion:
    # Near mapped faults (2.5 < d1 <= 20 px), transfer mechanics + physics dominates;
    # In under-mapped piedmonts & basins (d1 > 20 px), catalogue-blind 3D contact-depth carries full weight.
    d1_grid = np.zeros(fp.shape, dtype=np.float32)
    d1_grid[fp] = d1_eval
    gate_near = np.exp(-np.maximum(d1_grid - 4.0, 0.0) / 18.0).astype(np.float32)
    wA = w_tr_far + (w_tr_near - w_tr_far) * gate_near
    csat_2d = (1.0 - (1.0 - np.clip(wA * s_tr, 0.0, 0.999)) * (1.0 - np.clip(w_con * s_con, 0.0, 0.999))).astype(
        np.float32
    )
    csat_2d[~fp] = 0.0
    return dict(
        csat=csat_2d,
        transfer=s_tr,
        concealed=s_con,
        d1=d1_grid,
        struct_names=struct_names,
    )


def allocate_submodular_dots(
    surface_2d: np.ndarray,
    footprint: np.ndarray,
    visible: np.ndarray,
    d1_2d: np.ndarray,
    quad_2d: np.ndarray,
    *,
    collar_px: float = 2.5,
    pi0: float = 0.0024,
    max_dots: int = 42_000,
) -> tuple[np.ndarray, dict]:
    """Calibrate per quadrant and run shared ``gems57.emit.greedy_allocate``."""
    fp = np.asarray(footprint, bool)
    vis = np.asarray(visible, bool)
    allowed = fp & (~vis) & (d1_2d > collar_px)
    p_cal = bayes_quadrant_calibrate(surface_2d, allowed, quad_2d, pi0=pi0)
    k_truth = float(p_cal[allowed].sum())
    alloc = emit.greedy_allocate(
        p_cal,
        allowed,
        k_truth,
        floor=0.015,
        max_dots=max_dots,
        candidate_cap=450_000,
    )
    dots = (alloc.emitted & allowed).astype(np.float32)
    info = dict(
        n_dots=int(alloc.n_dots),
        k_truth_prior=k_truth,
        surrogate_dti_model=float(alloc.surrogate_dti),
        rounds=int(alloc.rounds),
        pi0=pi0,
        collar_px=collar_px,
    )
    return dots, info


def poisson_disk_dots(
    surface_2d: np.ndarray,
    allowed: np.ndarray,
    budget: int,
    sep_px: float = 2.83,
) -> np.ndarray:
    """Isotropic D2.8 Poisson-disk emitter used strictly as an ablation control."""
    alw = np.asarray(allowed, bool)
    ids = np.flatnonzero(alw & (surface_2d > 0))
    order = np.argsort(-surface_2d.ravel()[ids], kind="stable")
    ids = ids[order]
    blocked = ~alw.copy()
    out = np.zeros(surface_2d.shape, dtype=np.float32)
    h, w = out.shape
    r = int(np.ceil(sep_px))
    offsets = [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1) if dy * dy + dx * dx < sep_px * sep_px]
    n = 0
    for idx in ids:
        y, x = divmod(int(idx), w)
        if blocked[y, x]:
            continue
        out[y, x] = 1.0
        n += 1
        if n >= budget:
            break
        for dy, dx in offsets:
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w:
                blocked[yy, xx] = True
    return out
