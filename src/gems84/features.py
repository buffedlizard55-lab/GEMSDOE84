"""Feature engineering for Lane H84-THMS (GEMSDOE84).

72 strictly label-free physical / THM / 2m-probe / paleo-sinter / 10m-3DEP breakline /
fluvial-chi / up-dip advection / radiometric / 1m-LiDAR channels
+ 24 fold-proper visible-catalogue structural-relay, wing-crack & THM-coupling channels
(= 96 total channels).

Strict leakage & provenance invariants:
  1. Never reads `labels.tif`, `hidden`, `truth`, `dist_known_fault_px`, or SGMC fault rasters.
  2. Cold-cache capable: builds all 72 physical channels directly from `training_features.tif`
     and `external/` in a memory-bounded streaming pass (< 1.1 GB peak RSS), fixing the
     `IR-84-01` cold-cache RuntimeError stub found in GEMSDOE83.
  3. Bridges the 24.60% 1 m USGS 3DEP LiDAR coverage gap seamlessly using 100%-coverage
     10 m USGS 3DEP breaklines (`topo_10m_derived_100m_u8.tif`) and 10 m fluvial chi/knickpoint
     layers (`dem10_chi_100m_i16.tif`, `dem10_chi_100m_u8.tif`).
"""
from __future__ import annotations

import csv
import gc
import io
import struct
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import rasterio
from rasterio.warp import transform as rio_transform
from scipy import ndimage as ndi
from scipy.signal import oaconvolve

FORBIDDEN_COLUMNS = frozenset({"dist_known_fault_px", "known_fault", "label"})

TRAINING_BAND_NAMES: Tuple[str, ...] = (
    "mag_anomaly_deviation",
    "mag_reduced_to_pole",
    "tmi_horizontal_gradient",
    "geodetic_second_invariant",
    "iso_gravity_slope",
    "tilt_angle_total_curvature",
    "geodetic_shear_rate",
    "geodetic_dilatation_rate",
    "tmi_vertical_gradient",
    "distance_to_earthquake",
    "iso_gravity_vertical_gradient",
    "detrended_elevation",
    "iso_gravity_anomaly",
    "total_magnetic_intensity",
    "depth_to_basement",
    "earthquake_density",
    "conductivity_surface",
    "iso_gravity_horizontal_gradient",
    "detrended_elevation_slope",
)

PHYSICAL_CHANNEL_NAMES: Tuple[str, ...] = (
    # 19 standardized official bands
    "z_mag_anomaly_deviation",
    "z_mag_reduced_to_pole",
    "z_tmi_horizontal_gradient",
    "z_geodetic_second_invariant",
    "z_iso_gravity_slope",
    "z_tilt_angle_total_curvature",
    "z_geodetic_shear_rate",
    "z_geodetic_dilatation_rate",
    "z_tmi_vertical_gradient",
    "z_distance_to_earthquake",
    "z_iso_gravity_vertical_gradient",
    "z_detrended_elevation",
    "z_iso_gravity_anomaly",
    "z_total_magnetic_intensity",
    "z_depth_to_basement",
    "z_earthquake_density",
    "z_conductivity_surface",
    "z_iso_gravity_horizontal_gradient",
    "z_detrended_elevation_slope",
    # 8 first-derivative gradients
    "grad_mag_reduced_to_pole",
    "grad_tilt_angle_total_curvature",
    "grad_detrended_elevation",
    "grad_iso_gravity_anomaly",
    "grad_total_magnetic_intensity",
    "grad_depth_to_basement",
    "grad_conductivity_surface",
    "grad_detrended_elevation_slope",
    # 6 Laplacians
    "lap_tilt_angle_total_curvature",
    "lap_detrended_elevation",
    "lap_iso_gravity_anomaly",
    "lap_total_magnetic_intensity",
    "lap_depth_to_basement",
    "lap_conductivity_surface",
    # 8 Hessian across-strike ridges
    "ridge_mag_reduced_to_pole",
    "ridge_tilt_angle_total_curvature",
    "ridge_detrended_elevation",
    "ridge_iso_gravity_anomaly",
    "ridge_total_magnetic_intensity",
    "ridge_depth_to_basement",
    "ridge_conductivity_surface",
    "ridge_detrended_elevation_slope",
    # 4 multi-scale 5-px texture channels
    "std5_tilt_angle_total_curvature",
    "std5_detrended_elevation",
    "std5_total_magnetic_intensity",
    "std5_conductivity_surface",
    # 15 core multi-physics, geothermal, radiometric & 1m LiDAR channels
    "x_couple_tmi_dem",
    "x_couple_tmi_grav",
    "x_ridge_dem_slope",
    "x_strain_transtension",
    "geotherm_vent_plume_s6",
    "geotherm_vent_plume_s18",
    "geotherm_reservoir_enthalpy",
    "geotherm_claycap_conduit",
    "rad_k_metasomatism",
    "rad_u_redox_halo",
    "rad_tc_grad",
    "mag_shallow_residual",
    "mag_shallow_ridge",
    "lidar_relief_norm_scarp",
    "lidar_scarp_coherence",
    # 12 novel H84-THMS channels
    "thm_paleo_sinter_seal_s8",
    "thm_paleo_sinter_seal_s20",
    "thm_probe2m_upward_flux",
    "thm_silica_valve_breach",
    "thm_topo10_breakline_ridge",
    "thm_topo10_aspect_coherence",
    "thm_fluvial_chi_step",
    "thm_fluvial_knickpoint_density",
    "thm_seamless_scarp_chi",
    "thm_updip_grav_basement",
    "thm_updip_mag_demag",
    "thm_updip_scarp_concordance",
)

H84_NOVEL_PHYSICAL_NAMES: Tuple[str, ...] = PHYSICAL_CHANNEL_NAMES[-12:]

STRUCTURAL_NETWORK_NAMES: Tuple[str, ...] = (
    "ns_logdist",
    "ns_den4",
    "ns_den12",
    "ns_den32",
    "ns_cont",
    "ns_gap",
    "ns_sib",
    "ns_cont_max",
    "ns_sib_max",
    "ns_coh",
    "net_beam_short",
    "net_beam_med",
    "net_beam_long",
    "net_bridge_med",
    "net_bridge_long",
    "net_tip_ray",
    "net_ann_near",
    "net_ann_far",
)

COUPLING_INTERACTION_NAMES: Tuple[str, ...] = (
    "coup_geotherm_tip",
    "coup_geotherm_gap",
    "coup_lidar_cont",
    "coup_strain_sib",
    "coup_thm_valve_bridge",
    "coup_seamless_scarp_beam",
)

STRUCT8 = np.ones((3, 3), dtype=bool)
N_STRIKE_BINS = 12
R_KERNEL = 25


def physical_channel_names() -> List[str]:
    return list(PHYSICAL_CHANNEL_NAMES)


def all_channel_names() -> List[str]:
    return physical_channel_names() + list(STRUCTURAL_NETWORK_NAMES) + list(COUPLING_INTERACTION_NAMES)


def _robust_z_flat(vec: np.ndarray) -> np.ndarray:
    v = np.asarray(vec, dtype=np.float32)
    finite = np.isfinite(v)
    if not finite.any():
        return np.zeros_like(v, dtype=np.float32)
    med = float(np.median(v[finite]))
    mad = float(np.median(np.abs(v[finite] - med)))
    scale = max(1.4826 * mad, float(np.std(v[finite])), 1e-6)
    out = np.where(finite, (v - med) / scale, 0.0)
    return np.clip(out, -8.0, 8.0).astype(np.float32)


def _fill_band(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    out = arr.astype(np.float32, copy=True)
    bad = ~np.isfinite(out) | (np.abs(out) > 1e20)
    valid_fp = footprint & ~bad
    med = float(np.median(out[valid_fp])) if valid_fp.any() else 0.0
    out[bad] = med
    out[~footprint] = med
    return out


def _grad_mag(a: np.ndarray) -> np.ndarray:
    gy, gx = np.gradient(a.astype(np.float32))
    return np.hypot(gx, gy).astype(np.float32)


def _laplace(a: np.ndarray) -> np.ndarray:
    return ndi.laplace(a.astype(np.float32), mode="nearest").astype(np.float32)


def _hessian_ridge(a: np.ndarray) -> np.ndarray:
    """Across-strike second-derivative principal curvature magnitude (Blakely & Simpson, 1986)."""
    f = ndi.gaussian_filter(a.astype(np.float32), sigma=1.0, mode="nearest")
    dyy = ndi.correlate(f, np.array([[1.0, -2.0, 1.0]], dtype=np.float32), mode="nearest")
    dxx = ndi.correlate(f, np.array([[1.0], [-2.0], [1.0]], dtype=np.float32), mode="nearest")
    dxy = ndi.correlate(
        f,
        np.array([[1.0, 0.0, -1.0], [0.0, 0.0, 0.0], [-1.0, 0.0, 1.0]], dtype=np.float32) * 0.25,
        mode="nearest",
    )
    tr = 0.5 * (dxx + dyy)
    det = dxx * dyy - dxy * dxy
    disc = np.sqrt(np.maximum(tr * tr - det, 0.0))
    lam1 = tr + disc
    lam2 = tr - disc
    return np.where(np.abs(lam1) >= np.abs(lam2), np.abs(lam1), np.abs(lam2)).astype(np.float32)


def _local_std(a: np.ndarray, sigma: float = 5.0) -> np.ndarray:
    f = a.astype(np.float32)
    m = ndi.gaussian_filter(f, sigma=sigma, mode="nearest")
    m2 = ndi.gaussian_filter(f * f, sigma=sigma, mode="nearest")
    return np.sqrt(np.maximum(m2 - m * m, 0.0)).astype(np.float32)


def _advect_updip_2d(field: np.ndarray, vy: np.ndarray, vx: np.ndarray, step_px: float = 2.0) -> np.ndarray:
    """Sample `field` at `(r + step_px * vy, c + step_px * vx)` to project hanging-wall
    subsurface steps back up-dip to the surface fault trace `(r, c)`."""
    H, W = field.shape
    rr, cc = np.indices((H, W), dtype=np.float32)
    rq = np.clip(rr + np.float32(step_px) * vy, 0.0, float(H - 1))
    cq = np.clip(cc + np.float32(step_px) * vx, 0.0, float(W - 1))
    return ndi.map_coordinates(field.astype(np.float32), [rq, cq], order=1, mode="nearest").astype(np.float32)


def _rasterize_geothermal_thm_and_vents(
    raw_dir: Path, shape: Tuple[int, int], transform, footprint: np.ndarray
) -> Dict[str, np.ndarray]:
    """Rasterize DOE GDR #1391 thermal wells/springs, chemical geothermometers,
    Quaternary volcanic vents, 709 paleo-geothermal sinter/travertine fault seals,
    and 3,800 shallow 2m temperature probe measurements.
    Strictly blocks any forbidden label-derived columns.
    """
    H, W = shape
    x0 = float(transform.c)
    dx = float(transform.a)
    y0 = float(transform.f)
    dy = float(transform.e)

    temp_grid = np.zeros((H, W), dtype=np.float32)
    qtz_grid = np.zeros((H, W), dtype=np.float32)
    chal_grid = np.zeros((H, W), dtype=np.float32)
    cat_grid = np.zeros((H, W), dtype=np.float32)

    ws_path = raw_dir / "external" / "gdr_wellspring_in_footprint.csv"
    if ws_path.exists():
        with ws_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            safe_cols = [c for c in (reader.fieldnames or []) if c not in FORBIDDEN_COLUMNS]
            assert "dist_known_fault_px" not in safe_cols
            for row in reader:
                try:
                    if "row" in row and "col" in row and row["row"] != "" and row["col"] != "":
                        r = int(float(row["row"]))
                        col = int(float(row["col"]))
                    else:
                        ux = float(row.get("utm_x") or row["utm_e"])
                        uy = float(row.get("utm_y") or row["utm_n"])
                        col = int((ux - x0) / dx)
                        r = int((uy - y0) / dy)
                except (KeyError, ValueError):
                    continue
                if not (0 <= r < H and 0 <= col < W):
                    continue
                try:
                    tc = float(row.get("temp_c", "") or "nan")
                    if np.isfinite(tc) and 15.0 < tc < 400.0:
                        ex = max(0.0, tc - 15.0)
                        if ex > temp_grid[r, col]:
                            temp_grid[r, col] = ex
                except ValueError:
                    pass
                for keys, grid_arr in (
                    (("geothermquartz_c", "gt_quartz_c"), qtz_grid),
                    (("geothermchalc_c", "gt_chalcedony_c"), chal_grid),
                    (("geothermcat_c", "gt_na_k_ca_c"), cat_grid),
                ):
                    raw_val = ""
                    for k in keys:
                        if row.get(k):
                            raw_val = row[k]
                            break
                    if not raw_val:
                        continue
                    try:
                        val = float(raw_val)
                        if np.isfinite(val) and 25.0 < val < 450.0:
                            ex = max(0.0, val - 25.0)
                            if ex > grid_arr[r, col]:
                                grid_arr[r, col] = ex
                    except ValueError:
                        pass

    vent_grid = np.zeros((H, W), dtype=np.float32)
    vv_path = raw_dir / "external" / "gdr_volcanic_vents_in_footprint.csv"
    if vv_path.exists():
        with vv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            safe_vcols = [c for c in (reader.fieldnames or []) if c not in FORBIDDEN_COLUMNS]
            assert "dist_known_fault_px" not in safe_vcols
            for row in reader:
                try:
                    if "row" in row and "col" in row and row["row"] != "" and row["col"] != "":
                        r = int(float(row["row"]))
                        col = int(float(row["col"]))
                    else:
                        ux = float(row.get("utm_x") or row["utm_e"])
                        uy = float(row.get("utm_y") or row["utm_n"])
                        col = int((ux - x0) / dx)
                        r = int((uy - y0) / dy)
                except (KeyError, ValueError):
                    continue
                if 0 <= r < H and 0 <= col < W:
                    vent_grid[r, col] += 1.0

    # Paleo-geothermal sinter, travertine & silicified fault breccia seals (709 records)
    paleo_grid = np.zeros((H, W), dtype=np.float32)
    paleo_zip = raw_dir / "external" / "paleo_geothermal_regional.zip"
    if paleo_zip.exists():
        with zipfile.ZipFile(paleo_zip) as zf:
            txt = zf.read("Paleo_geothermal_final.csv").decode("latin1", errors="replace")
            prows = list(csv.DictReader(io.StringIO(txt)))
        lons, lats, weights = [], [], []
        for row in prows:
            try:
                lon = float(row["Long_deg_NAD83"])
                lat = float(row["Lat_deg_NAD83"])
            except (KeyError, ValueError):
                continue
            dtype = (row.get("Deposit_type", "") or "").lower()
            w = 1.5 if ("sinter" in dtype or "silic" in dtype or "travertine" in dtype) else 1.0
            lons.append(lon)
            lats.append(lat)
            weights.append(w)
        if lons:
            xs, ys = rio_transform("EPSG:4269", "EPSG:32611", lons, lats)
            for ux, uy, w in zip(xs, ys, weights):
                col = int((ux - x0) / dx)
                r = int((uy - y0) / dy)
                if 0 <= r < H and 0 <= col < W:
                    paleo_grid[r, col] += float(w)

    # 2m shallow temperature probe upward heat-flux survey (3,800 records)
    probe_grid = np.zeros((H, W), dtype=np.float32)
    probe_zip = raw_dir / "external" / "2m_temperature_probe_INGENIOUS_regional_data.zip"
    if probe_zip.exists():
        with zipfile.ZipFile(probe_zip) as zf:
            dbf = zf.read("2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf")
        numrec, lenheader, lenrecord = struct.unpack("<4xIHH20x", dbf[:32])
        fields = []
        off = 32
        while off < lenheader - 1 and dbf[off] != 0x0D:
            name = dbf[off : off + 11].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
            flen = dbf[off + 16]
            fields.append((name, flen))
            off += 32
        pos = lenheader
        for _ in range(numrec):
            rec = dbf[pos : pos + lenrecord]
            pos += lenrecord
            if not rec or rec[0] == 0x2A:
                continue
            d = {}
            foff = 1
            for name, flen in fields:
                if name not in FORBIDDEN_COLUMNS:
                    d[name] = rec[foff : foff + flen].decode("latin1", errors="ignore").strip()
                foff += flen
            try:
                ux = float(d.get("UTM_E", "") or "nan")
                uy = float(d.get("UTM_N", "") or "nan")
            except ValueError:
                continue
            if not (np.isfinite(ux) and np.isfinite(uy)):
                continue
            col = int((ux - x0) / dx)
            r = int((uy - y0) / dy)
            if not (0 <= r < H and 0 <= col < W):
                continue
            try:
                f2m = float(d.get("F2mDAB", "") or "0")
            except ValueError:
                f2m = 0.0
            try:
                t2m = float(d.get("T2m", "") or "nan")
            except ValueError:
                t2m = np.nan
            try:
                t15m = float(d.get("T15m", "") or "nan")
            except ValueError:
                t15m = np.nan
            up_grad = max(0.0, t2m - t15m) if (np.isfinite(t2m) and np.isfinite(t15m) and t15m > 0) else 0.0
            anom = max(0.0, f2m) + 0.5 * up_grad + (max(0.0, t2m - 20.0) * 0.25 if np.isfinite(t2m) else 0.0)
            if anom > probe_grid[r, col]:
                probe_grid[r, col] = float(anom)

    vent_plume_s6 = _robust_z_flat(
        np.log1p(ndi.gaussian_filter(temp_grid + 2.0 * vent_grid, sigma=6.0)[footprint])
    )
    vent_plume_s18 = _robust_z_flat(
        np.log1p(ndi.gaussian_filter(temp_grid + 2.0 * vent_grid, sigma=18.0)[footprint])
    )
    q_s10 = _robust_z_flat(np.log1p(ndi.gaussian_filter(qtz_grid, sigma=10.0)[footprint]))
    ch_s12 = _robust_z_flat(np.log1p(ndi.gaussian_filter(chal_grid, sigma=12.0)[footprint]))
    ca_s12 = _robust_z_flat(np.log1p(ndi.gaussian_filter(cat_grid, sigma=12.0)[footprint]))
    enthalpy = _robust_z_flat(0.45 * q_s10 + 0.30 * ch_s12 + 0.25 * ca_s12)

    paleo_s8 = _robust_z_flat(np.log1p(ndi.gaussian_filter(paleo_grid, sigma=8.0)[footprint]))
    paleo_s20 = _robust_z_flat(np.log1p(ndi.gaussian_filter(paleo_grid, sigma=20.0)[footprint]))
    probe_s10 = _robust_z_flat(np.log1p(ndi.gaussian_filter(probe_grid, sigma=10.0)[footprint]))

    del temp_grid, qtz_grid, chal_grid, cat_grid, vent_grid, paleo_grid, probe_grid
    gc.collect()
    return {
        "geotherm_vent_plume_s6": vent_plume_s6,
        "geotherm_vent_plume_s18": vent_plume_s18,
        "geotherm_reservoir_enthalpy": enthalpy,
        "thm_paleo_sinter_seal_s8": paleo_s8,
        "thm_paleo_sinter_seal_s20": paleo_s20,
        "thm_probe2m_upward_flux": probe_s10,
    }


def load_or_build_rowmajor_f16(
    raw_dir: Path, footprint: np.ndarray, proc_dir: Path
) -> Tuple[List[str], np.ndarray]:
    """Return `(names, X_rm_f16)` where `X_rm_f16` has shape `(n_fp, 72)`.
    Streams directly from `training_features.tif` and `external/` on a cold cache.
    """
    names = physical_channel_names()
    n_ch = len(names)
    n_px = int(footprint.sum())
    proc_dir.mkdir(parents=True, exist_ok=True)
    rm_path = proc_dir / "h84_phys_rm.f16.npy"
    meta_path = proc_dir / "h84_phys_rm.names.txt"

    if rm_path.exists() and meta_path.exists():
        cached_names = [line.strip() for line in meta_path.read_text().splitlines() if line.strip()]
        if cached_names == names:
            mm = np.load(rm_path, mmap_mode="r")
            if mm.shape == (n_px, n_ch):
                return names, mm

    H, W = footprint.shape
    col_path = proc_dir / "h84_phys_col.f16.npy"
    mm_col = np.lib.format.open_memmap(col_path, mode="w+", dtype=np.float16, shape=(n_ch, n_px))
    col_idx = {nm: i for i, nm in enumerate(names)}

    def _write_col(nm: str, vec_fp: np.ndarray) -> None:
        mm_col[col_idx[nm], :] = np.nan_to_num(vec_fp, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float16)

    # Pass 1: Official 19-band training_features.tif
    tf_path = raw_dir / "training_features.tif"
    kept_bands: Dict[str, np.ndarray] = {}
    keep_set = {
        "mag_reduced_to_pole",
        "geodetic_second_invariant",
        "tilt_angle_total_curvature",
        "geodetic_shear_rate",
        "geodetic_dilatation_rate",
        "detrended_elevation",
        "iso_gravity_anomaly",
        "total_magnetic_intensity",
        "depth_to_basement",
        "conductivity_surface",
        "iso_gravity_horizontal_gradient",
        "detrended_elevation_slope",
    }
    with rasterio.open(tf_path) as ds:
        transform = ds.transform
        for b_idx, b_name in enumerate(TRAINING_BAND_NAMES, start=1):
            arr = _fill_band(ds.read(b_idx), footprint)
            z_fp = _robust_z_flat(arr[footprint])
            _write_col(f"z_{b_name}", z_fp)
            if b_name in keep_set:
                kept_bands[b_name] = arr
            else:
                del arr

    # Derivatives on kept bands
    grad_targets = (
        "mag_reduced_to_pole",
        "tilt_angle_total_curvature",
        "detrended_elevation",
        "iso_gravity_anomaly",
        "total_magnetic_intensity",
        "depth_to_basement",
        "conductivity_surface",
        "detrended_elevation_slope",
    )
    grad_fp_cache: Dict[str, np.ndarray] = {}
    for b_name in grad_targets:
        g_arr = _grad_mag(kept_bands[b_name])
        z_g = _robust_z_flat(g_arr[footprint])
        _write_col(f"grad_{b_name}", z_g)
        if b_name in ("conductivity_surface", "depth_to_basement", "mag_reduced_to_pole"):
            grad_fp_cache[b_name] = g_arr
        else:
            del g_arr

    lap_targets = (
        "tilt_angle_total_curvature",
        "detrended_elevation",
        "iso_gravity_anomaly",
        "total_magnetic_intensity",
        "depth_to_basement",
        "conductivity_surface",
    )
    for b_name in lap_targets:
        l_arr = _laplace(kept_bands[b_name])
        _write_col(f"lap_{b_name}", _robust_z_flat(l_arr[footprint]))
        del l_arr

    ridge_fp_cache: Dict[str, np.ndarray] = {}
    for b_name in grad_targets:
        r_arr = _hessian_ridge(kept_bands[b_name])
        z_r = _robust_z_flat(r_arr[footprint])
        _write_col(f"ridge_{b_name}", z_r)
        if b_name == "detrended_elevation":
            ridge_fp_cache[b_name] = z_r
        del r_arr

    std5_targets = (
        "tilt_angle_total_curvature",
        "detrended_elevation",
        "total_magnetic_intensity",
        "conductivity_surface",
    )
    for b_name in std5_targets:
        s_arr = _local_std(kept_bands[b_name], sigma=5.0)
        _write_col(f"std5_{b_name}", _robust_z_flat(s_arr[footprint]))
        del s_arr

    # Cross-sensor & geomechanical interactions
    z_tmi = np.asarray(mm_col[col_idx["z_total_magnetic_intensity"], :], dtype=np.float32)
    z_dem = np.asarray(mm_col[col_idx["z_detrended_elevation"], :], dtype=np.float32)
    z_grav = np.asarray(mm_col[col_idx["z_iso_gravity_anomaly"], :], dtype=np.float32)
    z_slp = np.asarray(mm_col[col_idx["z_detrended_elevation_slope"], :], dtype=np.float32)
    z_dil = np.asarray(mm_col[col_idx["z_geodetic_dilatation_rate"], :], dtype=np.float32)
    z_shr = np.asarray(mm_col[col_idx["z_geodetic_shear_rate"], :], dtype=np.float32)
    z_inv = np.asarray(mm_col[col_idx["z_geodetic_second_invariant"], :], dtype=np.float32)

    _write_col("x_couple_tmi_dem", _robust_z_flat(z_tmi * z_dem))
    _write_col("x_couple_tmi_grav", _robust_z_flat(z_tmi * z_grav))
    _write_col("x_ridge_dem_slope", _robust_z_flat(ridge_fp_cache["detrended_elevation"] * z_slp))
    transtension_fp = _robust_z_flat(np.maximum(z_dil, -0.5) * np.maximum(z_shr, 0.0) + 0.5 * z_shr * z_inv)
    _write_col("x_strain_transtension", transtension_fp)
    del z_tmi, z_dem, z_grav, z_slp, z_dil, z_shr, z_inv, ridge_fp_cache
    gc.collect()

    # Pass 2: Geothermal wells/springs, 2m probes, paleo-sinter seals & volcanic vents
    geo_dict = _rasterize_geothermal_thm_and_vents(raw_dir, (H, W), transform, footprint)
    for k_nm, vec_fp in geo_dict.items():
        _write_col(k_nm, vec_fp)

    z_cond_grad = np.asarray(mm_col[col_idx["grad_conductivity_surface"], :], dtype=np.float32)
    z_cond = np.asarray(mm_col[col_idx["z_conductivity_surface"], :], dtype=np.float32)
    claycap_fp = _robust_z_flat(
        0.50 * geo_dict["geotherm_reservoir_enthalpy"]
        + 0.30 * z_cond_grad
        + 0.20 * z_cond
    )
    _write_col("geotherm_claycap_conduit", claycap_fp)

    valve_breach_fp = _robust_z_flat(
        (
            0.40 * np.maximum(geo_dict["geotherm_reservoir_enthalpy"], 0.0)
            + 0.35 * np.maximum(geo_dict["thm_paleo_sinter_seal_s8"], 0.0)
            + 0.25 * np.maximum(geo_dict["thm_probe2m_upward_flux"], 0.0)
        )
        * (1.0 + 0.35 * np.maximum(transtension_fp, 0.0) + 0.35 * np.maximum(z_cond_grad, 0.0))
        + 0.25 * geo_dict["thm_paleo_sinter_seal_s20"]
        + 0.25 * geo_dict["thm_probe2m_upward_flux"]
    )
    _write_col("thm_silica_valve_breach", valve_breach_fp)
    del geo_dict, z_cond_grad, z_cond, claycap_fp, valve_breach_fp
    gc.collect()

    # Pass 3: USGS GeoDAWN radiometric & 150m upward-continued magnetic extensions
    rad_path = raw_dir / "external" / "geodawn_rad_u8.tif"
    ext_path = raw_dir / "external" / "geodawn_extensions_u8.tif"
    with rasterio.open(rad_path) as ds_rad, rasterio.open(ext_path) as ds_ext:
        k_r = ds_rad.read(1).astype(np.float32)
        th_r = ds_rad.read(2).astype(np.float32)
        u_r = ds_rad.read(3).astype(np.float32)
        tc_r = ds_rad.read(4).astype(np.float32)
        thk_e = ds_ext.read(1).astype(np.float32)
        uk_e = ds_ext.read(2).astype(np.float32)
        uth_e = ds_ext.read(3).astype(np.float32)
        tmi_up150 = ds_ext.read(4).astype(np.float32)

    k_metasom = _robust_z_flat((k_r / (th_r + 5.0))[footprint]) - 0.5 * _robust_z_flat(thk_e[footprint])
    _write_col("rad_k_metasomatism", _robust_z_flat(k_metasom))
    u_redox = _robust_z_flat(u_r[footprint]) + 0.5 * _robust_z_flat(uth_e[footprint]) + 0.5 * _robust_z_flat(uk_e[footprint])
    _write_col("rad_u_redox_halo", _robust_z_flat(u_redox))
    tc_grad = _grad_mag(ndi.gaussian_filter(tc_r, sigma=1.2, mode="nearest"))
    _write_col("rad_tc_grad", _robust_z_flat(tc_grad[footprint]))
    del k_r, th_r, u_r, tc_r, thk_e, uk_e, uth_e, k_metasom, u_redox, tc_grad

    # Shallow magnetic residual (TMI - TMI_up150 smoothed)
    tmi_z_2d = np.zeros((H, W), dtype=np.float32)
    tmi_z_2d[footprint] = _robust_z_flat(kept_bands["total_magnetic_intensity"][footprint])
    up150_z_2d = np.zeros((H, W), dtype=np.float32)
    up150_z_2d[footprint] = _robust_z_flat(tmi_up150[footprint])
    mag_sh_res_2d = tmi_z_2d - up150_z_2d
    _write_col("mag_shallow_residual", _robust_z_flat(mag_sh_res_2d[footprint]))
    mag_sh_ridge_2d = _hessian_ridge(mag_sh_res_2d)
    _write_col("mag_shallow_ridge", _robust_z_flat(mag_sh_ridge_2d[footprint]))
    del tmi_up150, tmi_z_2d, up150_z_2d, mag_sh_ridge_2d
    gc.collect()

    # Pass 4: USGS 3DEP 1m LiDAR + 10m seamless breakline + 10m fluvial chi/knickpoint bridge
    lid_path = raw_dir / "external" / "lidar_scarp_features_u8.tif"
    with rasterio.open(lid_path) as ds_lid:
        ex_max = (ds_lid.read(1).astype(np.float32) / 255.0) ** 2 * 1.5
        step_max = (ds_lid.read(3).astype(np.float32) / 255.0) ** 2 * 1.0
        downface = (ds_lid.read(6).astype(np.float32) / 255.0) ** 2 * 1.0
        upface = (ds_lid.read(7).astype(np.float32) / 255.0) ** 2 * 1.0
        cross_max = (ds_lid.read(8).astype(np.float32) / 255.0) ** 2 * 1.0
        relief = (ds_lid.read(9).astype(np.float32) / 255.0) ** 2 * 300.0
        coh100 = ds_lid.read(10).astype(np.float32) / 255.0
        lid_valid = (ds_lid.read(12) > 0) & footprint

    scarp_raw = (0.45 * step_max + 0.35 * ex_max + 0.20 * np.maximum(downface, upface) - 0.25 * cross_max) / np.sqrt(
        relief + 9.0
    )
    scarp_raw = np.where(lid_valid, scarp_raw, np.median(scarp_raw[lid_valid]) if lid_valid.any() else 0.0)
    lidar_norm_fp = _robust_z_flat(scarp_raw[footprint])
    _write_col("lidar_relief_norm_scarp", lidar_norm_fp)

    coh_raw = np.where(lid_valid, coh100 * np.maximum(scarp_raw, 0.0), 0.0)
    _write_col("lidar_scarp_coherence", _robust_z_flat(coh_raw[footprint]))
    del ex_max, step_max, downface, upface, cross_max, relief, coh100, scarp_raw, coh_raw

    # 10m seamless breakline & curvature stack (100% coverage)
    topo10_path = raw_dir / "external" / "topo_10m_derived_100m_u8.tif"
    with rasterio.open(topo10_path) as ds_t10:
        t10_slp90 = ds_t10.read(1).astype(np.float32) / 255.0
        t10_steep = ds_t10.read(3).astype(np.float32) / 255.0
        t10_rel = ds_t10.read(5).astype(np.float32) / 255.0
        t10_curv = ds_t10.read(6).astype(np.float32) / 255.0
        t10_asp_coh = ds_t10.read(7).astype(np.float32) / 255.0
        t10_hs_lin = ds_t10.read(8).astype(np.float32) / 255.0

    topo10_break_2d = (0.45 * t10_curv + 0.35 * t10_slp90 + 0.20 * t10_hs_lin) / np.sqrt(t10_rel * 100.0 + 9.0)
    topo10_break_fp = _robust_z_flat(topo10_break_2d[footprint])
    _write_col("thm_topo10_breakline_ridge", topo10_break_fp)
    topo10_coh_fp = _robust_z_flat((t10_asp_coh * (0.3 + 0.7 * t10_steep))[footprint])
    _write_col("thm_topo10_aspect_coherence", topo10_coh_fp)
    del t10_slp90, t10_steep, t10_rel, t10_curv, t10_asp_coh, t10_hs_lin, topo10_break_2d, topo10_coh_fp

    # 10m fluvial chi & knickpoint stack
    chi_i16_path = raw_dir / "external" / "dem10_chi_100m_i16.tif"
    chi_u8_path = raw_dir / "external" / "dem10_chi_100m_u8.tif"
    with rasterio.open(chi_i16_path) as ds_ci, rasterio.open(chi_u8_path) as ds_cu:
        chi_step_max = np.maximum(ds_ci.read(1).astype(np.float32), 0.0) / 1000.0
        chi_ksn = np.maximum(ds_ci.read(3).astype(np.float32), 0.0)
        knick_n = ds_cu.read(2).astype(np.float32)
        raised_n = ds_cu.read(3).astype(np.float32)

    chi_step_fp = _robust_z_flat(np.log1p(chi_step_max[footprint])) + 0.5 * _robust_z_flat(np.log1p(chi_ksn[footprint]))
    chi_step_fp = _robust_z_flat(chi_step_fp)
    _write_col("thm_fluvial_chi_step", chi_step_fp)
    knick_smooth = ndi.gaussian_filter(knick_n + 0.5 * raised_n, sigma=2.5, mode="nearest")
    knick_fp = _robust_z_flat(np.log1p(knick_smooth[footprint]))
    _write_col("thm_fluvial_knickpoint_density", knick_fp)
    del chi_step_max, chi_ksn, knick_n, raised_n, knick_smooth

    # Seamless 1m-LiDAR + 10m-3DEP scarp & fluvial-chi bridge
    lid_valid_fp = lid_valid[footprint]
    seamless_scarp_fp = np.where(lid_valid_fp, 0.70 * lidar_norm_fp + 0.30 * topo10_break_fp, topo10_break_fp)
    seamless_scarp_fp = _robust_z_flat(seamless_scarp_fp + 0.35 * chi_step_fp + 0.20 * knick_fp)
    _write_col("thm_seamless_scarp_chi", seamless_scarp_fp)
    del lid_valid, lid_valid_fp, lidar_norm_fp, topo10_break_fp, chi_step_fp, knick_fp
    gc.collect()

    # Pass 5: Up-dip 60-deg basement-gravity-magnetic advection & surface concordance
    db_smooth = ndi.gaussian_filter(kept_bands["depth_to_basement"], sigma=2.0, mode="nearest")
    dby, dbx = np.gradient(db_smooth)
    db_mag = np.hypot(dby, dbx) + np.float32(1e-5)
    # Unit vector pointing down-dip into the deeper hanging-wall basin
    vy_down = (dby / db_mag).astype(np.float32)
    vx_down = (dbx / db_mag).astype(np.float32)

    grav_base_field = (
        0.55 * _fill_band(kept_bands["iso_gravity_horizontal_gradient"], footprint)
        + 0.45 * grad_fp_cache["depth_to_basement"]
    )
    updip_grav_2d = _advect_updip_2d(grav_base_field, vy_down, vx_down, step_px=2.0)
    updip_grav_fp = _robust_z_flat(updip_grav_2d[footprint])
    _write_col("thm_updip_grav_basement", updip_grav_fp)

    mag_demag_field = 0.60 * grad_fp_cache["mag_reduced_to_pole"] + 0.40 * np.maximum(-mag_sh_res_2d, 0.0)
    updip_mag_2d = _advect_updip_2d(mag_demag_field, vy_down, vx_down, step_px=2.0)
    updip_mag_fp = _robust_z_flat(updip_mag_2d[footprint])
    _write_col("thm_updip_mag_demag", updip_mag_fp)

    concord_fp = _robust_z_flat(
        np.maximum(seamless_scarp_fp, -0.5) * (0.55 * np.maximum(updip_grav_fp, 0.0) + 0.45 * np.maximum(updip_mag_fp, 0.0))
    )
    _write_col("thm_updip_scarp_concordance", concord_fp)

    del kept_bands, grad_fp_cache, mag_sh_res_2d, db_smooth, dby, dbx, db_mag, vy_down, vx_down
    del grav_base_field, updip_grav_2d, mag_demag_field, updip_mag_2d, updip_grav_fp, updip_mag_fp, concord_fp, seamless_scarp_fp, transtension_fp
    mm_col.flush()
    mm_rm = np.lib.format.open_memmap(rm_path, mode="w+", dtype=np.float16, shape=(n_px, n_ch))
    step = 500_000
    for a in range(0, n_px, step):
        b = min(a + step, n_px)
        mm_rm[a:b, :] = np.asarray(mm_col[:, a:b], dtype=np.float16).T
    mm_rm.flush()
    del mm_rm, mm_col
    col_path.unlink(missing_ok=True)
    meta_path.write_text("\n".join(names) + "\n")
    gc.collect()
    return names, np.load(rm_path, mmap_mode="r")


def _strike_field(mask: np.ndarray) -> np.ndarray:
    """Line direction theta in [0, pi) from structure tensor of smoothed mask."""
    i = ndi.gaussian_filter(mask.astype(np.float32), 1.0)
    gy = ndi.sobel(i, axis=0)
    gx = ndi.sobel(i, axis=1)
    jxx = ndi.gaussian_filter(gx * gx, 3.0)
    jyy = ndi.gaussian_filter(gy * gy, 3.0)
    jxy = ndi.gaussian_filter(gx * gy, 3.0)
    phi = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)
    theta = np.mod(phi + np.pi / 2.0, np.pi)
    return theta.astype(np.float32)


def _oriented_kernels(theta: float, r: int = R_KERNEL) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    dy, dx = np.mgrid[-r : r + 1, -r : r + 1].astype(np.float32)
    ux, uy = np.cos(theta), np.sin(theta)
    along = dx * ux + dy * uy
    across = -dx * uy + dy * ux
    lat = np.exp(-0.5 * (across / 1.5) ** 2) * np.exp(-np.abs(along) / 12.0) * (np.abs(along) <= 25)
    kf = (lat * (along > 0.5)).astype(np.float32)
    kb = (lat * (along < -0.5)).astype(np.float32)
    ks = ((np.abs(across) >= 4) & (np.abs(across) <= 20) & (np.abs(along) <= 15)).astype(np.float32)
    ks *= np.exp(-0.5 * (along / 8.0) ** 2).astype(np.float32)
    kf /= kf.sum()
    kb /= kb.sum()
    ks /= ks.sum()
    return kf, kb, ks


def compute_structural_network_features(
    visible_mask: np.ndarray, footprint: np.ndarray
) -> Dict[str, np.ndarray]:
    """Compute all 18 fold-proper structural network features strictly from `visible_mask`."""
    m = np.asarray(visible_mask, dtype=bool)
    fp = np.asarray(footprint, dtype=bool)
    mf = m.astype(np.float32)
    out: Dict[str, np.ndarray] = {}

    dist = ndi.distance_transform_edt(~m).astype(np.float32)
    out["ns_logdist"] = np.log1p(dist)
    del dist

    out["ns_den4"] = ndi.gaussian_filter(mf, 4.0)
    out["ns_den12"] = ndi.gaussian_filter(mf, 12.0)
    out["ns_den32"] = ndi.gaussian_filter(mf, 32.0)

    theta = _strike_field(m)
    bins = np.minimum((theta / np.pi * N_STRIKE_BINS).astype(np.int16), N_STRIKE_BINS - 1)
    cont = np.zeros(m.shape, np.float32)
    gap = np.zeros(m.shape, np.float32)
    sib = np.zeros(m.shape, np.float32)
    cont_max = np.zeros(m.shape, np.float32)
    sib_max = np.zeros(m.shape, np.float32)
    for k in range(N_STRIKE_BINS):
        mk = (m & (bins == k)).astype(np.float32)
        if not mk.any():
            continue
        kf, kb, ks = _oriented_kernels((k + 0.5) * np.pi / N_STRIKE_BINS)
        f = np.maximum(oaconvolve(mk, kf, mode="same"), 0.0).astype(np.float32)
        b = np.maximum(oaconvolve(mk, kb, mode="same"), 0.0).astype(np.float32)
        s = np.maximum(oaconvolve(mk, ks, mode="same"), 0.0).astype(np.float32)
        c = f + b
        cont += c
        gap += np.sqrt(f * b)
        sib += s
        np.maximum(cont_max, c, out=cont_max)
        np.maximum(sib_max, s, out=sib_max)
        del f, b, s, c, mk
    out.update(ns_cont=cont, ns_gap=gap, ns_sib=sib, ns_cont_max=cont_max, ns_sib_max=sib_max)

    c2 = ndi.gaussian_filter(mf * np.cos(2 * theta), 20.0)
    s2 = ndi.gaussian_filter(mf * np.sin(2 * theta), 20.0)
    den = ndi.gaussian_filter(mf, 20.0)
    out["ns_coh"] = (np.hypot(c2, s2) / (den + 1e-6) * (den > 1e-4)).astype(np.float32)
    del theta, bins, c2, s2, den
    gc.collect()

    # Multi-scale hollow beams (s >= 4 px, strictly outside 3-px synthetic withhold collar) & fault-tip propagation rays
    gy = ndi.sobel(mf, axis=0)
    gx = ndi.sobel(mf, axis=1)
    strike = np.arctan2(-gx, gy)
    del gy, gx
    nb_count = ndi.convolve(mf, np.ones((3, 3), dtype=np.float32), mode="constant", cval=0.0)
    tips = m & (nb_count >= 1.5) & (nb_count <= 3.5)
    del nb_count

    beam_short = np.zeros(m.shape, dtype=np.float32)
    beam_med = np.zeros(m.shape, dtype=np.float32)
    beam_long = np.zeros(m.shape, dtype=np.float32)
    bridge_med = np.zeros(m.shape, dtype=np.float32)
    bridge_long = np.zeros(m.shape, dtype=np.float32)
    tip_ray = np.zeros(m.shape, dtype=np.float32)

    for k in range(8):
        ang = k * (np.pi / 8.0)
        align = np.abs(np.cos(strike - ang))
        oriented = np.where(m & (align > 0.78), mf, 0.0).astype(np.float32)
        oriented_tips = np.where(tips & (align > 0.72), 1.0, 0.0).astype(np.float32)
        del align
        dy, dx = np.sin(ang), np.cos(ang)

        f_s = np.zeros(m.shape, dtype=np.float32)
        b_s = np.zeros(m.shape, dtype=np.float32)
        f_m = np.zeros(m.shape, dtype=np.float32)
        b_m = np.zeros(m.shape, dtype=np.float32)
        f_l = np.zeros(m.shape, dtype=np.float32)
        b_l = np.zeros(m.shape, dtype=np.float32)
        t_r = np.zeros(m.shape, dtype=np.float32)

        for s in (4, 6, 8, 10, 12, 16, 20, 26, 32, 40):
            r_off = int(round(s * dy))
            c_off = int(round(s * dx))
            sh_f = np.roll(oriented, (r_off, c_off), axis=(0, 1))
            sh_b = np.roll(oriented, (-r_off, -c_off), axis=(0, 1))
            if s <= 12:
                ws = float(np.exp(-s / 8.0))
                f_s += ws * sh_f
                b_s += ws * sh_b
            if s <= 26:
                wm = float(np.exp(-s / 16.0))
                f_m += wm * sh_f
                b_m += wm * sh_b
            wl = float(np.exp(-s / 28.0))
            f_l += wl * sh_f
            b_l += wl * sh_b
            if s <= 26:
                wt = float(np.exp(-s / 14.0))
                t_r += wt * (
                    np.roll(oriented_tips, (r_off, c_off), axis=(0, 1))
                    + np.roll(oriented_tips, (-r_off, -c_off), axis=(0, 1))
                )

        del oriented, oriented_tips
        f_s = ndi.gaussian_filter(f_s, sigma=1.2)
        b_s = ndi.gaussian_filter(b_s, sigma=1.2)
        f_m = ndi.gaussian_filter(f_m, sigma=1.8)
        b_m = ndi.gaussian_filter(b_m, sigma=1.8)
        f_l = ndi.gaussian_filter(f_l, sigma=2.5)
        b_l = ndi.gaussian_filter(b_l, sigma=2.5)
        t_r = ndi.gaussian_filter(t_r, sigma=1.8)

        np.maximum(beam_short, f_s + b_s, out=beam_short)
        np.maximum(beam_med, f_m + b_m, out=beam_med)
        np.maximum(beam_long, f_l + b_l, out=beam_long)
        np.maximum(bridge_med, np.sqrt(f_m * b_m), out=bridge_med)
        np.maximum(bridge_long, np.sqrt(f_l * b_l), out=bridge_long)
        np.maximum(tip_ray, t_r, out=tip_ray)
        del f_s, b_s, f_m, b_m, f_l, b_l, t_r

    del strike, tips
    ann_near = np.maximum(
        0.0, ndi.gaussian_filter(mf, sigma=7.0) - 0.85 * ndi.gaussian_filter(mf, sigma=2.0)
    ).astype(np.float32)
    ann_far = np.maximum(
        0.0, ndi.gaussian_filter(mf, sigma=18.0) - 0.85 * ndi.gaussian_filter(mf, sigma=4.0)
    ).astype(np.float32)

    raw_hollow = {
        "net_beam_short": beam_short,
        "net_beam_med": beam_med,
        "net_beam_long": beam_long,
        "net_bridge_med": bridge_med,
        "net_bridge_long": bridge_long,
        "net_tip_ray": tip_ray,
        "net_ann_near": ann_near,
        "net_ann_far": ann_far,
    }
    for k, arr in raw_hollow.items():
        z_arr = np.zeros(m.shape, dtype=np.float32)
        z_arr[fp] = _robust_z_flat(arr[fp])
        out[k] = z_arr
    for k in (
        "ns_logdist",
        "ns_den4",
        "ns_den12",
        "ns_den32",
        "ns_cont",
        "ns_gap",
        "ns_sib",
        "ns_cont_max",
        "ns_sib_max",
        "ns_coh",
    ):
        out[k] = np.where(fp, out[k], 0.0).astype(np.float32)
    del raw_hollow
    gc.collect()
    return out


def compute_structural_and_coupling_fp(
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    X_phys_rm: np.ndarray,
    phys_names: List[str],
    cache_path: Path | None = None,
) -> np.ndarray:
    """Compute or load the `(n_fp, 24)` float16 matrix of 18 structural + 6 THM/physical coupling features."""
    n_fp = int(footprint.sum())
    n_cols = len(STRUCTURAL_NETWORK_NAMES) + len(COUPLING_INTERACTION_NAMES)
    if cache_path is not None and cache_path.exists():
        mm = np.load(cache_path, mmap_mode="r")
        if mm.shape == (n_fp, n_cols):
            return mm

    net = compute_structural_network_features(visible_mask, footprint)
    mat = np.empty((n_fp, n_cols), dtype=np.float16)
    for j, nm in enumerate(STRUCTURAL_NETWORK_NAMES):
        mat[:, j] = net[nm][footprint].astype(np.float16)

    idx_claycap = phys_names.index("geotherm_claycap_conduit")
    idx_plume = phys_names.index("geotherm_reservoir_enthalpy")
    idx_lidar = phys_names.index("lidar_relief_norm_scarp")
    idx_strain = phys_names.index("x_strain_transtension")
    idx_valve = phys_names.index("thm_silica_valve_breach")
    idx_seamless = phys_names.index("thm_seamless_scarp_chi")
    idx_concord = phys_names.index("thm_updip_scarp_concordance")

    claycap = np.asarray(X_phys_rm[:, idx_claycap], dtype=np.float32)
    plume = np.asarray(X_phys_rm[:, idx_plume], dtype=np.float32)
    lidar = np.asarray(X_phys_rm[:, idx_lidar], dtype=np.float32)
    strain = np.asarray(X_phys_rm[:, idx_strain], dtype=np.float32)
    valve = np.asarray(X_phys_rm[:, idx_valve], dtype=np.float32)
    seamless = np.asarray(X_phys_rm[:, idx_seamless], dtype=np.float32)
    concord = np.asarray(X_phys_rm[:, idx_concord], dtype=np.float32)

    tip_fp = net["net_tip_ray"][footprint]
    gap_fp = _robust_z_flat(net["ns_gap"][footprint])
    cont_fp = _robust_z_flat(net["ns_cont"][footprint])
    sib_fp = _robust_z_flat(net["ns_sib"][footprint])
    bridge_fp = 0.5 * (net["net_bridge_med"][footprint] + net["net_bridge_long"][footprint])
    beam_fp = 0.5 * (net["net_beam_short"][footprint] + net["net_beam_med"][footprint])

    base_j = len(STRUCTURAL_NETWORK_NAMES)
    mat[:, base_j + 0] = _robust_z_flat(np.maximum(claycap, 0.0) * np.maximum(tip_fp, 0.0)).astype(np.float16)
    mat[:, base_j + 1] = _robust_z_flat(np.maximum(plume, 0.0) * np.maximum(gap_fp, 0.0)).astype(np.float16)
    mat[:, base_j + 2] = _robust_z_flat(np.maximum(lidar, 0.0) * np.maximum(cont_fp, 0.0)).astype(np.float16)
    mat[:, base_j + 3] = _robust_z_flat(np.maximum(strain, 0.0) * np.maximum(sib_fp, 0.0)).astype(np.float16)
    mat[:, base_j + 4] = _robust_z_flat(np.maximum(valve, 0.0) * np.maximum(bridge_fp, 0.0)).astype(np.float16)
    mat[:, base_j + 5] = _robust_z_flat(
        (0.6 * np.maximum(seamless, 0.0) + 0.4 * np.maximum(concord, 0.0)) * np.maximum(beam_fp, 0.0)
    ).astype(np.float16)

    del net, claycap, plume, lidar, strain, valve, seamless, concord, tip_fp, gap_fp, cont_fp, sib_fp, bridge_fp, beam_fp
    gc.collect()

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(cache_path, mat)
        del mat
        gc.collect()
        return np.load(cache_path, mmap_mode="r")
    return mat


def synthetic_withhold(
    mask: np.ndarray,
    footprint: np.ndarray,
    quad: np.ndarray,
    seed: int,
    frac: float = 0.20,
    collar_px: int = 3,
) -> Tuple[np.ndarray, np.ndarray]:
    """Re-withhold whole 8-connected components of `mask` per quadrant with a `collar_px` buffer.

    Returns `(syn_hidden, syn_state)` where `syn_state` is the reduced catalogue mask
    from which features are computed during training. Never touches outer withheld truth.
    """
    m = np.asarray(mask, dtype=bool) & np.asarray(footprint, dtype=bool)
    comp, n = ndi.label(m, STRUCT8)
    sizes = np.bincount(comp.ravel(), minlength=n + 1)
    hidden = np.zeros(m.shape, dtype=bool)
    for q in range(4):
        inq = quad == q
        cand = np.unique(comp[m & inq])
        clipped = np.unique(comp[m & ~inq])
        elig = np.setdiff1d(cand[cand > 0], clipped)
        if elig.size == 0:
            continue
        rng = np.random.default_rng(840_000 + 97 * seed + q)
        perm = rng.permutation(elig)
        cum = np.cumsum(sizes[perm])
        k = int(np.searchsorted(cum, frac * float((m & inq).sum()))) + 1
        hidden |= np.isin(comp, perm[: min(k, perm.size)]) & m
    collar = ndi.distance_transform_edt(~hidden) <= collar_px
    state = m & ~collar
    assert not (state & hidden).any()
    return hidden, state
