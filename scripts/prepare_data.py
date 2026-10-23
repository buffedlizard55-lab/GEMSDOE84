#!/usr/bin/env python3
"""Prepare and verify competition data, grid geometry, 72-channel physical stack,
and 359-raster registry halo bitmatrix for Lane H84-THMS (GEMSDOE84).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import grid as GRID  # noqa: E402
from gems84 import dinkelbach_emitter as DE, features as F  # noqa: E402

RAW_DIR = ROOT / ".cache" / "gems_data"
BRIDGE_DIR = ROOT / "data" / "bridge"
PROC_DIR = RAW_DIR / "processed"
EVID_DIR = ROOT / "evidence"
DOCS_EVID_DIR = ROOT / "docs" / "evidence"
REG_DIR = ROOT / "registry"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    t0 = time.time()
    BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
    for fn in ("sample_submission.tif", "labels.tif", "existing_faults.tif"):
        src = RAW_DIR / fn
        dst = BRIDGE_DIR / fn
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)

    g = GRID.load_grid(BRIDGE_DIR)
    foot = g.footprint
    cat = g.catalogue

    tf_path = RAW_DIR / "training_features.tif"
    with rasterio.open(tf_path) as ds:
        tf_shape = list(ds.shape)
        tf_count = int(ds.count)
        tf_crs = str(ds.crs)
        tf_transform = list(ds.transform)[:6]

    grid_audit = {
        "schema": "gemsdoe84-grid-audit-v1",
        "crs": str(g.crs),
        "shape": list(foot.shape),
        "transform": list(GRID.TRANSFORM)[:6],
        "total_grid_cells": int(foot.size),
        "active_footprint_cells": int(foot.sum()),
        "outside_footprint_cells": int((~foot).sum()),
        "mapped_catalogue_cells": int(cat.sum()),
        "mapped_catalogue_footprint_fraction": round(float(cat.sum() / foot.sum()), 6),
        "labels_equals_existing_faults_byte_identical": bool(
            sha256_file(BRIDGE_DIR / "labels.tif") == sha256_file(BRIDGE_DIR / "existing_faults.tif")
        ),
        "sample_submission_positive_cells": int(cat.sum()),
        "training_features_bands": tf_count,
        "training_features_shape": tf_shape,
        "training_features_crs": tf_crs,
        "training_features_transform": tf_transform,
    }
    for d in (EVID_DIR, DOCS_EVID_DIR):
        d.mkdir(parents=True, exist_ok=True)
        (d / "grid_audit.json").write_text(json.dumps(grid_audit, indent=2) + "\n")

    phys_names, X_phys = F.load_or_build_rowmajor_f16(RAW_DIR, foot, PROC_DIR)
    stds = np.asarray(X_phys[::64], dtype=np.float32).std(axis=0)
    zero_std = [phys_names[i] for i, s in enumerate(stds) if s == 0.0]
    if zero_std:
        raise RuntimeError(f"Zero-variance physical channels detected: {zero_std}")

    packed_halos, n_halos, records = DE.build_or_load_registry_halos(
        RAW_DIR / "scored", foot, PROC_DIR, budget=37_654
    )

    feat_receipt = {
        "schema": "gemsdoe84-feature-receipt-v1",
        "lane_id": "H84-THMS",
        "n_physical_channels": len(phys_names),
        "n_structural_network_channels": len(F.STRUCTURAL_NETWORK_NAMES),
        "n_coupling_interaction_channels": len(F.COUPLING_INTERACTION_NAMES),
        "n_total_channels": len(phys_names) + len(F.STRUCTURAL_NETWORK_NAMES) + len(F.COUPLING_INTERACTION_NAMES),
        "physical_matrix_shape": list(X_phys.shape),
        "physical_matrix_dtype": str(X_phys.dtype),
        "zero_variance_channels": zero_std,
        "physical_channel_names": phys_names,
        "structural_network_names": list(F.STRUCTURAL_NETWORK_NAMES),
        "coupling_interaction_names": list(F.COUPLING_INTERACTION_NAMES),
        "registry_halo_bitmatrix_shape": list(packed_halos.shape),
        "registry_halos_tracked": int(n_halos),
        "elapsed_s": round(time.time() - t0, 2),
    }
    REG_DIR.mkdir(parents=True, exist_ok=True)
    (REG_DIR / "feature_receipt.json").write_text(json.dumps(feat_receipt, indent=2) + "\n")
    print(
        f"Prepared 96-channel H84-THMS feature stack ({len(phys_names)} physical + 24 structural/coupling) "
        f"and {n_halos} registry halos in {time.time() - t0:.1f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
