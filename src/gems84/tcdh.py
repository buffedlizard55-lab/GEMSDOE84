"""H84-B (H84-TCDH): Transtensional Coulomb Slip-Dilation x Multi-Altitude
Potential-Field Tilt-Worm Persistence x Hydrothermal Upflow-Conduit &
Tip-Anisotropic Structural Mechanics.

All catalogue-derived quantities are computed strictly from the ``visible``
fault mask supplied to each fold (never from withheld truth). External CSV
layers that carry precomputed ``dist_known_fault_px`` columns are read via
explicit ``usecols`` allowlists that exclude ``dist_known_fault_px`` and assert
its absence.

Designed for <= 3.8 GiB RAM environments via disk-backed numpy memmaps and
block-wise 2D array streaming.
"""
from __future__ import annotations

import gc
import hashlib
import struct
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from numpy.lib.format import open_memmap
import pandas as pd
import rasterio
from rasterio.warp import transform as warp_transform
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier

from gems57.network import STRUCT3, local_strike, offset_components, segment_table, segments
from gems57.relay_bend_anatomy import kinematic_transition_field, two_host_frame

from .basis import _fill, _rank01

PINNED_SHA256: Dict[str, str] = {
    "training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
    "external/lidar_scarp_features_u8.tif": "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568",
    "external/topo_10m_derived_100m_u8.tif": "a6398d9950965dec6aae6ccecdaa6ced48645d133eab222cbdd11def9bdabfa4",
    "external/dem10_chi_100m_i16.tif": "8897ba9c30ef1cd7ad5f23c16c6dfd7bb070e7e757f36fd9486eb45edfd973a5",
    "external/geodawn_rad_u8.tif": "c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682",
    "external/geodawn_extensions_u8.tif": "a35a9c6d2a14786f4dab85481ee59769213072f5dab5b2535ea82ae4d9bb7d9b",
    "external/2m_temperature_probe_INGENIOUS_regional_data.zip": "1301f70d230058e616ea5d34d1c7a32fabf7d49198172f376c59c89bd652eca3",
    "external/paleo_geothermal_regional.zip": "faffcf697f32dbbf6cbb317cd1effb3e305538ce38eb239d72d0c6fa071e91ca",
    "external/gdr_wellspring_in_footprint.csv": "122718e65bdf55aab0ee12ad20d80062f0deb1de957225a61ad880dd5dc196ea",
    "external/trace_segments_utm11.csv": "c5edf9df3e0e1413c52784884fc38e5b9ca54627b27c6f8baf7713e908f48513",
}

PHYS_FEATURES: Tuple[str, ...] = (
    # Block 1: Multi-altitude potential-field tilt-worm persistence & basement edges (10)
    "pf_rtp_hg",
    "pf_tmi_tilt_sharp",
    "pf_up150_hg",
    "pf_tilt_worm_persist",
    "pf_flightline_ringing",
    "pf_grav_hg",
    "pf_grav_tilt_sharp",
    "pf_mag_grav_worm",
    "pf_base_grad",
    "pf_piedmont_window",
    # Block 2: Spin-2 structure tensor & transtensional Coulomb slip-dilation (7)
    "mech_spin2_coh",
    "mech_sin2_strike",
    "mech_cos2_strike",
    "mech_geod_shear",
    "mech_geod_dilate",
    "mech_coulomb_transtens",
    "mech_seismic_swarm",
    # Block 3: Blind hydrothermal upflow, geothermometer disequilibrium, MT & radiometrics (10)
    "hydro_t2m_anom_15",
    "hydro_t2m_surveyed",
    "hydro_sinter_halo",
    "hydro_spring_temp",
    "hydro_geotherm_diseq",
    "hydro_vent_dike",
    "hydro_mt_clay_edge",
    "hydro_rad_k_bnorm",
    "hydro_rad_uk_bnorm",
    "hydro_upflow_conduit",
    # Block 4: Multi-resolution tectonic geomorphology, fluvial chi, & deconfounders (9)
    "geom_lidar_valid",
    "geom_lidar_scarp",
    "geom_topo10_scarp",
    "geom_det_ridge",
    "geom_chi_knick",
    "geom_chi_subsurf",
    "deconf_lahontan_terrace",
    "deconf_road_prox",
    "geom_scarp_clean",
)

ANAT_FEATURES: Tuple[str, ...] = (
    "anat_log_d1_smooth",
    "anat_log_dperp_smooth",
    "anat_log_dpar",
    "anat_tip_proj_ratio",
    "anat_side",
    "anat_log_len1",
    "anat_anchor_coh",
    "anat_log_d2",
    "anat_relay_ratio",
    "anat_relay_facing",
    "anat_two_host_cos2",
    "anat_log_len2",
    "anat_belt_dens_800m",
    "anat_belt_dens_2500m",
    "anat_belt_dens_7500m",
    "anat_kinematic_trans",
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_sensor_hashes(data_dir: Path) -> Dict[str, str]:
    verified: Dict[str, str] = {}
    for rel, expected in PINNED_SHA256.items():
        p = data_dir / rel
        if not p.exists():
            raise FileNotFoundError(f"Missing pinned sensor input: {p}")
        got = _sha256_file(p)
        if got != expected:
            raise ValueError(f"SHA-256 mismatch on {p}: expected {expected}, got {got}")
        verified[rel] = got
    return verified


def _read_clean_band(src: rasterio.DatasetReader, b: int, fp: np.ndarray) -> np.ndarray:
    """Read float32 band and replace GDAL -3.4e38 nodata sentinels with NaN."""
    a = src.read(b).astype(np.float32)
    bad = (~fp) | (~np.isfinite(a)) | (np.abs(a) > 1e15)
    a[bad] = np.nan
    return a


def _robust_z_fp(arr2d: np.ndarray, fp: np.ndarray, clip: float = 8.0) -> np.ndarray:
    """Median/MAD robust z-score on footprint pixels -> 1D float32 of length fp.sum()."""
    v = arr2d[fp].astype(np.float64)
    fin = np.isfinite(v) & (np.abs(v) <= 1e15)
    if not fin.any():
        return np.zeros(v.shape, np.float32)
    med = float(np.median(v[fin]))
    mad = float(np.median(np.abs(v[fin] - med))) * 1.4826
    if not np.isfinite(mad) or mad < 1e-6:
        mad = max(float(np.std(v[fin])), 1e-6)
    z = np.where(fin, (v - med) / mad, 0.0)
    return np.clip(z, -clip, clip).astype(np.float32)


def _robust_z_2d(arr2d: np.ndarray, fp: np.ndarray, clip: float = 10.0) -> np.ndarray:
    """Normalized 2D array (NaN outside valid pixels) safe against float32 overflow."""
    out = np.full(arr2d.shape, np.nan, np.float32)
    out[fp] = _robust_z_fp(arr2d, fp, clip=clip)
    bad = (~fp) | (~np.isfinite(arr2d)) | (np.abs(arr2d) > 1e15)
    out[bad] = np.nan
    return out


def _rank01_2d(arr2d: np.ndarray, fp: np.ndarray) -> np.ndarray:
    v = arr2d[fp].astype(np.float64)
    v = np.where(np.isfinite(v) & (np.abs(v) <= 1e15), v, np.nan)
    out = np.zeros(arr2d.shape, np.float32)
    out[fp] = _rank01(v)
    return out


def _block_norm_u8(u8_band: np.ndarray, block_id: np.ndarray, fp: np.ndarray) -> np.ndarray:
    out = np.zeros(u8_band.shape, np.float32)
    valid = fp & (u8_band > 0)
    for b in (0, 1, 2, 3, 4):
        m = valid & (block_id == b)
        if m.sum() < 100:
            continue
        vals = u8_band[m].astype(np.float32)
        med = float(np.median(vals))
        mad = max(float(np.median(np.abs(vals - med))) * 1.4826, 1.0)
        out[m] = np.clip((vals - med) / mad, -8.0, 8.0)
    return out


def _grad_mag_and_strike(field2d: np.ndarray, fp: np.ndarray, sigma: float = 1.2) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Overflow-safe gradient magnitude and spin-2 lineament strike (CW from North)."""
    z = _robust_z_2d(field2d, fp, clip=10.0)
    f = _fill(z)
    gy = ndi.gaussian_filter(f, sigma, order=(1, 0))
    gx = ndi.gaussian_filter(f, sigma, order=(0, 1))
    mag = np.hypot(gx, gy).astype(np.float32)

    j_ee = ndi.gaussian_filter(gx * gx, sigma * 1.5)
    j_nn = ndi.gaussian_filter(gy * gy, sigma * 1.5)
    j_en = ndi.gaussian_filter(gx * (-gy), sigma * 1.5)
    tr = j_nn + j_ee + 1e-8
    diff = j_nn - j_ee
    two_ne = 2.0 * j_en
    lam_diff = np.hypot(diff, two_ne)
    coh = np.clip(lam_diff / tr, 0.0, 1.0).astype(np.float32)
    cos2_alpha = diff / (lam_diff + 1e-8)
    sin2_alpha = two_ne / (lam_diff + 1e-8)
    sin2_strike = (-coh * sin2_alpha).astype(np.float32)
    cos2_strike = (-coh * cos2_alpha).astype(np.float32)
    return mag, sin2_strike, cos2_strike


def _hessian_ridge(field2d: np.ndarray, fp: np.ndarray, sigma: float) -> np.ndarray:
    z = _robust_z_2d(field2d, fp, clip=10.0)
    f = _fill(z)
    hyy = ndi.gaussian_filter(f, sigma, order=(2, 0))
    hxx = ndi.gaussian_filter(f, sigma, order=(0, 2))
    hxy = ndi.gaussian_filter(f, sigma, order=(1, 1))
    eig_min = 0.5 * (hxx + hyy) - np.hypot(0.5 * (hxx - hyy), hxy)
    return ((sigma ** 2) * np.maximum(-eig_min, 0.0)).astype(np.float32)


def _utm_to_rc(utm_e: np.ndarray, utm_n: np.ndarray, shape: Tuple[int, int]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    cols = np.floor((utm_e - 243350.0) / 100.0).astype(np.int32)
    rows = np.floor((4508550.0 - utm_n) / 100.0).astype(np.int32)
    ok = (rows >= 0) & (rows < shape[0]) & (cols >= 0) & (cols < shape[1])
    return rows[ok], cols[ok], ok


def _load_2m_probes(zip_path: Path, shape: Tuple[int, int]) -> Tuple[np.ndarray, np.ndarray]:
    with zipfile.ZipFile(zip_path) as z:
        shp = z.read("2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.shp")
        dbf = z.read("2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf")
    num_rec, hdr_len, rec_len = struct.unpack("<IHH", dbf[4:12])
    fields: List[Tuple[str, int]] = []
    pos = 32
    while dbf[pos] != 0x0D:
        fname = dbf[pos:pos + 11].split(b"\x00")[0].decode("ascii", "replace")
        flen = dbf[pos + 16]
        fields.append((fname, flen))
        pos += 32

    lons = np.empty(num_rec, np.float64)
    lats = np.empty(num_rec, np.float64)
    dab = np.zeros(num_rec, np.float32)
    t2m = np.zeros(num_rec, np.float32)
    spos = 100
    for i in range(num_rec):
        _rec_num, clen = struct.unpack(">II", shp[spos:spos + 8])
        stype = struct.unpack("<i", shp[spos + 8:spos + 12])[0]
        if stype in (1, 11, 21):
            x, y = struct.unpack("<dd", shp[spos + 12:spos + 28])
            lons[i], lats[i] = x, y
        else:
            lons[i], lats[i] = np.nan, np.nan
        spos += 8 + clen * 2
        rbytes = dbf[hdr_len + i * rec_len + 1:hdr_len + (i + 1) * rec_len]
        off = 0
        for fn, fl in fields:
            if fn in ("T2m", "F2mDAB"):
                s = rbytes[off:off + fl].decode("ascii", "replace").strip()
                try:
                    val = float(s) if s else 0.0
                except ValueError:
                    val = 0.0
                if fn == "T2m":
                    t2m[i] = val
                else:
                    dab[i] = val
            off += fl

    fin = np.isfinite(lons) & np.isfinite(lats)
    ux, uy = warp_transform("EPSG:4269", "EPSG:32611", lons[fin].tolist(), lats[fin].tolist())
    rows, cols, ok = _utm_to_rc(np.asarray(ux), np.asarray(uy), shape)
    strength = np.maximum(dab[fin][ok], 0.0) + 0.25 * np.maximum(t2m[fin][ok] - 24.0, 0.0)
    anom = np.zeros(shape, np.float32)
    pres = np.zeros(shape, np.float32)
    np.maximum.at(anom, (rows, cols), np.clip(strength, 0.0, 40.0))
    pres[rows, cols] = 1.0
    anom_s = (0.65 * ndi.gaussian_filter(anom, 12.0) + 0.35 * ndi.gaussian_filter(anom, 30.0)).astype(np.float32)
    pres_s = np.clip(ndi.gaussian_filter(pres, 22.0) * 60.0, 0.0, 1.0).astype(np.float32)
    return anom_s, pres_s


def _load_paleo_sinter(zip_path: Path, shape: Tuple[int, int]) -> np.ndarray:
    with zipfile.ZipFile(zip_path) as z:
        df = pd.read_csv(
            z.open("Paleo_geothermal_final.csv"),
            encoding="cp1252",
            usecols=["Long_deg_NAD83", "Lat_deg_NAD83", "Deposit_type"],
        )
    fin = df["Long_deg_NAD83"].notna() & df["Lat_deg_NAD83"].notna()
    df = df.loc[fin]
    ux, uy = warp_transform(
        "EPSG:4269", "EPSG:32611",
        df["Long_deg_NAD83"].to_numpy().tolist(),
        df["Lat_deg_NAD83"].to_numpy().tolist(),
    )
    dtype_str = df["Deposit_type"].fillna("").str.lower().to_numpy()
    w = np.where(np.char.find(dtype_str.astype(str), "sinter") >= 0, 1.5, 1.0).astype(np.float32)
    rows, cols, ok = _utm_to_rc(np.asarray(ux), np.asarray(uy), shape)
    pts = np.zeros(shape, np.float32)
    np.maximum.at(pts, (rows, cols), w[ok])
    return (0.6 * ndi.gaussian_filter(pts, 7.0) + 0.4 * ndi.gaussian_filter(pts, 24.0)).astype(np.float32)


def _load_wellspring_and_vents(ext_dir: Path, shape: Tuple[int, int]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    ws_cols = ["row", "col", "temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c"]
    ws = pd.read_csv(ext_dir / "gdr_wellspring_in_footprint.csv", usecols=ws_cols)
    assert "dist_known_fault_px" not in ws.columns

    r = ws["row"].to_numpy(np.int32)
    c = ws["col"].to_numpy(np.int32)
    ok = (r >= 0) & (r < shape[0]) & (c >= 0) & (c < shape[1])
    r, c = r[ok], c[ok]
    tc = np.nan_to_num(ws["temp_c"].to_numpy(np.float32)[ok], nan=0.0)
    tq = np.nan_to_num(ws["geothermquartz_c"].to_numpy(np.float32)[ok], nan=0.0)
    tch = np.nan_to_num(ws["geothermchalc_c"].to_numpy(np.float32)[ok], nan=0.0)
    tcat = np.nan_to_num(ws["geothermcat_c"].to_numpy(np.float32)[ok], nan=0.0)
    tmax_geo = np.maximum(np.maximum(tq, tch), np.clip(tcat, 0.0, 260.0))
    diseq = np.clip(tmax_geo - np.maximum(tc, 16.0), 0.0, 220.0)
    surf_excess = np.clip(tc - 20.0, 0.0, 120.0)

    g_temp = np.zeros(shape, np.float32)
    g_diseq = np.zeros(shape, np.float32)
    np.maximum.at(g_temp, (r, c), np.log1p(surf_excess))
    np.maximum.at(g_diseq, (r, c), np.log1p(diseq))
    temp_halo = (0.65 * ndi.gaussian_filter(g_temp, 8.0) + 0.35 * ndi.gaussian_filter(g_temp, 25.0)).astype(np.float32)
    diseq_halo = (0.65 * ndi.gaussian_filter(g_diseq, 10.0) + 0.35 * ndi.gaussian_filter(g_diseq, 28.0)).astype(np.float32)

    vv_cols = ["row", "col"]
    vv = pd.read_csv(ext_dir / "gdr_volcanic_vents_in_footprint.csv", usecols=vv_cols)
    assert "dist_known_fault_px" not in vv.columns
    vr = vv["row"].to_numpy(np.int32)
    vc = vv["col"].to_numpy(np.int32)
    vok = (vr >= 0) & (vr < shape[0]) & (vc >= 0) & (vc < shape[1])
    g_vent = np.zeros(shape, np.float32)
    g_vent[vr[vok], vc[vok]] = 1.0
    vent_halo = ndi.gaussian_filter(g_vent, 22.0).astype(np.float32)
    return temp_halo, diseq_halo, vent_halo


def load_trace_sense_raster(ext_dir: Path, shape: Tuple[int, int]) -> np.ndarray:
    df = pd.read_csv(ext_dir / "trace_segments_utm11.csv", usecols=["x0", "y0", "x1", "y1", "sense"])
    code_map = {"N": 1, "RL": 2, "LL": 3}
    codes = df["sense"].fillna("").str.strip().map(code_map).fillna(0).to_numpy(np.int8)
    valid = codes > 0
    x0 = df["x0"].to_numpy(np.float64)[valid]
    y0 = df["y0"].to_numpy(np.float64)[valid]
    x1 = df["x1"].to_numpy(np.float64)[valid]
    y1 = df["y1"].to_numpy(np.float64)[valid]
    codes = codes[valid]

    out = np.zeros(shape, np.int8)
    for t in (0.0, 0.5, 1.0):
        xt = x0 + t * (x1 - x0)
        yt = y0 + t * (y1 - y0)
        r, c, ok = _utm_to_rc(xt, yt, shape)
        out[r, c] = np.maximum(out[r, c], codes[ok])
    for val in (1, 2, 3):
        m = ndi.binary_dilation(out == val, iterations=1)
        out = np.where((out == 0) & m, np.int8(val), out)
    return out


def build_or_load_physics_stack(
    data_dir: Path, work_dir: Path, fp: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Stream-build disk-backed memmaps for X_phys (36 cols) and X_base19 (19 cols)."""
    verify_sensor_hashes(data_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    cache_phys = work_dir / "tcdh_phys_v1.npy"
    cache_b19 = work_dir / "tcdh_base19_v1.npy"
    cache_ori = work_dir / "tcdh_geo_spin2_v1.npz"
    n_fp = int(fp.sum())

    if cache_phys.exists() and cache_b19.exists() and cache_ori.exists():
        Xp = np.load(cache_phys, mmap_mode="r")
        Xb = np.load(cache_b19, mmap_mode="r")
        ori = np.load(cache_ori)
        if Xp.shape == (n_fp, len(PHYS_FEATURES)) and Xb.shape == (n_fp, 19) and np.isfinite(Xp[:1000]).all():
            return Xp, Xb, ori["sin2"], ori["cos2"]

    shape = fp.shape
    ext = data_dir / "external"
    Xp_mm = open_memmap(cache_phys, mode="w+", dtype=np.float32, shape=(n_fp, len(PHYS_FEATURES)))
    Xb_mm = open_memmap(cache_b19, mode="w+", dtype=np.float32, shape=(n_fp, 19))

    # Pass 0: populate X_base19 one band at a time (~50 MB peak)
    with rasterio.open(data_dir / "training_features.tif") as src:
        for b in range(1, 20):
            arr = _read_clean_band(src, b, fp)
            Xb_mm[:, b - 1] = _robust_z_fp(arr, fp)
            del arr
    Xb_mm.flush()
    gc.collect()

    # Pass 1: Potential-field tilt-worm & basement architecture
    with rasterio.open(data_dir / "training_features.tif") as src:
        b_rtp = _read_clean_band(src, 2, fp)
        b_tmi_hg = _read_clean_band(src, 3, fp)
        b_tmi_vg = _read_clean_band(src, 9, fp)
        b_grav_vg = _read_clean_band(src, 11, fp)
        b_grav = _read_clean_band(src, 13, fp)
        b_base = _read_clean_band(src, 15, fp)
        b_grav_hg = _read_clean_band(src, 18, fp)

    rtp_hg, rtp_s2, rtp_c2 = _grad_mag_and_strike(b_rtp, fp, sigma=1.2)
    del b_rtp
    thg_abs = np.where(np.isfinite(b_tmi_hg), np.abs(b_tmi_hg), 0.0)
    tvg_abs = np.where(np.isfinite(b_tmi_vg), np.abs(b_tmi_vg), 0.0)
    eps_m = float(np.percentile(thg_abs[fp], 25)) + 1e-6
    tmi_tilt_sharp = (1.0 - np.arctan2(tvg_abs, thg_abs + eps_m) / (0.5 * np.pi)).astype(np.float32)
    r_vg = _rank01_2d(tvg_abs, fp)
    del b_tmi_hg, b_tmi_vg, thg_abs, tvg_abs

    with rasterio.open(ext / "geodawn_extensions_u8.tif") as src:
        uk_u8 = src.read(2)
        up150_u8 = src.read(4)

    up150_f = np.where(fp & (up150_u8 > 0), up150_u8.astype(np.float32), np.nan)
    up150_hg, up150_s2, up150_c2 = _grad_mag_and_strike(up150_f, fp, sigma=1.5)
    up150_hg = np.where(fp & (up150_u8 > 0), up150_hg, 0.0)
    del up150_f, up150_u8

    r_rtp = _rank01_2d(rtp_hg, fp)
    r_up = _rank01_2d(up150_hg, fp)
    align_up = np.clip(0.5 * (1.0 + rtp_s2 * up150_s2 + rtp_c2 * up150_c2), 0.0, 1.0)
    tilt_worm_persist = (np.sqrt(r_rtp * r_up) * align_up * (0.5 + 0.5 * tmi_tilt_sharp)).astype(np.float32)
    flightline_ring = (np.clip(-rtp_c2, 0.0, 1.0) * r_vg * np.clip(1.0 - r_up, 0.0, 1.0)).astype(np.float32)
    del up150_s2, up150_c2, align_up, r_vg

    ghg_abs = np.where(np.isfinite(b_grav_hg), np.maximum(b_grav_hg, 0.0), 0.0)
    gvg_abs = np.where(np.isfinite(b_grav_vg), np.abs(b_grav_vg), 0.0)
    _, grav_s2, grav_c2 = _grad_mag_and_strike(b_grav, fp, sigma=2.0)
    del b_grav, b_grav_hg, b_grav_vg
    eps_g = float(np.percentile(ghg_abs[fp], 25)) + 1e-6
    grav_tilt_sharp = (1.0 - np.arctan2(gvg_abs, ghg_abs + eps_g) / (0.5 * np.pi)).astype(np.float32)
    r_grav = _rank01_2d(ghg_abs, fp)
    align_mg = np.clip(0.5 * (1.0 + rtp_s2 * grav_s2 + rtp_c2 * grav_c2), 0.0, 1.0)
    mag_grav_worm = (np.sqrt(r_rtp * r_grav) * align_mg).astype(np.float32)
    del gvg_abs, align_mg

    base_grad, base_s2, base_c2 = _grad_mag_and_strike(b_base, fp, sigma=2.0)
    z_base = np.clip(np.where(np.isfinite(b_base), b_base, 0.0), 20.0, 10000.0)
    piedmont_win = np.exp(-0.5 * ((np.log10(z_base) - np.log10(450.0)) / 0.55) ** 2).astype(np.float32)
    del b_base, z_base

    Xp_mm[:, 0] = _robust_z_fp(rtp_hg, fp)
    Xp_mm[:, 1] = _robust_z_fp(tmi_tilt_sharp, fp)
    Xp_mm[:, 2] = _robust_z_fp(up150_hg, fp)
    Xp_mm[:, 3] = _robust_z_fp(tilt_worm_persist, fp)
    Xp_mm[:, 4] = _robust_z_fp(flightline_ring, fp)
    Xp_mm[:, 5] = _robust_z_fp(ghg_abs, fp)
    Xp_mm[:, 6] = _robust_z_fp(grav_tilt_sharp, fp)
    Xp_mm[:, 7] = _robust_z_fp(mag_grav_worm, fp)
    Xp_mm[:, 8] = _robust_z_fp(base_grad, fp)
    Xp_mm[:, 9] = _robust_z_fp(piedmont_win, fp)
    r_base_grad = _rank01_2d(base_grad, fp)
    subsurf_edge = np.maximum(r_rtp, np.maximum(r_up, r_grav))
    del rtp_hg, tmi_tilt_sharp, up150_hg, tilt_worm_persist, flightline_ring, ghg_abs, grav_tilt_sharp, mag_grav_worm, base_grad, r_rtp, r_up
    gc.collect()

    # Pass 2: 10 m topo + 3DEP LiDAR + Spin-2 Coulomb mechanics
    with rasterio.open(ext / "topo_10m_derived_100m_u8.tif") as src:
        s1_u8 = src.read(1)
        topo_valid = fp & (s1_u8 > 0)
        slope_p90 = s1_u8.astype(np.float32)
        curv_prof = src.read(6).astype(np.float32)
        asp_coh = src.read(7).astype(np.float32)
        hs_lin = src.read(8).astype(np.float32)
        del s1_u8

    _, topo_s2, topo_c2 = _grad_mag_and_strike(np.where(topo_valid, slope_p90, np.nan), fp, sigma=1.2)

    with rasterio.open(ext / "lidar_scarp_features_u8.tif") as src:
        lid_ex = src.read(1)
        lid_step = src.read(3)
        lid_lapn = src.read(4)
        lid_lapp = src.read(5)
        lid_coh = src.read(10)
        lid_strike_u8 = src.read(11)
        lid_valid_u8 = src.read(12)

    lid_valid = fp & (lid_valid_u8 > 0) & (lid_step > 0)
    lid_coh_f = np.where(lid_valid, np.clip((lid_coh.astype(np.float32) - 1.0) / 254.0, 0.0, 1.0), 0.0)
    lid_strike_deg = np.where(lid_valid, ((lid_strike_u8.astype(np.float32) - 1.0) / 254.0) * 180.0, 0.0)
    lid_s2 = np.where(lid_valid, lid_coh_f * np.sin(np.radians(2.0 * lid_strike_deg)), 0.0).astype(np.float32)
    lid_c2 = np.where(lid_valid, lid_coh_f * np.cos(np.radians(2.0 * lid_strike_deg)), 0.0).astype(np.float32)
    del lid_coh, lid_strike_u8, lid_valid_u8, lid_strike_deg

    w_lid = np.where(lid_valid, 0.35, 0.0).astype(np.float32)
    geo_s2 = ((0.35 * rtp_s2 + 0.20 * grav_s2 + 0.15 * base_s2 + 0.30 * topo_s2 + w_lid * lid_s2) / (1.0 + w_lid)).astype(np.float32)
    geo_c2 = ((0.35 * rtp_c2 + 0.20 * grav_c2 + 0.15 * base_c2 + 0.30 * topo_c2 + w_lid * lid_c2) / (1.0 + w_lid)).astype(np.float32)
    del rtp_s2, rtp_c2, grav_s2, grav_c2, base_s2, base_c2, lid_s2, lid_c2, w_lid
    spin2_coh = np.hypot(geo_s2, geo_c2).astype(np.float32)
    unit_s2 = geo_s2 / (spin2_coh + 1e-6)
    unit_c2 = geo_c2 / (spin2_coh + 1e-6)

    with rasterio.open(data_dir / "training_features.tif") as src:
        b_2nd = _read_clean_band(src, 4, fp)
        b_shear = _read_clean_band(src, 7, fp)
        b_dilat = _read_clean_band(src, 8, fp)
        b_deq = _read_clean_band(src, 10, fp)
        b_ieq = _read_clean_band(src, 16, fp)
        b_cond = _read_clean_band(src, 17, fp)
        b_det_slope = _read_clean_band(src, 19, fp)

    align_nne = 0.5 * (1.0 + unit_s2 * np.sin(np.radians(44.0)) + unit_c2 * np.cos(np.radians(44.0)))
    align_nw = 0.5 * (1.0 + unit_s2 * np.sin(np.radians(280.0)) + unit_c2 * np.cos(np.radians(280.0)))
    r_shear = _rank01_2d(b_shear, fp)
    r_dilat = _rank01_2d(b_dilat, fp)
    r_2nd = _rank01_2d(b_2nd, fp)
    coulomb_transtens = (
        spin2_coh * (0.55 * align_nne * (0.5 * r_dilat + 0.5 * r_2nd) + 0.45 * align_nw * r_shear)
    ).astype(np.float32)
    seismic_swarm = (_rank01_2d(b_ieq, fp) * (1.0 - _rank01_2d(b_deq, fp)) * (0.5 + 0.5 * r_2nd)).astype(np.float32)

    Xp_mm[:, 10] = _robust_z_fp(spin2_coh, fp)
    Xp_mm[:, 11] = geo_s2[fp]
    Xp_mm[:, 12] = geo_c2[fp]
    Xp_mm[:, 13] = _robust_z_fp(b_shear, fp)
    Xp_mm[:, 14] = _robust_z_fp(b_dilat, fp)
    Xp_mm[:, 15] = _robust_z_fp(coulomb_transtens, fp)
    Xp_mm[:, 16] = _robust_z_fp(seismic_swarm, fp)
    np.savez_compressed(cache_ori, sin2=geo_s2[fp], cos2=geo_c2[fp])
    geo_s2_fp, geo_c2_fp = geo_s2[fp].copy(), geo_c2[fp].copy()
    del spin2_coh, unit_s2, unit_c2, align_nne, align_nw, r_shear, r_dilat, r_2nd, coulomb_transtens, seismic_swarm
    del b_2nd, b_shear, b_dilat, b_deq, b_ieq, geo_s2, geo_c2
    gc.collect()

    # Pass 3: Hydrothermal fault-valve upflow, geothermometer disequilibrium, MT & radiometrics
    t2m_anom, t2m_pres = _load_2m_probes(ext / "2m_temperature_probe_INGENIOUS_regional_data.zip", shape)
    sinter_halo = _load_paleo_sinter(ext / "paleo_geothermal_regional.zip", shape)
    spring_temp, geotherm_diseq, vent_halo = _load_wellspring_and_vents(ext, shape)
    mt_clay_edge, _, _ = _grad_mag_and_strike(b_cond, fp, sigma=2.5)

    with rasterio.open(ext / "acquisition_block_id_100m.tif") as src:
        acq_block = src.read(1)
    with rasterio.open(ext / "geodawn_rad_u8.tif") as src:
        k_u8 = src.read(1)
    rad_k_bn = _block_norm_u8(k_u8, acq_block, fp)
    rad_uk_bn = _block_norm_u8(uk_u8, acq_block, fp)
    del k_u8, uk_u8, acq_block

    playa_evap = np.clip((1.0 - _rank01_2d(slope_p90, fp)) * _rank01_2d(b_cond, fp), 0.0, 1.0)
    rad_uk_deconf = (rad_uk_bn - 1.5 * playa_evap).astype(np.float32)
    del b_cond, playa_evap, rad_uk_bn

    r_hydro_sum = np.zeros(shape, np.float32)
    r_hydro_sum[fp] = (
        0.30 * _rank01(t2m_anom[fp])
        + 0.25 * _rank01(sinter_halo[fp])
        + 0.25 * _rank01(geotherm_diseq[fp])
        + 0.20 * _rank01(mt_clay_edge[fp])
    )
    upflow_conduit = (r_hydro_sum * subsurf_edge * (0.5 + 0.5 * piedmont_win)).astype(np.float32)

    Xp_mm[:, 17] = _robust_z_fp(t2m_anom, fp)
    Xp_mm[:, 18] = t2m_pres[fp]
    Xp_mm[:, 19] = _robust_z_fp(sinter_halo, fp)
    Xp_mm[:, 20] = _robust_z_fp(spring_temp, fp)
    Xp_mm[:, 21] = _robust_z_fp(geotherm_diseq, fp)
    Xp_mm[:, 22] = _robust_z_fp(vent_halo, fp)
    Xp_mm[:, 23] = _robust_z_fp(mt_clay_edge, fp)
    Xp_mm[:, 24] = rad_k_bn[fp]
    Xp_mm[:, 25] = _robust_z_fp(rad_uk_deconf, fp)
    Xp_mm[:, 26] = _robust_z_fp(upflow_conduit, fp)
    del t2m_anom, t2m_pres, sinter_halo, spring_temp, geotherm_diseq, vent_halo, mt_clay_edge, rad_k_bn, rad_uk_deconf, r_hydro_sum, upflow_conduit, subsurf_edge, piedmont_win
    gc.collect()

    # Pass 4: Geomorphology, fluvial chi, & Lahontan / road deconfounders
    ex_f = np.where(lid_valid, (((lid_ex.astype(np.float32) - 1.0) / 254.0) ** 2) * 1.5, 0.0)
    step_f = np.where(lid_valid, ((lid_step.astype(np.float32) - 1.0) / 254.0) ** 2, 0.0)
    lap_f = np.where(
        lid_valid,
        ((((lid_lapn.astype(np.float32) - 1.0) / 254.0) ** 2) + (((lid_lapp.astype(np.float32) - 1.0) / 254.0) ** 2)) * 0.05,
        0.0,
    )
    lid_raw = (0.40 * step_f + 0.35 * ex_f + 0.25 * lap_f * 10.0) * (0.4 + 0.6 * lid_coh_f)
    del lid_ex, lid_step, lid_lapn, lid_lapp, ex_f, step_f, lap_f, lid_coh_f
    lid_scarp_z = np.zeros(shape, np.float32)
    if lid_valid.any():
        lv = lid_raw[lid_valid]
        lmed = float(np.median(lv))
        lmad = max(float(np.median(np.abs(lv - lmed))) * 1.4826, 1e-4)
        lid_scarp_z[lid_valid] = np.clip((lv - lmed) / lmad, -5.0, 8.0)
    del lid_raw

    topo10_raw = np.where(
        topo_valid,
        (0.35 * (slope_p90 / 255.0) + 0.30 * (curv_prof / 255.0) + 0.35 * (hs_lin / 255.0))
        * (0.4 + 0.6 * (asp_coh / 255.0)),
        0.0,
    ).astype(np.float32)
    del slope_p90, curv_prof, asp_coh, hs_lin, topo_valid

    det_ridge = (
        0.6 * _hessian_ridge(b_det_slope, fp, sigma=1.2)
        + 0.4 * _hessian_ridge(topo10_raw, fp, sigma=1.5)
    ).astype(np.float32)
    del b_det_slope

    with rasterio.open(ext / "dem10_chi_100m_i16.tif") as src:
        chi_step = src.read(1)
        ksn_max = src.read(3)
        zmean_m = src.read(5).astype(np.float32)

    ch_valid = fp & (chi_step != -32768) & (ksn_max != -32768)
    chi_pt = np.where(
        ch_valid,
        np.log1p(np.abs(chi_step.astype(np.float32)) / 100.0) * np.log1p(np.maximum(ksn_max.astype(np.float32), 0.0)),
        0.0,
    ).astype(np.float32)
    del chi_step, ksn_max, ch_valid
    chi_knick = ndi.gaussian_filter(chi_pt, sigma=2.0).astype(np.float32)
    chi_subsurf = (chi_knick * (0.5 * r_grav + 0.5 * r_base_grad)).astype(np.float32)
    del chi_pt, r_base_grad

    z_clean = np.where(fp & (zmean_m > 0), zmean_m, 1500.0)
    del zmean_m
    lah_elev = np.maximum(
        np.exp(-0.5 * ((z_clean - 1335.0) / 20.0) ** 2),
        0.85 * np.exp(-0.5 * ((z_clean - 1398.0) / 22.0) ** 2),
    ).astype(np.float32)
    _, z_s2, z_c2 = _grad_mag_and_strike(z_clean, fp, sigma=5.0)
    scarp_contour_tangency = np.clip(0.5 * (1.0 + topo_s2 * z_s2 + topo_c2 * z_c2), 0.0, 1.0)
    lahontan_terrace = (lah_elev * scarp_contour_tangency * np.clip(1.0 - r_grav, 0.0, 1.0)).astype(np.float32)
    del z_clean, lah_elev, z_s2, z_c2, topo_s2, topo_c2, scarp_contour_tangency, r_grav

    with rasterio.open(ext / "tiger_road_distance_m.tif") as src:
        d_road = src.read(1).astype(np.float32)
    road_prox = np.exp(-np.clip(np.where(np.isfinite(d_road), d_road, 5000.0), 0.0, 10000.0) / 120.0).astype(np.float32)
    del d_road

    r_scarp_comb = np.zeros(shape, np.float32)
    r_scarp_comb[fp] = (
        0.35 * _rank01(np.maximum(lid_scarp_z[fp], 0.0))
        + 0.35 * _rank01(topo10_raw[fp])
        + 0.30 * _rank01(det_ridge[fp])
    )
    scarp_clean = (
        r_scarp_comb * (1.0 - 0.65 * lahontan_terrace) * (1.0 - 0.55 * road_prox)
    ).astype(np.float32)

    Xp_mm[:, 27] = lid_valid[fp].astype(np.float32)
    Xp_mm[:, 28] = lid_scarp_z[fp]
    Xp_mm[:, 29] = _robust_z_fp(topo10_raw, fp)
    Xp_mm[:, 30] = _robust_z_fp(det_ridge, fp)
    Xp_mm[:, 31] = _robust_z_fp(chi_knick, fp)
    Xp_mm[:, 32] = _robust_z_fp(chi_subsurf, fp)
    Xp_mm[:, 33] = _robust_z_fp(lahontan_terrace, fp)
    Xp_mm[:, 34] = _robust_z_fp(road_prox, fp)
    Xp_mm[:, 35] = _robust_z_fp(scarp_clean, fp)
    Xp_mm.flush()
    del lid_valid, lid_scarp_z, topo10_raw, det_ridge, chi_knick, chi_subsurf, lahontan_terrace, road_prox, r_scarp_comb, scarp_clean
    del Xp_mm, Xb_mm
    gc.collect()

    return (
        np.load(cache_phys, mmap_mode="r"),
        np.load(cache_b19, mmap_mode="r"),
        geo_s2_fp,
        geo_c2_fp,
    )


def compute_visible_anatomy_fp(
    visible: np.ndarray,
    fp: np.ndarray,
    sense_src_raw: np.ndarray,
    d1_floor_px: float = 3.5,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute 16 scale-smooth structural coupling features strictly from ``visible``."""
    vis = np.asarray(visible, bool) & fp
    if not vis.any():
        raise ValueError("visible fault mask is empty")

    strike_v, coh_v = local_strike(vis, smooth_px=3.0)
    seg, n_seg = segments(vis, max_len_px=12)[:2]
    tab = segment_table(seg, n_seg)
    thf = two_host_frame(vis)

    ys, xs = np.nonzero(fp)
    d1 = thf["d1"][ys, xs]
    ay1, ax1 = thf["iy1"][ys, xs], thf["ix1"][ys, xs]
    c1 = thf["c1"][ys, xs]
    d2 = thf["d2"][ys, xs]
    ay2, ax2 = thf["iy2"][ys, xs], thf["ix2"][ys, xs]
    c2 = thf["c2"][ys, xs]
    comp_len = thf["comp_len"]
    del thf
    gc.collect()

    def _anchor_strike(ay: np.ndarray, ax: np.ndarray) -> np.ndarray:
        anc_s = seg[ay, ax]
        sa = strike_v[ay, ax]
        ss = tab.strike[np.clip(anc_s, 0, len(tab.strike) - 1)]
        s = np.where(np.isfinite(sa), sa, ss)
        return np.where(np.isfinite(s), s, 0.0).astype(np.float32)

    s1 = _anchor_strike(ay1, ax1)
    s2 = _anchor_strike(ay2, ax2)
    anc_coh = np.where(np.isfinite(coh_v[ay1, ax1]), np.clip(coh_v[ay1, ax1], 0.0, 1.0), 0.0).astype(np.float32)
    del strike_v, coh_v, seg

    dy1 = (ys - ay1).astype(np.float32)
    dx1 = (xs - ax1).astype(np.float32)
    del ay1, ax1
    d_par, d_perp, side = offset_components(dy1, dx1, s1)
    d_par_abs = np.abs(d_par).astype(np.float32)
    d_perp = d_perp.astype(np.float32)
    del d_par

    u1y = dy1 / (d1 + 1e-4)
    u1x = dx1 / (d1 + 1e-4)
    del dy1, dx1
    dy2 = (ys - ay2).astype(np.float32)
    dx2 = (xs - ax2).astype(np.float32)
    del ay2, ax2
    u2y = dy2 / (d2 + 1e-4)
    u2x = dx2 / (d2 + 1e-4)
    del dy2, dx2

    Xa = np.empty((ys.size, 16), np.float32)
    Xa[:, 0] = np.log1p(np.maximum(d1, d1_floor_px))
    Xa[:, 1] = np.log1p(np.maximum(d_perp, 2.0))
    Xa[:, 2] = np.log1p(d_par_abs)
    Xa[:, 3] = d_par_abs / (d1 + 1.5)
    Xa[:, 4] = side
    Xa[:, 5] = np.log1p(comp_len[np.clip(c1, 0, len(comp_len) - 1)])
    Xa[:, 6] = anc_coh
    Xa[:, 7] = np.log1p(np.minimum(d2, 500.0))
    Xa[:, 8] = np.minimum(d1, d2) / np.maximum(d1 + d2, 1e-4)
    Xa[:, 9] = np.clip(-(u1y * u2y + u1x * u2x), -1.0, 1.0)
    Xa[:, 10] = np.cos(np.radians(2.0 * (s1 - s2)))
    Xa[:, 11] = np.log1p(comp_len[np.clip(c2, 0, len(comp_len) - 1)])
    del side, anc_coh, u1y, u1x, u2y, u2x, s1, s2, c1, c2, d2

    vis_f = vis.astype(np.float32)
    Xa[:, 12] = np.log1p(ndi.gaussian_filter(vis_f, sigma=8.0)[ys, xs] * 200.0)
    Xa[:, 13] = np.log1p(ndi.gaussian_filter(vis_f, sigma=25.0)[ys, xs] * 600.0)
    Xa[:, 14] = np.log1p(ndi.gaussian_filter(vis_f, sigma=75.0)[ys, xs] * 1800.0)
    del vis_f
    Xa[:, 15] = kinematic_transition_field(vis, sense_src_raw, smooth_px=15.0)[ys, xs]
    del ys, xs
    gc.collect()
    return Xa, d1, d_perp, d_par_abs


def _predict_hgb_batched(clf: HistGradientBoostingClassifier, X: np.ndarray, batch: int = 400_000) -> np.ndarray:
    out = np.empty(X.shape[0], np.float32)
    for start in range(0, X.shape[0], batch):
        out[start:start + batch] = clf.predict_proba(np.asarray(X[start:start + batch], np.float32))[:, 1].astype(np.float32)
    return out


def _robust_z_fp_1d(v: np.ndarray, clip: float = 8.0) -> np.ndarray:
    med = float(np.median(v))
    mad = max(float(np.median(np.abs(v - med))) * 1.4826, float(np.std(v)), 1e-6)
    return np.clip((v - med) / mad, -clip, clip).astype(np.float32)


def fit_predict_stage_a_loqo(
    X_phys: np.ndarray,
    fp: np.ndarray,
    quad: np.ndarray,
    visible: np.ndarray,
    seed: int = 84,
    n_neg_per_fold: int = 220_000,
    erode_px: int = 12,
) -> np.ndarray:
    """4-quadrant spatially cross-fitted pure-physics model (ZERO catalogue features)."""
    vis = np.asarray(visible, bool) & fp
    d_vis_fp = ndi.distance_transform_edt(~vis)[fp]
    vis_fp = vis[fp]
    quad_fp = quad[fp]

    oof_prob = np.zeros(X_phys.shape[0], np.float32)
    for q in range(4):
        test_q = quad == q
        forbidden = ndi.binary_dilation(test_q, iterations=erode_px)
        train_dom_fp = (fp & ~forbidden & (quad >= 0))[fp]

        pos_idx = np.flatnonzero(train_dom_fp & vis_fp)
        neg_pool = np.flatnonzero(train_dom_fp & (d_vis_fp > 5.0))
        rng = np.random.default_rng(seed * 100 + q)
        neg_idx = rng.choice(neg_pool, min(n_neg_per_fold, neg_pool.size), replace=False)

        tr_idx = np.concatenate([pos_idx, neg_idx])
        X_tr = np.asarray(X_phys[tr_idx], np.float32)
        y_tr = np.concatenate([np.ones(pos_idx.size, np.int8), np.zeros(neg_idx.size, np.int8)])

        clf = HistGradientBoostingClassifier(
            max_iter=240,
            learning_rate=0.06,
            max_leaf_nodes=47,
            min_samples_leaf=180,
            l2_regularization=2.0,
            random_state=seed * 10 + q,
        )
        clf.fit(X_tr, y_tr)
        del X_tr, y_tr

        te_idx = np.flatnonzero(quad_fp == q)
        raw_p = _predict_hgb_batched(clf, X_phys[te_idx])
        pi_sample = pos_idx.size / max(pos_idx.size + neg_idx.size, 1)
        pi_true = pos_idx.size / max(int(train_dom_fp.sum()), 1)
        odds_scale = (pi_true / max(1.0 - pi_true, 1e-6)) / max(pi_sample / max(1.0 - pi_sample, 1e-6), 1e-6)
        p_clip = np.clip(raw_p, 1e-6, 1.0 - 1e-6)
        odds = (p_clip / (1.0 - p_clip)) * odds_scale
        oof_prob[te_idx] = (odds / (1.0 + odds)).astype(np.float32)

    del d_vis_fp
    p2d = np.zeros(fp.shape, np.float32)
    p2d[fp] = oof_prob
    r1 = _hessian_ridge(p2d, fp, sigma=1.1)[fp]
    r2 = _hessian_ridge(p2d, fp, sigma=2.2)[fp]
    cont = ndi.gaussian_filter(p2d, sigma=3.0)[fp].astype(np.float32)
    del p2d
    gc.collect()

    return np.column_stack([
        oof_prob,
        _robust_z_fp_1d(r1),
        _robust_z_fp_1d(r2),
        _robust_z_fp_1d(cont),
    ]).astype(np.float32)


def _make_inner_component_split(
    train_vis: np.ndarray, rng: np.random.Generator, hide_frac: float = 0.22, buffer_px: int = 3
) -> Tuple[np.ndarray, np.ndarray]:
    comp, ncomp = ndi.label(train_vis, structure=STRUCT3)
    if ncomp < 4:
        raise ValueError("insufficient training components for inner split")
    sizes = np.bincount(comp.ravel(), minlength=ncomp + 1)
    ids = np.arange(1, ncomp + 1)
    perm = rng.permutation(ids)
    target = hide_frac * float(train_vis.sum())
    k = min(int(np.searchsorted(np.cumsum(sizes[perm]), target)) + 1, perm.size - 2)
    chosen = perm[:max(k, 1)]
    inner_hid = np.isin(comp, chosen) & train_vis
    collar = ndi.distance_transform_edt(~inner_hid) <= buffer_px
    inner_vis = train_vis & ~collar
    return inner_vis, inner_hid


_STAGE_B_PHYS_IDX: Tuple[int, ...] = (
    3, 4, 7, 9, 10, 15, 16, 17, 19, 21, 26, 28, 32, 33, 34, 35,
)


def fit_predict_stage_b_loqo(
    X_phys: np.ndarray,
    stage_a_oof: np.ndarray,
    fp: np.ndarray,
    quad: np.ndarray,
    visible: np.ndarray,
    sense_src_raw: np.ndarray,
    seed: int = 84,
    phys_idx: Tuple[int, ...] = _STAGE_B_PHYS_IDX,
    Xa_outer: np.ndarray | None = None,
    n_inner_draws: int = 2,
    n_neg_per_draw: int = 140_000,
    erode_px: int = 12,
) -> Tuple[np.ndarray, np.ndarray]:
    """4-quadrant LOQO meta-model trained via inner whole-component splits of ``visible``."""
    vis = np.asarray(visible, bool) & fp
    quad_fp = quad[fp]
    if Xa_outer is None:
        Xa_outer, _, _, _ = compute_visible_anatomy_fp(vis, fp, sense_src_raw)
    pidx = list(phys_idx)

    oof_p = np.zeros(X_phys.shape[0], np.float32)

    for q in range(4):
        test_q = quad == q
        forbidden = ndi.binary_dilation(test_q, iterations=erode_px)
        train_dom = fp & ~forbidden & (quad >= 0)
        train_dom_fp = train_dom[fp]
        train_vis = vis & train_dom

        X_tr_parts: List[np.ndarray] = []
        y_tr_parts: List[np.ndarray] = []
        odds_scales: List[float] = []

        for d_idx in range(n_inner_draws):
            rng = np.random.default_rng(seed * 1000 + q * 37 + d_idx)
            inner_vis, inner_hid = _make_inner_component_split(
                train_vis, rng, hide_frac=0.22, buffer_px=3
            )
            Xa_in, d1_in, _, _ = compute_visible_anatomy_fp(inner_vis, fp, sense_src_raw)
            uncensored = train_dom_fp & (d1_in > 3.0)
            hid_fp = inner_hid[fp] & uncensored
            pos_i = np.flatnonzero(hid_fp)
            neg_pool = np.flatnonzero(uncensored & ~hid_fp)
            neg_i = rng.choice(neg_pool, min(n_neg_per_draw, neg_pool.size), replace=False)

            sel = np.concatenate([pos_i, neg_i])
            X_draw = np.hstack([
                stage_a_oof[sel],
                np.asarray(X_phys[sel][:, pidx], np.float32),
                Xa_in[sel],
            ])
            y_draw = np.concatenate([np.ones(pos_i.size, np.int8), np.zeros(neg_i.size, np.int8)])
            X_tr_parts.append(X_draw)
            y_tr_parts.append(y_draw)

            pi_s = pos_i.size / max(pos_i.size + neg_i.size, 1)
            pi_t = pos_i.size / max(int(uncensored.sum()), 1)
            odds_scales.append((pi_t / max(1.0 - pi_t, 1e-6)) / max(pi_s / max(1.0 - pi_s, 1e-6), 1e-6))
            del Xa_in, d1_in, inner_vis, inner_hid
            gc.collect()

        X_tr = np.vstack(X_tr_parts)
        y_tr = np.concatenate(y_tr_parts)
        del X_tr_parts, y_tr_parts
        clf = HistGradientBoostingClassifier(
            max_iter=220,
            learning_rate=0.055,
            max_leaf_nodes=39,
            min_samples_leaf=220,
            l2_regularization=3.0,
            random_state=seed * 50 + q,
        )
        clf.fit(X_tr, y_tr)
        del X_tr, y_tr

        te_idx = np.flatnonzero(quad_fp == q)
        X_te = np.hstack([
            stage_a_oof[te_idx],
            np.asarray(X_phys[te_idx][:, pidx], np.float32),
            Xa_outer[te_idx],
        ])
        raw_p = _predict_hgb_batched(clf, X_te)
        del X_te, clf

        oscale = float(np.mean(odds_scales))
        p_clip = np.clip(raw_p, 1e-6, 1.0 - 1e-6)
        odds = (p_clip / (1.0 - p_clip)) * oscale
        oof_p[te_idx] = (odds / (1.0 + odds)).astype(np.float32)
        gc.collect()

    phys_prob = stage_a_oof[:, 0]
    phys_ridge = np.clip(0.5 + 0.22 * stage_a_oof[:, 1] + 0.12 * stage_a_oof[:, 2], 0.35, 1.85)
    phys_rel = np.clip(phys_prob / max(float(np.median(phys_prob)), 1e-5), 0.30, 3.50)
    blended_fp = np.clip(oof_p * (0.45 + 0.55 * np.sqrt(phys_rel)) * phys_ridge, 0.0, 1.0).astype(np.float32)
    s_raw = float(oof_p.sum())
    s_bl = float(blended_fp.sum())
    if s_bl > 0:
        blended_fp = np.clip(blended_fp * (s_raw / s_bl), 0.0, 1.0).astype(np.float32)

    p2d = np.zeros(fp.shape, np.float32)
    p2d[fp] = blended_fp
    return p2d, oof_p


def anisotropic_allowed_mask(
    fp: np.ndarray,
    visible: np.ndarray,
    d1_fp: np.ndarray,
    dperp_fp: np.ndarray,
    dpar_fp: np.ndarray,
    phys_prob_fp: np.ndarray,
    lateral_collar_px: float = 2.0,
) -> np.ndarray:
    vis = np.asarray(visible, bool) & fp
    p_med = float(np.median(phys_prob_fp))
    is_tip_ext = (d1_fp > 1.0) & (dpar_fp > 1.25 * dperp_fp) & (phys_prob_fp > 1.15 * p_med)
    keep_fp = (d1_fp > lateral_collar_px) | is_tip_ext
    allowed = np.zeros(fp.shape, bool)
    allowed[fp] = keep_fp
    allowed &= fp & ~vis
    return allowed


def concealed_blind_basin_score_fp(X_phys: np.ndarray, X_base19: np.ndarray) -> np.ndarray:
    """Catalogue-free subsurface + hydrothermal score for concealed basin interiors.

    Combines buried basement-depth gradient (pf_base_grad), magnetic & gravity
    tilt-angle zero-crossing sharpness, Walker Lane transtensional Coulomb
    alignment, microseismic swarm differential, and INGENIOUS 2 m temperature
    probe + paleo-sinter + chemical geothermometer disequilibrium halos on
    low-relief alluvial cover (det_elev_slope z < -0.05). Zero registry or
    catalogue inputs are consulted.
    """
    hydro_comp = (
        0.35 * np.asarray(X_phys[:, 17], np.float32)
        + 0.35 * np.asarray(X_phys[:, 19], np.float32)
        + 0.30 * np.asarray(X_phys[:, 21], np.float32)
    )
    raw = (
        0.26 * np.asarray(X_phys[:, 8], np.float32)
        + 0.16 * np.asarray(X_phys[:, 1], np.float32)
        + 0.14 * np.asarray(X_phys[:, 6], np.float32)
        + 0.16 * np.asarray(X_phys[:, 15], np.float32)
        + 0.14 * np.asarray(X_phys[:, 16], np.float32)
        + 0.14 * hydro_comp
    )
    pos = raw - float(raw.min()) + 0.05
    low_relief_cover = (np.asarray(X_base19[:, 18], np.float32) < -0.05).astype(np.float32)
    return (pos * low_relief_cover).astype(np.float32)


def emit_twostrat_nms3(
    fp: np.ndarray,
    visible: np.ndarray,
    p_tcdh_fp: np.ndarray,
    phys_prob_fp: np.ndarray,
    blind_basin_fp: np.ndarray,
    d1_fp: np.ndarray,
    dperp_fp: np.ndarray,
    dpar_fp: np.ndarray,
    n_corridor: int = 22_000,
    n_far_blind: int = 15_654,
    far_min_dist_px: float = 36.0,
    sep_px: int = 3,
) -> Tuple[np.ndarray, np.ndarray]:
    """Two-stratum sep=3 px (300 m) kernel-separated dot allocator + unified continuous surface.

    Stratum 1 (n_corridor dots): Highest LOQO H84-TCDH fault posteriors across
    anisotropic tip-extensions, relay step-overs, and range-piedmont structures.
    Stratum 2 (n_far_blind dots): Highest concealed subsurface basement/hydrothermal/
    Coulomb lineaments in unexplored basin interiors (d_vis > far_min_dist_px) under
    low-relief alluvial cover, separated by >= sep_px from Stratum 1.

    Returns (emitted_bool_2d, unified_surface_2d).
    """
    vis = np.asarray(visible, bool) & fp
    allowed = anisotropic_allowed_mask(fp, vis, d1_fp, dperp_fp, dpar_fp, phys_prob_fp, lateral_collar_px=2.0)

    s_corr = np.zeros(fp.shape, np.float32)
    s_corr[fp] = np.clip(p_tcdh_fp, 0.0, 1.0)
    s_corr[vis] = 0.0
    em1 = greedy_thin_fixed_sep(s_corr, allowed, max_dots=n_corridor, sep_px=sep_px)

    far_score_fp = blind_basin_fp * (d1_fp > far_min_dist_px).astype(np.float32)
    # Normalize far_score_fp into [0, 0.5] so unified surface remains strictly in [0, 1]
    fmax = max(float(far_score_fp.max()), 1e-6)
    s_far = np.zeros(fp.shape, np.float32)
    s_far[fp] = 0.50 * (far_score_fp / fmax)
    s_far[vis] = 0.0

    # Enforce strict >= sep_px (300 m) separation between Stratum 1 and Stratum 2
    yy, xx = np.mgrid[-sep_px:sep_px + 1, -sep_px:sep_px + 1]
    excl1 = ndi.binary_dilation(em1, structure=(yy * yy + xx * xx) <= sep_px * sep_px)
    em2 = greedy_thin_fixed_sep(s_far, allowed & ~excl1, max_dots=n_far_blind, sep_px=sep_px)

    unified_surface = np.clip(np.maximum(s_corr, 0.35 * s_far), 0.0, 1.0).astype(np.float32)
    unified_surface[~fp] = 0.0
    unified_surface[vis] = 0.0
    return (em1 | em2), unified_surface


def greedy_thin_fixed_sep(
    score2d: np.ndarray, allowed: np.ndarray, max_dots: int = 37_654, sep_px: int = 3
) -> np.ndarray:
    cand = allowed & (score2d > 0)
    ys, xs = np.nonzero(cand)
    if ys.size == 0:
        return np.zeros(score2d.shape, bool)
    order = np.argsort(-score2d[ys, xs], kind="stable")
    ys, xs = ys[order], xs[order]
    H, W = score2d.shape
    blocked = np.zeros(score2d.shape, bool)
    emitted = np.zeros(score2d.shape, bool)
    dy, dx = np.mgrid[-sep_px:sep_px + 1, -sep_px:sep_px + 1]
    in_disc = (dy * dy + dx * dx) <= sep_px * sep_px
    oy, ox = dy[in_disc], dx[in_disc]
    n = 0
    for i in range(ys.size):
        if n >= max_dots:
            break
        y, x = int(ys[i]), int(xs[i])
        if blocked[y, x]:
            continue
        emitted[y, x] = True
        n += 1
        ny = np.clip(y + oy, 0, H - 1)
        nx = np.clip(x + ox, 0, W - 1)
        blocked[ny, nx] = True
    return emitted
