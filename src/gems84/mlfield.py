"""Catalogue-analogue field: HGB classifier on the catalogue-blind physics basis.

Positives: VISIBLE catalogue cells.  Negatives: footprint cells > 5 px from any
visible fault (label-blind -- withheld faults are never consulted, so on the
holdout some negatives are genuinely hidden faults, exactly as on the live board).
Output basis columns (rank-transformed in the footprint):
  * ``ml_prob``  -- predicted probability
  * ``ml_ridge`` -- scale-normalised Hessian line response of the probability
    field (sigma 1 px), i.e. the thin crest lines of the "looks like a mapped
    fault" surface.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier

from .basis import _fill, _rank01


def ridge_only(a: np.ndarray, sigma: float) -> np.ndarray:
    """Crest strength: -(most negative Hessian eigenvalue), clipped at 0, scale-normalised."""
    f = _fill(a)
    hyy = ndi.gaussian_filter(f, sigma, order=(2, 0))
    hxx = ndi.gaussian_filter(f, sigma, order=(0, 2))
    hxy = ndi.gaussian_filter(f, sigma, order=(1, 1))
    lo = 0.5 * (hxx + hyy) - np.sqrt(0.25 * (hxx - hyy) ** 2 + hxy ** 2)
    return (sigma ** 2) * np.maximum(-lo, 0.0)


def train_predict(X_phys: np.ndarray, footprint: np.ndarray, visible: np.ndarray,
                  seed: int = 84, n_neg: int = 250_000):
    fp = footprint
    vis = np.asarray(visible, bool) & fp
    d = ndi.distance_transform_edt(~vis)[fp]
    pos = np.flatnonzero(vis[fp])
    negpool = np.flatnonzero(d > 5)
    rng = np.random.default_rng(seed)
    neg = rng.choice(negpool, min(n_neg, negpool.size), replace=False)
    idx = np.concatenate([pos, neg])
    y = np.concatenate([np.ones(pos.size), np.zeros(neg.size)])
    clf = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.08, max_leaf_nodes=48,
                                         min_samples_leaf=200, l2_regularization=1.0,
                                         random_state=seed)
    clf.fit(X_phys[idx].astype(np.float32), y)
    prob = np.zeros(X_phys.shape[0], np.float32)
    step = 600_000
    for a in range(0, X_phys.shape[0], step):
        prob[a:a + step] = clf.predict_proba(X_phys[a:a + step].astype(np.float32))[:, 1]
    full = np.full(fp.shape, np.nan, np.float32)
    full[fp] = prob
    ridge = ridge_only(np.where(fp, full, np.nan), 1.0)
    cols = np.stack([_rank01(prob).astype(np.float16),
                     _rank01(ridge[fp]).astype(np.float16)], axis=1)
    return cols, ["ml_prob", "ml_ridge"], dict(n_pos=int(pos.size), n_neg=int(neg.size))
