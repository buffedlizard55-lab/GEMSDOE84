"""Unit tests for the GEMSDOE84 lane. Run: python -m pytest -q"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]

from gems57 import metric  # noqa: E402
from gems84 import liti  # noqa: E402

def test_template_unmodified():
    """vendor/gems57 must match the shared pin (registry/template_pin.json); no private forks."""
    pin = json.loads((ROOT / "registry/template_pin.json").read_text())
    for name, want in pin["files"].items():
        got = hashlib.sha256((ROOT / "vendor/gems57" / name).read_bytes()).hexdigest()
        assert got == want, f"shared template file {name} differs from the pin"


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
