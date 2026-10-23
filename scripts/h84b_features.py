#!/usr/bin/env python3
"""Lane H84B-UAS feature stack builder (label-free, distance-blind).

Builds a float32 memmap stack (n_channels, 3730, 3292) in $GEMS84_DATA/work/
from SHA-pinned inputs only. NO catalogue-distance feature is computed.
Channels: 19 official bands (robust-z) + 7 gradient magnitudes + 4 Hessian
ridge responses + 12 lidar + 9 topo10m + 4 radiometric + K/Th, U/Th
+ 2 earthquake-coincidence channels = 59.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi

DATA = Path(os.environ.get("GEMS84_DATA", "/home/user/gemsdata"))
WORK = DATA / "work"; WORK.mkdir(parents=True, exist_ok=True)
H, W = 3730, 3292
SENT = -3.0e38

BAND_SHORT = ["mag_anom","rtp","tmi_hg","geod_2ndinv","iso_grav_slope","tc",
 "geod_shear","geod_dilat","tmi_vg","deq","iso_grav_vg","det_elev","iso_grav",
 "tmi","depth_base","ieq","cond_surf","iso_grav_hg","det_elev_slope"]
GRAD_BANDS = ["rtp","tc","iso_grav","tmi","depth_base","det_elev","cond_surf"]
RIDGE_BANDS = ["tc","det_elev","rtp","depth_base"]

def load_fp():
    with rasterio.open("data/bridge/labels.tif") as ds:
        lab = ds.read(1)
    return lab != -1, lab == 1

def robust_z(a, fp):
    v = a[fp & np.isfinite(a)]
    med = float(np.median(v)); q1,q3 = np.percentile(v,[25,75])
    iqr = max(float(q3-q1), 1e-9)
    out = np.clip((a-med)/(iqr/1.349), -8, 8).astype(np.float32)
    out[~np.isfinite(out)] = 0.0
    return out

def grad_mag(z):
    gy = ndi.sobel(z, axis=0); gx = ndi.sobel(z, axis=1)
    return np.hypot(gx, gy).astype(np.float32)

def ridge_resp(z):
    zs = ndi.gaussian_filter(z, 1.0)
    gyy = ndi.gaussian_filter(zs, 1.0, order=(2,0)); gxy = ndi.gaussian_filter(zs, 1.0, order=(1,1)); gxx = ndi.gaussian_filter(zs, 1.0, order=(0,2))
    tr = gxx+gyy; disc = np.sqrt(np.maximum((gxx-gyy)**2/4.0 + gxy**2, 0))
    lmin = tr/2.0 - disc
    return np.maximum(-lmin, 0).astype(np.float32)

def main():
    fp, _ = load_fp()
    names = []
    zcache = {}
    # pass 1: official bands -> keep z for selected bands in RAM (7+4 bands *49MB ok)
    with rasterio.open(DATA/"training_features.tif") as ds:
        for i, nm in enumerate(BAND_SHORT, start=1):
            b = ds.read(i).astype(np.float32)
            b[b <= SENT] = np.nan
            z = robust_z(b, fp)
            names.append(f"z_{nm}")
            if nm in GRAD_BANDS or nm in RIDGE_BANDS or nm in ("ieq","geod_dilat","deq"):
                zcache[nm] = z
            yield (f"z_{nm}", z)
    for nm in GRAD_BANDS:
        yield (f"grad_{nm}", robust_z(grad_mag(zcache[nm]).astype(np.float32), fp))
    for nm in RIDGE_BANDS:
        yield (f"ridge_{nm}", robust_z(ridge_resp(zcache[nm]), fp))
    # lidar 12 + topo 9 (uint8 scaled)
    with rasterio.open(DATA/"external/lidar_scarp_features_u8.tif") as ds:
        desc = ds.descriptions
        for i in range(1, ds.count+1):
            b = ds.read(i).astype(np.float32)/255.0
            yield (f"lidar_{(desc[i-1] or f'b{i}').strip()}", np.clip(b,0,1).astype(np.float32))
    with rasterio.open(DATA/"external/topo_10m_derived_100m_u8.tif") as ds:
        desc = ds.descriptions
        for i in range(1, ds.count+1):
            b = ds.read(i).astype(np.float32)/255.0
            yield (f"topo_{(desc[i-1] or f'b{i}').strip()}", np.clip(b,0,1).astype(np.float32))
    with rasterio.open(DATA/"external/geodawn_rad_u8.tif") as ds:
        desc = ds.descriptions
        raws = {}
        for i in range(1, ds.count+1):
            b = ds.read(i).astype(np.float32)/255.0
            key = (desc[i-1] or f"b{i}").strip()
            raws[key] = b
            yield (f"rad_{key}", np.clip(b,0,1).astype(np.float32))
        if {"K","Th","U"} <= set(raws):
            yield ("rad_KoverTh", robust_z((raws["K"]/(raws["Th"]+0.02)).astype(np.float32), fp))
            yield ("rad_UoverTh", robust_z((raws["U"]/(raws["Th"]+0.02)).astype(np.float32), fp))
    # earthquake coincidence (H-UAS-5 diagnostic channels)
    yield ("eq_coincidence", robust_z((zcache["ieq"]*np.maximum(zcache["geod_dilat"],0)).astype(np.float32), fp))
    yield ("eq_invdist", robust_z((-zcache["deq"]).astype(np.float32), fp))

if __name__ == "__main__":
    chans = list(main())
    names = [n for n,_ in chans]
    out = np.memmap(WORK/"h84b_stack.dat", dtype=np.float32, mode="w+", shape=(len(chans), H, W))
    for i,(n,a) in enumerate(chans):
        assert a.shape==(H,W) and np.isfinite(a).all(), n
        out[i] = a
        print(f"{i:2d} {n:34s} min={a.min():.3f} max={a.max():.3f} std={a.std():.3f}", flush=True)
    out.flush()
    (WORK/"h84b_stack.json").write_text(json.dumps({"channels": names, "shape": [len(names), H, W]}, indent=1))
    print("STACK_OK", len(names))
