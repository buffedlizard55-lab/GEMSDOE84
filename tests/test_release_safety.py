"""Regression checks for blocked downloads and malformed raster inspection."""
import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from scripts.build_site import check_blocked_release
from scripts.validate_submission import audit


@pytest.mark.parametrize('suffix', ['.tif', '.TIF', '.tiff', '.zip'])
def test_blocked_release_rejects_unlinked_binaries(tmp_path, suffix):
    nested = tmp_path / 'old' / ('stale' + suffix)
    nested.parent.mkdir()
    nested.write_bytes(b'stale')
    with pytest.raises(ValueError, match='downloadable artifacts'):
        check_blocked_release({'verdict': 'negative', 'raster_sha256': 'a'*64}, tmp_path)


def test_negative_without_artifacts_is_allowed(tmp_path):
    check_blocked_release({'verdict': 'negative'}, tmp_path)


def test_renderer_cannot_authorize_promote(tmp_path):
    with pytest.raises(ValueError, match='selector'):
        check_blocked_release({'verdict': 'promote'}, tmp_path)


def write(path, shape, value=0):
    with rasterio.open(path, 'w', driver='GTiff', height=shape[0], width=shape[1],
                       count=1, dtype='float32', crs='EPSG:32611',
                       transform=from_origin(400000, 4600000, 100, 100)) as dst:
        dst.write(np.full(shape, value, dtype='float32'), 1)


def test_audit_wrong_shape_returns_failure_not_index_error(tmp_path):
    ref, candidate = tmp_path/'ref.tif', tmp_path/'candidate.tif'
    write(ref, (4, 4)); write(candidate, (2, 2))
    result = audit(candidate, ref)
    assert result['status'] == 'FAIL'
    assert not result['checks']['shape_match']
    assert result['submission_authorized'] is False
    json.dumps(result)


def test_infinity_cannot_pass_combined_finite_range_flag(tmp_path):
    ref, candidate = tmp_path/'ref.tif', tmp_path/'candidate.tif'
    write(ref, (4, 4)); write(candidate, (4, 4), float('inf'))
    result = audit(candidate, ref)
    assert result['status'] == 'FAIL'
    assert not result['checks']['all_finite_values_in_[0,1]']
