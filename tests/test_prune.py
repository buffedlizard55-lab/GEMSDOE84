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


def test_written_prune_artifacts_against_pinned_template():
    import hashlib
    import json
    from pathlib import Path
    import rasterio
    root=Path(__file__).resolve().parents[1]
    card=json.loads((root/'evidence/prune_gt3_20261023.json').read_text())
    pins={e['id']:e for e in card['inputs']}
    for key in ('sample_submission','labels','existing_faults'):
        p=root/'data/bridge'/pins[key]['dest']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==pins[key]['sha256']
    with rasterio.open(root/'data/bridge/sample_submission.tif') as ref:
        foot=np.isfinite(ref.read(1));profile=ref.profile
    with rasterio.open(root/'data/bridge/labels.tif') as ds:
        a=ds.read(1);cat=np.isfinite(a)&(a>0)&foot
    distance=distance_transform_edt(~cat)
    masks=[]
    for mode in ('nan','zeros'):
        p=root/card[mode]['path']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==card[mode]['sha256']
        with rasterio.open(p) as ds:
            assert ds.crs==profile['crs'] and ds.transform==profile['transform']
            assert ds.shape==foot.shape and ds.dtypes==('float32',) and ds.count==1
            a=ds.read(1)
        assert np.isfinite(a[foot]).all() and np.isin(a[foot],[0.,1.]).all()
        assert np.isnan(a[~foot]).all() if mode=='nan' else (a[~foot]==0).all()
        assert (a[cat]==0).all() and (a>0).sum()==37654
        assert (distance[a>0]>3).all()
        masks.append(a>0)
    assert np.array_equal(*masks)
