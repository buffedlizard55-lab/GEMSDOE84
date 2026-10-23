"""Exact MODEL ranking and fixed-count PRUNE, independent of restored data."""
from __future__ import annotations

import numpy as np
import pytest

from gems57 import metric
from gems84.prune_intermediate import kernel_trim_to_parent_count, snap_target_feasibility


def test_greedy_removals_match_shared_exact_metric_at_every_step():
    reference = np.zeros((16, 18), bool)
    reference[3:13, 2:15] = True
    parent = np.zeros_like(reference)
    for y, x in ((4, 3), (4, 6), (4, 9), (4, 12), (7, 3), (7, 6), (7, 9), (7, 12), (10, 4), (10, 11)):
        parent[y, x] = True
    ring = np.zeros_like(parent)
    ring[11, 6] = ring[11, 8] = ring[12, 12] = True
    result, order, stats = kernel_trim_to_parent_count(parent, ring, reference)
    live = parent | ring
    for selected in order:
        before = metric.dti_exact(live.astype(float), reference)['dti']
        deltas = []
        for flat in np.flatnonzero(parent & live):
            trial = live.copy()
            trial.ravel()[flat] = False
            delta = metric.dti_exact(trial.astype(float), reference)['dti'] - before
            deltas.append((flat, delta))
        selected_delta = dict(deltas)[selected]
        assert selected_delta == pytest.approx(max(delta for _, delta in deltas), abs=1e-12)
        live.ravel()[selected] = False
    assert np.array_equal(live, result)
    assert result[ring].all()
    assert int(result.sum()) == int(parent.sum())
    assert stats['reference_evidence_class'] == 'MODEL'
    assert stats['reference_dti_after_trim'] == pytest.approx(metric.dti_exact(result.astype(float), reference)['dti'])
    again, order2, _ = kernel_trim_to_parent_count(parent, ring, reference)
    assert np.array_equal(again, result) and np.array_equal(order2, order)


def test_kernel_ties_boundaries_and_disconnected_truth_are_exact():
    rng = np.random.default_rng(520810)
    for _ in range(8):
        reference = rng.random((18, 19)) > .3
        reference[0, 0] = reference[-1, -1] = True
        indices = rng.permutation(np.flatnonzero(reference))
        parent, ring = np.zeros_like(reference), np.zeros_like(reference)
        parent.ravel()[indices[:35]] = True
        ring.ravel()[indices[35:40]] = True
        mask, deleted, stats = kernel_trim_to_parent_count(parent, ring, reference)
        assert int(mask.sum()) == 35
        assert len(deleted) == 5
        assert (mask & ~reference).sum() == 0
        assert stats['reference_tp_after_trim'] == pytest.approx(metric.dti_exact(mask.astype(float), reference)['tp'])


def test_operator_never_mutates_parent_and_validates_reference():
    reference = np.ones((9, 9), bool)
    parent = np.zeros_like(reference)
    parent[2, 2] = parent[2, 6] = parent[6, 2] = parent[6, 6] = True
    ring = np.zeros_like(parent)
    ring[4, 4] = True
    before = parent.copy()
    kernel_trim_to_parent_count(parent, ring, reference)
    assert np.array_equal(before, parent)
    with pytest.raises(ValueError, match='disjoint'):
        kernel_trim_to_parent_count(parent, parent, reference)
    reference[2, 2] = False
    with pytest.raises(ValueError, match='fixed parent reference'):
        kernel_trim_to_parent_count(parent, ring, reference)


def test_snap_empty_target_window_is_a_constructive_impossibility():
    parent = np.zeros((10, 10), bool)
    parent[5, 5] = True
    allowed = np.ones_like(parent)
    allowed[3:8, 3:8] = False
    receipt = snap_target_feasibility(parent, allowed, 2.0)
    assert receipt['dots_without_any_allowed_target'] == 1
    assert not receipt['feasible_by_individual_windows']
    allowed[5, 7] = True
    assert snap_target_feasibility(parent, allowed, 2.0)['feasible_by_individual_windows']
    assert not snap_target_feasibility(parent, allowed, 1.42)['feasible_by_individual_windows']


def test_binary_canary_auc_handles_ties_exactly():
    from scripts.build_prune_intermediate import binary_auc
    feature = np.array([[1, 0, 1, 1, 0, 0]], bool)
    pos = np.array([[1, 1, 1, 0, 0, 0]], bool)
    neg = ~pos
    p, n = feature[pos], feature[neg]
    brute = ((p[:, None] > n[None, :]) + .5 * (p[:, None] == n[None, :])).mean()
    assert binary_auc(feature, pos, neg) == pytest.approx(brute)


def test_built_intermediate_pair_and_evidence_are_consistent():
    import csv
    import hashlib
    import json
    from pathlib import Path
    import rasterio
    from scipy.ndimage import distance_transform_edt
    from scripts.validate_submission import validate

    root = Path(__file__).resolve().parents[1]
    report_path = root / 'evidence/prune_1p5_796cb891.json'
    if not report_path.exists():
        pytest.skip('one planned candidate has not been built yet')
    report = json.loads(report_path.read_text())
    assert report['axis'] == 'PRUNE' and report['value'] == '1.5'
    assert report['n_dots'] == 37654
    assert report['dots_added'] == report['dots_removed'] == 1344
    assert report['pct_changed'] == pytest.approx(100 * 2688 / 37654)
    assert report['historical_ledger_rows'] == 125 and report['historical_bytes_preserved']
    assert report['submission_slots_used'] == 0 and not report['submission_authorized']
    assert len(report['verified_inputs']) == 27 and all(f['verified'] for f in report['verified_inputs'])
    assert report['parent_rebuild']['all_checks_passed']
    assert all(report['mask_checks'].values())
    assert len(report['form_note']) <= 140
    assert report['snap_infeasibility']['dots_without_any_allowed_target'] == 30
    assert report['ranking']['reference_evidence_class'] == 'MODEL'
    assert report['no_similarity_thresholds_applied']
    template = root / 'data/bridge/sample_submission.tif'
    catalogue = root / 'data/bridge/existing_faults.tif'
    manifest = json.loads((root / 'registry/data_manifest.json').read_text())
    pins = {r['id']: r['sha256'] for r in manifest['files']}
    assert hashlib.sha256(template.read_bytes()).hexdigest() == pins['sample_submission']
    assert hashlib.sha256(catalogue.read_bytes()).hexdigest() == pins['existing_faults']
    with rasterio.open(template) as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(catalogue) as ds:
        cat = (ds.read(1) > 0) & foot
    distance = distance_transform_edt(~cat)
    masks = []
    for encoding in ('nan', 'zeros'):
        file = report['files'][encoding]
        path = root / file['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == file['sha256']
        assert validate(path, template, encoding)['format_valid']
        with rasterio.open(path) as ds:
            values = ds.read(1)
        mask = np.isfinite(values) & (values > 0)
        masks.append(mask)
        assert np.isin(values[foot], [0, 1]).all()
        assert int(mask.sum()) == 37654
        assert float(values[cat].sum()) == 0
        assert float(distance[mask].min()) == 2.0
        assert not (mask & ~foot).any()
    assert np.array_equal(*masks)
    rows = list(csv.DictReader((root / 'ledger/submissions.csv').open()))
    own = [r for r in rows if r['id'] == report['id']]
    assert len(own) == 1
    row = own[0]
    assert row['axis'] == 'PRUNE' and row['value'] == '1.5'
    assert row['sha256'] == report['files']['nan']['sha256']
    assert row['sha256_zeros'] == report['files']['zeros']['sha256']
    for other in rows:
        if other['id'] != row['id']:
            assert row['sha256'] not in (other.get('sha256'), other.get('sha256_zeros'))
            assert row['sha256_zeros'] not in (other.get('sha256'), other.get('sha256_zeros'))
    diagnostics = report['report_only_diagnostics']
    control = diagnostics['catalogue_hide_and_recover']
    assert control['report_only'] and 'NOT fold-clean' in control['mode']
    summary = control['shared_summary']
    assert summary['evidence_class'] == 'PROXY'
    assert summary['scores']['PRUNE1.5']['withheld_positive_pixels'] == 22893
    assert len(summary['scores']['PRUNE1.5']['ci95']) == 2
    assert control['unique_withheld_pixels_across_draws'] == 21032
    assert diagnostics['leakage_canary']['max_single_feature_strength'] <= .90
    assert diagnostics['sgmc_control']['status'] == 'NOT_RUN'
    assert 'UNVERIFIED' in diagnostics['sgmc_control']['license']


def test_recorded_intermediate_cannot_be_rebuilt_and_ledger_cannot_be_replaced(tmp_path):
    import csv
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    ledger = root / 'ledger/submissions.csv'
    rows = list(csv.DictReader(ledger.open()))
    if not any(row['axis'] == 'PRUNE' and row['value'] == '1.5' for row in rows):
        pytest.skip('candidate is not built yet')
    before = ledger.read_bytes()
    result = subprocess.run([sys.executable, str(root / 'scripts/build_prune_intermediate.py'),
                             '--axis', 'PRUNE', '--data-dir', str(tmp_path / 'missing')],
                            cwd=root, capture_output=True, text=True)
    assert result.returncode != 0 and 'Already built/recorded' in result.stderr
    assert not (tmp_path / 'missing').exists()
    assert ledger.read_bytes() == before
    replacement = subprocess.run([sys.executable, str(root / 'scripts/build_ledger.py')],
                                 cwd=root, capture_output=True, text=True)
    assert replacement.returncode == 2 and 'Refusing to replace existing ledger' in replacement.stderr
    assert ledger.read_bytes() == before
