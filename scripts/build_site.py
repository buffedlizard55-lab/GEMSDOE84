"""Render release state from the run card; never infer promotion from a format pass."""
from pathlib import Path
import html
import json
import shutil
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'docs'

def esc(x):return html.escape(str(x))

def page(title,body):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · GEMS84</title><link rel="stylesheet" href="style.css"></head><body><header><a class="brand" href="index.html">GEMS<span>84</span></a><nav><a href="index.html">Run overview</a><a href="executive-summary.html">Submission guide</a><a href="research.html">Research & evidence</a><a href="liti/index.html">Lane H84-A LITI</a></nav></header><main>{body}</main><footer>Evidence-first fault discovery · snapshot 2026-10-22 · no organizer submission made</footer></body></html>'''


def check_blocked_release(card, docs):
    """Reject stale binary downloads before rendering this negative-only site.

    Pages serves files whether or not a button links to them. A hash's mere
    presence is not a validator receipt and must never unlock a stale artifact.
    """
    if card.get('verdict') != 'negative':
        raise ValueError('This renderer supports negative runs only; selector release required')
    artifacts = [p for p in docs.rglob('*')
                 if p.is_file() and p.suffix.lower() in {'.tif', '.tiff', '.zip'}]
    if artifacts:
        raise ValueError('Blocked release contains downloadable artifacts: ' +
                         ', '.join(str(p.relative_to(docs)) for p in artifacts))


def main():
    card=json.loads((ROOT/'evidence/run-card.json').read_text())
    check_blocked_release(card, D)
    ev=D/'evidence';ev.mkdir(exist_ok=True)
    for p in (ROOT/'evidence').glob('*.json'):shutil.copy2(p,ev/p.name)
    shutil.copy2(ROOT/'registry/inventory.json',ev/'inventory.json')
    h=card.get('holdout_dti')
    scores=h.get('scores',{}) if h else {}
    result='Not evaluated — stopped by an earlier safety gate.'
    if scores:
        s=scores['rfd'];c=scores['step_control']
        result=f'''<div class="metrics"><article><small>HOLDOUT-DTI · exploratory candidate</small><strong>{s['dti']:.5f}</strong><p>95% CI [{s['ci95'][0]:.5f}, {s['ci95'][1]:.5f}]</p></article><article><small>HOLDOUT-DTI · paired step control</small><strong>{c['dti']:.5f}</strong><p>95% CI [{c['ci95'][0]:.5f}, {c['ci95'][1]:.5f}]</p></article><article><small>Withheld-positive pixels</small><strong>{s['withheld_positive_pixels']:,}</strong><p>{esc(h['evaluator_version'])}</p></article></div><p>Conditional spatial-block bootstrap; not a leaderboard interval. Chunk holdout is weaker than requested whole-fault validation. <a href="evidence/holdout.json">Read complete metric receipt →</a></p>'''
    downloads='<p><b>No submission TIFF released.</b> The safety gate stopped this candidate. No old submission has been substituted.</p>'
    blockers=''.join(f'<li>{esc(x)}</li>' for x in card['promotion_blockers'])
    body=f'''<p class="eyebrow">GEMSDOE84 / LANE H84-RFD</p><h1>Test the geology.<br>Release only the evidence.</h1><p class="lede">A distinct radiometric–terrain hypothesis, audited against the public submission registry. Built to reject weak ideas before they cost a competition slot.</p><section class="warning"><span class="badge">NEGATIVE · DO NOT SUBMIT</span><h2>Competition submission is blocked</h2>{downloads}<ul>{blockers}</ul><a href="executive-summary.html">Exactly how the submission gate works →</a></section><section><h2>What this run measured</h2>{result}</section><section class="grid"><article><p class="eyebrow">01 / MECHANISM</p><h2>Opposing radiometric flanks</h2><p>{esc(card['mechanism'])}. The signature may be a fault, or simply a lithologic/sedimentary boundary. It is not a direct geothermal-vent detection.</p></article><article><p class="eyebrow">02 / ORIGINALITY</p><h2>New construction, strict veto</h2><p>Built from cached physical layers, not a prior prediction TIFF. Full-footprint rank checks precede placement. Final dots stop on the first registry overlap violation, with no dense-raster exception.</p></article></section><section><h2>Auditable, not assumed</h2><div class="links"><a href="evidence/run-card.json" download>Download JSON run card ↓</a><a href="research.html">Hypotheses & source register →</a><a href="evidence/inventory.json">Pinned public registry →</a></div><p>No current leaderboard score or weekly submission cap was verified. No organizer-confirmed improvement is claimed.</p></section>'''
    (D/'index.html').write_text(page('Run overview',body))
    guide=f'''<p class="eyebrow">EXECUTIVE SUMMARY</p><h1>Can I submit this file?</h1><section class="warning"><span class="badge">NOT THIS RUN</span><h2>No promotion means no competition upload</h2>{downloads}<p>Automated checks have a final answer: <b>negative</b>. No human inspection is needed to determine the current release state. Outstanding upstream validation/protocol issues cannot be resolved by a visual inspection.</p></section><section><h2>Future eligible submission: exact sequence</h2><ol><li>The pipeline must recover whole buffered fault segments without leakage, beat the reproduced current best on identical holdout folds, and pass both registry phases.</li><li>The shared writer emits a single-band float32 TIFF and a ZIP containing only that TIFF. On-disk checks require finite [0,1] values, no NaN inside the footprint, zero outside, exact sample grid, and no mapped-fault positives.</li><li>A separate selector must approve promotion and check the current weekly cap on the authenticated submission page. This project has not verified that cap.</li><li>Only after those gates: download the specifically cleared TIFF (not a report, JSON, or research-only artifact).</li><li>Visit the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">official competition</a>, select New submission, choose the TIFF or verified one-TIFF ZIP, and paste the short note below.</li><li>Preserve the organizer receipt, exact file hash, score and timestamp as ORGANIZER-CONFIRMED evidence. Never relabel a projection or local DTI as a live score.</li></ol></section><section><h2>Reserved identity — not submitted</h2><dl><dt>Name</dt><dd><code>{esc(card['submission_name'])}</code></dd><dt>Short note</dt><dd><code>{esc(card['note'])}</code></dd></dl><p>The note is {len(card['note'])} characters. This identity is not a submission receipt.</p></section><section><h2>About the previous range error</h2><p>Its cause cannot be inferred without the rejected bytes. This writer rejects NaN, infinity and out-of-range values before writing; it validates the bytes again after writing. It does not silently clip or repair a prediction. A local format pass still does not prove organizer acceptance.</p><h2>Historical ZIP irregularity</h2><p>The archived H33 ZIP contains an empty .zip entry, not a TIFF. Do not submit that ZIP. <a href="evidence/h33-zip-inspection.json">Byte-inspection receipt</a>.</p></section>'''
    (D/'executive-summary.html').write_text(page('Submission guide',guide))
    research='<p class="eyebrow">RESEARCH NOTEBOOK</p><h1>Claims with a trail.</h1><p>Source authority and retrieval status are recorded separately. Links to blocked official hosts are manual-review pointers, not claims of successful verification.</p>'
    for name,title in [('result.md','Final negative result and next steps'),('hypotheses.md','Four preregistered hypotheses'),('h33-analysis.md','Why H33 might have improved'),('sources.md','Sources and limitations'),('review-passes.md','Three-pass review and unmet requirements')]:
        text=(D/'research'/name).read_text()
        research+=f'<section><h2>{title}</h2><p><a href="research/{name}">Open source note</a></p><pre>{esc(text)}</pre></section>'
    research+='<section><h2>Machine evidence</h2><ul>'+''.join(f'<li><a href="evidence/{p.name}">{esc(p.name)}</a></li>' for p in sorted(ev.glob('*.json')))+'</ul></section>'
    (D/'research.html').write_text(page('Research',research))
    (D/'.nojekyll').touch()

if __name__=='__main__':main()
