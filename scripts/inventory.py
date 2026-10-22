"""Inventory linked public repositories at pinned commits; cache is never committed."""
import concurrent.futures as cf
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data/registry'
CACHE.mkdir(parents=True, exist_ok=True)
NAMES = ['GEMSDOE'] + [f'{i}GEMSDOE' if i in {5,6,7,8,11,12,13,14,15,16,17,18,19,20,55,56,57,58,59,60,61,62} else f'GEMSDOE{i}' for i in range(2,89)]
# The prompt explicitly uses 60GEMSDOE etc only for some early sites; later 60..62 use numerical prefixes.

def api(path, raw=False):
    cmd = ['gh','api',path]
    if raw: cmd += ['-H','Accept: application/vnd.github.raw']
    return subprocess.check_output(cmd, stderr=subprocess.PIPE)

def tree(name):
    repo = f'buffedlizard55-lab/{name}'
    try:
        info = json.loads(api(f'repos/{repo}'))
        d = json.loads(api(f"repos/{repo}/git/trees/{info['default_branch']}?recursive=1"))
        if d.get('truncated'): raise ValueError('truncated tree')
        rows = [dict(repo=repo, commit=d['sha'], path=x['path'], blob=x['sha'], size=x['size']) for x in d['tree'] if x['type']=='blob' and x['path'].lower().endswith('.tif') and ('download' in x['path'] or x['path'].startswith('submissions/')) and 'quarantine' not in x['path'].lower()]
        return dict(repo=repo,commit=d['sha'],rasters=rows)
    except Exception as e:
        return dict(repo=repo,error=str(e))

def download(row):
    p = CACHE / (row['blob']+'.tif')
    try:
        if not p.exists(): p.write_bytes(api(f"repos/{row['repo']}/git/blobs/{row['blob']}",True))
        row.update(cache_file=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    except Exception as e: row['error']=str(e)
    return row

if __name__ == '__main__':
    with cf.ThreadPoolExecutor(max_workers=8) as pool: repos=list(pool.map(tree,NAMES))
    unique={}
    for r in repos:
        for x in r.get('rasters',[]): unique.setdefault(x['blob'],x)
    with cf.ThreadPoolExecutor(max_workers=6) as pool: rasters=list(pool.map(download,unique.values()))
    report=dict(scope='Linked public repositories, downloads/ and submissions/ TIFFs only; not private or organizer registry',repositories=repos,rasters=rasters,complete_accessible_scan=not any('error' in r for r in [*repos,*rasters]))
    (ROOT/'registry/inventory.json').write_text(json.dumps(report,indent=2)+'\n')
    print('repos',len(repos),'rasters',len(rasters),'errors',sum('error' in r for r in [*repos,*rasters]),flush=True)
