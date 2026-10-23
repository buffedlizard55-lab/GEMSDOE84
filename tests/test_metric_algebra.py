"""Brief v2 section-2 algebra, unit-tested against the shared metric code.

DTI = T / (0.2*T + 0.2*(S - M) + 0.8*|G|) for a binary dot field, where
T = kernel credit summed over truth pixels, S = sum p (= dot count),
M = sum over dots of max_g k(d).  A non-redundant dot pays iff its credit
exceeds 0.2 * current DTI; in general dots must be ranked by the exact
marginal gain recomputed from the metric, not by the shortcut.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vendor"))
from gems57 import metric  # noqa: E402


def test_binary_algebra_identity_random():
    rng = np.random.default_rng(7)
    for _ in range(12):
        h = w = 18
        truth = rng.random((h, w)) > 0.88
        truth[3, 3] = True
        pred = rng.random((h, w)) > 0.82
        r = metric.dti_binary(pred, truth)
        # M = S - FP_w for a binary field (FP_w = sum p*(1 - max_g k)).
        M = r["n_emitted"] - r["fp"]
        T, S, K = r["tp"], float(r["n_emitted"]), float(r["n_truth"])
        dti_alg = T / (0.2 * T + 0.2 * (S - M) + 0.8 * K)
        assert abs(dti_alg - r["dti"]) < 1e-9


def test_exact_marginal_matches_recomputed_dti():
    rng = np.random.default_rng(11)
    checked = 0
    for _ in range(30):
        h = w = 14
        truth = np.zeros((h, w), dtype=bool)
        truth[7, 2:12] = True                      # one line of truth
        pred = np.zeros((h, w))
        ys, xs = np.where(rng.random((h, w)) > 0.9)
        pred[ys, xs] = 1.0
        base = metric.dti_exact(pred, truth)
        T, K, n = base["tp"], float(base["n_truth"]), int((pred > 0).sum())
        M = n - base["fp"]                          # binary field
        empties = np.argwhere(pred == 0)
        j = int(rng.integers(len(empties)))
        y, x = (int(v) for v in empties[j])
        pred2 = pred.copy()
        pred2[y, x] = 1.0
        after = metric.dti_exact(pred2, truth)
        dT = after["tp"] - T
        k_self = float(metric.kernel(metric.distance_transform_edt(~truth)[y, x]))
        exact = metric.marginal_accept(dT, k_self, T, M, n, K)
        actual = after["dti"] > base["dti"] + 1e-12
        if abs(after["dti"] - base["dti"]) > 1e-12:
            assert exact == actual
            checked += 1
    assert checked >= 10


def test_isolated_dot_shortcut_bar():
    # One isolated truth pixel far from any other coverage: dT == k_self,
    # so the exact test must reduce to k > 0.2 * DTI.
    truth = np.zeros((21, 21), dtype=bool)
    truth[10, 10] = True
    truth[2, 2] = True
    pred = np.zeros((21, 21))
    pred[2, 2] = 1.0                                # existing perfect dot
    base = metric.dti_exact(pred, truth)
    bar = metric.marginal_inclusion_threshold(base["dti"])
    assert abs(bar - 0.2 * base["dti"]) < 1e-12
    # A dot 2 px from the isolated truth pixel: k = 1 - 2/3 > bar -> pays.
    p2 = pred.copy(); p2[10, 12] = 1.0
    assert metric.dti_exact(p2, truth)["dti"] > base["dti"]
    # A dot >3 px from any truth: k = 0 <= bar -> does not pay.
    p3 = pred.copy(); p3[10, 15] = 1.0
    assert metric.dti_exact(p3, truth)["dti"] < base["dti"]
