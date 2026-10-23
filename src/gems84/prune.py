"""Fixed-count collar refill using exact DTI increments on a declared MODEL truth.

The surrogate is the binary support union of three pinned ancestor predictions,
NOT observed or inferred new-fault labels. No catalogue recovery tuning is done.
Shared gems57 metric offsets/DTI remain the reference implementation.
"""
import heapq

import numpy as np
from scipy.ndimage import distance_transform_edt
from gems57 import metric


def refill(kept, pool, surrogate, count, min_sep=2.8):
    """Lazy greedy exact marginal DTI ranking; stable row-major tie-break.

    For positive gains, D and s=T/D increase monotonically. Thus a stale
    (dT-s*dD)/(D+dD) is an upper bound: coverage only increases and dT falls.
    Fail closed if no positive increment or insufficient spacing-safe pool.
    """
    mask = kept.copy()
    truth = np.asarray(surrogate, bool)
    dy, dx, kw = metric.OFF_DY, metric.OFF_DX, metric.OFF_K
    cover = np.maximum(0., 1. - distance_transform_edt(~mask) / 3.)
    credit = np.maximum(0., 1. - distance_transform_edt(~truth) / 3.)
    T = float(cover[truth].sum())
    D = .2*T + .2*(mask.sum()-credit[mask].sum()) + .8*truth.sum() + metric.EPS
    cov = np.pad(cover, 3)
    tr = np.pad(truth, 3)
    h, w = mask.shape
    eligible = pool & ~mask & (distance_transform_edt(~mask) >= min_sep)
    blocked = ~eligible
    disk = [(y,x) for y in range(-3,4) for x in range(-3,4)
            if y*y+x*x < min_sep*min_sep]

    def increment(flat):
        r,c = divmod(flat,w)
        yy,xx = r+3+dy,c+3+dx
        dt = float((tr[yy,xx]*np.maximum(0., kw-cov[yy,xx])).sum())
        dd = .2*(dt+1.-credit[r,c])
        gain = (dt-(T/D)*dd)/(D+dd)
        return gain,dt,dd

    heap=[]
    for f in np.flatnonzero(eligible):
        gain,_,_ = increment(int(f))
        heap.append((-gain,int(f),0))
    heapq.heapify(heap)
    records=[]
    while heap and len(records)<count:
        _,f,version=heapq.heappop(heap)
        r,c=divmod(f,w)
        if blocked[r,c]:
            continue
        gain,dt,dd=increment(f)
        if version != len(records):
            heapq.heappush(heap,(-gain,f,len(records)))
            continue
        if gain <= 0:
            raise ValueError('No positive MODEL marginal gain; refusing unranked refill')
        mask[r,c]=True
        records.append({'flat_index':f,'model_marginal_dti':gain})
        yy,xx=r+3+dy,c+3+dx
        cov[yy,xx]=np.maximum(cov[yy,xx],kw)
        T+=dt;D+=dd
        for y,x in disk:
            if 0<=r+y<h and 0<=c+x<w:
                blocked[r+y,c+x]=True
    if len(records)!=count:
        raise ValueError(f'Refill exhausted: {len(records)} of {count}; no spacing relaxation')
    return mask,records
