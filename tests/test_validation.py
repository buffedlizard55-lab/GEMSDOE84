import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from validate_submission import validate


def write(path, values, **kwargs):
    profile = dict(driver='GTiff', width=4, height=4, count=1,
                   dtype='float32', crs='EPSG:32611',
                   transform=from_origin(400000, 4600000, 100, 100))
    profile.update(kwargs)
    with rasterio.open(path, 'w', **profile) as dst:
        dst.write(np.full((4, 4), values, dtype='float32'), 1)


def test_valid_is_not_authorization(tmp_path):
    a, b = tmp_path/'a.tif', tmp_path/'b.tif'
    write(a, 0); write(b, .5)
    result = validate(b, a)
    assert result['format_valid']
    assert not result['submission_authorized']
    assert len(result['sha256']) == 64


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -.01, 1.01])
def test_reject_invalid_values(tmp_path, value):
    a, b = tmp_path/'a.tif', tmp_path/'b.tif'
    write(a, 0); write(b, value)
    assert not validate(b, a)['format_valid']


@pytest.mark.parametrize('kwargs', [dict(crs='EPSG:4326'), dict(count=2),
    dict(transform=from_origin(400001, 4600000, 100, 100)), dict(width=5)])
def test_reject_geometry(tmp_path, kwargs):
    a, b = tmp_path/'a.tif', tmp_path/'b.tif'
    write(a, 0)
    profile = dict(driver='GTiff', width=4, height=4, count=1,
                   dtype='float32', crs='EPSG:32611',
                   transform=from_origin(400000, 4600000, 100, 100))
    profile.update(kwargs)
    with rasterio.open(b, 'w', **profile) as dst:
        dst.write(np.zeros((profile['count'], profile['height'], profile['width']), dtype='float32'))
    assert not validate(b, a)['format_valid']


def test_nodata_in_footprint(tmp_path):
    a, b = tmp_path/'a.tif', tmp_path/'b.tif'
    write(a, .5); write(b, 0, nodata=0)
    assert not validate(b, a)['format_valid']
