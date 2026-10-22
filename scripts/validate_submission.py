"""Independent format inspection, NOT the missing shared writer or scientific evaluator.

Exit 0 means format-valid only. It never authorizes a competition slot.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def validate(candidate, template):
    checks = {}
    with rasterio.open(template) as ref, rasterio.open(candidate) as src:
        checks.update(
            geotiff=src.driver == 'GTiff',
            single_band=src.count == 1,
            crs=src.crs is not None and src.crs == ref.crs,
            shape=(src.height, src.width) == (ref.height, ref.width),
            transform=src.transform == ref.transform,
            real_dtype=np.dtype(src.dtypes[0]).kind in 'fiu',
        )
        if not all(checks.values()):
            return {'format_valid': False, 'checks': checks, 'sha256': sha256(candidate)}
        footprint_pixels = 0
        checks.update(finite_all=True, range_all=True, no_masked_footprint=True)
        for _, window in ref.block_windows(1):
            footprint = ref.dataset_mask(window=window) > 0
            footprint_pixels += int(footprint.sum())
            values = src.read(1, window=window)
            valid = src.read_masks(1, window=window) > 0
            # Stronger than minimum footprint rule: finite, bounded values everywhere.
            checks['finite_all'] &= bool(np.isfinite(values).all())
            checks['range_all'] &= bool(((values >= 0) & (values <= 1)).all())
            checks['no_masked_footprint'] &= bool(valid[footprint].all())
        checks['nonempty_footprint'] = footprint_pixels > 0
    return {'format_valid': all(checks.values()), 'checks': checks,
            'footprint_pixels': footprint_pixels, 'sha256': sha256(candidate),
            'template_sha256': sha256(template),
            'submission_authorized': False,
            'scope': 'Format only; scientific, registry and selector gates remain separate.'}


def audit(candidate, reference, footprint_path=None, footprint_band=1):
    """Compatibility API for the concurrently merged format-inspection tests.

    Uses the same strict implementation; alternate footprint sources are not
    silently accepted without an agreed authoritative footprint policy.
    """
    if footprint_path is not None or footprint_band != 1:
        raise ValueError('Use the authoritative template dataset mask')
    result = validate(candidate, reference)
    checks = result['checks']
    with rasterio.open(candidate) as src:
        values = src.read(1)
        with rasterio.open(reference) as ref:
            footprint = ref.dataset_mask() > 0
        compatible = dict(checks)
        compatible.update(
            footprint_has_no_nan=bool(not np.isnan(values[footprint]).any()),
            all_finite_values_in_unit_interval=checks.get('range_all', False),
            crs_match=checks['crs'], shape_match=checks['shape'],
            transform_match=checks['transform'],
            nan_inside_footprint=int(np.isnan(values[footprint]).sum()),
        )
        compatible['all_finite_values_in_[0,1]'] = checks.get('range_all', False)
        compatible['finite_values_outside_[0,1]_count'] = int(
            (np.isfinite(values) & ((values < 0) | (values > 1))).sum())
    return dict(result, status='PASS' if result['format_valid'] else 'FAIL',
                checks=compatible)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--template', '--reference', dest='template', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--json', action='store_true', help='JSON is always printed')
    args = parser.parse_args()
    try:
        result = validate(args.candidate, args.template)
    except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
        result = {'format_valid': False, 'error': str(exc)}
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['format_valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
