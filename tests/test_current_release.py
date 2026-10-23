"""Regression tests for evidence-bound release status, not claims of model quality."""
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from scripts.audit_release import assert_lane_open, digest, inspect
from scripts.build_site import checked_status
from gems57 import uniqueness as U

ROOT = Path(__file__).resolve().parents[1]


def write(path, values, transform=None, crs='EPSG:32611'):
    a = np.asarray(values, dtype='float32')
    with rasterio.open(path, 'w', driver='GTiff', height=a.shape[0], width=a.shape[1],
                       count=1, dtype='float32', crs=crs,
                       transform=transform or from_origin(400000, 4600000, 100, 100)) as dst:
        dst.write(a, 1)


@pytest.fixture
def files(tmp_path):
    ref, cat, candidate, prior = [tmp_path / f'{n}.tif' for n in ('ref', 'cat', 'candidate', 'prior')]
    write(ref, np.zeros((9, 9))); write(cat, np.zeros((9, 9)))
    a = np.zeros((9, 9)); a[4, 4] = 1
    write(candidate, a); write(prior, np.ones((9, 9)))
    return candidate, ref, cat, prior


def test_dense_witness_is_binding_not_exempt(files):
    candidate, ref, cat, prior = files
    report = inspect(candidate, ref, cat, prior, digest(prior))
    assert report['certificate']['universal_overlap_blocker']
    assert report['pre_placement_stop'] and report['final_duplicate']
    assert report['registry_comparison']['worst_dot_overlap'] == 1.0
    assert report['registry_comparison']['worst_spearman_full_footprint'] is None
    assert report['registry_comparison']['complete_accessible_scan'] is False
    assert report['submission_authorized'] is False
    json.dumps(report, allow_nan=False)


def test_witness_integrity_is_not_assumed(files):
    candidate, ref, cat, prior = files
    with pytest.raises(ValueError, match='SHA-256 mismatch'):
        inspect(candidate, ref, cat, prior, '0' * 64)


@pytest.mark.parametrize('which', ['prior', 'candidate', 'catalogue'])
def test_equal_shape_different_grid_cannot_pass(files, which):
    candidate, ref, cat, prior = files
    path = {'prior': prior, 'candidate': candidate, 'catalogue': cat}[which]
    write(path, np.ones((9, 9)), transform=from_origin(401000, 4600000, 100, 100))
    with pytest.raises(ValueError, match='grid|CRS/transform'):
        inspect(candidate, ref, cat, prior, digest(prior))


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -0.1, 1.1])
def test_bad_candidate_is_not_repaired(files, value):
    candidate, ref, cat, prior = files
    a = np.zeros((9, 9)); a[4, 4] = value; write(candidate, a)
    before = digest(candidate)
    with pytest.raises(ValueError, match='finite'):
        inspect(candidate, ref, cat, prior, digest(prior))
    assert digest(candidate) == before


def test_exact_euclidean_overlap_boundary():
    prior = np.zeros((11, 11)); prior[5, 5] = 1
    a = np.zeros_like(prior); a[5, 8] = 1
    assert U.dot_overlap(a, prior) == 1
    a[:] = 0; a[6, 8] = 1
    assert U.dot_overlap(a, prior) == 0  # sqrt(10) > 3


def test_no_current_audit_cannot_enable_old_generators(tmp_path):
    with pytest.raises(RuntimeError, match='fails closed'):
        assert_lane_open(tmp_path)
    (tmp_path / 'registry').mkdir()
    (tmp_path / 'registry/release_status.json').write_text('{"stop_required":true}')
    with pytest.raises(RuntimeError, match='STOP'):
        assert_lane_open(tmp_path)


def test_current_projection_is_negative_consistent_and_not_new():
    status = checked_status(ROOT)
    assert status['pre_placement_stop'] and status['final_duplicate']
    assert status['holdout_dti'] is None
    assert status['new_experiments_executed'] == 0
    assert status['new_raster_sha256'] is None
    assert status['organizer_confirmed_score'] is None
    assert status['validator_output']['all_checks_passed']
    assert status['validator_output']['n_nan'] == 0
    assert status['audited_artifact']['sha256'] == status['validator_output']['sha256']
    for rel in ['run_card.json', 'evidence/run-card.json', 'evidence/run_card.json',
                'registry/run_card.json', 'docs/run-card.json', 'docs/data/run-card.json',
                'docs/evidence/run_card.json']:
        c = json.loads((ROOT / rel).read_text())
        assert c['verdict'] == 'negative' and c['submission_authorized'] is False
        assert c['submission_name'] is None and c['raster_sha256'] is None
        assert c['audited_artifact'] == status['audited_artifact']
        assert len(c['submission_note']) <= 140


def test_renderer_cannot_grant_authorization(tmp_path):
    (tmp_path / 'registry').mkdir()
    (tmp_path / 'registry/release_status.json').write_text(
        '{"verdict":"promote","submission_authorized":true}')
    with pytest.raises(ValueError, match='selector'):
        checked_status(tmp_path)


@pytest.mark.parametrize('script', ['evaluate_holdout.py', 'submission_writer.py'])
def test_real_shared_command_entrypoints(script):
    result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script)],
                            cwd=ROOT, text=True, capture_output=True, check=True)
    data = json.loads(result.stdout)
    if script == 'evaluate_holdout.py':
        assert data['status'] == 'ARCHIVED_REPORT_ONLY_NOT_RECOMPUTED'
        assert data['scientific_clearance'] is False
    else:
        assert data['all_checks_passed']
        assert 'not organizer acceptance' in data['validation_class']


def test_guard_stops_production_before_loading_features():
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/run_h84_thms_pipeline.py')],
                            cwd=ROOT, text=True, capture_output=True)
    assert result.returncode != 0
    assert 'H84 lane STOP' in result.stderr
    assert 'No such file' not in result.stderr  # stop, not accidental missing-data crash


def test_holdout_emission_has_no_registry_halo_input():
    tree = ast.parse((ROOT / 'scripts/run_h84_thms_pipeline.py').read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run_exp2_dualseed_holdout')
    calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == 'emit_dinkelbach_submodular']
    assert len(calls) == 2
    for call in calls:
        kwargs = {k.arg: k.value for k in call.keywords}
        assert isinstance(kwargs['packed_halos_fp'], ast.Constant)
        assert kwargs['packed_halos_fp'].value is None
        assert kwargs['fp_lut'].value is None
        assert kwargs['n_halos'].value == 0
    # Old scores must not be reused as evidence for this changed emission policy.
    assert 'none-fold-only-v1' in ast.unparse(fn)
    archived = json.loads((ROOT / 'evidence/h84_exp2_dualseed_holdout.json').read_text())
    assert archived.get('holdout_registry_policy') != 'none-fold-only-v1'


def test_site_and_card_rebuild_are_deterministic():
    paths = list((ROOT / 'docs').glob('*.html')) + [ROOT / 'index.html', ROOT / 'executive-summary.html', ROOT / 'run_card.json']
    before = {p: digest(p) for p in paths}
    for script in ['build_run_card.py', 'build_site.py']:
        subprocess.run([sys.executable, str(ROOT / 'scripts' / script)], cwd=ROOT, check=True, capture_output=True)
    assert before == {p: digest(p) for p in paths}
    for p in paths:
        if p.suffix == '.html':
            text = p.read_text()
            assert 'DO NOT SUBMIT' in text
            assert 'OK TO DOWNLOAD &amp; SUBMIT' not in text
            assert 'gemsdoe84-h84-csat-d28-20261022T234500Z-a5483424-zeros' in text


def test_surface_failure_stops_before_any_dot_placement(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from scripts import run_h84_thms_pipeline as pipeline
    g = SimpleNamespace(footprint=np.ones((9, 9), bool), catalogue=np.zeros((9, 9), bool))
    monkeypatch.setattr(pipeline, 'EVID_DIR', tmp_path)
    monkeypatch.setattr(pipeline, 'build_or_load_full_production_surface', lambda *args: np.ones((9, 9), 'float32'))
    monkeypatch.setattr(pipeline, 'literal_registry_phase', lambda *args: {'unique': False})
    def forbidden(*args, **kwargs):
        pytest.fail('emitter must not run before a failed surface gate')
    monkeypatch.setattr(pipeline.DE, 'emit_dinkelbach_submodular', forbidden)
    with pytest.raises(RuntimeError, match='STOP before dot placement'):
        pipeline.run_exp3_build_and_audit(g, None, [], None, None, None, 0)
    assert json.loads((tmp_path / 'h84_preplacement_stop.json').read_text())['unique'] is False
