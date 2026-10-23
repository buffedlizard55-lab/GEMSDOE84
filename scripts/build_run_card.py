#!/usr/bin/env python3
"""Publish one current negative run card; never synthesize slot authorization.

Historical experiments remain under evidence/ and research/official/. In
particular, chance-corrected diagnostics cannot override the literal protocol.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    audit = json.loads((ROOT / 'registry/release_status.json').read_text())
    if audit.get('verdict') != 'negative' or audit.get('submission_authorized') is not False:
        raise ValueError('Current audit cannot be promoted by a run-card renderer')
    card = dict(audit)
    card.update(
        raster_sha256=None, submission_name=None, validator_output=audit['validator_output'],
        submission_note=audit['note'], download_allowed=True,
        submission_file='docs/downloads/' + audit['audited_artifact']['name'] + '.tif',
        # Top-level identity is intentionally null: no new submission was generated.
        # The explicit archived artifact supplies download identity, not a new candidate.
        registry_correlation_overlap={
            'duplicate': audit['final_duplicate'], 'complete_accessible_scan': False,
            'overlap_3px': audit['registry_comparison']['worst_dot_overlap'],
            'rank_correlation': audit['registry_comparison']['worst_spearman_full_footprint'],
            'pre_placement_stop': audit['pre_placement_stop']},
        submission_slots_used=0,
    )
    # One authoritative schema across historical spelling variants and site projections.
    for path in ['run_card.json', 'evidence/run-card.json', 'evidence/run_card.json',
                 'registry/run_card.json', 'docs/run-card.json', 'docs/data/run-card.json',
                 'docs/evidence/run_card.json']:
        (ROOT / path).write_text(json.dumps(card, indent=2, allow_nan=False) + '\n')
    print('Published NEGATIVE run card. No new TIFF; archived download is research only.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
