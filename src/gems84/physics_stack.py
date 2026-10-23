"""Zero-leakage static multi-physics, harmonic upward-continuation pullback (HUPW),
and DOE GDR-1391 INGENIOUS geothermal upflow feature stack for Lane H84-B (CTHF).

Memory contract (designed for 3.8 GiB RAM, 0 swap):
  * Stores all static channels in a disk-backed float16 memmap of shape (N_fp, F).
  * Processes one modality block at a time and explicitly releases full-grid float32
    scratch buffers, keeping resident RAM strictly below ~650 MiB.
  * ZERO label / fault-catalogue information is read anywhere in this module;
    in external GDR CSVs, ``dist_known_fault_px`` is explicitly skipped by name.
"""
from __future__ import annotations

import csv
import gc
import io
import json
import struct
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform as warp_transform
from scipy import ndimage as ndi

from .paths import EXTERNAL, FEATURES_TIF, WORK

STACK_VERSION = "h84b_static_v1"
PIXEL_M = 100.0
ORIGIN_X = 243350.0
ORIGIN_Y = 4508550.0


def _read_feature_band(idx: int, fp: np.ndarray) -> np.ndarray:
    with rasterio.open(FEATURES_TIF) as src:
        a = src.read(idx).astype(np.float32)
        nod = src.nodata
    bad = ~np.isfinite(a) | (a <= -1e30) | ((nod is not None) & (a == np.float32(nod)))
    a[bad | ~fp] = np.nan
    return a


def _fill_nearest(a: np.ndarray) -> np.ndarray:
    bad = ~np.isfinite(a)
    if not bad.any():
        return a.astype(np.float32, copy=False)
    if bad.all():
        return np.zeros(a.shape, np.float32)
    idx = ndi.distance_transform_edt(bad, return_distances=False, return_indices=True)
    return a[tuple(idx)].astype(np.float32, copy=False)


def _zscore_clip(v: np.ndarray, clip: float = 8.0) -> np.ndarray:
    """Robust median/MAD standardization clipped to [-clip, +clip] for float16 precision."""
    x = np.asarray(v, np.float32)
    ok = np.isfinite(x)
    if not ok.any():
        return np.zeros(x.shape, np.float16)
    med = float(np.median(x[ok]))
    mad = float(np.median(np.abs(x[ok] - med))) * 1.4826
    if mad < 1e-6:
        mad = float(np.std(x[ok]))
    scale = max(mad, 1e-6)
    out = np.full(x.shape, np.nan, np.float32)
    out[ok] = np.clip((x[ok] - med) / scale, -clip, clip)
    return out.astype(np.float16)


def _rank01_fp(arr2d: np.ndarray, fp: np.ndarray) -> np.ndarray:
    v = arr2d[fp].astype(np.float32)
    out = np.zeros(v.shape, np.float32)
    ok = np.isfinite(v)
    if ok.any():
        order = np.argsort(v[ok], kind="stable")
        r = np.empty(order.size, np.float32)
        r[order] = (np.arange(order.size, dtype=np.float32) + 0.5) / order.size
        out[ok] = r
    out2d = np.zeros(fp.shape, np.float32)
    out2d[fp] = out
    return out2d


def _hessian_crest_and_strike(f_filled: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Scale-normalized ridge crest -(min eigenvalue), trough +(max eigenvalue), and tangent angle."""
    hyy = ndi.gaussian_filter(f_filled, sigma, order=(2, 0))
    hxx = ndi.gaussian_filter(f_filled, sigma, order=(0, 2))
    hxy = ndi.gaussian_filter(f_filled, sigma, order=(1, 1))
    tr = 0.5 * (hxx + hyy)
    disc = np.hypot(0.5 * (hxx - hyy), hxy)
    s2 = np.float32(sigma * sigma)
    crest = s2 * np.maximum(-(tr - disc), 0.0)
    trough = s2 * np.maximum(tr + disc, 0.0)
    # Normal to ridge is eigenvector of minimum (most negative) eigenvalue; tangent is +90 deg
    normal_ang = 0.5 * np.arctan2(-2.0 * hxy, -(hxx - hyy))
    strike_ang = normal_ang + 0.5 * np.pi
    return crest.astype(np.float32), trough.astype(np.float32), strike_ang.astype(np.float32)


def spectral_upward_continue(field_filled: np.ndarray, heights_m: tuple[float, ...],
                             dx_m: float = PIXEL_M) -> list[np.ndarray]:
    """Exact 2D Laplace equation harmonic upward continuation in radial wavenumber space:
    U_hat(kx, ky; h) = U_hat(kx, ky; 0) * exp(-h * sqrt(kx^2 + ky^2)), h > 0.
    Uses mirror-padded edge taper to suppress wrap-around ringing at grid borders.
    """
    H, W = field_filled.shape
    pad = 96
    padded = np.pad(field_filled.astype(np.float32), ((pad, pad), (pad, pad)), mode="reflect")
    ph, pw = padded.shape
    # Subtract planar trend before FFT, add back afterward
    med = float(np.median(padded))
    spec = np.fft.rfft2(padded - med)
    ky = (2.0 * np.pi * np.fft.fftfreq(ph, d=dx_m)).astype(np.float32)[:, None]
    kx = (2.0 * np.pi * np.fft.rfftfreq(pw, d=dx_m)).astype(np.float32)[None, :]
    kr = np.hypot(ky, kx)
    outs = []
    for h_m in heights_m:
        att = np.exp(-float(h_m) * kr).astype(np.float32)
        up = np.fft.irfft2(spec * att, s=(ph, pw))[pad:pad + H, pad:pad + W] + med
        outs.append(up.astype(np.float32))
    return outs


def _updip_pullback(field2d: np.ndarray, dy_fw: np.ndarray, dx_fw: np.ndarray,
                    shift_px: np.ndarray) -> np.ndarray:
    """Shift hanging-wall potential-field anomalies up-dip back to the fault subcrop trace.

    If a 60-deg dipping normal fault subcrops at x_trace and dips in direction -e_fw
    (into the basin), its basement anomaly centers at x_trace - shift * e_fw.
    Evaluating field(x - shift * e_fw) at candidate trace location x samples the
    hanging-wall anomaly generated by a fault breaking the surface at x.
    """
    H, W = field2d.shape
    yy, xx = np.indices((H, W), dtype=np.float32)
    sy = np.clip(yy - shift_px * dy_fw, 0.0, H - 1.001)
    sx = np.clip(xx - shift_px * dx_fw, 0.0, W - 1.001)
    return ndi.map_coordinates(field2d, [sy, sx], order=1, mode="nearest").astype(np.float32)


def _utm_to_rc(utm_x: np.ndarray, utm_y: np.ndarray, shape: tuple[int, int]):
    cols = np.floor((utm_x - ORIGIN_X) / PIXEL_M).astype(np.int32)
    rows = np.floor((ORIGIN_Y - utm_y) / PIXEL_M).astype(np.int32)
    ok = (rows >= 0) & (rows < shape[0]) & (cols >= 0) & (cols < shape[1])
    return rows[ok], cols[ok], ok


def build_geothermal_fields(fp: np.ndarray) -> dict[str, np.ndarray]:
    """Construct strictly label-free DOE GDR-1391 INGENIOUS geothermal upflow channels:
      1. 3,800 2-meter shallow temperature probes (F2mDAB & T2m, Coolbaugh et al., 2007)
      2. 709 Quaternary siliceous sinter, travertine & tufa paleovents (Ayling, 2020)
      3. 27,092 spring/well Quartz/Chalcedony/Cation geothermometers (dist_known_fault_px NOT read!)
      4. 21 Quaternary basaltic/bimodal volcanic vents (dist_known_fault_px NOT read!)
    """
    H, W = fp.shape

    # 1. Shallow 2m temperature probes (INGENIOUS DBF)
    f2m_grid = np.zeros((H, W), np.float32)
    t2m_grid = np.zeros((H, W), np.float32)
    with zipfile.ZipFile(EXTERNAL / "2m_temperature_probe_INGENIOUS_regional_data.zip") as z:
        dbf = z.read("2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf")
    num_rec, hdr_len, rec_len = struct.unpack("<4xIHH20x", dbf[:32])
    fields = []
    pos = 32
    while dbf[pos] != 0x0D:
        fname = dbf[pos:pos + 11].split(b"\x00", 1)[0].decode("ascii", "replace")
        flen = dbf[pos + 16]
        fields.append((fname, flen))
        pos += 32
    lons, lats, t2ms, f2ms = [], [], [], []
    for ri in range(num_rec):
        rec = dbf[hdr_len + ri * rec_len + 1: hdr_len + (ri + 1) * rec_len]
        off = 0
        row_d = {}
        for fname, flen in fields:
            if fname in ("LatDegreeN", "LongDegree", "T2m", "F2mDAB"):
                row_d[fname] = rec[off:off + flen].decode("ascii", "replace").strip()
            off += flen
        try:
            lo = float(row_d["LongDegree"])
            la = float(row_d["LatDegreeN"])
            t2 = float(row_d["T2m"]) if row_d["T2m"] else 0.0
            f2 = float(row_d["F2mDAB"]) if row_d["F2mDAB"] else 0.0
            if -125.0 < lo < -110.0 and 35.0 < la < 45.0:
                lons.append(lo); lats.append(la); t2ms.append(t2); f2ms.append(f2)
        except ValueError:
            continue
    if lons:
        ux, uy = warp_transform("EPSG:4269", "EPSG:32611", lons, lats)
        rr, cc, ok = _utm_to_rc(np.asarray(ux), np.asarray(uy), (H, W))
        np.maximum.at(f2m_grid, (rr, cc), np.maximum(np.asarray(f2ms, np.float32)[ok], 0.0))
        np.maximum.at(t2m_grid, (rr, cc), np.maximum(np.asarray(t2ms, np.float32)[ok] - 18.0, 0.0))

    f2m_local = ndi.gaussian_filter(f2m_grid, 3.5) * 40.0
    f2m_plume = ndi.gaussian_filter(f2m_grid + 0.25 * t2m_grid, 14.0) * 120.0

    # 2. Paleo-geothermal sinter / travertine / tufa vents
    sinter_mask = np.zeros((H, W), bool)
    with zipfile.ZipFile(EXTERNAL / "paleo_geothermal_regional.zip") as z:
        txt = z.read("Paleo_geothermal_final.csv").decode("utf-8-sig", errors="replace")
    plons, plats, pweights = [], [], []
    for row in csv.DictReader(io.StringIO(txt)):
        try:
            lo = float(row["Long_deg_NAD83"])
            la = float(row["Lat_deg_NAD83"])
            dtype = (row.get("Deposit_type") or "").lower()
            # Sinter precipitates from >180 C boiling silica fluids; travertine from CO2-rich fault upflow
            w = 1.35 if "sinter" in dtype else 1.0
            plons.append(lo); plats.append(la); pweights.append(w)
        except (ValueError, KeyError):
            continue
    sinter_imp = np.zeros((H, W), np.float32)
    if plons:
        ux, uy = warp_transform("EPSG:4269", "EPSG:32611", plons, plats)
        rr, cc, ok = _utm_to_rc(np.asarray(ux), np.asarray(uy), (H, W))
        sinter_mask[rr, cc] = True
        np.maximum.at(sinter_imp, (rr, cc), np.asarray(pweights, np.float32)[ok])
    d_sinter = ndi.distance_transform_edt(~sinter_mask).astype(np.float32) if sinter_mask.any() else np.full((H, W), 500.0, np.float32)
    sinter_near = np.exp(-d_sinter / 10.0) + 0.5 * ndi.gaussian_filter(sinter_imp, 22.0) * 80.0

    # 3. Chemical geothermometers & discharge temperatures (STRICTLY ignoring dist_known_fault_px!)
    ALLOWED_WS_COLS = {"row", "col", "temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c"}
    geotherm_excess = np.zeros((H, W), np.float32)
    spring_hot = np.zeros((H, W), np.float32)
    with (EXTERNAL / "gdr_wellspring_in_footprint.csv").open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            sub = {k: row[k] for k in ALLOWED_WS_COLS if k in row}
            try:
                r = int(float(sub["row"])); c = int(float(sub["col"]))
                if not (0 <= r < H and 0 <= c < W):
                    continue
                tc = float(sub["temp_c"]) if sub.get("temp_c") else np.nan
                gq = float(sub["geothermquartz_c"]) if sub.get("geothermquartz_c") else np.nan
                gc_ = float(sub["geothermchalc_c"]) if sub.get("geothermchalc_c") else np.nan
                gcat = float(sub["geothermcat_c"]) if sub.get("geothermcat_c") else np.nan
                t_res = np.nanmax([gq, gc_, gcat, 0.0])
                t_surf = tc if np.isfinite(tc) else 15.0
                # Convective fault-conduit disequilibrium: high reservoir SiO2/cation T relative to surface cooling
                diseq = max(t_res - max(t_surf, 14.0), 0.0)
                if diseq > 0:
                    geotherm_excess[r, c] = max(geotherm_excess[r, c], min(diseq, 240.0))
                if np.isfinite(tc) and tc > 21.0:
                    spring_hot[r, c] = max(spring_hot[r, c], min(tc - 21.0, 100.0))
            except ValueError:
                continue

    geotherm_short = ndi.gaussian_filter(geotherm_excess, 6.0) * 12.0
    geotherm_regional = ndi.gaussian_filter(geotherm_excess, 24.0) * 40.0
    hot_spring_plume = ndi.gaussian_filter(spring_hot, 9.0) * 20.0

    # 4. Quaternary volcanic vents (STRICTLY ignoring dist_known_fault_px!)
    vent_mask = np.zeros((H, W), bool)
    with (EXTERNAL / "gdr_volcanic_vents_in_footprint.csv").open() as f:
        for row in csv.DictReader(f):
            try:
                r = int(float(row["row"])); c = int(float(row["col"]))
                if 0 <= r < H and 0 <= c < W:
                    vent_mask[r, c] = True
            except (ValueError, KeyError):
                continue
    d_vent = ndi.distance_transform_edt(~vent_mask).astype(np.float32) if vent_mask.any() else np.full((H, W), 500.0, np.float32)
    vent_prox = np.exp(-d_vent / 30.0)

    return {
        "geo_f2m_local": f2m_local,
        "geo_f2m_plume": f2m_plume,
        "geo_sinter_conduit": sinter_near.astype(np.float32),
        "geo_diseq_short": geotherm_short.astype(np.float32),
        "geo_diseq_reg": geotherm_regional.astype(np.float32),
        "geo_hotspring_plume": hot_spring_plume.astype(np.float32),
        "geo_volcanic_vent": vent_prox.astype(np.float32),
    }


def load_or_build_static_stack(fp: np.ndarray) -> tuple[np.memmap, dict]:
    """Build or open the cached (N_fp, F) float16 static feature memmap + local strike array."""
    WORK.mkdir(parents=True, exist_ok=True)
    meta_path = WORK / f"{STACK_VERSION}.json"
    mmap_path = WORK / f"{STACK_VERSION}.f16"
    strike_path = WORK / f"{STACK_VERSION}_strike.f16"
    n_fp = int(fp.sum())

    if meta_path.exists() and mmap_path.exists() and strike_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("n_fp") == n_fp:
            mm = np.memmap(mmap_path, dtype=np.float16, mode="r", shape=(n_fp, len(meta["names"])))
            return mm, meta

    # Pre-allocate memmap cleanly on disk + precompute exact footprint nearest-neighbor fill index once!
    MAX_COLS = 96
    tmp_path = WORK / f"{STACK_VERSION}.part.f16"
    mm = np.memmap(tmp_path, dtype=np.float16, mode="w+", shape=(n_fp, MAX_COLS))
    fp_idx = tuple(ndi.distance_transform_edt(~fp, return_distances=False, return_indices=True))

    def fast_fill(a: np.ndarray) -> np.ndarray:
        out = a[fp_idx].astype(np.float32, copy=True)
        still_bad = ~np.isfinite(out)
        if still_bad.any():
            out = _fill_nearest(out)
        return out
    names: list[str] = []
    groups: dict[str, list[str]] = {
        "core_topo": [],
        "subsurf_hupw": [],
        "lidar_1m": [],
        "dem10_chi": [],
        "radiometric": [],
        "geothermal_ahfv": [],
    }

    def push(name: str, arr2d: np.ndarray, grp: str, keep_nan: bool = False):
        idx = len(names)
        v = arr2d[fp].astype(np.float32)
        if not keep_nan:
            v = np.where(np.isfinite(v), v, np.nan)
        mm[:, idx] = _zscore_clip(v)
        names.append(name)
        groups[grp].append(name)

    # --- Block A: Crustal Potential Fields, Harmonic Upward Continuation & 60-deg Pullback (H84-H2) ---
    dbase = _read_feature_band(15, fp)
    dbase_f = fast_fill(dbase)
    gy_b = ndi.gaussian_filter(dbase_f, 3.0, order=(1, 0))
    gx_b = ndi.gaussian_filter(dbase_f, 3.0, order=(0, 1))
    gnorm_b = np.hypot(gy_b, gx_b) + 1e-6
    # Footwall unit vector points toward shallower basement (-grad depth_to_base_surf)
    dy_fw = (-gy_b / gnorm_b).astype(np.float32)
    dx_fw = (-gx_b / gnorm_b).astype(np.float32)
    # Horizontal offset of basement anomaly center in hanging wall for ~60-deg normal fault: d * cot(60)
    shift_px = np.clip(np.maximum(dbase_f, 0.0) * 0.57735027 / PIXEL_M, 0.0, 3.5).astype(np.float32)

    push("depth_to_base", dbase, "subsurf_hupw")
    push("depth_base_grad_s2", np.hypot(
        ndi.gaussian_filter(dbase_f, 2.0, order=(1, 0)),
        ndi.gaussian_filter(dbase_f, 2.0, order=(0, 1)),
    ), "subsurf_hupw")
    b_crest, _, b_strike = _hessian_crest_and_strike(dbase_f, 2.5)
    push("depth_base_scarp_crest", b_crest, "subsurf_hupw")
    del dbase, gy_b, gx_b, gnorm_b, b_crest
    gc.collect()

    # Isostatic gravity + 4-altitude spectral upward continuation + worm persistence + pullback
    grav = _read_feature_band(13, fp)
    grav_f = fast_fill(grav)
    push("iso_grav_anom", grav, "subsurf_hupw")
    push("iso_grav_slope", _read_feature_band(5, fp), "subsurf_hupw")
    push("iso_grav_vg", _read_feature_band(11, fp), "subsurf_hupw")
    push("iso_grav_hg", _read_feature_band(18, fp), "subsurf_hupw")

    g_ups = spectral_upward_continue(grav_f, (200.0, 500.0, 1200.0, 2500.0))
    grav_worm_prod = np.ones(fp.shape, np.float32)
    for h_m, gu in zip((200, 500, 1200, 2500), g_ups):
        ghg = np.hypot(ndi.gaussian_filter(gu, 1.5, order=(1, 0)),
                       ndi.gaussian_filter(gu, 1.5, order=(0, 1)))
        w_crest, _, g_strike = _hessian_crest_and_strike(ghg, 1.8)
        grav_worm_prod *= np.maximum(_rank01_fp(w_crest, fp), 1e-4)
        if h_m in (200, 1200):
            push(f"grav_worm_h{h_m}", w_crest, "subsurf_hupw")
    grav_worm = np.power(grav_worm_prod, 0.25)
    grav_worm_pullback = _updip_pullback(grav_worm, dy_fw, dx_fw, shift_px)
    push("grav_worm_persist4", grav_worm, "subsurf_hupw")
    push("grav_worm_pullback60", grav_worm_pullback, "subsurf_hupw")
    gy_g = ndi.gaussian_filter(grav_f, 2.0, order=(1, 0))
    gx_g = ndi.gaussian_filter(grav_f, 2.0, order=(0, 1))
    del grav, g_ups, grav_worm_prod, grav_f
    gc.collect()

    # Reduced-to-Pole magnetics + 4-altitude spectral upward continuation + pullback + cross-gradient
    rtp = _read_feature_band(2, fp)
    rtp_f = fast_fill(rtp)
    push("mag_anom", _read_feature_band(1, fp), "subsurf_hupw")
    push("rtp", rtp, "subsurf_hupw")
    push("tmi_hg", _read_feature_band(3, fp), "subsurf_hupw")
    tc = _read_feature_band(6, fp)
    push("tc_tilt", tc, "subsurf_hupw")
    # Tilt derivative edge sharpness: |cos(tc)| peaks near 0-deg tilt contour directly over vertical contacts
    push("tc_zero_contour", np.cos(np.deg2rad(np.clip(fast_fill(tc), 0.0, 90.0))), "subsurf_hupw")
    push("tmi_vg", _read_feature_band(9, fp), "subsurf_hupw")
    tmi = _read_feature_band(14, fp)
    push("tmi", tmi, "subsurf_hupw")

    r_ups = spectral_upward_continue(rtp_f, (200.0, 500.0, 1200.0, 2500.0))
    rtp_worm_prod = np.ones(fp.shape, np.float32)
    for h_m, ru in zip((200, 500, 1200, 2500), r_ups):
        rhg = np.hypot(ndi.gaussian_filter(ru, 1.5, order=(1, 0)),
                       ndi.gaussian_filter(ru, 1.5, order=(0, 1)))
        w_crest, _, r_strike = _hessian_crest_and_strike(rhg, 1.8)
        rtp_worm_prod *= np.maximum(_rank01_fp(w_crest, fp), 1e-4)
        if h_m in (200, 1200):
            push(f"rtp_worm_h{h_m}", w_crest, "subsurf_hupw")
    rtp_worm = np.power(rtp_worm_prod, 0.25)
    rtp_worm_pullback = _updip_pullback(rtp_worm, dy_fw, dx_fw, shift_px)
    push("rtp_worm_persist4", rtp_worm, "subsurf_hupw")
    push("rtp_worm_pullback60", rtp_worm_pullback, "subsurf_hupw")
    push("joint_grav_rtp_pullback", np.sqrt(grav_worm_pullback * rtp_worm_pullback), "subsurf_hupw")

    # Gallardo & Meju (2003) structural cross-gradient alignment between gravity & RTP
    gy_r = ndi.gaussian_filter(rtp_f, 2.0, order=(1, 0))
    gx_r = ndi.gaussian_filter(rtp_f, 2.0, order=(0, 1))
    cross_sin = np.abs(gx_g * gy_r - gy_g * gx_r) / (np.hypot(gx_g, gy_g) * np.hypot(gx_r, gy_r) + 1e-5)
    push("gallardo_meju_concordance", (1.0 - cross_sin) * np.sqrt(grav_worm * rtp_worm), "subsurf_hupw")
    subsurf_structural_backbone = (0.55 * grav_worm_pullback + 0.45 * rtp_worm_pullback).astype(np.float32)
    del rtp, tc, r_ups, rtp_worm_prod, rtp_f, gy_g, gx_g, gy_r, gx_r, cross_sin
    gc.collect()

    # Conductivity clay-cap edge + Geodetic strain invariants + Microseismicity
    cond = _read_feature_band(17, fp)
    cond_f = fast_fill(cond)
    cond_grad = np.hypot(ndi.gaussian_filter(cond_f, 2.0, order=(1, 0)),
                         ndi.gaussian_filter(cond_f, 2.0, order=(0, 1)))
    push("cond_surf", cond, "subsurf_hupw")
    push("cond_smectite_edge", cond_grad, "subsurf_hupw")

    g2 = _read_feature_band(4, fp)
    gshear = _read_feature_band(7, fp)
    gdil = _read_feature_band(8, fp)
    push("geod_2ndinv", g2, "subsurf_hupw")
    push("geod_shearrate", gshear, "subsurf_hupw")
    push("geod_dilaterate", gdil, "subsurf_hupw")
    push("geod_transtension_ratio", gdil / (np.abs(g2) + 0.5), "subsurf_hupw")
    push("deq_log", np.log1p(np.maximum(_read_feature_band(10, fp), 0.0)), "subsurf_hupw")
    push("ieq_density", _read_feature_band(16, fp), "subsurf_hupw")
    del cond, cond_f, g2, gshear, gdil
    gc.collect()

    # --- Block B: Core 100m Detrended Topography + Multi-Scale Ridges ---
    det = _read_feature_band(12, fp)
    det_f = fast_fill(det)
    push("det_elev", det, "core_topo")
    push("det_elev_slope", _read_feature_band(19, fp), "core_topo")
    c1, t1, topo_strike = _hessian_crest_and_strike(det_f, 1.3)
    c2, t2, _ = _hessian_crest_and_strike(det_f, 2.8)
    c5, _, _ = _hessian_crest_and_strike(det_f, 5.5)
    push("det_crest_s1p3", c1, "core_topo")
    push("det_trough_s1p3", t1, "core_topo")
    push("det_crest_s2p8", c2, "core_topo")
    push("det_trough_s2p8", t2, "core_topo")
    push("det_crest_s5p5", c5, "core_topo")
    del det, det_f, c1, t1, c2, t2, c5
    gc.collect()

    # --- Block C: Sub-100m 1m 3DEP LiDAR Scarps (NaN where LiDAR tile absent!) ---
    with rasterio.open(EXTERNAL / "lidar_scarp_features_u8.tif") as src:
        lid = src.read().astype(np.float32)
    l_valid = (lid[11] > 0) & fp

    def _lid(idx: int) -> np.ndarray:
        a = lid[idx].copy()
        a[~l_valid] = np.nan
        return a

    ex_max = _lid(0)
    step_max = _lid(2)
    downf = _lid(5)
    upf = _lid(6)
    l_rel = _lid(8)
    coh100 = _lid(9)
    l_strike_raw = lid[10]
    push("lidar_ex_max", ex_max, "lidar_1m", keep_nan=True)
    push("lidar_ex_mean", _lid(1), "lidar_1m", keep_nan=True)
    push("lidar_step_max", step_max, "lidar_1m", keep_nan=True)
    push("lidar_lapneg", _lid(3), "lidar_1m", keep_nan=True)
    push("lidar_lappos", _lid(4), "lidar_1m", keep_nan=True)
    push("lidar_cross_max", _lid(7), "lidar_1m", keep_nan=True)
    push("lidar_relief", l_rel, "lidar_1m", keep_nan=True)
    push("lidar_coh100", coh100, "lidar_1m", keep_nan=True)
    # Tectonic scarp normalized sharpness (catches low-throw piedmont fan scarps while discounting canyon walls)
    push("lidar_tectonic_step_ratio", step_max * (coh100 / 255.0) / (l_rel + 8.0), "lidar_1m", keep_nan=True)
    push("lidar_scarp_polarity", (downf - upf) / (downf + upf + 6.0), "lidar_1m", keep_nan=True)

    # Composite local structural strike azimuth in [0, pi): prefer 1m LiDAR where valid & coherent, else potential/topo
    lid_ang = (l_strike_raw / 255.0) * np.pi
    use_lid = l_valid & (lid[9] > 40)
    composite_strike = np.where(use_lid, lid_ang, np.where(grav_worm_pullback > 0.55, g_strike, topo_strike)).astype(np.float32)
    np.memmap(strike_path, dtype=np.float16, mode="w+", shape=(n_fp,))[:] = composite_strike[fp].astype(np.float16)
    del lid, ex_max, step_max, downf, upf, l_rel, coh100, lid_ang, use_lid, composite_strike, g_strike, topo_strike
    gc.collect()

    # --- Block D: Seamless 10m 3DEP Geomorphometry + Fluvial Chi / Knickpoints + Paleoshoreline Rejection ---
    with rasterio.open(EXTERNAL / "topo_10m_derived_100m_u8.tif") as src:
        t10 = src.read().astype(np.float32)
    for b_idx, b_name in enumerate([
        "dem10_slope_p90", "dem10_slope_max", "dem10_steep_frac", "dem10_slope_std",
        "dem10_relief_local", "dem10_curv_prof", "dem10_aspect_coh", "dem10_hs_lineament",
    ]):
        a = t10[b_idx]
        a[a <= 0] = np.nan
        push(b_name, a, "dem10_chi", keep_nan=True)
    relief10 = t10[4].copy()
    slope10 = t10[1].copy()
    del t10
    gc.collect()

    with rasterio.open(EXTERNAL / "dem10_chi_100m_i16.tif") as src:
        chi16 = src.read().astype(np.float32)
    with rasterio.open(EXTERNAL / "dem10_chi_100m_u8.tif") as src:
        chi8 = src.read().astype(np.float32)

    zmean = np.where(chi16[4] > 0, chi16[4], np.nan)
    chi_step = np.where(chi16[0] > -30000, chi16[0], np.nan)
    ksn = np.where(chi16[2] > -30000, chi16[2], np.nan)
    push("chi_step_max", chi_step, "dem10_chi", keep_nan=True)
    push("chi_ksn_max", ksn, "dem10_chi", keep_nan=True)
    push("chi_knick_density", ndi.gaussian_filter(chi8[1], 2.0), "dem10_chi")
    push("chi_raised_n", chi8[2], "dem10_chi")

    # Explicit Pleistocene Lake Lahontan (~1332m highstand; 1265-1348m wave-cut terrace zone) mimic indicator:
    # Wave-cut benches produce sharp 1m/10m scarps tightly clustered along equipotential shoreline elevations
    # WITHOUT deep potential-field basement offset!
    lahontan_band = np.exp(-0.5 * ((_fill_nearest(zmean) - 1328.0) / 32.0) ** 2)
    shoreline_mimic = lahontan_band * _rank01_fp(slope10, fp) * (1.0 - subsurf_structural_backbone)
    push("lahontan_shoreline_mimic", shoreline_mimic.astype(np.float32), "core_topo")
    del chi16, chi8, zmean, chi_step, ksn, lahontan_band, shoreline_mimic, slope10
    gc.collect()

    # --- Block E: GeoDAWN Airborne Radiometrics & Hydrothermal K/Th Alteration ---
    with rasterio.open(EXTERNAL / "geodawn_rad_u8.tif") as src:
        rad = src.read().astype(np.float32)
    with rasterio.open(EXTERNAL / "geodawn_extensions_u8.tif") as src:
        rext = src.read().astype(np.float32)
    rad_ok = (rad[3] > 0) & fp
    k_ch = np.where(rad_ok, rad[0], np.nan)
    th_ch = np.where(rad_ok, rad[1], np.nan)
    k_over_th = _fill_nearest(k_ch) / (_fill_nearest(th_ch) + 8.0)
    # High-pass boiling-zone adularia/potassic alteration (removes regional felsic ash-flow tuff background)
    kth_hp = k_over_th - ndi.gaussian_filter(k_over_th, 9.0)
    push("rad_kth_alteration_hp", kth_hp.astype(np.float32), "radiometric")
    push("rad_uth_redox", np.where(rad_ok, rext[2], np.nan), "radiometric", keep_nan=True)
    rad_edge = np.hypot(ndi.gaussian_filter(_fill_nearest(k_ch), 1.8, order=(1, 0)),
                        ndi.gaussian_filter(_fill_nearest(k_ch), 1.8, order=(0, 1))) + \
               np.hypot(ndi.gaussian_filter(_fill_nearest(th_ch), 1.8, order=(1, 0)),
                        ndi.gaussian_filter(_fill_nearest(th_ch), 1.8, order=(0, 1)))
    push("rad_lith_contact_grad", rad_edge.astype(np.float32), "radiometric")
    # Shallow magnetite destruction along hydrothermal conduits: high attenuation between surface TMI and +150m TMI
    tmi_surf_r = _rank01_fp(_fill_nearest(tmi), fp)
    tmi_up150_r = _rank01_fp(rext[3], fp)
    push("mag_destruction_shallow", (tmi_up150_r - tmi_surf_r).astype(np.float32), "radiometric")
    del rad, rext, k_ch, th_ch, k_over_th, kth_hp, rad_edge, tmi, tmi_surf_r, tmi_up150_r
    gc.collect()

    # --- Block F: Official DOE GDR-1391 INGENIOUS Geothermal Conduits (H84-H3) ---
    geo = build_geothermal_fields(fp)
    for gname, garr in geo.items():
        push(gname, garr, "geothermal_ahfv")
    # Coupled hydrothermal fault-valve throat: thermal anomaly * subsurface structural worm * smectite clay-cap edge
    thermal_total = _rank01_fp(
        geo["geo_f2m_local"] + geo["geo_sinter_conduit"] + geo["geo_diseq_short"] + 0.5 * geo["geo_hotspring_plume"],
        fp,
    )
    fault_valve_throat = thermal_total * subsurf_structural_backbone * (0.5 + 0.5 * _rank01_fp(cond_grad, fp))
    push("ahfv_fault_valve_throat", fault_valve_throat.astype(np.float32), "geothermal_ahfv")

    # Concealed-basin vs exposed-range continuous burial index (0 = exposed bedrock range, 1 = deep flat alluvial basin)
    basin_cover_idx = (1.0 - _rank01_fp(relief10, fp)) * _rank01_fp(dbase_f, fp)
    push("basin_cover_index", basin_cover_idx.astype(np.float32), "subsurf_hupw")

    n_cols = len(names)
    mm.flush()
    del mm
    # Trim file strictly to exact n_cols columns
    raw = np.memmap(tmp_path, dtype=np.float16, mode="r", shape=(n_fp, MAX_COLS))
    final = np.memmap(mmap_path, dtype=np.float16, mode="w+", shape=(n_fp, n_cols))
    chunk = 500_000
    for s in range(0, n_fp, chunk):
        final[s:s + chunk] = raw[s:s + chunk, :n_cols]
    final.flush()
    del raw, final
    tmp_path.unlink(missing_ok=True)

    meta = {
        "version": STACK_VERSION,
        "n_fp": n_fp,
        "n_features": n_cols,
        "names": names,
        "groups": groups,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    gc.collect()
    return np.memmap(mmap_path, dtype=np.float16, mode="r", shape=(n_fp, n_cols)), meta
