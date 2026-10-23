"""Parent R0 (``h33-h33-2-b2``): grid loading, exact rebuild and dot-raster emission.

The parent is *not* approximated here.  It is rebuilt from the recorded upstream recipe and
its SHA-256 is asserted against the pin committed in this repo
(``evidence/h33-original-audit.json`` -> ``zeros_tif.sha256``).

Recorded recipe (upstream ``buffedlizard55-lab/GEMSDOE32``, files pinned by SHA-256 in
``registry/data_manifest.json`` / ``evidence/input_restore_receipt.json``):

* ``src/gems32/holdout.py:86-89`` -- ``foot = np.isfinite(sample_submission)`` and
  ``labels = read_binary(labels.tif) & foot`` where ``read_binary(a) = isfinite(a) & (a > 0)``.
* ``src/gems32/hypotheses33.py:307-329`` -- ``compute_h33_2_flank_sweep``:
  ``mask = base & (distance_transform_edt(~labels) > B)`` with ``B = 2``
  (``scripts/run_h33_validation.py:112`` uses ``buffers=(2, 3)``; B=2 is the shipped arm).
* ``scripts/run_h33_validation.py`` -- ``base`` is the owner-reported 0.2708 emission
  ``gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif``.
* ``src/gems32/submission.py:118-166`` -- ``write_submission_pair``:
  ``clean = mask & foot & ~labels``; ``-zeros`` writes ``0.0`` outside the footprint,
  GTiff/deflate/predictor=3/zlevel=9/tiled 256x256, ``nodata=None``, profile copied from the
  template raster (``labels.tif`` was passed as the template by ``run_h33_validation.py``).

Only ``codeload.github.com``-sourced, hash-verified mirrors are read.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

# SHA-256 pins for the parent lineage (see module docstring for the evidence source).
R0_ZEROS_SHA256 = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
R0_NAN_SHA256 = "baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd"
BASE_02708_SHA256 = "ab02300152248fdda04e988e2cd2a0c13f35eec42fcf670a15e8b76b19e24a73"

R0_ZEROS_REL = "parent/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"
R0_NAN_REL = "parent/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif"
BASE_REL = "parent/gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif"

EXPECTED_SHAPE = (3730, 3292)
EXPECTED_FOOTPRINT_PIXELS = 5_167_373
EXPECTED_R0_DOTS = 37_654
R0_CATALOGUE_BUFFER_PX = 2  # the B=2 flank prune that defines the parent

GTIFF_PROFILE = dict(
    driver="GTiff",
    dtype="float32",
    count=1,
    compress="deflate",
    predictor=3,
    zlevel=9,
    tiled=True,
    blockxsize=256,
    blockysize=256,
    nodata=None,
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_binary(path: Path) -> np.ndarray:
    """Upstream ``gems32.holdout.read_binary``: finite and strictly positive."""
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0)


@dataclass
class Grid:
    """Competition grid: footprint, catalogue mask and the catalogue distance transform."""

    foot: np.ndarray
    catalogue: np.ndarray
    d_cat: np.ndarray
    shape: tuple[int, int]
    template_profile: dict

    @property
    def off_catalogue_3px(self) -> np.ndarray:
        """Hard constraint 4: no mass on catalogue pixels, >= 3 px away from them."""
        return self.foot & (self.d_cat >= 3.0)


def load_grid(data_dir: Path) -> Grid:
    """Load the grid exactly as the parent's recipe does."""
    with rasterio.open(data_dir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    catalogue = read_binary(data_dir / "labels.tif") & foot
    with rasterio.open(data_dir / "labels.tif") as ds:
        profile = ds.profile.copy()
    return Grid(
        foot=foot,
        catalogue=catalogue,
        d_cat=distance_transform_edt(~catalogue),
        shape=tuple(foot.shape),
        template_profile=profile,
    )


def rebuild_r0_mask(data_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """Rebuild the parent dot mask.  Returns ``(mask, base)``.

    ``base`` is the 0.2708 emission; ``mask`` is that emission with every dot at catalogue
    distance <= 2 px deleted -- the exact recorded definition of ``h33-h33-2-b2``.
    """
    grid = load_grid(data_dir)
    base = read_binary(data_dir / BASE_REL)
    mask = base & (grid.d_cat > R0_CATALOGUE_BUFFER_PX)
    mask = mask & grid.foot & ~grid.catalogue
    return mask, base


def emit_dots(mask: np.ndarray, grid: Grid, out_path: Path, mode: str = "zeros") -> Path:
    """Write a dot raster with the parent writer's profile.  ``mode``: ``zeros`` or ``nan``."""
    if mode not in ("zeros", "nan"):
        raise ValueError("mode must be 'zeros' or 'nan'")
    clean = (np.asarray(mask, bool) & grid.foot & ~grid.catalogue)
    profile = grid.template_profile.copy()
    profile.update(GTIFF_PROFILE)
    if mode == "nan":
        profile["nodata"] = float("nan")
        arr = np.where(grid.foot, clean.astype(np.float32), np.nan).astype(np.float32)
    else:
        profile["nodata"] = None
        arr = np.where(grid.foot, clean.astype(np.float32), 0.0).astype(np.float32)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(arr, 1)
    return out_path


def r0_pins_from_evidence(root: Path) -> dict:
    """Read the committed R0 pins so the rebuild is checked against repo evidence, not memory."""
    audit = json.loads((root / "evidence" / "h33-original-audit.json").read_text())
    return {
        "zeros_sha256": audit["zeros_tif"]["sha256"],
        "nan_sha256": audit["nan_tif"]["sha256"],
        "dots": audit["zeros_tif"]["emitted_positive_pixels"],
        "candidate_id": audit["candidate_id"],
        "slug": audit["slug"],
    }


def verify_r0_file(path: Path, grid: Grid) -> dict:
    """Re-read a written dot raster from disk and report the gate statistics."""
    with rasterio.open(path) as ds:
        arr = ds.read(1)
        meta = {
            "crs": str(ds.crs),
            "shape": [ds.height, ds.width],
            "dtype": ds.dtypes[0],
            "count": ds.count,
            "transform": [round(float(v), 4) for v in tuple(ds.transform)[:6]],
            "nodata": None if ds.nodata is None or (isinstance(ds.nodata, float) and np.isnan(ds.nodata)) else float(ds.nodata),
        }
    in_foot = arr[grid.foot]
    out_foot = arr[~grid.foot]
    dots = int((in_foot > 0.5).sum())
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        **meta,
        "dots": dots,
        "on_catalogue_dots": int(((arr > 0.5) & grid.catalogue).sum()),
        "in_footprint_min": float(np.min(in_foot)),
        "in_footprint_max": float(np.max(in_foot)),
        "in_footprint_nan": int(np.isnan(in_foot).sum()),
        "in_footprint_finite": int(np.isfinite(in_foot).sum()),
        "outside_nan": int(np.isnan(out_foot).sum()) if out_foot.size else 0,
        "outside_zero": int((out_foot == 0.0).sum()) if out_foot.size else 0,
        "outside_count": int(out_foot.size),
    }
