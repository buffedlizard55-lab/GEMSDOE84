#!/usr/bin/env python3
"""Build one PRUNE >3 px, fixed-count arm; refuse repeated axis/value or hashes.

All raster inputs are pinned before read. Outputs are predictions, not distributed
competition inputs. Run with .venv/bin/python scripts/build_prune_variant.py.
--validate-only re-reads the existing output without rebuilding an experiment.
"""
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'vendor')]
import numpy as np
import rasterio
from sklearn.metrics import roc_auc_score
from gems84.parent import (load_grid, rebuild_r0_mask, sha256_file, emit_dots,
                           BASE_REL, BASE_02708_SHA256)
from gems84.prune import refill

DATA=ROOT/'.cache/gems_data'
PARENT='h33-h33-2-b2'
VALUE='gt3-refill-ancestor-union'
CARD=ROOT/'evidence/prune_gt3_20261023.json'


def verify_inputs():
    wanted={'labels','existing_faults','sample_submission','scored_h19_5','scored_h19_4','scored_h16_1'}
    entries=[e for e in json.loads((ROOT/'registry/data_manifest.json').read_text())['files'] if e['id'] in wanted]
    entries.append({'id':'lineage_base','dest':BASE_REL,'sha256':BASE_02708_SHA256})
    for e in entries:
        assert sha256_file(DATA/e['dest'])==e['sha256'], e['id']
    return entries


def validate(path, grid, r0, mode):
    with rasterio.open(DATA/'sample_submission.tif') as ref, rasterio.open(path) as ds:
        a=ds.read(1)
        checks={'crs':ds.crs==ref.crs and ds.crs.to_epsg()==32611,
                'shape':ds.shape==ref.shape,'transform':ds.transform==ref.transform,
                'dtype':ds.dtypes==('float32',),'bands':ds.count==1,
                'inside_finite':bool(np.isfinite(a[grid.foot]).all()),
                'inside_range':bool(((a[grid.foot]>=0)&(a[grid.foot]<=1)).all()),
                'outside':bool(np.isnan(a[~grid.foot]).all()) if mode=='nan' else bool((a[~grid.foot]==0).all()),
                'zero_catalogue':bool((a[grid.catalogue]==0).all()),
                'count':int((a>0).sum())==int(r0.sum()),
                'collar':bool((grid.d_cat[a>0]>3).all())}
    mask=a>0
    removed=int((r0&~mask).sum());added=int((mask&~r0).sum())
    pct=100*removed/int(r0.sum())
    checks['changed_1_to_50_pct']=1<=pct<=50
    checks['only_collar_removed']=bool((grid.d_cat[r0&~mask]<=3).all())
    assert all(checks.values()),checks
    return {'checks':checks,'sha256':sha256_file(path),'n_dots':int(mask.sum()),
            'removed':removed,'added':added,'retained':int((mask&r0).sum()),
            'pct_changed':pct,'symmetric_difference_pixels':removed+added,
            'symmetric_difference_pct_of_parent':100*(removed+added)/int(r0.sum()),
            'minimum_catalogue_distance_px':float(grid.d_cat[mask].min()),
            'path':str(path.relative_to(ROOT))}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--validate-only',action='store_true');args=ap.parse_args()
    pins=verify_inputs()
    subprocess.run([sys.executable,str(ROOT/'scripts/rebuild_r0.py'),'--receipt',str(ROOT/'.cache/prune_r0_preflight.json')],check=True)
    grid=load_grid(DATA);r0,_=rebuild_r0_mask(DATA)
    if args.validate_only:
        card=json.loads(CARD.read_text())
        for mode in ('nan','zeros'):
            rep=validate(ROOT/card[mode]['path'],grid,r0,mode)
            assert rep==card[mode]
        print('PASS: both written files re-read; hashes, parent diff and format match')
        return
    ledger=ROOT/'ledger/submissions.csv'
    with ledger.open(newline='') as f:
        reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    assert not any(r['axis'].upper()=='PRUNE' and r['value']==VALUE for r in rows), 'axis/value already built'
    arrays=[]
    canaries={}
    rng=np.random.default_rng(20261023)
    pos=np.flatnonzero(grid.catalogue)
    neg=rng.choice(np.flatnonzero(grid.foot&~grid.catalogue),size=100000,replace=False)
    for e in pins:
        if not e['id'].startswith('scored_'):continue
        with rasterio.open(DATA/e['dest']) as ds:
            assert ds.shape==grid.shape
            assert ds.transform==grid.template_profile['transform']
            assert ds.crs==grid.template_profile['crs']
            a=np.nan_to_num(ds.read(1),nan=0.)
        y=np.r_[np.ones(len(pos)),np.zeros(len(neg))]
        auc=float(roc_auc_score(y,np.r_[a.ravel()[pos],a.ravel()[neg]]))
        canaries[e['id']]={'auc':auc,'direction_free_auc':max(auc,1-auc)}
        assert max(auc,1-auc)<=.90, 'Leakage canary: investigate before emission'
        arrays.append(a>0)
    surrogate=np.logical_or.reduce(arrays)&grid.foot
    kept=r0&(grid.d_cat>3)
    pool=surrogate&grid.foot&(grid.d_cat>3)&~r0
    candidate,ranking=refill(kept,pool,surrogate,int(r0.sum()-kept.sum()))
    temp=ROOT/'.cache/prune-output';temp.mkdir(exist_ok=True)
    files={mode:emit_dots(candidate,grid,temp/f'{mode}.tif',mode=mode) for mode in ('nan','zeros')}
    hashes={mode:sha256_file(path) for mode,path in files.items()}
    prior={r.get(k,'') for r in rows for k in ('sha256','sha256_zeros','sha256_nan')}
    assert not (set(hashes.values())&prior),'exact hash already in ledger'
    name=f'{PARENT}-prune{VALUE}-20261023-{hashes["nan"][:8]}'
    reports={}
    for mode,path in files.items():
        dest=ROOT/'releases'/f'{name}{"-zeros" if mode=="zeros" else ""}.tif'
        assert not dest.exists()
        path.rename(dest)
        reports[mode]=validate(dest,grid,r0,mode)
    note=f'{PARENT}; PRUNE >3px, refill {reports["nan"]["removed"]}, count fixed; MODEL +0.002 (range -0.01 to +0.01)'
    assert len(note)<=140
    card={'id':name,'parent':PARENT,'axis':'PRUNE','value':VALUE,'status':'BUILT',
          'git_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
          'seed':20261023,'inputs':pins,'parent_rebuild':json.loads((ROOT/'.cache/prune_r0_preflight.json').read_text()),
          **reports,'dedupe':{'exact_hash_new':True,'axis_value_new':True},
          'prediction':{'evidence_class':'MODEL','central_change':.002,'plausible_range':[-.01,.01],
                        'note':'Judgment only, not a calibrated interval or live score. Below 0.01 is no evidence.'},
          'mechanism_card':{
              'hypothesis':'Replacing the near-catalogue collar with spaced ancestor-supported dots modestly improves coverage of unmapped fault segments.',
              'mechanism':'Remove only 2171 dots at catalogue distances (2,3] px, preserving all other R0 locations. Refill away from catalogue at the same count and >=2.8 px spacing from retained/new dots. This reallocates the narrow mapped-trace halo to existing ancestor ridge support, without adding a new physical signal.',
              'non_fault_mimic':'Ancestor ridge support may represent erosional channels, lithologic boundaries or alluvial fan margins rather than tectonic scarps.',
              'alternative':'The removed collar may contain unmapped parallel splays or newly mapped geometry of known systems; then widening the collar loses useful coverage.',
              'falsifier':'A receipt change <=-0.01 versus a receipted R0 rejects the predicted benefit on public chunks; abs(change)<0.01 is no evidence. Neither identifies private truth.',
              'confounder':'Refill support/ranking is necessary to hold count fixed; the result tests collar-plus-fixed-refill policy, not distance alone.'},
          'refill':{'surrogate':'MODEL binary support union of pinned H19-5, H19-4, H16-1 ancestors; not truth or calibrated probabilities',
                    'algorithm':'exact marginal DTI on surrogate using shared metric offsets; lazy greedy; row-major tie-break',
                    'spacing_px':2.8,'no_feature_fit':True,'ranking':ranking},
          'reports':{'leakage_canary':{'scope':'Full-catalogue association diagnostic, NOT a fold-clean holdout',
                     'positives':len(pos),'negatives':len(neg),'features':canaries},
                     'hide_and_recover':{'status':'NOT_RUN','n_withheld_positives':None,'ci95':None,
                     'reason':'Ancestor predictions have no verified fold-clean reconstruction; a masked-only evaluation would leak. Not a gate.'},
                     'SGMC':{'status':'NOT_RUN','reason':'Pinned SGMC input absent; not used or fetched; not a gate.'}},
          'form_note':note,'receipt_score':None,'date':None}
    CARD.write_text(json.dumps(card,indent=2)+'\n')
    row={k:'' for k in fields}
    row.update(id=name,site='GEMSDOE84',name=name,evidence_class='MODEL',encoding='nan+zeros',
               n_dots=reports['nan']['n_dots'],pct_changed=reports['nan']['pct_changed'],
               sha8=hashes['nan'][:8],sha256=hashes['nan'],sha256_zeros=hashes['zeros'],
               parent=PARENT,axis='PRUNE',value=VALUE,status='BUILT',receipt='N',
               predicted_change='+0.002; plausible -0.01 to +0.01 (MODEL)',form_note=note,
               notes='Replacement fraction = removed/R0; symmetric difference separately in evidence card. No live receipt.')
    with ledger.open('a',newline='') as f:csv.DictWriter(f,fieldnames=fields).writerow(row)
    print(json.dumps({k:card[k] for k in ('id','nan','zeros','prediction','form_note')},indent=2))


if __name__=='__main__':main()
