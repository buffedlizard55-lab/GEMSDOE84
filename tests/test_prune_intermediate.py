"""Exact MODEL ranking and fixed-count PRUNE, independent of restored data."""
from __future__ import annotations

import numpy as np
import pytest

from gems57 import metric
from gems84.prune_intermediate import kernel_trim_to_parent_count, snap_target_feasibility


def test_greedy_removals_match_shared_exact_metric_at_every_step():
    reference = np.zeros((16, 18), bool)
    reference[3:13, 2:15] = True
    parent = np.zeros_like(reference)
    for y, x in ((4, 3), (4, 6), (4, 9), (4, 12), (7, 3), (7, 6), (7, 9), (7, 12), (10, 4), (10, 11)):
        parent[y, x] = True
    ring = np.zeros_like(parent)
    ring[11, 6] = ring[11, 8] = ring[12, 12] = True
    result, order, stats = kernel_trim_to_parent_count(parent, ring, reference)
    live = parent | ring
    for selected in order:
        before = metric.dti_exact(live.astype(float), reference)['dti']
        deltas = []
        for flat in np.flatnonzero(parent & live):
            trial = live.copy()
            trial.ravel()[flat] = False
            delta = metric.dti_exact(trial.astype(float), reference)['dti'] - before
            deltas.append((flat, delta))
        selected_delta = dict(deltas)[selected]
        assert selected_delta == pytest.approx(max(delta for _, delta in deltas), abs=1e-12)
        live.ravel()[selected] = False
    assert np.array_equal(live, result)
    assert result[ring].all()
    assert int(result.sum()) == int(parent.sum())
    assert stats['reference_evidence_class'] == 'MODEL'
    assert stats['reference_dti_after_trim'] == pytest.approx(metric.dti_exact(result.astype(float), reference)['dti'])
    again, order2, _ = kernel_trim_to_parent_count(parent, ring, reference)
    assert np.array_equal(again, result) and np.array_equal(order2, order)


def test_kernel_ties_boundaries_and_disconnected_truth_are_exact():
    rng = np.random.default_rng(520810)
    for _ in range(8):
        reference = rng.random((18, 19)) > .3
        reference[0, 0] = reference[-1, -1] = True
        indices = rng.permutation(np.flatnonzero(reference))
        parent, ring = np.zeros_like(reference), np.zeros_like(reference)
        parent.ravel()[indices[:35]] = True
        ring.ravel()[indices[35:40]] = True
        mask, deleted, stats = kernel_trim_to_parent_count(parent, ring, reference)
        assert int(mask.sum()) == 35
        assert len(deleted) == 5
        assert (mask & ~reference).sum() == 0
        assert stats['reference_tp_after_trim'] == pytest.approx(metric.dti_exact(mask.astype(float), reference)['tp'])


def test_operator_never_mutates_parent_and_validates_reference():
    reference = np.ones((9, 9), bool)
    parent = np.zeros_like(reference)
    parent[2, 2] = parent[2, 6] = parent[6, 2] = parent[6, 6] = True
    ring = np.zeros_like(parent)
    ring[4, 4] = True
    before = parent.copy()
    kernel_trim_to_parent_count(parent, ring, reference)
    assert np.array_equal(before, parent)
    with pytest.raises(ValueError, match='disjoint'):
        kernel_trim_to_parent_count(parent, parent, reference)
    reference[2, 2] = False
    with pytest.raises(ValueError, match='fixed parent reference'):
        kernel_trim_to_parent_count(parent, ring, reference)


def test_snap_empty_target_window_is_a_constructive_impossibility():
    parent = np.zeros((10, 10), bool)
    parent[5, 5] = True
    allowed = np.ones_like(parent)
    allowed[3:8, 3:8] = False
    receipt = snap_target_feasibility(parent, allowed, 2.0)
    assert receipt['dots_without_any_allowed_target'] == 1
    assert not receipt['feasible_by_individual_windows']
    allowed[5, 7] = True
    assert snap_target_feasibility(parent, allowed, 2.0)['feasible_by_individual_windows']
    assert not snap_target_feasibility(parent, allowed, 1.42)['feasible_by_individual_windows']


def test_binary_canary_auc_handles_ties_exactly():
    from scripts.build_prune_intermediate import binary_auc
    feature = np.array([[1, 0, 1, 1, 0, 0]], bool)
    pos = np.array([[1, 1, 1, 0, 0, 0]], bool)
    neg = ~pos
    p, n = feature[pos], feature[neg]
    brute = ((p[:, None] > n[None, :]) + .5 * (p[:, None] == n[None, :])).mean()
    assert binary_auc(feature, pos, neg) == pytest.approx(brute)
