"""Fixed H84-RFD exploratory experiment; strict duplicate stop, no slot use."""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vendor'))
from gems57 import grid, holdout, evaluate_holdout as EH, submission_writer as SW


def save(name,obj):
    (ROOT/'evidence'/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')


def unit(a,valid):
    if not np.any(valid):
        raise ValueError('No valid feature pixels')
    scale=float(np.quantile(a[valid],.99))
    return np.where(valid,np.clip(a/max(scale,1e-8),0,1),0).astype('float32')


def build(g):
    with rasterio.open(ROOT/'data/raw/external/lidar_scarp_features_u8.tif') as s:
        grid._check(s,'cached lidar'); l=s.read().astype('float32')/255
    with rasterio.open(ROOT/'data/raw/external/geodawn_rad_u8.tif') as s:
        grid._check(s,'cached radiometrics'); r=s.read().astype('float32')/255
    valid=g.footprint & (l[11]>0) & (r[0]>0) & (r[1]>0)
    # Fill missing cells only to avoid filtering nodata as artificial edges.
    near=ndi.distance_transform_edt(~valid,return_distances=False,return_indices=True)
    ck=ndi.gaussian_laplace(r[0][tuple(near)],3).astype('float32')
    ct=ndi.gaussian_laplace(r[1][tuple(near)],3).astype('float32')
    safe=ndi.binary_erosion(valid,iterations=12)
    dip=unit(np.sqrt(np.maximum(-ck*ct,0)),safe)
    step=unit(l[2]/np.maximum(l[8],1/255),safe)
    coh=unit(l[9],safe)
    baseline=np.sqrt(step*coh).astype('float32')
    candidate=np.sqrt(dip*baseline).astype('float32')
    features=dict(step=step,relief=unit(l[8],safe),coherence=coh,k_curvature=unit(np.abs(ck),safe),th_curvature=unit(np.abs(ct),safe),dipole=dip)
    return features,baseline,candidate


def dots(surface,allowed,budget,sep=3):
    if budget<=0 or sep<=0:
        raise ValueError('Positive budget and separation required')
    allowed=np.asarray(allowed,bool)
    ids=np.flatnonzero(allowed & (surface>0))
    ids=ids[np.argsort(-surface.ravel()[ids],kind='stable')]
    blocked=~allowed.copy(); out=np.zeros(surface.shape,'float32')
    h,w=out.shape; n=0
    offsets=[(y,x) for y in range(-sep,sep+1) for x in range(-sep,sep+1) if y*y+x*x<sep*sep]
    for idx in ids:
        y,x=divmod(int(idx),w)
        if blocked[y,x]: continue
        out[y,x]=1; n+=1
        for dy,dx in offsets:
            yy,xx=y+dy,x+dx
            if 0<=yy<h and 0<=xx<w: blocked[yy,xx]=True
        if n>=budget: break
    return out


def rank_vector(a):
    a=rankdata(a).astype('float64'); a-=a.mean()
    norm=np.linalg.norm(a)
    return a/norm if norm else None


def registry_array(record,g):
    from rasterio.warp import reproject, Resampling
    with rasterio.open(ROOT/record['cache_file']) as s:
        a=s.read(1)
        aligned=(s.shape==g.shape and s.crs==g.crs and s.transform==g.transform)
        if not aligned:
            out=np.zeros(g.shape,'float32')
            reproject(a,out,src_transform=s.transform,src_crs=s.crs,dst_transform=g.transform,dst_crs=g.crs,src_nodata=s.nodata,dst_nodata=0,resampling=Resampling.nearest)
            a=out
    return a, aligned


def surface_audit(surface,g,inventory):
    digest=hashlib.sha256(surface.tobytes()).hexdigest()
    checkpoint=ROOT/'data/surface-checkpoint.json'
    old=json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
    cached={r['sha256']:r for r in old.get('rows',[])} if old.get('candidate_sha256')==digest else {}
    mine=rank_vector(surface[g.footprint]); rows=[]
    for i,r in enumerate(inventory['rasters']):
        if 'error' in r: raise RuntimeError('registry contains inaccessible raster')
        if r['sha256'] in cached:
            row=cached[r['sha256']];rho=row['rho']
        else:
            try:
                a,aligned=registry_array(r,g)
                a=np.nan_to_num(a[g.footprint],nan=0,posinf=0,neginf=0)
                theirs=rank_vector(a)
                rho=float(np.dot(mine,theirs)) if mine is not None and theirs is not None else None
                row=dict(repo=r['repo'],path=r['path'],sha256=r['sha256'],rho=rho,native_grid_matches=aligned,comparison_resampling=None if aligned else 'nearest to template grid; invalid original submission grid flagged')
            except (rasterio.errors.RasterioIOError, ValueError) as exc:
                rho=None
                row=dict(repo=r['repo'],path=r['path'],sha256=r['sha256'],rho=None,error=str(exc),clearance_blocked=True)
        rows.append(row)
        if (i+1)%10==0:
            checkpoint.write_text(json.dumps(dict(candidate_sha256=digest,rows=rows)))
        if (i+1)%50==0: print('surface registry',i+1,flush=True)
        if rho is not None and rho>.90:
            save('surface-audit.json',dict(rows=rows,duplicate=True,stopped_at_first_duplicate=True)); return False
    save('surface-audit.json',dict(rows=rows,duplicate=False,scope=inventory['scope'],complete_comparable_scan=not any('error' in r for r in rows),undefined_or_unreadable_correlations=sum(r['rho'] is None for r in rows)))
    return True


def final_audit(p,g,inventory):
    my=p>0; n=int(my.sum()); rows=[]
    # Most broadly covering rasters first: a strict literal duplicate veto must not be relaxed for lattices.
    records=sorted(inventory['rasters'],key=lambda r: r['size'],reverse=True)
    mine=rank_vector(p[g.footprint])
    for i,r in enumerate(records):
        try:
            a,aligned=registry_array(r,g)
        except (rasterio.errors.RasterioIOError, ValueError) as exc:
            rows.append(dict(repo=r['repo'],path=r['path'],sha256=r['sha256'],error=str(exc),clearance_blocked=True))
            continue
        other=np.isfinite(a)&(a>0)&g.footprint
        near=ndi.distance_transform_edt(~other)<=3 if other.any() else np.zeros_like(my)
        overlap=float((my&near).sum()/n) if n else 0
        v=rank_vector(np.where(other,a,0)[g.footprint])
        rho=float(np.dot(mine,v)) if mine is not None and v is not None else None
        rows.append(dict(repo=r['repo'],path=r['path'],sha256=r['sha256'],overlap=overlap,rho=rho))
        if overlap>.70 or (rho is not None and rho>.90):
            save('dots-audit.json',dict(rows=rows,duplicate=True,stopped_at_first_duplicate=True,thresholds=dict(rho=.90,overlap=.70),no_representation_exemptions=True))
            return False
    complete=not any('error' in r for r in rows)
    save('dots-audit.json',dict(rows=rows,duplicate=False,complete_comparable_scan=complete,scope=inventory['scope']))
    return complete


def main():
    from audit_release import assert_lane_open
    assert_lane_open()
    from prepare_data import verify
    verify()
    g=grid.load_grid(ROOT/'data/raw')
    inv=json.loads((ROOT/'registry/inventory.json').read_text())
    card=dict(hypothesis='H84-RFD',mechanism='Opposite K/Th Gaussian curvature flanks coincident with coherent relief-normalized LiDAR step',non_fault_mimic='Lithologic contact and transported sediment',holdout_dti=None,registry_correlation_overlap=None,raster_sha256=None,validator_output={'status':'not generated'},submission_name='gems84-rfd-s3-fixed-20261022',note='Radiometric flanking dipole x coherent normalized scarp; fixed sigma3; research only.',verdict='negative',submission_slots_used=0,promotion_blockers=['Whole geological segment plus buffer holdout not available in inherited template','No organizer-authenticated data or receipt','No comparable reproduced current holdout best'])
    feats,base,surface=build(g)
    ctx=holdout.build_holdout(g,seeds=(20,),modes=('all',))
    canaries=[]
    rng=np.random.default_rng(84)
    for cell in ctx.cells:
        truth=ctx.hidden_by_cell[cell.key][cell.bbox]
        active=cell.active
        pos=np.flatnonzero(truth&active); neg=np.flatnonzero(active&~truth)
        neg=rng.choice(neg,min(len(neg),100000),replace=False)
        ids=np.r_[pos,neg]; y=np.r_[np.ones(len(pos)),np.zeros(len(neg))]
        for name,a in feats.items():
            auc=float(roc_auc_score(y,a[cell.bbox].ravel()[ids]))
            canaries.append(dict(fold=cell.key,feature=name,auc=auc,withheld_positives=len(pos),evidence_class='HOLDOUT-DIAGNOSTIC-AUC',passed=auc<=.90))
    save('canaries.json',dict(rows=canaries,passed=all(r['passed'] for r in canaries),caveat='AUC is a diagnostic, not DTI or organizer score.'))
    if not all(r['passed'] for r in canaries):
        card['promotion_blockers'].append('Leakage canary failed'); save('run-card.json',card);return
    print('canaries pass',flush=True)
    if not surface_audit(surface,g,inv):
        card['promotion_blockers'].append('Surface duplicate: stopped');save('run-card.json',card);return
    terms={n:[] for n in ['rfd','step_control']}
    for cell in ctx.cells:
        sl=cell.bbox
        hidden=ctx.hidden_by_cell[cell.key]
        visible=(g.catalogue&~hidden)[sl]
        fold=dict(region=cell.active,visible=visible,truth=hidden[sl])
        budget=max(1,round(37654*cell.active.sum()/g.footprint.sum()))
        for name,a in [('rfd',surface),('step_control',base)]:
            p=dots(a[sl],cell.active,budget)
            result,t=EH.evaluate(p,fold,g.footprint[sl],origin=(sl[0].start,sl[1].start),global_shape=g.shape)
            terms[name].append(t)
            print(cell.key,name,result['dti'],flush=True)
    summary=EH.pooled_summary({n:np.sum(ts,axis=0) for n,ts in terms.items()},candidate='rfd',draws=1000,seed=84)
    save('holdout.json',summary); card['holdout_dti']=summary
    if summary['paired_differences']['step_control']['delta']<=0:
        card['promotion_blockers'].append('Candidate did not beat paired step-only control on this exploratory holdout')
    surface_report=json.loads((ROOT/'evidence/surface-audit.json').read_text())
    if any('error' in row for row in surface_report['rows']):
        card['promotion_blockers'].append('Unreadable registry raster prevents full comparable-registry clearance')
    card['surface_audit_summary']=dict(indexed=len(surface_report['rows']),receipt='evidence/surface-audit.json',max_full_footprint_rho=max((row['rho'] for row in surface_report['rows'] if row['rho'] is not None),default=None))
    p=dots(surface,g.footprint&~g.catalogue,37654)
    # This hash identifies a decoded, non-submission array even if packaging is vetoed.
    card['decoded_array_sha256']=hashlib.sha256(p.tobytes()).hexdigest()
    if not final_audit(p,g,inv):
        audit=json.loads((ROOT/'evidence/dots-audit.json').read_text())
        card['promotion_blockers'].append('Final dots duplicate by literal protocol: stopped before TIFF packaging' if audit['duplicate'] else 'Incomplete registry comparison: stopped before TIFF packaging')
        card['registry_correlation_overlap']=audit
        save('run-card.json',card);return
    out=ROOT/'docs/downloads'/f"{card['submission_name']}.tif"
    out.parent.mkdir(parents=True,exist_ok=True)
    receipt=SW.write_submission(out,p,ROOT/'data/raw/sample_submission.tif',g.footprint,note=card['note'],name=card['submission_name'],catalogue=g.catalogue,metadata={'release':'research-only; negative; not approved for competition submission'})
    card['raster_sha256']=hashlib.sha256(out.read_bytes()).hexdigest()
    card['validator_output']=receipt
    card['registry_correlation_overlap']=dict(surface='evidence/surface-audit.json',dots='evidence/dots-audit.json')
    save('run-card.json',card)

if __name__=='__main__': main()
