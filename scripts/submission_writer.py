#!/usr/bin/env python3
"""Template-pinned fail-closed submission writer entry point (`vendor/gems57/submission_writer.py`).

Re-exports `write_submission` from `vendor/gems57/submission_writer.py`.
Guarantees single-band float32 EPSG:32611 3730x3292 GeoTIFF with values strictly in [0, 1],
nodata=None, zero NaN/Inf anywhere, and zero outside footprint.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

from gems57.submission_writer import write_submission  # noqa: E402,F401
from gems57 import grid as GRID, validate as V  # noqa: E402


def main() -> int:
    card_path = ROOT / "run_card.json"
    if not card_path.exists():
        print("run_card.json not found; run scripts/run_h84_thms_pipeline.py first.", file=sys.stderr)
        return 1
    card = json.loads(card_path.read_text())
    g = GRID.load_grid(ROOT / "data" / "bridge")
    rep = V.validate(ROOT / card["audited_artifact"]["path"], g.footprint, g.catalogue)
    print(json.dumps(rep, indent=2))
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
