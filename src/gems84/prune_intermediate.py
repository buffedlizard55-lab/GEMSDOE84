"""Fixed-count inward PRUNE control using only the parent's H19-5 field.

No new physical signal is introduced. The reference is a *MODEL lineament mask*,
not hidden fault truth. Ranking uses the shared metric's exact 25-offset kernel:
remove the least uniquely covered reference mass, update affected neighbours and
repeat. Since every dot lies on the binary reference, FP=0 for this MODEL only;
exact DTI loss is monotone in lost reference credit. This is not a live-score or
catalogue-PROXY estimator. No alpha*n shortcut or correlation/overlap gate.
"""
from __future__ import annotations

import hashlib
import heapq

import numpy as np
from scipy.sparse import coo_matrix

from gems57 import metric


def snap_target_feasibility(parent, allowed, max_shift=2.0):
    """An empty permitted target window proves count-preserving SNAP impossible."""
    parent = np.asarray(parent, bool)
    allowed = np.asarray(allowed, bool)
    if parent.shape != allowed.shape or max_shift < 0:
        raise ValueError("matching grids and a nonnegative displacement are required")
    y, x = np.nonzero(parent)
    h, w = parent.shape
    count = np.zeros(len(y), np.int32)
    r = int(np.ceil(max_shift))
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy * dy + dx * dx > max_shift * max_shift:
                continue
            yy, xx = y + dy, x + dx
            ok = (yy >= 0) & (yy < h) & (xx >= 0) & (xx < w)
            ids = np.flatnonzero(ok)
            count[ids] += allowed[yy[ok], xx[ok]]
    return {
        "max_shift_px": max_shift, "parent_dots": int(parent.sum()),
        "dots_without_any_allowed_target": int(np.count_nonzero(count == 0)),
        "minimum_targets_per_dot": int(count.min()) if count.size else 0,
        "counts_sha256": hashlib.sha256(count.tobytes()).hexdigest(),
        "feasible_by_individual_windows": bool((count > 0).all()),
        "caveat": "Nonempty windows alone do not prove an injective assignment; empty windows disprove it.",
    }


def kernel_trim_to_parent_count(parent, ring, reference):
    """Insert the entire ring; trim the same number of original dots by exact MODEL loss.

    Ring and parent must be disjoint and lie on the fixed binary parent field.
    Greedy deletion updates *all* kernel neighbours after every removal. Ties
    resolve by original raster index. There is no RNG or changing field/rank fit.
    Returns the final mask, an ordered deletion certificate, and MODEL diagnostics.
    """
    parent, ring, reference = (np.asarray(a, bool) for a in (parent, ring, reference))
    if parent.ndim != 2 or parent.shape != ring.shape or parent.shape != reference.shape:
        raise ValueError("parent, ring and reference must be matching 2-D masks")
    if np.any(parent & ring):
        raise ValueError("ring must be disjoint from the parent")
    n_remove = int(ring.sum())
    if n_remove == 0 or n_remove >= int(parent.sum()):
        raise ValueError("nonempty ring must be smaller than the parent")
    combined = parent | ring
    if np.any(combined & ~reference):
        raise ValueError("all dots must lie on the fixed parent reference field")

    h, w = parent.shape
    pred_flat = np.flatnonzero(combined)
    py, px = np.divmod(pred_flat, w)
    truth_flat = np.flatnonzero(reference)
    n_truth = len(truth_flat)
    lookup = np.full(h * w, -1, np.int32)
    lookup[truth_flat] = np.arange(n_truth, dtype=np.int32)
    edge_pred, edge_truth, edge_weight = [], [], []
    for dy, dx, weight in zip(metric.OFF_DY, metric.OFF_DX, metric.OFF_K):
        yy, xx = py + dy, px + dx
        ok = (yy >= 0) & (yy < h) & (xx >= 0) & (xx < w)
        ids = np.flatnonzero(ok)
        gt = lookup[yy[ok] * w + xx[ok]]
        hit = gt >= 0
        edge_pred.append(ids[hit])
        edge_truth.append(gt[hit])
        edge_weight.append(np.full(int(hit.sum()), weight, np.float64))
    ep, et, ew = map(np.concatenate, (edge_pred, edge_truth, edge_weight))
    adjacency = coo_matrix((ew, (ep, et)), shape=(len(py), n_truth)).tocsr()
    by_truth = adjacency.tocsc()
    del lookup, edge_pred, edge_truth, edge_weight

    credit = np.zeros(n_truth, np.float64)
    np.maximum.at(credit, et, ew)
    second = np.zeros_like(credit)
    np.maximum.at(second, et[ew < credit[et]], ew[ew < credit[et]])
    ties = np.bincount(et[ew == credit[et]], minlength=n_truth)
    gap = np.where(ties == 1, credit - second, 0.0)
    loss = np.zeros(len(py), np.float64)
    winner_edges = (ew == credit[et]) & (ties[et] == 1)
    np.add.at(loss, ep[winner_edges], gap[et[winner_edges]])
    del ep, et, ew, gap, second, ties, winner_edges

    eligible = parent.ravel()[pred_flat]
    active = np.ones(len(py), bool)
    generation = np.zeros(len(py), np.int32)
    heap = [(float(loss[i]), int(pred_flat[i]), 0, i) for i in np.flatnonzero(eligible)]
    heapq.heapify(heap)
    initial_loss_sha = hashlib.sha256(np.asarray(loss[eligible], '<f8').tobytes()).hexdigest()
    tp = float(credit.sum())
    initial_tp = tp
    deleted_flat, lost_credit, exact_dti_delta = [], [], []

    def contributor(gt):
        start, end = by_truth.indptr[gt:gt + 2]
        ids, weights = by_truth.indices[start:end], by_truth.data[start:end]
        live = active[ids]
        ids, weights = ids[live], weights[live]
        if not len(ids):
            return None, 0.0, 0.0
        best = float(weights.max())
        top = weights == best
        if int(top.sum()) > 1:
            return None, best, 0.0
        winner = int(ids[np.flatnonzero(top)[0]])
        other = float(weights[~top].max()) if (~top).any() else 0.0
        return winner, best, best - other

    for _ in range(n_remove):
        while heap:
            dcredit, flat, gen, pred = heapq.heappop(heap)
            if active[pred] and gen == generation[pred]:
                break
        else:
            raise RuntimeError("not enough eligible original parent dots")
        start, end = adjacency.indptr[pred:pred + 2]
        affected = adjacency.indices[start:end]
        old = [(int(gt), contributor(int(gt))) for gt in affected]
        before = metric.dti_from_components(tp, 0.0, n_truth - tp)
        active[pred] = False
        changed, actual_loss = set(), 0.0
        for gt, (old_winner, old_credit, old_gap) in old:
            if old_winner is not None:
                loss[old_winner] -= old_gap
                changed.add(old_winner)
            new_winner, new_credit, new_gap = contributor(gt)
            if new_winner is not None:
                loss[new_winner] += new_gap
                changed.add(new_winner)
            credit[gt] = new_credit
            actual_loss += old_credit - new_credit
        if not np.isclose(actual_loss, dcredit, rtol=1e-9, atol=1e-10):
            raise RuntimeError("stale/non-exact marginal reference credit")
        tp -= actual_loss
        after = metric.dti_from_components(tp, 0.0, n_truth - tp)
        for other in changed:
            if active[other] and eligible[other]:
                if loss[other] < -1e-9:
                    raise RuntimeError("negative deletion credit")
                loss[other] = max(0.0, loss[other])
                generation[other] += 1
                heapq.heappush(heap, (float(loss[other]), int(pred_flat[other]),
                                      int(generation[other]), int(other)))
        deleted_flat.append(flat)
        lost_credit.append(actual_loss)
        exact_dti_delta.append(after - before)

    out = combined.copy()
    deleted = np.asarray(deleted_flat, np.int64)
    out.ravel()[deleted] = False
    if int(out.sum()) != int(parent.sum()) or not out[ring].all():
        raise RuntimeError("fixed-count/ring retention invariant failed")
    # Full-grid independent shared metric, not the adjacency bookkeeping, certifies
    # the exact MODEL arithmetic once at the end (and in synthetic unit tests).
    shared = metric.dti_exact(out.astype(np.float32), reference)
    if not np.isclose(shared['tp'], tp, rtol=1e-11, atol=1e-8) or shared['fp'] != 0.0:
        raise RuntimeError("deletion bookkeeping disagrees with the shared exact metric")
    return out, deleted, {
        "reference_evidence_class": "MODEL",
        "reference": "Pinned H19-5 parent lineament mask; NOT fault truth or a probability calibration",
        "reference_pixels": n_truth,
        "reference_tp_before_trim": initial_tp, "reference_tp_after_trim": tp,
        "reference_dti_after_trim": shared['dti'],
        "initial_parent_deletion_credit_sha256": initial_loss_sha,
        "deleted_order_sha256": hashlib.sha256(deleted.astype('<i8').tobytes()).hexdigest(),
        "deletion_credit_min": float(min(lost_credit)),
        "deletion_credit_max": float(max(lost_credit)),
        "exact_reference_dti_delta_sum": float(sum(exact_dti_delta)),
        "ranking": "Greedy exact shared-kernel deletion loss, updated after each removal; row-major tie-break",
        "randomness": "None; seed 520810 is used only for report-only diagnostics",
        "caveat": "Reference arithmetic is MODEL ranking only, not a PROXY or predicted live improvement.",
    }
