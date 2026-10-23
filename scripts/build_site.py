#!/usr/bin/env python3
"""Deterministic, fail-closed release portal; one current audit, no hardcoded promotion.

No network/model calls. Missing or unsafe release evidence is an error, never an
implicit green badge. Historical science reports stay separate from authorization.
"""
from __future__ import annotations

import hashlib
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_blocked_release(card: dict, docs: Path) -> None:
    """Legacy API: a renderer cannot grant selector authorization."""
    if card.get('verdict') == 'promote':
        raise ValueError('A site renderer cannot authorize a selector decision')
    if any(p.is_file() and p.suffix.lower() in {'.tif', '.tiff', '.zip'} for p in docs.rglob('*')):
        raise ValueError('Blocked legacy release contains downloadable artifacts')


def checked_status(root: Path) -> dict:
    card = json.loads((root / 'registry/release_status.json').read_text())
    if card.get('submission_authorized') is not False or card.get('verdict') != 'negative':
        raise ValueError('This audited negative release cannot authorize a selector decision')
    a = card['audited_artifact']
    paths = [root / a['path'], root / 'docs/downloads' / f"{a['name']}.tif"]
    for path in paths:
        if hashlib.sha256(path.read_bytes()).hexdigest() != a['sha256']:
            raise ValueError(f'Artifact hash mismatch: {path}')
    if not card['stop_required']:
        raise ValueError('Missing literal lane stop')
    return card


def main() -> int:
    card = checked_status(ROOT)
    name = html.escape(card['audited_artifact']['name'])
    sha = html.escape(card['audited_artifact']['sha256'])
    ov = card['registry_comparison']['worst_dot_overlap']
    rho = card['registry_comparison']['worst_spearman_full_footprint']
    val = card['validator_output']
    sources = json.loads((ROOT / 'registry/sources.json').read_text())
    source_rows = ''.join(f'<tr><td><a href="{html.escape(s["url"], quote=True)}">{html.escape(s["title"])}</a></td>'
                          f'<td>{html.escape(s["status"])}</td><td>{html.escape(s["role"])}</td></tr>' for s in sources)
    checks = ''.join(f'<tr><td>{html.escape(k)}</td><td>{"PASS" if v else "FAIL"}</td></tr>' for k, v in val['checks'].items())
    sections = {
        'index': '''<h2>Executive decision</h2><p>The prior download is format-valid but fails the literal uniqueness protocol. No new unique TIFF was generated. We stopped before new placement; no weekly slot was used. A negative result is the honest deliverable.</p>
<p>Automatic inspection is not the same as organizer acceptance, scientific validation, or selector authorization. The selector cannot promote this file while the stop is active.</p>
<div class="grid"><article><h3>Local format</h3><p>PASS · all-finite [0,1], single band, reference grid match.</p></article><article><h3>Literal uniqueness</h3><p>FAIL · registry witness covers every allowed cell. No density exemptions.</p></article><article><h3>Scientific validation</h3><p>NOT CERTIFIED · archived production-like holdout consumes full-catalogue registry halos.</p></article></div>''',
        'executive-summary': '''<h2>How a future authorized submission works</h2><ol><li>Generate a genuinely new prediction using the shared evaluator and writer. No copying or renaming a prior TIFF.</li><li>Pass feature canaries; freeze whole-segment buffered holdout; recompute every catalogue-derived feature from visible faults only. Compare pooled HOLDOUT-DTI and paired confidence intervals against the same-fold best.</li><li>Pass literal registry checks on the surface before placement and the final dots. Missing inventory data cannot establish uniqueness. Resolve the present saturated-registry policy with the protocol owner before resuming.</li><li>Reopen the written TIFF: one band, exact reference CRS/shape/transform, all values finite in [0,1], no masked footprint cells. The shared writer also creates a ZIP with exactly one TIFF.</li><li>A separate selector verifies current competition rules, remaining weekly allowance and evidence, then authorizes a slot. This project has not done so.</li><li>Only then use the organizer submission form: select the authorized .tif (or one-TIFF .zip), use a unique name and note of at most 140 characters, and record the organizer receipt. Never call a projection a score.</li></ol><p><strong>Current result: DO NOT UPLOAD the archived download.</strong> No manual raster inspection is required to reach this decision; the automated gate already failed. The missing work is scientific/protocol clearance, not a human checkbox.</p><p>For the reported range error: verify actual data values and nodata metadata, not just image appearance. This file passes the stricter local all-finite policy, but the exact cause of the earlier portal error is not established.</p>''',
        'methodology': '''<h2>Why H33 may have improved</h2><p>The upstream H33 evidence starts from an inherited GEMSDOE28 base and removes low-credit predictions near mapped faults. Under pooled DTI, deleting redundant dots can reduce false-positive mass more than true-positive coverage. This is a precision-budget mechanism, not proof of a new physical detector.</p><p>Its user-reported score is not organizer-confirmed here. The hidden truth is unavailable, so exact causal attribution or a guarantee of improvement is impossible. Earlier claims of precisely quantified hidden credit and guaranteed higher performance are not endorsed.</p><p>For fixed positive count G: <code>DTI = t / ((1-beta)t + alpha*f + beta*G)</code>. The shared evaluator uses alpha=0.2, beta=0.8 and a 300m triangular kernel. Those settings are repository configuration; this session did not retrieve the official metric page. The official reference notebook confirms training loss weights, not the distance evaluator.</p><p><a href="research/SESSION_REVIEW_20261023.md">Read the derivation, immutable source links and four within-lane hypotheses</a>.</p>''',
        'results': f'''<h2>Fresh audit measurements — not performance scores</h2><table><tr><th>Measurement</th><th>Result</th></tr><tr><td>Archived TIFF vs pinned registry witness, forward overlap within 3px</td><td>{ov:.6f} (limit 0.70) · FAIL</td></tr><tr><td>Full-footprint rank correlation vs this witness</td><td>{rho!s} (constant ranks are undefined; null is not zero)</td></tr><tr><td>Allowed cells not covered by witness halo</td><td>{card['certificate']['uncovered_allowed_pixels']}</td></tr><tr><td>Pre-placement state</td><td>STOP by universal saturation proof; no new surface generated.</td></tr><tr><td>Registry scan completeness</td><td>One counterexample; not a complete refreshed scan. Enough to refute, never to certify.</td></tr></table><h2>Reopened TIFF validator</h2><table><tr><th>Check</th><th>Result</th></tr>{checks}</table><h2>Holdout evidence</h2><p>No new HOLDOUT-DTI was measured. Historical A5 numbers are not used for promotion: its emitter depends on full-catalogue registry halos. A feature AUC canary alone cannot rule out that leakage path. Archived results and confidence intervals remain in evidence files, not as leaderboard predictions.</p>''',
        'hypotheses': '''<h2>Four proposals within the inherited H84-THMS lane</h2><p>Ranked qualitatively by expected validation value and cost, not projected scores. No new method was implemented or tested after the lane stop.</p><ol><li><strong>Thermal upgradient plume-head residuals</strong> (medium cost): wells/springs + DEM; suppress elevation and downstream outflow effects to localize buried conduits. Mimic: lateral warm aquifer.</li><li><strong>Azimuthal clay-cap breach contrast</strong> (medium): thermal heads + MT depth slices; discriminate localized cap edges from closed saline basin conductors. Mimic: playa salinity.</li><li><strong>Reactivated seal versus fossil outflow</strong> (medium-high): paleo deposits + modern probes + terrain, with matched cold deposits as negative controls. Mimic: abandoned outflow/tufa. Source cache incomplete, not data-viable now.</li><li><strong>Cross-catchment replicated thermal/scarp breaks</strong> (medium-high): terrain, chi, LiDAR and thermal heads; require independent catchment replication. Mimic: lake terrace or lithologic knickpoint.</li></ol><p>Explicit constructions not found in current THMS feature code; uniqueness across all family work is unverified. Official external sources are network-restricted, so no new-source proposal is declared obtainable/viable.</p><p><a href="research/SESSION_REVIEW_20261023.md">Full layer specifications, novelty limitations and pre-registered validation plan</a>.</p>''',
        'irregularities': '''<h2>Blocking irregularities</h2><ul><li>Earlier uniqueness gate truncated/exempted registry supports and audited after placement.</li><li>Archived A5 holdout consumes full-catalogue registry halos. Leakage not ruled out.</li><li>The restore manifest does not cover every optional source used by the feature builder. Absence can silently produce zero fields.</li><li>The prior evaluator/writer command wrappers imported nonexistent functions. Fixed to use real shared APIs; CLI smoke tests added.</li><li>Competition URL ID 306 in the supplied prompt conflicted with 311 in the prior source ledger. Canonical ID unresolved; supplied links retained with status, not silently authenticated.</li><li>Conflicting user leaderboard figures have no organizer receipt. No live score or weekly cap confirmed.</li><li>Current cache lacks training and external feature stacks; GitHub mirrors are not organizer-authenticated.</li></ul><p><a href="research/SESSION_REVIEW_20261023.md">Detailed three-pass review and next work</a>.</p>''',
        'sources': '<h2>Source ledger</h2><p>Only GitHub, GitHub API/codeload, npm and PyPI hosts are reachable. Official links below are manual-review pointers unless retrieval is explicitly recorded. No invented source verification, data license or leaderboard receipt.</p><table><tr><th>Source</th><th>Retrieval status</th><th>Evidence boundary</th></tr>' + source_rows + '</table><p><a href="research/official/reference-extract.json">Retrieved organizer notebook extract and SHA-256</a> · <a href="research/SESSION_REVIEW_20261023.md">Claim-by-claim source review</a></p>',
        'research': '<h2>Research notebook</h2><p><a href="research/SESSION_REVIEW_20261023.md">Current scientific and engineering review</a>. Fault prediction aids exploration but does not establish a productive geothermal vent or reservoir. Heat, permeability, sustainable flow and economics require additional evidence.</p>',
    }
    css = '''*{box-sizing:border-box}body{margin:0;background:#f4f6fa;color:#172337;font:16px/1.65 system-ui,sans-serif}header{background:#14283e;color:white;padding:24px max(6vw,20px)}header a{color:#cceaff;margin-right:20px;display:inline-block}main{max-width:1120px;margin:auto;padding:28px 24px}section,article{background:white;padding:24px;border-radius:12px;margin-bottom:24px;border:1px solid #d9e1eb}.notice{border-left:6px solid #b12932;background:#fff4f3}.label{font-weight:750;color:#a21f2a}h1{font-size:clamp(1.8rem,4vw,2.8rem);line-height:1.2}h2{line-height:1.3}a{color:#075d92}code{overflow-wrap:anywhere;font-size:.9em}.button{display:inline-block;background:#244e70;color:white;padding:12px 18px;border-radius:6px;margin:8px 8px 8px 0;text-decoration:none}table{width:100%;border-collapse:collapse;font-size:.9em;display:block;overflow-x:auto}td,th{text-align:left;padding:12px;border-bottom:1px solid #dde4ec;vertical-align:top}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}small{color:#526375}footer{padding:20px 0;color:#526375}'''
    (ROOT / 'docs/assets').mkdir(exist_ok=True)
    (ROOT / 'docs/assets/release.css').write_text(css + '\n')
    for page, body in sections.items():
        nav = ''.join(f'<a href="{key}.html">{title}</a>' for key, title in [
            ('index', 'Overview'), ('executive-summary', 'Submission guide'), ('results', 'Audit & validator'),
            ('hypotheses', 'Hypotheses'), ('methodology', 'H33 analysis'), ('sources', 'Sources'), ('irregularities', 'Blockers')])
        hero = f'''<section class="notice"><p class="label">NEGATIVE · DO NOT SUBMIT · LANE STOPPED</p><h1>Downloadable TIFF: research only</h1><p>The existing TIFF passes local format checks but fails your literal uniqueness rule. <strong>It is NOT cleared for competition submission.</strong> No new unique submission has been generated.</p><a class="button" href="downloads/{name}.tif" download>Download archived TIFF — DO NOT SUBMIT</a><a class="button" href="evidence/release-audit-20261023.json">Automated decision JSON</a><p><small>Archived name: <code>{name}</code><br>SHA-256: <code>{sha}</code><br>Research note (not a portal recommendation): {html.escape(card['note'])}</small></p></section>'''
        document = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GEMSDOE84 · {page} · research only</title><link rel="stylesheet" href="assets/release.css"></head><body><header><strong>GEMSDOE84 / H84-THMS</strong><p>Evidence first. Maximize P(Win). Own the Outcome.</p><nav>{nav}</nav></header><main>{hero}<section>{body}</section><footer>Audit: 2026-10-23 · No organizer acceptance, score or weekly slot asserted. Generated from registry/release_status.json.</footer></main></body></html>\n'''
        (ROOT / 'docs' / f'{page}.html').write_text(document)
        if page in ('index', 'executive-summary'):
            # Root copies are fully usable, with all browser-relative paths rebased.
            document = document.replace('href="', 'href="docs/')
            (ROOT / f'{page}.html').write_text(document)
    (ROOT / 'docs/downloads/index.html').write_text(
        (ROOT / 'docs/index.html').read_text().replace('href="', 'href="../'))
    for folder in ('research',):
        target = ROOT / 'docs' / folder
        target.mkdir(exist_ok=True)
    shutil.copy2(ROOT / 'research/SESSION_REVIEW_20261023.md', ROOT / 'docs/research/SESSION_REVIEW_20261023.md')
    (ROOT / 'docs/research/official').mkdir(exist_ok=True)
    shutil.copy2(ROOT / 'research/official/reference-extract.json', ROOT / 'docs/research/official/reference-extract.json')
    print('Built fail-closed research portal from current release audit.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
