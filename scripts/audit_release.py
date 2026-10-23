#!/usr/bin/env python3
"""Read-only raster audit and literal duplicate-stop; never generates predictions.

A partial inventory can prove a failure, never a uniqueness pass. The shared
saturation certificate can stop BEFORE any placement, even without a surface.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor'))
from gems57 import grid, uniqueness, validate  # noqa: E402

WITNESS_SHA = 'ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be'
WITNESS_BLOB = '374c88b1da2b803e2ed160de467fd71ae114010d'
WITNESS_REPO = 'buffedlizard55-lab/17GEMSDOE'
ARTIFACT = 'gems84-h84-thms-dink300-37654dots-20261022-2f4190b4-zeros'


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def inspect(candidate: Path, reference: Path, catalogue: Path, witness: Path,
            witness_sha: str) -> dict:
    """Validate identities before the shared literal comparison. Fail on corruption."""
    if digest(witness) != witness_sha:
        raise ValueError('registry witness SHA-256 mismatch')
    with rasterio.open(reference) as ref:
        fp = np.isfinite(ref.read(1)) & (ref.dataset_mask() > 0)
        expected = (ref.shape, ref.crs, ref.transform)
    with rasterio.open(catalogue) as cat:
        if (cat.shape, cat.crs, cat.transform) != expected:
            raise ValueError('catalogue grid differs from reference')
        known = (cat.read(1) > 0) & fp
    certificate = uniqueness.saturation_certificate(
        witness, fp, known, expected_grid=expected)
    # Reuse the single shared, untruncated literal gate. This index is intentionally
    # incomplete: a witness suffices to refute uniqueness, not to establish it.
    with rasterio.open(candidate) as src:
        if (src.shape, src.crs, src.transform) != expected or src.count != 1:
            raise ValueError('candidate grid/band count differs from reference')
        prediction = src.read(1)
    index = {'rasters': [{'cache_file': str(witness.resolve()), 'sha256': witness_sha,
                         'repo_first': WITNESS_REPO,
                         'sources': ['17GEMSDOE E-proba-multiscale (literal witness)']}],
             'complete_accessible_scan': False, 'errors': []}
    comparison = uniqueness.compare_array_to_registry(
        prediction, index, fp, file_sha256=digest(candidate), expected_grid=expected)
    validation = validate.validate(candidate, fp, known)
    return {'certificate': certificate, 'registry_comparison': comparison,
            'validator_output': validation,
            'pre_placement_stop': bool(certificate['universal_overlap_blocker']),
            'final_duplicate': bool(comparison['duplicate_count']),
            'submission_authorized': False}


def assert_lane_open(root: Path = ROOT) -> None:
    """Prevent older generators from ignoring a recorded lane-wide stop."""
    path = root / 'registry' / 'release_status.json'
    if not path.is_file():
        raise RuntimeError('No current release audit; lane fails closed. Run scripts/audit_release.py.')
    status = json.loads(path.read_text())
    if status.get('stop_required', True):
        raise RuntimeError('H84 lane STOP: literal registry duplicate or incomplete evidence. '
                           'See registry/release_status.json; no new placement or submission.')
    # Deliberately no authorization API: a separate selector owns weekly slots.


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--witness', type=Path, default=ROOT / '.cache/audit/registry-witness.tif')
    args = parser.parse_args()
    for name, expected in [('sample_submission.tif', grid.SHA256_SAMPLE_SUBMISSION),
                           ('existing_faults.tif', grid.SHA256_EXISTING_FAULTS)]:
        if digest(ROOT / 'data/bridge' / name) != expected:
            raise ValueError(f'bridge hash mismatch: {name}')
    result = inspect(ROOT / 'submissions' / f'{ARTIFACT}.tif',
                     ROOT / 'data/bridge/sample_submission.tif',
                     ROOT / 'data/bridge/existing_faults.tif', args.witness, WITNESS_SHA)
    report = {
        'schema': 'gems84-release-audit-v1',
        'audited_utc': datetime.now(timezone.utc).isoformat(),
        'lane': 'H84-THMS (inherited; no new lane selected)',
        'hypothesis': 'Thermal/sinter evidence corroborates geomorphic fault-valve corridors.',
        'mechanism': 'Existing H84-THMS candidate; audit only, no new fit or prediction.',
        'named_nonfault_mimic': 'Lateral thermal outflow in an alluvial aquifer; pluvial shoreline benches.',
        'new_candidate': None, 'new_raster_sha256': None, 'new_submission_name': None,
        'note': 'NEGATIVE: literal registry overlap blocks H84; archived TIFF is format-valid research only. No slot authorized.',
        'verdict': 'negative', 'stop_required': True,
        'download_allowed_for_research': True, 'submission_authorized': False,
        'new_experiments_executed': 0, 'submission_slots_used_this_session': 0,
        'holdout_dti': None,
        'holdout_status': 'Not rerun. Archived A5 uses full-catalogue registry halos during hide-and-recover; not certified leakage-free.',
        'organizer_confirmed_score': None,
        'witness_provenance': {
            'repository': WITNESS_REPO, 'git_blob': WITNESS_BLOB, 'sha256': WITNESS_SHA,
            'url': f'https://api.github.com/repos/{WITNESS_REPO}/git/blobs/{WITNESS_BLOB}',
            'trust': 'Team registry artifact, not an official scientific source.'},
        'audited_artifact': {'name': ARTIFACT, 'path': f'submissions/{ARTIFACT}.tif',
                            'sha256': digest(ROOT / 'submissions' / f'{ARTIFACT}.tif'),
                            'newly_generated': False},
        **result,
        'limitations': ['A single pinned witness refutes uniqueness; no complete registry refresh was performed.',
                        'Surface is absent locally; its correlation is not invented. Universal saturation proves a pre-placement impossibility.',
                        'No organizer submission receipt, current leaderboard or weekly cap was retrieved.',
                        'Cached training/external feature stacks are absent from this checkout.'],
    }
    for name in ['registry/release_status.json', 'evidence/release-audit-20261023.json',
                 'docs/evidence/release-audit-20261023.json']:
        path = ROOT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'verdict': report['verdict'], 'stop_required': True,
                      'universal_blocker': result['certificate']['universal_overlap_blocker'],
                      'overlap': result['registry_comparison']['worst_dot_overlap'],
                      'format_valid': result['validator_output']['all_checks_passed']}, indent=2))
    return 2  # expected scientific negative, not success disguised as readiness


if __name__ == '__main__':
    raise SystemExit(main())
