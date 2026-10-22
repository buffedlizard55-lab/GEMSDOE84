"""Band loading, footprint computation, and the two H84 physical-field detectors.

All 19 band names/descriptions below were read directly from training_features.tif's own
GDAL band-description metadata in this session (see registry/data_dictionary.json, produced
by scripts/dump_data_dictionary.py) -- they are not retyped from memory.

Neither H84-1 nor H84-3 uses labels.tif as a model input. Both are pure functions of the
official 19-band physical feature stack. labels.tif is used ONLY downstream, for holdout
scoring and the leakage canary (src/gems84/holdout.py), which is the correct and required
order of operations (compute features blind to ground truth, then validate against it).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter, binary_erosion
from skimage.filters import sato

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


NEEDED_BANDS = ["rtp", "cond_surf", "tmi_hg", "depth_to_base_surf", "det_elev"]


def load_stack(band_names=None, dtype=np.float32):
    """Load only the requested bands (default: the 4 bands H84-1/H84-3 actually use) as
    float32, to stay inside this sandbox's ~3.8 GB memory budget. `valid` is still computed
    honestly from the AND of all 19 bands' own per-pixel validity (read once, cheaply, one
    band at a time) so the footprint is identical to using the full stack."""
    band_names = band_names if band_names is not None else NEEDED_BANDS
    with rasterio.open(DATA / "training_features.tif") as ds:
        names = [d.split(" - ")[0].strip() for d in ds.descriptions]
        nodata = ds.nodata
        profile = ds.profile
        shape = ds.shape

        valid = np.ones(shape, dtype=bool)
        for i in range(ds.count):
            b = ds.read(i + 1, out_dtype=np.float32)
            valid &= np.isfinite(b) & ~np.isclose(b, nodata, rtol=0, atol=1e6)
            del b

        bands = {}
        for n in band_names:
            idx = names.index(n) + 1
            bands[n] = ds.read(idx, out_dtype=dtype)
    return bands, valid, profile


def load_labels():
    with rasterio.open(DATA / "labels.tif") as ds:
        lab = ds.read(1)
        profile = ds.profile
    valid = lab != -1
    fault = lab == 1
    return fault, valid, profile


def footprint(feat_valid: np.ndarray, label_valid: np.ndarray) -> np.ndarray:
    return feat_valid & label_valid


def zscore(x: np.ndarray, valid: np.ndarray) -> np.ndarray:
    m = x[valid].mean()
    s = x[valid].std() + 1e-9
    z = (x - m) / s
    z[~valid] = 0.0
    return z


def highpass(x: np.ndarray, valid: np.ndarray, sigma_px: float) -> np.ndarray:
    """Local anomaly = raw minus a regional (low-pass) trend, computed with NORMALIZED
    CONVOLUTION so the irregular GeoDAWN survey boundary does not inject a spurious cliff
    into the background estimate (a naive 'fill-with-mean-then-blur' leaves exactly that
    cliff at every valid/invalid interface, which this session's first holdout run showed
    dominates the field -- see docs/research/h84-hypotheses.md "IR-84-001"). Normalized
    convolution: bg = blur(x * valid) / blur(valid), i.e. the Gaussian average is taken
    only over valid support at every pixel (Knutsson & Westin 1993, a standard technique
    for smoothing data with holes/missing values)."""
    valid_f = valid.astype(np.float32)
    filled = np.where(valid, x, 0.0).astype(np.float32)
    num = gaussian_filter(filled, sigma=sigma_px, mode="nearest")
    den = gaussian_filter(valid_f, sigma=sigma_px, mode="nearest")
    bg = num / np.clip(den, 1e-6, None)
    hp = x - bg
    hp[~valid] = 0.0
    return hp


def interior_mask(valid: np.ndarray, margin_px: int = 12) -> np.ndarray:
    """Shrink the valid footprint inward by margin_px. Any pixel-scale local transform
    (highpass, Sato ridge filter) is unreliable within ~1 kernel-radius of the irregular
    GeoDAWN survey boundary, so detectors are not allowed to emit mass there (IR-84-001)."""
    return binary_erosion(valid, iterations=margin_px, border_value=0)


def minmax01(x: np.ndarray, valid: np.ndarray) -> np.ndarray:
    v = x[valid]
    lo, hi = np.percentile(v, 1.0), np.percentile(v, 99.0)
    if hi <= lo:
        hi = lo + 1e-9
    out = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    out[~valid] = 0.0
    return out


def h84_1_demagnetized_conductive_corridor(bands: dict, valid: np.ndarray,
                                            sigma_px: float = 15.0) -> np.ndarray:
    """H84-1: local RTP magnetic LOW (amplitude minimum, i.e. demagnetized halo) that is
    spatially conjugate with a local surface-conductivity HIGH (alteration/clay-cap proxy),
    with (a) a gate that *downweights* pixels dominated by a sharp magnetic gradient (those
    are lithologic-contact edge detectors -- a different, already-explored mechanism, see
    docs/research/prior-art-audit.md), and (b) a Sato ridge/vesselness filter that favours
    elongated, fault-aligned corridors over equant blobs (basin-fill sediments produce
    broad, equant, non-fault-controlled magnetic lows -- see docs/research/h84-hypotheses.md
    "named non-fault mimic").
    """
    rtp = bands["rtp"]
    cond = bands["cond_surf"]
    tmi_hg = bands["tmi_hg"]

    local_low = highpass(rtp, valid, sigma_px)          # positive = locally lower than regional
    local_low_pos = np.clip(-local_low, 0, None)        # we want RTP *lower* than background
    local_low_z = zscore(local_low_pos, valid)

    cond_hp = highpass(cond, valid, sigma_px)
    cond_high_z = zscore(np.clip(cond_hp, 0, None), valid)

    grad_z = zscore(tmi_hg, valid)
    edge_gate = np.exp(-np.clip(grad_z, 0, None))       # downweight strong-gradient (contact) pixels

    composite = np.clip(local_low_z, 0, None) * np.clip(cond_high_z, 0, None) * edge_gate
    composite[~valid] = 0.0

    ridge = sato(composite, sigmas=range(1, 4), black_ridges=False, mode="reflect")
    interior = interior_mask(valid, margin_px=12)
    ridge[~interior] = 0.0
    return minmax01(ridge, interior)


def h84_4_scarp_alteration_concordance(bands: dict, valid: np.ndarray, alteration_field: np.ndarray,
                                        sigma_px: float = 2.0) -> np.ndarray:
    """H84-4: require BOTH a topographic scarp (an elongated break-in-slope in detrended
    elevation, detected with a Sato ridge filter -- a different operator than the
    Laplacian-zero-crossing curvature transform already explored in this lineage, see
    docs/research/prior-art-audit.md) AND co-location with the H84-1/H84-3 alteration
    corridor. The conjunction trades recall for precision: per the metric's own algebraic
    reduction (1/DTI = alpha + alpha*(F/T) + beta*(K/T), docs/research/metric-reduction.md),
    cutting false-positive mass F at fixed true-positive mass T is the cheapest lever
    available, so AND-ing two independent, mechanistically different pieces of evidence
    (surface morphology + buried geophysics) is expected to raise DTI even if each one
    alone is weak -- this is the hypothesis this script actually tests, not assumed."""
    det_elev = bands["det_elev"]
    interior = interior_mask(valid, margin_px=12)
    filled = np.where(interior, det_elev, 0.0).astype(np.float32)
    scarp = sato(filled, sigmas=[sigma_px], black_ridges=False, mode="reflect")
    scarp[~interior] = 0.0
    scarp01 = minmax01(scarp, interior)
    conc = scarp01 * alteration_field
    return minmax01(conc, interior)


def h84_3_conductivity_basement_discordance(bands: dict, valid: np.ndarray,
                                             sigma_px: float = 15.0) -> np.ndarray:
    """H84-3: local surface-conductivity HIGH coincident with a local basement HIGH
    (shallow depth_to_base_surf, i.e. a horst). Physically: a basement horst that is
    *also* locally conductive at the surface is a discordance -- thin sedimentary cover
    does not normally carry an alteration/clay signature unless a near-vertical conduit
    (a blind fault) is cross-cutting the horst and bringing altered fluid to surface.
    """
    cond = bands["cond_surf"]
    depth = bands["depth_to_base_surf"]

    cond_hp = highpass(cond, valid, sigma_px)
    cond_high_z = zscore(np.clip(cond_hp, 0, None), valid)

    depth_hp = highpass(depth, valid, sigma_px)             # positive = locally deeper than regional
    shallow_z = zscore(np.clip(-depth_hp, 0, None), valid)  # positive = locally SHALLOWER (horst)

    composite = np.clip(cond_high_z, 0, None) * np.clip(shallow_z, 0, None)
    interior = interior_mask(valid, margin_px=12)
    composite[~interior] = 0.0
    return minmax01(composite, interior)
