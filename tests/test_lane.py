import importlib.util
import sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('lane',ROOT/'scripts/run_lane.py')
lane=importlib.util.module_from_spec(spec);spec.loader.exec_module(lane)
from gems57 import evaluate_holdout as E, metric, submission_writer as W


def test_dots_mask_range_separation():
    a=np.arange(225,dtype='float32').reshape(15,15)/225
    mask=np.ones_like(a,bool);mask[:,0]=False
    p=lane.dots(a,mask,12)
    assert p.sum()==12 and not p[:,0].any()
    xy=np.column_stack(np.nonzero(p))
    d=((xy[:,None]-xy[None,:])**2).sum(2)
    assert (d[np.triu_indices(len(xy),1)]>=9).all()


def test_unit_zero_and_rank():
    assert not lane.unit(np.zeros((4,4)),np.ones((4,4),bool)).any()
    assert lane.rank_vector(np.ones(6)) is None
    r=lane.rank_vector(np.arange(6))
    assert np.isclose(np.dot(r,r),1)


def test_writer_rejects_before_packaging(tmp_path):
    for value in [float('nan'),float('inf'),-1,1.001]:
        a=np.full((3,3),value)
        with pytest.raises(ValueError):
            W.write_submission(tmp_path/'bad.tif',a,'absent.tif',np.ones((3,3),bool),name='test',note='test')
        assert not list(tmp_path.iterdir())


def test_evaluator_masks_known_exactly_and_terms_match():
    valid=np.ones((15,15),bool);truth=np.zeros_like(valid);truth[7,7]=True
    visible=np.zeros_like(valid);visible[1,1]=True
    p=truth.astype('float32');p[1,1]=1
    result,t=E.evaluate(p,dict(region=valid,visible=visible,truth=truth),valid,block_side=5)
    assert result['dti']==pytest.approx(1,abs=1e-6)
    assert result['n_emitted']==1
    assert E.from_terms(t.sum(0))==pytest.approx(result['dti'])


def test_pooling_records_ci_counts_and_rejects_mismatch():
    a=np.array([[2.,1.,3.,5.],[1.,1.,2.,3.]])
    summary=E.pooled_summary({'rfd':a,'control':a.copy()},candidate='rfd',draws=50)
    assert summary['scores']['rfd']['withheld_positive_pixels']==8
    assert len(summary['scores']['rfd']['ci95'])==2
    b=a.copy();b[0,3]+=1
    with pytest.raises(ValueError):E.pooled_summary({'rfd':a,'control':b},candidate='rfd',draws=50)


def test_vendor_pins():
    import json,hashlib
    pins=json.loads((ROOT/'registry/template_pin.json').read_text())
    for name,digest in pins['files'].items():
        assert hashlib.sha256((ROOT/'vendor/gems57'/name).read_bytes()).hexdigest()==digest


def test_writer_real_tiff_and_zip_roundtrip(tmp_path):
    import rasterio,zipfile,json
    from gems57 import grid
    sample=tmp_path/'sample.tif'
    a=np.zeros(grid.HEIGHT*grid.WIDTH,dtype='float32').reshape(grid.HEIGHT,grid.WIDTH)
    fp=np.zeros_like(a,bool);fp[100:120,100:120]=True
    with rasterio.open(sample,'w',driver='GTiff',count=1,width=grid.WIDTH,height=grid.HEIGHT,dtype='float32',crs=f'EPSG:{grid.EPSG}',transform=grid.TRANSFORM,compress='deflate') as dst:dst.write(a,1)
    a[110,110]=1
    p=tmp_path/'candidate.tif'
    receipt=W.write_submission(p,a,sample,fp,name='test-only',note='Fixture only; never submit.')
    assert receipt['validator']['all_checks_passed']
    assert receipt['validator']['n_nan']==0
    assert receipt['approved_for_weekly_slot'] is False
    with zipfile.ZipFile(p.with_suffix('.zip')) as z:
        assert z.namelist()==[p.name]
        assert z.read(p.name)==p.read_bytes()
    with pytest.raises(FileExistsError):W.write_submission(p,a,sample,fp,name='test-only',note='test')


def test_empty_mask_and_zero_budget_fail_closed():
    with pytest.raises(ValueError):lane.unit(np.zeros((4,4)),np.zeros((4,4),bool))
    with pytest.raises(ValueError):lane.dots(np.ones((4,4)),np.ones((4,4),bool),0)


def test_site_local_links_and_fail_closed_release():
    import json, hashlib
    from html.parser import HTMLParser
    from urllib.parse import urlsplit,unquote
    class Links(HTMLParser):
        def __init__(self):super().__init__();self.links=[]
        def handle_starttag(self,tag,attrs):
            self.links.extend(v for k,v in attrs if k in ('href','src') and v)
    for p in (ROOT/'docs').glob('*.html'):
        parser=Links();parser.feed(p.read_text())
        for href in parser.links:
            u=urlsplit(href)
            if not u.scheme and u.path:
                assert (p.parent/unquote(u.path)).exists(),(p,href)
    card=json.loads((ROOT/'evidence/run-card.json').read_text())
    assert card['verdict'] in ('negative','promote')
    # For negative verdict, site must clearly state non-promotion; for promote, must not claim DO NOT SUBMIT as primary banner
    html = (ROOT/'docs/index.html').read_text()
    if card['verdict']=='negative':
        assert ('DO NOT SUBMIT' in html) or ('RESEARCH-ONLY' in html) or ('FORMAT-VALID ONLY' in html) or ('NEGATIVE' in html)
    assert card['submission_slots_used']==0
    # note field may be under 'note' or 'submission_note'
    note = card.get('note') or card.get('submission_note') or ''
    assert len(note)<=140
    # If registry was flagged as duplicate with literal rule, old lane required no TIFF; new lane allows a format-valid research artifact with explicit caveat
    if card['registry_correlation_overlap'].get('duplicate') and card.get('raster_sha256') is None:
        assert not list((ROOT/'docs').rglob('*.tif'))
    # If a raster is shipped, verify its format regardless of verdict
    if card.get('binary_removed_2026_10_23'):
        # IR-84-08: negative-lane binary deliberately removed; sha is receipt-only.
        assert not (ROOT / card['submission_file']).exists() if card.get('submission_file') else True
    elif card.get('raster_sha256'):
        tif = None
        # support both old and new run-card schemas
        if card.get('submission_file'):
            tif = ROOT / card['submission_file']
        elif card.get('submission') and isinstance(card['submission'], dict):
            tif = ROOT / 'docs/downloads' / card['submission'].get('file','')
        else:
            # fallback: find any tif in docs/downloads
            cands = list((ROOT/'docs/downloads').glob('*.tif'))
            tif = cands[0] if cands else None
        assert tif is not None and tif.exists(), f"expected TIFF for raster_sha256 {card['raster_sha256']}"
        assert hashlib.sha256(tif.read_bytes()).hexdigest() == card['raster_sha256']
        import rasterio
        with rasterio.open(tif) as s:
            a = s.read(1)
            assert s.count == 1 and s.dtypes[0] == 'float32' and s.shape == (3730, 3292)
            assert s.crs.to_epsg() == 32611
            assert tuple(s.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert str(card['raster_sha256']) in html or 'download' in html.lower()
