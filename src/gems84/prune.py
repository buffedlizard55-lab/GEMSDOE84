"""AXIS=PRUNE: catalogue-collar geometry at fixed dot count (Brief v2 section 5).

Parent R0 (``h33-h33-2-b2``) is the 0.2708-CLAIM solo ``d2_8`` lineage with every dot at
Euclidean catalogue distance ``d_cat <= 2.0 px`` deleted (37,654 dots, 0.2778 CLAIM).  The
historical ladder that produced R0 -- raw ``d2_8`` 44,090 dots (0.2600 CLAIM) -> prune
``d_cat > 1`` 40,199 dots (0.2708 CLAIM) -> prune ``d_cat > 2`` 37,654 dots (0.2778 CLAIM) --
confounds collar width with total mass at every step.  The operations here hold the dot
count at exactly 37,654 so a live receipt isolates collar geometry from AXIS=MASS:

* :func:`swap_in_near_collar` -- move the collar *inward* to ``d_cat > 1``: add every
  pre-prune dot in the ``1 < d_cat <= 2`` ring and remove the same number of R0's
  lowest exact-marginal-gain dots.
* :func:`drop_collar_band` -- move the collar *outward*: remove R0 dots inside a
  ``d_cat`` band; the caller refills the same count from the ranked candidate pool
  outside the new collar (``scripts/build_r0_variants.greedy_add_dots``).

Zero mass on catalogue pixels is never relaxed: every mask produced here is intersected
with ``~catalogue`` by construction of the inputs, and the inward variant keeps
``d_cat > 1.0 px`` (the AXIS=PRUNE exception in Hard Constraint 4).
"""
from __future__ import annotations

import numpy as np


def swap_in_near_collar(
    r0_mask: np.ndarray,
    near_pool: np.ndarray,
    gain_map: np.ndarray,
) -> tuple[np.ndarray, dict]:
    """Add all ``near_pool`` dots to ``r0_mask``, dropping the same number of lowest-gain dots.

    ``near_pool`` must be disjoint from ``r0_mask`` (the caller builds it as the pre-prune
    dots in the ``1 < d_cat <= 2`` ring).  ``gain_map`` is the exact 25-offset marginal DTI
    gain of each pixel against R0 (only its values on R0 dots are used).  Ties in gain are
    broken by row-major order via a stable sort, so the result is deterministic.
    """
    r0 = np.asarray(r0_mask, dtype=bool)
    pool = np.asarray(near_pool, dtype=bool) & ~r0
    n_add = int(pool.sum())
    if n_add == 0:
        raise ValueError("near_pool has no dots outside r0_mask")
    ry, rx = np.nonzero(r0)
    if n_add >= ry.size:
        raise ValueError(f"near_pool ({n_add}) is not smaller than r0_mask ({ry.size})")
    gains = np.asarray(gain_map, dtype=np.float64)[ry, rx]
    order_asc = np.argsort(gains, kind="mergesort")
    drop_idx = order_asc[:n_add]
    out = r0.copy()
    out[ry[drop_idx], rx[drop_idx]] = False
    out[pool] = True
    stats = {
        "dots_added": n_add,
        "dots_removed": int(n_add),
        "n_dots": int(out.sum()),
        "removed_gain_min": float(gains[drop_idx].min()),
        "removed_gain_max": float(gains[drop_idx].max()),
        "kept_gain_min": float(gains[order_asc[n_add:]].min()),
    }
    assert stats["n_dots"] == int(r0.sum())
    return out, stats


def drop_collar_band(
    r0_mask: np.ndarray,
    d_cat: np.ndarray,
    *,
    lo: float,
    hi: float,
    hi_inclusive: bool,
) -> tuple[np.ndarray, np.ndarray]:
    """Remove R0 dots with ``lo < d_cat < hi`` (or ``<= hi`` when ``hi_inclusive``).

    Returns ``(base_mask, removed_mask)``.  The caller refills ``removed_mask.sum()`` dots
    from a ranked candidate pool that satisfies the new collar, restoring the parent count.
    """
    r0 = np.asarray(r0_mask, dtype=bool)
    d = np.asarray(d_cat, dtype=np.float64)
    in_band = (d > lo) & (d <= hi if hi_inclusive else d < hi)
    removed = r0 & in_band
    if not removed.any():
        raise ValueError(f"no R0 dots in collar band ({lo}, {hi}{' incl' if hi_inclusive else ''})")
    return r0 & ~removed, removed
