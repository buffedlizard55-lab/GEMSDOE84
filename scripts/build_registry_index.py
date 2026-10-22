#!/usr/bin/env python3
"""Build the hash-verified uniqueness registry from every owner-published raster.

Corpus: registry/uniqueness_corpus.txt -- one line per unique git blob
(repo blob_sha bytes path), assembled from
  * 57GEMSDOE evidence/registry_full_index.json (655 grid rasters, repos <= 57),
  * GitHub tree listings of GEMSDOE52..62, GEMSDOE63..83 (+ GEMSDOE, 2, 4, 5, 24)
    filtered to submission-like .tif paths (no data/feature/cache/registry copies).
Each blob is downloaded to $GEMS84_DATA/registry/<blob>.tif and accepted only if
the git blob SHA-1 of the bytes equals the listed blob id.  Grid rasters
(single band, 3730x3292, EPSG:32611, the pinned transform) enter the index; any
other file is listed under ``skipped_non_grid`` with the reason.

Output: registry/registry_index.json (template uniqueness.py format).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]
from gems57.grid import TRANSFORM  # noqa: E402
from gems84.paths import REGISTRY_DIR  # noqa: E402


def main():
    corpus = [l.rstrip("\n").split(" ", 3) for l in open(ROOT / "registry/uniqueness_corpus.txt")]
    rasters, skipped, errors = [], [], []
    by_sha = {}
    for repo, blob, size, path in corpus:
        f = REGISTRY_DIR / f"{blob}.tif"
        if not f.exists() or f.stat().st_size == 0:
            errors.append(dict(repo=repo, blob=blob, path=path, error="not downloaded"))
            continue
        b = f.read_bytes()
        if hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest() != blob:
            errors.append(dict(repo=repo, blob=blob, path=path, error="git blob sha mismatch"))
            continue
        try:
            with rasterio.open(f) as s:
                ok = (s.count == 1 and s.shape == (3730, 3292) and s.crs is not None
                      and s.crs.to_epsg() == 32611 and s.transform == TRANSFORM)
                why = f"count={s.count} shape={s.shape} crs={s.crs}"
        except Exception as e:  # not a raster rasterio can read
            ok, why = False, f"unreadable: {e}"[:200]
        if not ok:
            skipped.append(dict(repo=repo, blob=blob, path=path, reason=why))
            continue
        sha = hashlib.sha256(b).hexdigest()
        if sha in by_sha:
            by_sha[sha]["sources"].append(f"{repo}:{path}")
            continue
        rec = dict(sha256=sha, bytes=len(b), blob=blob, cache_file=str(f),
                   sources=[f"{repo}:{path}"], repo_first=repo)
        by_sha[sha] = rec
        rasters.append(rec)
    out = dict(owner="buffedlizard55-lab", corpus_entries=len(corpus),
               n_unique_grid_rasters=len(rasters), skipped_non_grid=skipped, errors=errors,
               complete_accessible_scan=not errors, rasters=rasters,
               scope="owner-published public GitHub rasters listed in registry/uniqueness_corpus.txt; "
                     "not an organizer registry")
    (ROOT / "registry/registry_index.json").write_text(json.dumps(out, indent=1))
    print(dict(corpus=len(corpus), grid=len(rasters), skipped=len(skipped), errors=len(errors)))


if __name__ == "__main__":
    main()
