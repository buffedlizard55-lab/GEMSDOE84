#!/usr/bin/env python3
"""Build ONE unused intermediate PRUNE control, >1.5 px, at the exact R0 count.

The owner explicitly delegated axis selection in the latest brief. PRUNE is
chosen because R0 violates the non-PRUNE collar and 30 dots cannot reach a valid
SNAP target within 2 px. Integer PRUNE endpoints are already built/reserved.
The single intermediate value admits only the existing 200 m D2.8 ring, not the
141 m diagonal ring. Count compensation preserves the original H19-5 field's
shared-kernel coverage; no new physical signal or external data is introduced.

This script never submits, fetches pages, reads credentials, or authorizes slots.
It refuses recorded pairs/hashes. Re-validation is a separate read-only command;
do not run the builder again after its row is in the ledger.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'vendor')]

from gems57 import evaluate_holdout, holdout, submission_writer  # noqa: E402
from gems57.grid import load_grid as shared_grid  # noqa: E402
from gems84.brief_v2 import (  # noqa: E402
    BriefViolation, R0_ID, catalogue_clearance, ledger_hashes, read_experiment_history,
    read_ledger_rows, require_new_experiments, verify_pinned_files,
)
from gems84.parent import BASE_REL, emit_dots, load_grid, read_binary, sha256_file  # noqa: E402
from gems84.prune_intermediate import kernel_trim_to_parent_count, snap_target_feasibility  # noqa: E402
from scripts.restore_pinned_inputs import EXTRA_PINS  # noqa: E402
from scripts.validate_submission import validate  # noqa: E402

AXIS, VALUE, DATE = 'PRUNE', '1.5', '20261023'
SEED = 520810
PREDICTED = 'MODEL central +0.002 DTI; plausible -0.010..+0.015, uncalibrated scenario (not a confidence interval)'
H19_DEST = 'scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif'
SOURCES = (
    'scripts/build_prune_intermediate.py', 'src/gems84/prune_intermediate.py',
    'src/gems84/parent.py', 'src/gems84/brief_v2.py', 'scripts/rebuild_r0.py',
    'scripts/validate_submission.py', 'registry/data_manifest.json',
    'requirements-lock.txt', 'registry/preregistration_prune_1p5.json',
    'vendor/gems57/metric.py', 'vendor/gems57/holdout.py',
    'vendor/gems57/evaluate_holdout.py', 'vendor/gems57/submission_writer.py',
    'vendor/gems57/grid.py', 'vendor/gems57/gates.py', 'vendor/gems57/validate.py',
)

CARD = {
    'hypothesis': 'At fixed 37,654 dots, restoring the original 200 m ring while excluding the 141 m ring '
                  'recovers unmapped near-trace splays/geometry that a blanket >2 px collar removed.',
    'mechanism': 'Apply d_cat>1.5 px to the pinned pre-prune lineage: insert all D2.8 dots at d_cat=2 px. '
                 'Remove the same number of original R0 dots by the least exact marginal DTI loss against '
                 'the fixed H19-5 lineament reference, updating neighbours after every removal. All dots '
                 'remain in the original parent field at its >=2.8 px separation. This changes collar '
                 'allocation, not mass or the physical field. The reference is MODEL, never hidden truth.',
    'non_fault_mimic': 'Misregistered existing linework, fault-parallel erosional benches, fan-channel '
                      'margins and lithologic contacts can occupy the same 200 m band without a new fault.',
    'predicted_sign_and_size': PREDICTED,
    'prediction_basis': 'Weak positive sign is a structural scenario, not fitted to a local diagnostic. '
                        'Unmapped geometry may lie near known traces, but its prevalence and live credit '
                        'are unknown. Do not divide MODEL ranking units by a live denominator.',
    'falsifier': 'With comparable parent and candidate submission-page receipts, delta<=-0.01 contradicts '
                 'the proposed 200 m-ring benefit; delta>=+0.01 supports it on public chunks only. '
                 'Every absolute delta<0.01 is no evidence. Neither outcome proves a hidden-label geology.',
    'sources': [
        'https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516',
        'https://community.drivendata.org/t/where-do-you-draw-the-line/11536',
    ],
}


def binary_auc(feature, pos, neg):
    """Exact Mann-Whitney AUC for a binary feature, including ties, no subsampling."""
    if not pos.any() or not neg.any():
        raise ValueError('canary requires both classes')
    return float(.5 + .5 * (feature[pos].mean() - feature[neg].mean()))


def proxy_labels(value):
    if isinstance(value, dict):
        return {key: proxy_labels(item) for key, item in value.items()}
    if isinstance(value, list):
        return [proxy_labels(item) for item in value]
    return 'PROXY' if isinstance(value, str) and value == 'HOLDOUT-DTI' else value


def controls(data_dir, reference, parent, candidate, footprint):
    """Shared evaluator only. Shipped-mask diagnostic is explicitly censored, not fold-clean."""
    g = shared_grid(data_dir)
    terms, cells, canary = {'R0': None, 'PRUNE1.5': None}, [], []
    unique_truth = np.zeros_like(parent)
    for seed in (20, 21):
        folds, _ = holdout.buffered_component_draw(g, seed=seed)
        pos, neg = np.zeros_like(parent), np.zeros_like(parent)
        for fold in folds:
            active = footprint & fold['region'] & ~fold['masked_known']
            pos |= active & fold['truth']
            neg |= active & ~fold['truth']
            unique_truth |= active & fold['truth']
            cells.append(fold['receipt'])
        auc = binary_auc(reference, pos, neg)
        strength = max(auc, 1.0 - auc)
        canary.append(dict(feature='fixed_H19_5_parent_lineaments', seed=seed, auc=auc,
                           absolute_strength=strength, positives=int(pos.sum()), negatives=int(neg.sum())))
        if strength > .90:
            raise BriefViolation(f'STOP: single-feature leakage canary {strength:.5f}>0.90; investigate')
        for name, mask in (('R0', parent), ('PRUNE1.5', candidate)):
            prediction = mask.astype(np.float32)
            for fold in folds:
                _, block_terms = evaluate_holdout.evaluate(prediction, fold, footprint)
                terms[name] = block_terms if terms[name] is None else terms[name] + block_terms
    summary = proxy_labels(evaluate_holdout.pooled_summary(terms, draws=1000, seed=SEED, candidate='PRUNE1.5'))
    return {
        'catalogue_hide_and_recover': {
            'evidence_class': 'PROXY', 'report_only': True,
            'mode': 'Shipped masks; fixed full-catalogue exclusions and upstream field; NOT fold-clean',
            'caveat': 'The full catalogue informed R0 and the emitted collar before withholding. '
                      'New 200 m ring dots mechanically regain credit against catalogue-derived truth. '
                      'Upstream H19 was not retrained on visible folds. This cannot select/veto the collar '
                      'or calibrate live gain; the 95% CI is conditional on this biased instrument.',
            'unique_withheld_pixels_across_draws': int(unique_truth.sum()),
            'fold_receipts': cells, 'shared_summary': summary,
        },
        'leakage_canary': {
            'evidence_class': 'PROXY', 'threshold': .90, 'features_checked': 1,
            'features': canary, 'max_single_feature_strength': max(row['absolute_strength'] for row in canary),
            'passed': True,
            'caveat': 'Catalogue geometry is the explicit PRUNE design variable, not a learned feature. '
                      'Passing this one-feature check does not certify the upstream field or holdout leakage-free.',
        },
        'sgmc_control': {
            'evidence_class': 'PROXY', 'status': 'NOT_RUN', 'report_only': True,
            'source_url': 'https://doi.org/10.3133/ds1052',
            'license': 'UNVERIFIED: no explicit redistribution/shareability license receipt for the derived mirror',
            'reason': 'External-data permission not established; do not consume it. Hash verification only; no new external data used.',
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--axis', required=True, choices=[AXIS], help='Explicit agent choice under the latest owner delegation')
    parser.add_argument('--data-dir', type=Path, default=ROOT / '.cache/gems_data')
    args = parser.parse_args()
    data_dir = args.data_dir.resolve()
    ledger = ROOT / 'ledger/submissions.csv'
    before = ledger.read_bytes()
    history = read_experiment_history(ledger)
    require_new_experiments(history, R0_ID, AXIS, [VALUE])
    primary_rows = read_ledger_rows(ledger)
    known_hashes = ledger_hashes(history)
    manifest = json.loads((ROOT / 'registry/data_manifest.json').read_text())
    verified = verify_pinned_files(data_dir, list(manifest['files']) + list(EXTRA_PINS))
    print(f'[1/6] {len(verified)} pinned hashes verified', flush=True)
    source_sha = {path: sha256_file(ROOT / path) for path in SOURCES}
    git_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    import hashlib
    for path, expected in source_sha.items():
        committed = subprocess.check_output(['git', 'show', f'{git_sha}:{path}'], cwd=ROOT)
        if hashlib.sha256(committed).hexdigest() != expected:
            raise BriefViolation(f'Commit every source before building so the logged git SHA is exact: {path}')

    cache = ROOT / '.cache/prune-intermediate'
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='build-', dir=cache) as work:
        work = Path(work)
        rebuild_receipt = work / 'r0-rebuild.json'
        subprocess.run([sys.executable, str(ROOT / 'scripts/rebuild_r0.py'), '--data-dir', str(data_dir),
                        '--out', str(work / 'parent'), '--receipt', str(rebuild_receipt)], check=True, cwd=ROOT)
        rebuild = json.loads(rebuild_receipt.read_text())
        if not rebuild['all_checks_passed']:
            raise BriefViolation('STOP: exact R0 identity failed; never approximate')
        grid = load_grid(data_dir)
        parent = read_binary(work / 'parent/r0-rebuilt-zeros.tif')
        base = read_binary(data_dir / BASE_REL)
        reference = read_binary(data_dir / H19_DEST) & grid.foot
        ring = base & (grid.d_cat > 1.5) & (grid.d_cat <= 2.0) & ~parent & grid.foot
        if not np.array_equal(base & (grid.d_cat > 2), parent):
            raise BriefViolation('Recorded pre-prune lineage does not recreate R0')
        if int(ring.sum()) != 1344 or not np.all(grid.d_cat[ring] == 2.0):
            raise BriefViolation('Unexpected 200 m ring; do not silently change the experiment')
        print('[2/6] Exact R0; unused PRUNE1.5 admits 1,344 original 200 m-ring dots', flush=True)
        feasibility = snap_target_feasibility(parent, grid.off_catalogue_3px)
        mask, deleted, ranking = kernel_trim_to_parent_count(parent, ring, reference)
        added, removed = int((mask & ~parent).sum()), int((parent & ~mask).sum())
        changed = 100.0 * (added + removed) / int(parent.sum())
        checks = {
            'count_fixed': int(mask.sum()) == int(parent.sum()) == 37654,
            'parent_field_preserved': not np.any(mask & ~reference),
            'original_lineage_pool_only': not np.any(mask & ~base),
            'inside_footprint': not np.any(mask & ~grid.foot),
            'zero_catalogue_mass': not np.any(mask & grid.catalogue),
            'prune_collar_gt1p5': bool(np.all(grid.d_cat[mask] > 1.5)),
            'exact_200m_ring_inserted': np.array_equal(mask & ~parent, ring),
            'bounded_parent_difference': 1.0 <= changed <= 50.0,
            'prune_exception_only': catalogue_clearance(mask, grid.catalogue, grid.d_cat, AXIS)['passed'],
        }
        if not all(checks.values()):
            raise BriefViolation(f'Mask gates failed: {checks}')
        print(f'[3/6] One variant; count fixed; {changed:.12f}% symmetric parent difference', flush=True)
        diagnostics = controls(data_dir, reference, parent, mask, grid.foot)
        print('[4/6] REPORT-ONLY shared PROXY and canary complete; no proxy promotion gate', flush=True)

        note = f'{R0_ID}; PRUNE >1.5px, {added} ring-in/tail-out, n37654; MODEL +0.002 (-0.010..+0.015)'
        stage_nan = work / 'candidate.tif'
        emit_dots(mask, grid, stage_nan, mode='nan')
        nan_sha = sha256_file(stage_nan)
        file_id = f'{R0_ID}-PRUNE1p5-{DATE}-{nan_sha[:8]}'
        stage_zeros = work / f'{file_id}-zeros.tif'
        shared_receipt = submission_writer.write_submission(
            stage_zeros, mask.astype(np.float32), data_dir / 'sample_submission.tif', grid.foot,
            note=note, name=file_id, catalogue=grid.catalogue,
            metadata={'axis': AXIS, 'value': VALUE, 'parent': R0_ID, 'git_sha': git_sha, 'seed': SEED},
        )
        files = {}
        for encoding, path in (('nan', stage_nan), ('zeros', stage_zeros)):
            receipt = validate(path, data_dir / 'sample_submission.tif', encoding)
            if not receipt['format_valid'] or receipt['sha256'] in known_hashes:
                raise BriefViolation(f'Format/duplicate SHA-256 gate failed for {encoding}')
            with rasterio.open(path) as src:
                data = src.read(1)
            if not np.array_equal(data[grid.foot], mask[grid.foot].astype(np.float32)):
                raise BriefViolation('Written pixels differ from the experimental mask')
            files[encoding] = receipt
        if len(note) > 140 or len(file_id) > 140:
            raise BriefViolation('Form name/note exceeds 140 characters')
        outputs = {'nan': ROOT / 'releases' / f'{file_id}.tif',
                   'zeros': ROOT / 'releases' / f'{file_id}-zeros.tif'}
        if any(path.exists() for path in outputs.values()):
            raise BriefViolation('Refusing to overwrite any existing release')
        if ledger.read_bytes() != before:
            raise BriefViolation('Ledger changed during build; stop before publishing')
        require_new_experiments(read_experiment_history(ledger), R0_ID, AXIS, [VALUE])
        # Both serializations passed all gates in ignored staging before promotion.
        for encoding, source in (('nan', stage_nan), ('zeros', stage_zeros)):
            source.replace(outputs[encoding])
            disk = validate(outputs[encoding], data_dir / 'sample_submission.tif', encoding)
            if not disk['format_valid'] or disk['sha256'] != files[encoding]['sha256']:
                raise BriefViolation('Final-path disk re-read failed')
            files[encoding] = {**disk, 'path': str(outputs[encoding].relative_to(ROOT))}
        print(f'[5/6] Both encodings independently validated; {file_id}', flush=True)
        report = {
            'schema_version': 1, 'generated_utc': datetime.now(timezone.utc).isoformat(),
            'git_sha': git_sha, 'source_sha256': source_sha, 'seed': SEED,
            'runtime': {'python': sys.version.split()[0], 'numpy': np.__version__,
                        'rasterio': rasterio.__version__, 'gdal': rasterio.__gdal_version__},
            'axis': AXIS, 'value': VALUE, 'axis_selection': 'Agent-selected under explicit latest owner delegation',
            'id': file_id, 'parent': R0_ID, 'parent_claim': {'value': .2778, 'evidence_class': 'CLAIM'},
            'parent_rebuild': rebuild, 'verified_inputs': verified,
            'n_dots': int(mask.sum()), 'dots_added': added, 'dots_removed': removed,
            'symmetric_difference_pixels': added + removed, 'pct_changed': changed,
            'replaced_parent_dots_pct': 100.0 * removed / int(parent.sum()),
            'd_cat_min_px': float(grid.d_cat[mask].min()),
            'd_cat_median_px': float(np.median(grid.d_cat[mask])),
            'new_ring_d_cat_values_px': [float(v) for v in np.unique(grid.d_cat[ring])],
            'ranking': ranking, 'snap_infeasibility': feasibility, 'mask_checks': checks,
            'files': files, 'form_note': note, 'predicted_change': PREDICTED,
            'mechanism_card': CARD, 'report_only_diagnostics': diagnostics,
            'shared_fallback_writer': {
                'implementation': 'Unmodified vendor/gems57/submission_writer.py',
                'sha256': shared_receipt['sha256'],
                'validator': shared_receipt['validator'],
                'zip_policy': 'Shared writer ZIP/sidecar generated only in ignored staging and not published',
            },
            'no_similarity_thresholds_applied': True, 'submission_authorized': False,
            'submission_slots_used': 0,
            'historical_ledger_sha256': sha256_file(ledger), 'historical_ledger_rows': len(primary_rows),
            'historical_ledger_bytes': len(before),
            'data_policy': 'Only pinned parent-lineage competition artifacts used; no new external data. '
                           'Existing public competition-data mirrors remain flagged; input rasters are not republished.',
        }
        # CSV append preserves every historical byte and human receipt field.
        fields = next(csv.reader(io.StringIO(before.decode())))
        row = {field: '' for field in fields}
        row.update(id=file_id, site='GEMSDOE84', name=file_id, evidence_class='MODEL', encoding='nan+zeros',
                   n_dots='37654', pct_changed=format(changed, '.17g'), sha8=nan_sha[:8], sha256=nan_sha,
                   sha256_zeros=files['zeros']['sha256'], parent=R0_ID, axis=AXIS, value=VALUE,
                   status='BUILT', receipt='N', predicted_change=PREDICTED, form_note=note,
                   notes=f'Only PRUNE: add {added} original d_cat=2px dots; remove {removed} least exact H19-kernel-loss R0 dots; all count compensation on original field')
        addition = io.StringIO(newline='')
        csv.DictWriter(addition, fieldnames=fields, lineterminator='\r\n').writerow(row)
        if not before.endswith(b'\n'):
            raise BriefViolation('Ledger lacks final newline; do not silently rewrite history')
        payload = before + addition.getvalue().encode()
        report['historical_bytes_preserved'] = payload.startswith(before)
        out = ROOT / 'evidence/prune_1p5_796cb891.json'
        if out.exists() or ledger.read_bytes() != before:
            raise BriefViolation('Existing report or changed ledger; refusing to overwrite history')
        staged_report = work / 'report.json'
        staged_report.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        staged_ledger = work / 'submissions.csv'
        staged_ledger.write_bytes(payload)
        # Publish the fully serialized local evidence before atomically appending
        # the BUILT record. No historical row is parsed/reformatted or discarded.
        staged_report.replace(out)
        staged_ledger.replace(ledger)
        if not ledger.read_bytes().startswith(before):
            raise BriefViolation('Historical ledger prefix changed')
        print(f'[6/6] One BUILT row appended; receipt_score/date blank; report {out.relative_to(ROOT)}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
