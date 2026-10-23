import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems84.metric import dti_fast, dti_bruteforce, ALPHA, BETA


def test_fast_matches_bruteforce_random():
    rng = np.random.default_rng(0)
    for trial in range(8):
        h, w = 14, 14
        p = rng.random((h, w)) * (rng.random((h, w)) > 0.6)
        truth = rng.random((h, w)) > 0.85
        if truth.sum() == 0:
            truth[0, 0] = True
        fast = dti_fast(p, truth)
        brute = dti_bruteforce(p, truth)
        assert abs(fast["TPw"] - brute["TPw"]) < 1e-4, (trial, fast, brute)
        assert abs(fast["FPw"] - brute["FPw"]) < 1e-4, (trial, fast, brute)
        assert abs(fast["FNw"] - brute["FNw"]) < 1e-4, (trial, fast, brute)
        assert abs(fast["DTI"] - brute["DTI"]) < 1e-4, (trial, fast, brute)


def test_perfect_prediction_is_near_one():
    truth = np.zeros((20, 20), dtype=bool)
    truth[10, :] = True
    p = truth.astype(np.float64)
    r = dti_fast(p, truth)
    assert r["DTI"] > 0.999


def test_all_zero_prediction_scores_zero_with_any_truth():
    truth = np.zeros((20, 20), dtype=bool)
    truth[10, 10] = True
    p = np.zeros((20, 20))
    r = dti_fast(p, truth)
    assert r["TPw"] == 0.0
    assert r["DTI"] == 0.0


def test_single_vertical_line_known_shape():
    # Ground truth: single vertical line (matches the qualitative setup used in the
    # organizer's own worked example, section "Scoring example"). This test checks
    # internal self-consistency (fast == bruteforce), not the organizer's exact
    # printed numbers (we were not given the underlying raster, only a diagram).
    h, w = 9, 9
    truth = np.zeros((h, w), dtype=bool)
    truth[:, 4] = True
    p = np.zeros((h, w))
    p[:, 3] = 0.6
    p[:, 4] = 1.0
    p[:, 5] = 0.4
    fast = dti_fast(p, truth)
    brute = dti_bruteforce(p, truth)
    for k in ("TPw", "FPw", "FNw", "DTI"):
        assert abs(fast[k] - brute[k]) < 1e-4, (k, fast, brute)


def test_marginal_credit_identity():
    # [MEASURED] 1/DTI = alpha + alpha*(F/T) + beta*(K/T)  (re-derivation check)
    truth = np.zeros((15, 15), dtype=bool)
    truth[7, :] = True
    rng = np.random.default_rng(1)
    p = rng.random((15, 15)) * 0.5
    r = dti_fast(p, truth)
    T, F, K = r["TPw"], r["FPw"], r["n_truth"]
    lhs = 1.0 / r["DTI"]
    rhs = ALPHA + ALPHA * (F / T) + BETA * (K / T)
    assert abs(lhs - rhs) < 1e-4
