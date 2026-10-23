#!/usr/bin/env python3
"""Read-only scientific/format re-validation of the one PRUNE1.5 pair. Never rebuilds.

Original R0 and data must be restored from the existing pins. Local validation
never authorizes a slot or asserts an organizer score. Density/model diagnostics
are informational only; no correlation/overlap thresholds are applied.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import json
from pathlib import Path
import sys

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'vendor')]
from gems84.brief_v2 import (  # noqa: E402
    canonical_parent, catalogue_clearance, experiment_key, ledger_hashes,
    read_experiment_history, verify_pinned_files,
)
from gems84.parent import (  # noqa: E402
    BASE_REL, R0_ZEROS_REL, R0_ZEROS_SHA256, load_grid, read_binary, sha256_file,
)
from gems84.snap import density_cv  # noqa: E402
from scripts.restore_pinned_inputs import EXTRA_PINS  # noqa: E402
from scripts.validate_submission import validate  # noqa: E402


def inspect(data_dir):
    build = json.loads((ROOT / 'evidence/prune_1p5_796cb891.json').read_text())
    manifest = json.loads((ROOT / 'registry/data_manifest.json').read_text())
    verified = verify_pinned_files(data_dir, list(manifest['files']) + list(EXTRA_PINS))
    g = load_grid(data_dir)
    parent_path = data_dir / R0_ZEROS_REL
    if sha256_file(parent_path) != R0_ZEROS_SHA256:
        raise ValueError('R0 pin drift: stop, never approximate')
    parent, base = read_binary(parent_path), read_binary(data_dir / BASE_REL)
    history = read_experiment_history(ROOT / 'ledger/submissions.csv')
    own = [row for row in history if row['id'] == build['id']]
    others = [row for row in history if row['id'] != build['id']]
    formats, masks = {}, {}
    for encoding, file in build['files'].items():
        path = ROOT / file['path']
        formats[encoding] = validate(path, data_dir / 'sample_submission.tif', encoding)
        with rasterio.open(path) as ds:
            arr = ds.read(1)
        masks[encoding] = np.isfinite(arr) & (arr > 0)
        formats[encoding]['unit_mass_only'] = bool(np.isin(arr[g.foot], [0.0, 1.0]).all())
        formats[encoding]['catalogue_mass'] = float(arr[g.catalogue].sum())
    mask = masks['zeros']
    added, removed = mask & ~parent, parent & ~mask
    n_added, n_removed = int(added.sum()), int(removed.sum())
    key = experiment_key(build['parent'], build['axis'], build['value'])
    other_keys = {experiment_key(row['parent'], row['axis'], row['value']) for row in others
                  if row.get('parent') and row.get('axis') and row.get('value')}
    hashes = ledger_hashes(others)
    checks = {
        'parent_pin_and_count': int(parent.sum()) == 37654,
        'both_format_encodings': all(f['format_valid'] for f in formats.values()),
        'exact_file_hashes_match_build': all(formats[e]['sha256'] == f['sha256']
                                             for e, f in build['files'].items()),
        'unit_mass_only': all(f['unit_mass_only'] for f in formats.values()),
        'zero_catalogue_mass': all(f['catalogue_mass'] == 0.0 for f in formats.values()),
        'encoding_masks_identical': np.array_equal(masks['nan'], masks['zeros']),
        'count_fixed': int(mask.sum()) == 37654,
        'inside_footprint': not np.any(mask & ~g.foot),
        'prune_rule_gt_1p5': bool((g.d_cat[mask] > 1.5).all()),
        'explicit_prune_exception': catalogue_clearance(mask, g.catalogue, g.d_cat, 'PRUNE')['passed'],
        'original_preprune_pool_only': not np.any(mask & ~base),
        'new_ring_is_exactly_200m': np.array_equal(added, base & ~parent & (g.d_cat > 1.5) & (g.d_cat <= 2.0)),
        'exact_parent_difference': n_added == n_removed == 1344,
        'difference_within_1_to_50_percent': .01 <= (n_added + n_removed) / int(parent.sum()) <= .50,
        'one_owning_ledger_row': len(own) == 1,
        'own_ledger_identifiers_match': len(own) == 1 and experiment_key(
            own[0]['parent'], own[0]['axis'], own[0]['value']) == key,
        'own_ledger_hashes_match': len(own) == 1 and own[0]['sha256'] == build['files']['nan']['sha256']
            and own[0]['sha256_zeros'] == build['files']['zeros']['sha256'],
        'no_other_experiment_pair': key not in other_keys,
        'no_other_exact_file_hash': all(f['sha256'] not in hashes for f in build['files'].values()),
        'canonical_parent_R0': canonical_parent(build['parent']) == 'h33-h33-2-b2',
    }
    return {
        'schema_version': 1, 'generated_utc': datetime.now(timezone.utc).isoformat(),
        'id': build['id'], 'source_build_commit': build['git_sha'],
        'measurement_kind': 'Local re-validation, not a submission-page score receipt',
        'verified_inputs_count': len(verified), 'checks': checks,
        'all_checks_passed': bool(all(checks.values())), 'formats': formats,
        'n_dots': int(mask.sum()), 'dots_added': n_added, 'dots_removed': n_removed,
        'pct_changed_exact_fraction': str(Fraction(100 * (n_added + n_removed), int(parent.sum()))) + '%',
        'pct_changed': 100.0 * (n_added + n_removed) / int(parent.sum()),
        'report_only': {
            'block_density_cv_5km_parent': density_cv(parent, g.foot, 50),
            'block_density_cv_5km_candidate': density_cv(mask, g.foot, 50),
            'cv_method': 'Existing density_cv; full 50x50-pixel blocks; partial boundary blocks omitted. Not comparable to unverified CV reports with unknown block size.',
            'selection_tie_caveat': 'All selected MODEL deletion credits tie; preregistered row-major compensation is not a geological confidence ranking. Distribution statistics are not gates.',
        },
        'no_similarity_thresholds_applied': True, 'new_variants_built': 0,
        'submission_authorized': False, 'submission_slots_used': 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT / '.cache/gems_data')
    parser.add_argument('--output', type=Path, default=ROOT / '.cache/prune-1p5-validation.json')
    args = parser.parse_args()
    destination = args.output.resolve()
    if not any(destination.is_relative_to(directory.resolve())
               for directory in (ROOT / '.cache', ROOT / 'evidence')):
        parser.error('Validation output must stay in .cache/ or evidence/, never over a ledger/raster')
    if destination == (ROOT / 'evidence/prune_1p5_796cb891.json').resolve():
        parser.error('Do not overwrite the immutable build evidence with a new validation')
    result = inspect(args.data_dir.resolve())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['all_checks_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
