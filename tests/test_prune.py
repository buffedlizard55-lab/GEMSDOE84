import numpy as np
import pytest
from scipy.ndimage import distance_transform_edt
from gems57 import metric
from gems84.prune import refill


def test_exact_marginal_ranking_matches_exhaustive_metric():
    truth=np.zeros((18,19),bool)
    truth[3:15,4:14]=True
    mask=np.zeros_like(truth);mask[7,7]=True
    pool=truth.copy();pool[mask]=False
    actual,records=refill(mask,pool,truth,5)
    expected=mask.copy()
    for record in records:
        before=metric.dti_exact(expected.astype(float),truth)['dti']
        candidates=np.flatnonzero(pool&~expected&(distance_transform_edt(~expected)>=2.8))
        gains=[]
        for f in candidates:
            trial=expected.copy();trial.ravel()[f]=True
            gains.append(metric.dti_exact(trial.astype(float),truth)['dti']-before)
        best=int(candidates[np.argmax(gains)])
        assert record['flat_index']==best
        assert record['model_marginal_dti']==pytest.approx(max(gains),abs=1e-12)
        expected.ravel()[best]=True
    assert np.array_equal(actual,expected)


def test_exhausted_pool_fails_closed():
    truth=np.ones((10,10),bool);mask=np.zeros_like(truth);mask[5,5]=True
    with pytest.raises(ValueError,match='exhausted'):
        refill(mask,np.zeros_like(mask),truth,1)
