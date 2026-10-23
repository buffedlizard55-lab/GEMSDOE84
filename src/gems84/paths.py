"""Locations of large inputs that stay out of Git.

Override the data root with GEMS84_DATA (default: /home/user/gemsdata).
Every input is SHA-256 pinned in registry/data_manifest.json and verified by
scripts/fetch_data.py before use.
"""
from __future__ import annotations
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("GEMS84_DATA", "/home/user/gemsdata"))
BRIDGE = ROOT / "data" / "bridge"
FAULTS_TIF = BRIDGE / "existing_faults.tif"
SAMPLE_TIF = BRIDGE / "sample_submission.tif"
FEATURES_TIF = DATA / "training_features.tif"
EXTERNAL = DATA / "external"
REGISTRY_DIR = DATA / "registry"
WORK = DATA / "work"
