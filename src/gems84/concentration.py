"""AXIS=CONCENTRATION: km-block mass reallocation at fixed dot count (Brief v2 section 5).

Parent R0 (``h33-h33-2-b2``, 37,654 dots) is a maximal 2.8 px packing of a corroborated
ridge field, so its dots already sit where the per-pixel ranking is strongest.  This axis
asks a different, purely geographic question: holding count, spacing, collar and the
per-dot ranking fixed, does shifting dots *between* 5 km blocks -- out of blocks whose
mean parent-ranking surface ``q`` is low and into blocks where it is high -- raise DTI?

Operators here are pure array functions (no I/O) so they are unit-testable on synthetic
grids.  The builder (``scripts/build_concentration_variants.py``) supplies ``q`` and the
exact marginal-DTI gain map from the recorded parent recipe, removes the lowest-gain
dots inside donor blocks, and refills inside recipient blocks with the shared greedy
selector (``scripts/build_r0_variants.greedy_add_dots``) from the canonical candidate
pool at ``d_cat >= 3 px``.
"""
from __future__ import annotations

import numpy as np

BLOCK_PX = 50          # 50 px x 100 m = 5 km blocks
MIN_FOOT_FRAC = 0.5    # a block is eligible only if >= 50% of it is inside the footprint


def block_prior(q: np.ndarray, foot: np.ndarray, block_px: int = BLOCK_PX,
                min_foot_frac: float = MIN_FOOT_FRAC) -> tuple[np.ndarray, np.ndarray]:
    """Mean of ``q`` over footprint pixels per block.  Returns ``(prior, eligible)``.

    ``prior`` is NaN on ineligible blocks (footprint share < ``min_foot_frac``).  Blocks
    are ``block_px`` squares from origin (0, 0); the bottom/right partial strips of the
    grid belong to no block and are therefore frozen by every CONCENTRATION arm.
    """
    h, w = foot.shape
    ny, nx = h // block_px, w // block_px
    sl = np.s_[: ny * block_px, : nx * block_px]
    f = foot[sl].reshape(ny, block_px, nx, block_px).sum(axis=(1, 3)).astype(np.float64)
    qs = np.where(foot, q, 0.0)[sl].reshape(ny, block_px, nx, block_px).sum(axis=(1, 3))
    eligible = f >= (min_foot_frac * block_px * block_px)
    prior = np.where(eligible, qs / np.maximum(f, 1.0), np.nan)
    return prior, eligible


def expand_blocks(block_mask: np.ndarray, shape: tuple[int, int],
                  block_px: int = BLOCK_PX) -> np.ndarray:
    """Expand a per-block boolean mask to full grid resolution (strips stay False)."""
    ny, nx = block_mask.shape
    full = np.zeros(shape, dtype=bool)
    full[: ny * block_px, : nx * block_px] = np.kron(
        block_mask, np.ones((block_px, block_px), dtype=bool))
    return full


def donor_recipient_masks(prior: np.ndarray, eligible: np.ndarray,
                          shape: tuple[int, int], block_px: int = BLOCK_PX) -> dict:
    """Full-resolution donor/recipient block masks, pairwise disjoint by construction.

    ``bot50``: prior at/below the eligible-block median; ``top50``: strictly above it;
    ``top25``: at/above the 75th percentile.  Percentiles are over eligible blocks only.
    """
    vals = prior[eligible]
    if vals.size == 0:
        raise ValueError("no eligible blocks")
    p50 = float(np.percentile(vals, 50.0))
    p75 = float(np.percentile(vals, 75.0))
    out = {
        "bot50": expand_blocks(eligible & (prior <= p50), shape, block_px),
        "top50": expand_blocks(eligible & (prior > p50), shape, block_px),
        "top25": expand_blocks(eligible & (prior >= p75) & (prior > p50), shape, block_px),
        "p50": p50,
        "p75": p75,
        "n_eligible_blocks": int(eligible.sum()),
    }
    if np.any(out["bot50"] & out["top50"]) or np.any(out["bot50"] & out["top25"]):
        raise RuntimeError("donor/recipient block masks are not disjoint")
    return out


def lowest_gain_dots(mask: np.ndarray, region: np.ndarray, gain: np.ndarray,
                     n: int) -> np.ndarray:
    """Boolean mask of the ``n`` lowest-gain dots of ``mask`` inside ``region``.

    Stable (mergesort) ordering on row-major dot order, matching the recorded parent
    ranking convention used by the MASS/PRUNE builders.
    """
    ys, xs = np.nonzero(np.asarray(mask, bool) & np.asarray(region, bool))
    if n > ys.size:
        raise ValueError(f"requested {n} donor dots, region holds {ys.size}")
    order = np.argsort(np.asarray(gain, np.float64)[ys, xs], kind="mergesort")
    drop = np.zeros(np.asarray(mask).shape, dtype=bool)
    drop[ys[order[:n]], xs[order[:n]]] = True
    return drop


def block_dot_shares(mask: np.ndarray, regions: dict, foot: np.ndarray) -> dict:
    """Share of ``mask`` dots inside each named full-resolution region."""
    n = int(mask.sum())
    shares = {}
    for name in ("bot50", "top50", "top25"):
        shares[f"dots_{name}"] = int((mask & regions[name]).sum())
        shares[f"share_{name}"] = round(shares[f"dots_{name}"] / max(n, 1), 4)
    shares["dots_outside_eligible_blocks"] = int(
        (mask & foot & ~regions["bot50"] & ~regions["top50"]).sum())
    shares["n_dots"] = n
    return shares
