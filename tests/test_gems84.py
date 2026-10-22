"""Unit tests for the GEMSDOE84 lane. Run: python -m pytest -q"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems57 import metric  # noqa: E402
from gems84 import liti  # noqa: E402

PIN = {  # 60GEMSDOE@b99591e src/gems57 (same values as GEMSDOE81 registry/template_pin.json)
    "evaluate_holdout.py": "ad86640b46f3c5fc6b1aceec4c4bfc82d03e35008b37ab2a8ad6076e6810ff3a",
    "holdout.py": "7a0a84176986190b527aa9c6a84216c2dab4b599f25b1143db5f420e85020ab1",
    "metric.py": "4afe10cbaa229948520c75194b1ebc32676e72544f05582f0725092b097b4d7f",
    "submission_writer.py": "41220185ac2823fe5358603d38f2a915ea3e5f1ab1f94f0b237295b38b4a2565",
    "emit.py": "05c473e736e4a599b35be77b2791b62d72460383853c8fba0eb56ea26c99055d",
    "uniqueness.py": "1c5094b814277ae801ccea6a47cf744429cffcdc10f9cc79f229d5fc44a8df95",
    "validate.py": "e7849554b47f6a2b66aeb2f7cfd5db06267412f049f52a73f1c41f934a2c34dd",
    "grid.py": "b96df7ec0f33658a61b0baa5db85fcd19be2cd8b1873f99699bd26bddae8cd8d",
}


def test_template_unmodified():
    for name, want in PIN.items():
        got = hashlib.sha256((ROOT / "src/gems57" / name).read_bytes()).hexdigest()
        assert got == want, f"shared template file {name} was modified (no private forks)"


def test_coverage_matches_official_tp():
    rng = np.random.default_rng(0)
    p = (rng.random((60, 70)) < 0.03).astype(np.float32)
    truth = rng.random((60, 70)) < 0.05
    ys, xs = np.nonzero(truth)
    c, m = liti.coverage_at(p, ys, xs)
    exact = metric.dti_exact(p, truth)
    assert abs(float(c.sum()) - exact["tp"]) < 1e-5          # E[TP_w] identity at lambda = 1{truth}
    assert np.all(m >= c - 1e-7)                               # sum-kernel >= max-kernel


def test_predict_is_official_formula():
    D = liti.Design(Phi=np.ones((4, 1), np.float32), support=np.ones(4, bool),
                    C=np.array([[1, 0.5, 0, 0]], np.float32), Mm=np.zeros((1, 4), np.float32),
                    S=np.array([10.0]), w=1.0, names=["intercept"])
    s, parts = liti.predict(np.array([0.0]), 0.0, D)        # lambda = 1 everywhere
    A, G, F = 1.5, 4.0, 10.0
    assert abs(s[0] - A / (0.2 * A + 0.2 * F + 0.8 * G)) < 1e-9


def test_shipped_submission_valid():
    card = ROOT / "evidence/run_card.json"
    if not card.exists():
        pytest.skip("no run card yet")
    rc = json.loads(card.read_text())
    if not rc.get("submission"):
        # fail-closed path: a negative/duplicate verdict must leave NO submittable TIFF behind
        assert rc["verdict"] == "negative"
        assert not list((ROOT / "docs/downloads").glob("*.tif"))
        return
    tif = ROOT / "docs/downloads" / rc["submission"]["file"]
    if not tif.exists():
        pytest.skip("no shipped TIFF")
    import rasterio
    with rasterio.open(tif) as s:
        a = s.read(1)
        assert s.count == 1 and s.dtypes[0] == "float32" and s.shape == (3730, 3292)
        assert s.crs.to_epsg() == 32611
        assert tuple(s.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
    assert np.isfinite(a).all() and a.min() >= 0 and a.max() <= 1
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == rc["submission"]["sha256"]
