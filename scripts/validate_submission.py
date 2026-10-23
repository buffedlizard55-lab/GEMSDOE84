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


def validate(candidate, template, encoding='zeros'):
    """Re-read the exact template grid and check the selected exterior encoding.

    ``nan`` is Brief v2's primary file; ``zeros`` remains the conservative fallback
    and the backwards-compatible default. Neither result is organizer acceptance.
    """
    if encoding not in ('zeros', 'nan'):
        raise ValueError("encoding must be 'zeros' or 'nan'")
    checks = {}
    with rasterio.open(template) as ref, rasterio.open(candidate) as src:
        checks.update(
            geotiff=src.driver == 'GTiff',
            single_band=src.count == 1,
            crs=src.crs is not None and src.crs == ref.crs,
            shape=(src.height, src.width) == (ref.height, ref.width),
            transform=src.transform == ref.transform,
            real_dtype=np.dtype(src.dtypes[0]).kind in 'fiu',
            dtype_float32=src.dtypes[0] == 'float32',
        )
        if not all(checks.values()):
            return {'format_valid': False, 'checks': checks, 'sha256': sha256(candidate),
                    'encoding': encoding, 'submission_authorized': False}
        footprint_pixels = 0
        checks.update(finite_inside=True, range_inside=True, no_masked_footprint=True)
        if encoding == 'zeros':
            checks.update(finite_all=True, range_all=True, outside_zero=True)
        else:
            checks['outside_nan'] = True
        for _, window in ref.block_windows(1):
            # The pinned sample's footprint is its finite band-1 cells. The mask
            # additionally excludes explicit nodata for small synthetic templates.
            footprint = ((ref.dataset_mask(window=window) > 0)
                         & np.isfinite(ref.read(1, window=window)))
            footprint_pixels += int(footprint.sum())
            values = src.read(1, window=window)
            valid = src.read_masks(1, window=window) > 0
            inside, outside = values[footprint], values[~footprint]
            checks['finite_inside'] &= bool(np.isfinite(inside).all())
            checks['range_inside'] &= bool(((inside >= 0) & (inside <= 1)).all())
            checks['no_masked_footprint'] &= bool(valid[footprint].all())
            if encoding == 'zeros':
                checks['finite_all'] &= bool(np.isfinite(values).all())
                checks['range_all'] &= bool(((values >= 0) & (values <= 1)).all())
                checks['outside_zero'] &= bool((outside == 0).all())
            else:
                checks['outside_nan'] &= bool(np.isnan(outside).all())
        checks['nonempty_footprint'] = footprint_pixels > 0
    return {'format_valid': all(checks.values()), 'checks': checks,
            'encoding': encoding, 'footprint_pixels': footprint_pixels,
            'sha256': sha256(candidate), 'template_sha256': sha256(template),
            'submission_authorized': False,
            'scope': 'Format only; scientific and human slot decisions remain separate.'}


def audit(candidate, reference, footprint_path=None, footprint_band=1):
    """Compatibility API for the concurrently merged format-inspection tests.

    Uses the same strict implementation; alternate footprint sources are not
    silently accepted without an agreed authoritative footprint policy.
    """
    if footprint_path is not None or footprint_band != 1:
        raise ValueError('Use the authoritative template dataset mask')
    result = validate(candidate, reference)
    checks = result['checks']
    if not checks.get('shape', False) or not checks.get('real_dtype', False):
        return dict(result, status='FAIL', checks=dict(
            checks, crs_match=checks['crs'], shape_match=checks['shape'],
            transform_match=checks['transform']))
    with rasterio.open(candidate) as src:
        values = src.read(1)
        with rasterio.open(reference) as ref:
            footprint = ref.dataset_mask() > 0
        compatible = dict(checks)
        compatible.update(
            footprint_has_no_nan=bool(not np.isnan(values[footprint]).any()),
            all_finite_values_in_unit_interval=(checks.get('range_all', False) and checks.get('finite_all', False)),
            crs_match=checks['crs'], shape_match=checks['shape'],
            transform_match=checks['transform'],
            nan_inside_footprint=int(np.isnan(values[footprint]).sum()),
        )
        compatible['all_finite_values_in_[0,1]'] = (checks.get('range_all', False) and checks.get('finite_all', False))
        compatible['finite_values_outside_[0,1]_count'] = int(
            (np.isfinite(values) & ((values < 0) | (values > 1))).sum())
    return dict(result, status='PASS' if result['format_valid'] else 'FAIL',
                checks=compatible)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--template', '--reference', dest='template', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--encoding', choices=('zeros', 'nan'), default='zeros',
                        help='Exterior encoding: zeros fallback (default) or primary NaN file.')
    parser.add_argument('--json', action='store_true', help='JSON is always printed')
    args = parser.parse_args()
    try:
        result = validate(args.candidate, args.template, encoding=args.encoding)
    except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
        result = {'format_valid': False, 'submission_authorized': False, 'error': str(exc)}
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['format_valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
