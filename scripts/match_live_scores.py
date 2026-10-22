#!/usr/bin/env python3
"""Link each owner-reported live score (registry/live_scores.csv) to raster blobs.

Matching rule (deterministic, auditable): a raster matches a score row when the
normalised submission name (suffixes -nan/-zeros/-zero/-allfinite/-candidate
stripped) is a substring of the normalised raster filename, preferring the same
site repo.  The resulting candidate set is later reduced to rows whose matched
rasters all decode to the SAME in-footprint prediction (otherwise dropped).
Input corpus: registry/uniqueness_corpus.txt  (repo blob_sha bytes path).
Output: registry/live_score_matches.json
"""
import csv, json, os, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def norm(s):
    s = os.path.basename(s).lower()
    s = re.sub(r'\.(tif|tiff|zip)$', '', s)
    for _ in range(2):
        s = re.sub(r'[-_](nan|zeros|zero|allfinite|nan-outside|nanoutside|hard|candidate|outside)$', '', s)
    return s

rows = list(csv.DictReader(open(ROOT / 'registry/live_scores.csv')))
corpus = [l.rstrip('\n').split(' ', 3) for l in open(ROOT / 'registry/uniqueness_corpus.txt')]
# also every alias path for the same blob (old index lists multiple sources)
idx = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else None
aliases = [(c[0], c[1], c[3]) for c in corpus]
if idx:
    for r in idx['rasters']:
        for s in r['sources']:
            repo, path = s.split(':', 1); aliases.append((repo, r['blob'], path))
out, miss = [], []
for r in rows:
    if not r['public_score']:
        continue
    key = norm(r['submission_name'])
    same = [a for a in aliases if a[0].lower() == r['site_repo'].lower() and key in norm(a[2])]
    m = same or [a for a in aliases if key in norm(a[2])]
    if m:
        out.append(dict(site=r['site_repo'], name=r['submission_name'], score=float(r['public_score']),
                        evidence_class='OWNER-REPORTED (user prompt / GEMSDOE80 registry/live_scores.csv)',
                        matches=sorted({(a[0], a[1], a[2]) for a in m})))
    else:
        miss.append([r['site_repo'], r['submission_name'], r['public_score']])
json.dump(dict(matched=out, unmatched=miss), open(ROOT / 'registry/live_score_matches.json', 'w'), indent=1)
print('matched', len(out), 'unmatched', len(miss))
for x in miss: print('UNMATCHED', x)
