#!/usr/bin/env python3
"""Template-pinned holdout evaluator entry point (`vendor/gems57/evaluate_holdout.py`).

Re-exports all functions and constants from `vendor/gems57/evaluate_holdout.py`
(`gems57-pooled-hide-v2`, alpha=0.2, beta=0.8, 300 m triangular kernel).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

from gems57.evaluate_holdout import (  # noqa: E402,F401
    VERSION,
    check_canary,
    evaluate,
    from_terms,
    implementation_hashes,
    paired_bootstrap_ci,
    pooled_summary,
)


def main() -> int:
    exp2_path = ROOT / "evidence" / "h84_exp2_dualseed_holdout.json"
    if exp2_path.exists():
        data = json.loads(exp2_path.read_text())
        print(
            json.dumps(
                {
                    "evaluator_version": VERSION,
                    "implementation_hashes": implementation_hashes(),
                    "dualseed_pooled_scores": data["dualseed_pooled_summary"]["scores"],
                },
                indent=2,
            )
        )
    else:
        print(json.dumps({"evaluator_version": VERSION, "implementation_hashes": implementation_hashes()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
