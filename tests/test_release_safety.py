"""Regression checks for blocked downloads and malformed raster inspection."""
import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from scripts.build_site import check_blocked_release, validator_hero_html
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


def test_current_h84_release_is_fail_closed_despite_historical_promote_card():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    status = json.loads((root / 'registry/current_release_status.json').read_text())
    historical = json.loads((root / 'run_card.json').read_text())
    public_card = json.loads((root / 'docs/run-card.json').read_text())
    fresh_card = json.loads((root / 'evidence/fresh_run_card_20261023.json').read_text())
    rendered = validator_hero_html(historical, 'downloads/', 'evidence/')

    assert status['verdict'] == 'negative'
    assert status['submission_authorized'] is False
    assert status['candidate_specific_uniqueness']['rasters_checked'] == 359
    assert status['candidate_specific_uniqueness']['full_registry_raster_count'] == 1143
    assert status['candidate_specific_uniqueness']['decision'] == 'not cleared'
    assert status['candidate_specific_uniqueness']['full_registry_candidate_specific_scan'] == 'not available in this checkout'
    for card in (historical, public_card, fresh_card):
        assert str(card['verdict']).startswith('negative')
        assert card['submission_authorized'] is False
    assert 'NOT AUTHORIZED TO SUBMIT' in rendered
    assert 'DO NOT SUBMIT' in rendered
    assert 'NOT FOR SUBMISSION' in rendered
    assert 'OK TO DOWNLOAD &amp; SUBMIT' not in rendered
    assert 'PROMOTE' not in rendered


def test_release_status_scopes_other_lane_registry_scan():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    status = json.loads((root / 'registry/current_release_status.json').read_text())
    assert 'separate LITI candidate' in status['separate_lane_scan_note']
    assert status['organizer_receipt'] is None
    assert status['weekly_submission_slot_status'] == 'unverified'
