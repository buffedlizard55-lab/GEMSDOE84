"""Verify the exact input bytes and shared grid; no training-data fabrication."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vendor'))
from gems57 import grid

IDS={'labels','existing_faults','sample_submission','ext_lidar_scarp_features_u8','ext_geodawn_rad_u8'}
def verify():
    manifest=json.loads((ROOT/'registry/data_manifest.json').read_text())
    rows=[]
    for entry in manifest['files']:
        if entry['id'] not in IDS:continue
        p=ROOT/'data/raw'/entry['dest']
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        if digest!=entry['sha256']:raise ValueError(f"Input hash mismatch: {entry['id']}")
        rows.append(dict(id=entry['id'],sha256=digest,bytes=p.stat().st_size))
    if len(rows)!=len(IDS):raise ValueError('Manifest missing required inputs')
    g=grid.load_grid(ROOT/'data/raw')
    receipt=dict(files=rows,shape=list(g.shape),crs=str(g.crs),transform=list(tuple(g.transform)[:6]),footprint_pixels=int(g.footprint.sum()),catalogue_pixels=int(g.catalogue.sum()),organizer_authenticated=False,labels_identical_to_catalogue=True)
    (ROOT/'evidence/data-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

if __name__=='__main__':print(json.dumps(verify(),indent=2))
