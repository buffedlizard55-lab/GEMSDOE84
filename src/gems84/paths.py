"""Locations of large inputs that stay out of Git.

Override the data root with GEMS84_DATA (default: /home/user/.cache/gemsdata if
present, else /home/user/gemsdata). Every input is SHA-256 pinned in
registry/data_manifest.json and verified by scripts/fetch_data.py before use.
"""
from __future__ import annotations
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_DEFAULT = "/home/user/.cache/gemsdata" if Path("/home/user/.cache/gemsdata").exists() else "/home/user/gemsdata"
DATA = Path(os.environ.get("GEMS84_DATA", _DEFAULT))
BRIDGE = ROOT / "data" / "bridge"
SAMPLE_TIF = BRIDGE / "sample_submission.tif"
EVIDENCE = ROOT / "evidence"
DOWNLOADS = ROOT / "docs" / "downloads"
FEATURES_TIF = DATA / "training_features.tif"
EXTERNAL = DATA / "external"
SCORED_DIR = DATA / "scored"
REGISTRY_DIR = DATA / "registry"
WORK = DATA / "work"
