"""Tests for the AXIS=SNAP work: metric algebra, the snap operator, and the parent rebuild.

The metric-algebra tests are the ones the brief demands ("Algebra (derived; unit-test it)"):
they pin ``DTI = T / (0.2 T + 0.2 (S - M) + 0.8 |G|)`` against the shared template's literal
transcription of the published equations, so no lane in this repo can quietly drift to the
``alpha*n`` shortcut.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import metric as m57  # noqa: E402
from gems84.snap import _offsets, density_cv, robust_unit, snap_dots  # noqa: E402

DATA = ROOT / ".cache" / "gems_data"
R0_ZEROS_SHA256 = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"


# --------------------------------------------------------------------------- metric algebra
def _algebra_dti(pred: np.ndarray, truth: np.ndarray) -> float:
    """DTI = T / (0.2 T + 0.2 (S - M) + 0.8 |G|), computed from the definition."""
    credit, q, _ = m57.max_cover(pred, truth)
    T = float(credit.sum())                      # kernel credit summed over truth pixels
    S = float(pred.sum())                        # total predicted mass
    M = float((pred * q).sum())                  # self-credit summed over predicted pixels
    G = float(truth.sum())
    return T / (0.2 * T + 0.2 * (S - M) + 0.8 * G + m57.EPS)


def test_dti_algebra_matches_shared_exact_metric():
    rng = np.random.default_rng(11)
    for _ in range(6):
        h, w = 16, 16
        pred = np.where(rng.random((h, w)) > 0.75, rng.random((h, w)), 0.0)
        truth = rng.random((h, w)) > 0.85
        if not truth.any():
            truth[0, 0] = True
        exact = m57.dti_exact(pred, truth)["dti"]
        assert abs(_algebra_dti(pred, truth) - exact) < 1e-12
        brute = m57.dti_bruteforce(pred, truth)["dti"]
        assert abs(exact - brute) < 1e-9


def test_algebra_reduces_to_alpha_n_only_when_T_equals_M():
    """The 'alpha*n' shortcut is valid only for a near-bijection of dots and truth pixels."""
    truth = np.zeros((9, 9), bool)
    truth[4, 1:8] = True
    pred = truth.astype(float)          # one dot per truth pixel, exactly on it
    exact = m57.dti_exact(pred, truth)
    T, S, M, G = exact["tp"], float(pred.sum()), float((pred * m57.max_cover(pred, truth)[1]).sum()), float(truth.sum())
    assert T == pytest.approx(M)
    assert exact["dti"] == pytest.approx(T / (0.2 * T + 0.2 * (S - M) + 0.8 * G))
    # a redundant cluster has M > T, which is exactly where the shortcut breaks
    pred2 = pred.copy()
    pred2[3, 1:8] = 1.0                 # a second line of dots 1 px off the truth
    exact2 = m57.dti_exact(pred2, truth)
    M2 = float((pred2 * m57.max_cover(pred2, truth)[1]).sum())
    assert M2 > exact2["tp"]


def test_isolated_truth_pixel_payment_bar():
    """Brief section 2: an isolated truth pixel is paid by a dot iff its credit > 0.2 * DTI."""
    assert m57.marginal_inclusion_threshold(0.2778) == pytest.approx(0.05556, abs=1e-5)
    # 0.056 quoted in the brief at DTI ~ 0.28
    assert m57.marginal_inclusion_threshold(0.28) == pytest.approx(0.056, abs=1e-3)
    # a dot at 2 px earns 1 - 2/3 = 1/3 and pays; at 3 px it earns 0 and does not
    assert m57.marginal_accept(dT=1.0 / 3.0, k_self=1.0 / 3.0, T=5073.0, M=5073.0,
                               n=37654, K=12226)
    assert not m57.marginal_accept(dT=0.0, k_self=0.0, T=5073.0, M=5073.0,
                                   n=37654, K=12226)


# --------------------------------------------------------------------------- snap operator
def _synthetic(resp: np.ndarray, allowed: np.ndarray | None = None):
    dots = np.zeros(resp.shape, bool)
    return dots, resp, (np.ones(resp.shape, bool) if allowed is None else allowed)


def test_snap_moves_dot_to_stronger_response_within_window():
    resp = np.zeros((9, 9), np.float32)
    resp[4, 5] = 0.9                       # the real edge is 1 px east of the dot
    dots, r, allowed = _synthetic(resp)
    dots[4, 4] = True
    out = snap_dots(dots, r, allowed, max_shift=2.0, margin=0.05)
    assert out.stats["dots_moved"] == 1
    assert out.mask[4, 5] and not out.mask[4, 4]
    assert out.stats["max_displacement_px"] == pytest.approx(1.0)


def test_snap_does_not_move_on_a_tie():
    """margin=0 must still mean 'strictly stronger', or a flat surface shuffles every dot."""
    resp = np.full((9, 9), 0.4, np.float32)
    dots, r, allowed = _synthetic(resp)
    dots[4, 4] = True
    out = snap_dots(dots, r, allowed, max_shift=2.0, margin=0.0)
    assert out.stats["dots_moved"] == 0
    assert np.array_equal(out.mask, dots)


def test_snap_respects_margin_and_window():
    resp = np.zeros((11, 11), np.float32)
    resp[5, 8] = 0.30                      # 3 px away: outside both windows
    dots, r, allowed = _synthetic(resp)
    dots[5, 5] = True
    for window in (1.42, 2.0):
        assert snap_dots(dots, r, allowed, window, margin=0.0).stats["dots_moved"] == 0
    resp[5, 6] = 0.10                      # a weak neighbour: below the margin
    assert snap_dots(dots, r, allowed, 2.0, margin=0.25).stats["dots_moved"] == 0
    assert snap_dots(dots, r, allowed, 2.0, margin=0.05).stats["dots_moved"] == 1


def test_snap_preserves_count_and_exclusions_and_is_deterministic():
    rng = np.random.default_rng(3)
    resp = rng.random((60, 60)).astype(np.float32)
    dots = np.zeros((60, 60), bool)
    allowed = np.ones((60, 60), bool)
    allowed[:, :8] = False                 # a forbidden zone the dots must never enter
    ys = rng.integers(5, 55, 400)
    xs = rng.integers(8, 55, 400)          # the parent itself never violates its exclusion
    dots[ys, xs] = True
    n0 = int(dots.sum())
    a = snap_dots(dots, resp, allowed, 2.0, margin=0.01)
    b = snap_dots(dots, resp, allowed, 2.0, margin=0.01)
    assert a.stats["count_preserved"] and int(a.mask.sum()) == n0
    assert not (a.mask & ~allowed).any()
    assert np.array_equal(a.mask, b.mask)                       # no RNG anywhere
    assert a.stats["max_displacement_px"] <= 2.0 + 1e-9
    assert a.stats["mean_displacement_px"] > 0.0
    # every moved dot landed on a strictly stronger response
    for y0, x0, y1, x1, r0, r1, _d in a.moves:
        assert r1 - r0 >= 0.01 - 1e-9


def test_snap_never_puts_two_dots_on_one_pixel():
    resp = np.zeros((20, 20), np.float32)
    resp[10, 10] = 1.0                     # every neighbour wants the same pixel
    dots = np.zeros((20, 20), bool)
    dots[9, 10] = dots[11, 10] = dots[10, 9] = True
    out = snap_dots(dots, resp, np.ones((20, 20), bool), 2.0, margin=0.1)
    assert int(out.mask.sum()) == 3
    assert out.stats["candidate_pixels_rejected_already_claimed"] >= 1


def test_offsets_are_inside_the_declared_radius():
    for window in (1.0, 1.42, 2.0, 2.5):
        for dy, dx, d in _offsets(window):
            assert 0.0 < d <= window + 1e-9
            assert abs(np.hypot(dy, dx) - d) < 1e-12


def test_robust_unit_is_bounded_and_footprint_limited():
    rng = np.random.default_rng(5)
    a = rng.normal(size=(40, 40)).astype(np.float32) * 10
    foot = np.zeros((40, 40), bool)
    foot[5:35, 5:35] = True
    u = robust_unit(a, foot)
    assert u.min() >= 0.0 and u.max() <= 1.0
    assert (u[~foot] == 0.0).all()


def test_density_cv_detects_concentration_change():
    foot = np.ones((40, 40), bool)
    uniform = np.zeros((40, 40), bool)
    uniform[::2, ::2] = True
    clustered = np.zeros((40, 40), bool)
    clustered[:20, :20] = True
    assert density_cv(clustered, foot, 10) > density_cv(uniform, foot, 10)


# --------------------------------------------------------------------------- parent rebuild
@pytest.mark.skipif(not (DATA / "parent").exists(), reason="pinned parent inputs not restored")
def test_parent_r0_rebuilds_byte_identical(tmp_path):
    from gems84.parent import emit_dots, load_grid, rebuild_r0_mask, sha256_file

    grid = load_grid(DATA)
    mask, base = rebuild_r0_mask(DATA)
    assert int(mask.sum()) == 37654
    assert int(base.sum()) == 40199
    assert not (mask & grid.catalogue).any()
    assert not (mask & (grid.d_cat <= 2.0)).any()          # the B=2 flank prune
    assert (base & (grid.d_cat > 2.0)).sum() == mask.sum()  # and nothing else was removed
    p = emit_dots(mask, grid, tmp_path / "r0-zeros.tif", mode="zeros")
    assert sha256_file(p) == R0_ZEROS_SHA256


@pytest.mark.skipif(not (DATA / "parent").exists(), reason="pinned parent inputs not restored")
def test_parent_footprint_and_catalogue_counts():
    from gems84.parent import load_grid

    grid = load_grid(DATA)
    assert int(grid.foot.sum()) == 5_167_373
    assert int(grid.catalogue.sum()) == 60_988
