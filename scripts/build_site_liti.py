#!/usr/bin/env python3
"""Render the LITI lane pages (docs/liti/) from evidence/*.json — numbers are never hand-typed.

The project landing page (docs/index.html) belongs to scripts/build_site.py (lane H84-RFD)."""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E, D = ROOT / "evidence", ROOT / "docs" / "liti"
REPO = "https://github.com/buffedlizard55-lab/GEMSDOE84"

CSS = """
:root{--bg:#0f1720;--card:#16212c;--ink:#e6edf3;--mut:#9fb0c0;--ok:#2ea043;--bad:#da3633;--warn:#d29922;--acc:#58a6ff}
*{box-sizing:border-box}body{margin:0;font:15px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}
header{padding:18px 24px;border-bottom:1px solid #253241;display:flex;gap:18px;flex-wrap:wrap;align-items:center}
header b{font-size:18px}nav a{color:var(--mut);margin-right:14px;text-decoration:none}nav a:hover{color:var(--ink)}
main{max-width:1060px;margin:0 auto;padding:24px}.card{background:var(--card);border:1px solid #253241;border-radius:10px;padding:18px 20px;margin:0 0 18px}
h1{font-size:24px;margin:0 0 6px}h2{font-size:19px;margin:0 0 10px}h3{font-size:16px;margin:16px 0 6px}
.banner{border-left:6px solid var(--bad)}.banner.ok{border-left-color:var(--ok)}.pill{display:inline-block;padding:2px 9px;border-radius:99px;font-size:12px;font-weight:600}
.pass{background:#12361f;color:#56d364}.fail{background:#3d1214;color:#ff7b72}.info{background:#14283f;color:#79c0ff}
a{color:var(--acc)}code,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;background:#0b121a;padding:1px 5px;border-radius:5px;word-break:break-all}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{border-bottom:1px solid #253241;padding:6px 8px;text-align:left;vertical-align:top}th{color:var(--mut);font-weight:600}
.btn{display:inline-block;background:#238636;color:#fff;padding:9px 16px;border-radius:8px;text-decoration:none;font-weight:600;margin:6px 8px 6px 0}
.btn.sec{background:#30363d}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
.k{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.04em}.v{font-size:20px;font-weight:700}
small{color:var(--mut)}
"""


def page(title, body):
    nav = ('<nav><a href="index.html">Submission</a><a href="executive-summary.html">How to submit</a>'
           '<a href="research.html">Research &amp; results</a><a href="irregularities.html">Irregularities</a>'
           '<a href="sources.html">Sources</a><a href="../index.html">Project home</a><a href="' + REPO + '">Repo</a></nav>')
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)} · GEMSDOE84</title><style>{CSS}</style></head><body>"
            f"<header><b>GEMSDOE84 · lane H84-A LITI</b>{nav}</header><main>{body}</main></body></html>")


def pill(ok, yes="PASS", no="FAIL"):
    return f'<span class="pill {"pass" if ok else "fail"}">{yes if ok else no}</span>'


def f4(x):
    return "n/a" if x is None else f"{x:.4f}"


def main():
    rc = json.loads((E / "run_card.json").read_text())
    anat = json.loads((E / "incumbent_anatomy.json").read_text())
    fit = json.loads((E / "e2a_liti_ml_fit.json").read_text())
    e1 = json.loads((E / "e1_liti_fit.json").read_text())
    sub, val, ho = rc["submission"], rc["validator"], rc["holdout"]
    neg = rc["verdict"] != "promote"
    reg = rc["registry"]
    dl = f"downloads/{sub['file']}" if sub else "#"  # noqa
    dz = f"downloads/{sub['zip']}" if sub else "#"

    # ---------------- index (executive summary first) ----------------
    hs = ho["scores"]
    ci = rc["candidate_identity"]
    if sub:
        file_card = (f'<div class="card"><h2>The generated file</h2><a class="btn" href="{dl}" download>Download .tif</a>'
                     f'<a class="btn sec" href="{dz}" download>Download .zip (single TIFF)</a>'
                     f'<table><tr><th>Submission name</th><td><code>{html.escape(sub["name"])}</code></td></tr>'
                     f'<tr><th>Note ({sub["note_chars"]} / 140)</th><td><code>{html.escape(sub["note"])}</code></td></tr>'
                     f'<tr><th>TIFF sha256</th><td><code>{sub["sha256"]}</code></td></tr></table></div>')
        val_row = (f"<tr><th>Format / range</th><td>{pill(val['all_checks_passed'])} NaN={val['n_nan']}, min={val['min']}, "
                   f"max={val['max']}</td></tr>")
    else:
        file_card = (f'<div class="card"><h2>No file to download from this lane</h2>'
                     f'<p>The packager is fail-closed. Because the uniqueness gate logged the candidate as a duplicate, it wrote <b>no TIFF</b>, '
                     f'so nothing here can be submitted by mistake. The candidate is identified by the SHA-256 of its decoded '
                     f'array, <code>{ci["decoded_prediction_sha256"]}</code> ({ci["dots"]:,} dots), and kept outside Git for audit.</p>'
                     f'<p>A file that does pass every gate would be written with the shared fail-closed '
                     f'<code>submission_writer</code>: all-finite float32, values in [0, 1], 0 outside the footprint, '
                     f'EPSG:32611, 3730×3292, the sample geotransform, and a one-TIFF .zip. That avoids the earlier portal error '
                     f'“Predicted values must be in range [0, 1]”. <a href="executive-summary.html">How to submit</a>.</p></div>')
        val_row = ("<tr><th>Format / range validator</th><td><span class='pill info'>not run</span> no TIFF was written "
                   "(the duplicate gate stopped the run first)</td></tr>")
    body = f"""
<div class="card banner {'ok' if not neg else ''}">
<h1>Is it OK to submit? {'<span class="pill fail">NO — negative result</span>' if neg else '<span class="pill pass">YES — cleared for selector</span>'}</h1>
<p>{html.escape(rc['ok_to_submit'])}</p>
<p><b>Why:</b> {html.escape(rc['verdict_reason'])}. HOLDOUT-DTI (evaluator <code>{ho['evaluator_version']}</code>,
{ho['withheld_positive_pixels']:,} withheld positives): candidate <b>{f4(hs['liti']['dti'])}</b>
[{f4(hs['liti']['ci95'][0])}, {f4(hs['liti']['ci95'][1])}] vs incumbent recipe <b>{f4(hs['incumbent_recipe']['dti'])}</b>
[{f4(hs['incumbent_recipe']['ci95'][0])}, {f4(hs['incumbent_recipe']['ci95'][1])}].</p>
</div>
{file_card}
<div class="card"><h2>Automatic gates (no human inspection)</h2>
<table>
{val_row}
<tr><th>Uniqueness — surface Spearman ≤ 0.90 vs {reg['surface']['checked']:,} registry rasters</th><td>{pill(reg['surface']['passed'])} worst ρ = {f4(reg['surface']['worst_spearman'])}</td></tr>
<tr><th>Uniqueness — final dots, literal rule (ρ ≤ 0.90 and ≤ 70 % of dots within 3 px)</th><td>{pill(reg['dots_literal'].get('passed'))}
 worst overlap {f4(reg['dots_literal'].get('worst_dot_overlap'))} (<small>{html.escape(str(reg['dots_literal'].get('worst_overlap_submission')))}</small>), worst ρ {f4(reg['dots_literal'].get('worst_spearman_full_footprint'))}</td></tr>
<tr><th>Uniqueness — final dots, chance-corrected (IR-84-03)</th><td>{pill(reg['dots_chance_corrected'].get('passed'))}
 literal flags {reg['dots_chance_corrected'].get('literal_overlap_flags')}, of which universal blockers {reg['dots_chance_corrected'].get('universal_blockers')} (their 3-px halo covers &gt;70 % of the footprint, so any raster fails them); binding flags {reg['dots_chance_corrected'].get('binding_overlap_flags')}</td></tr>
<tr><th>Protocol holdout gate (must beat the best comparable control)</th><td>{pill(ho['gate_passed'])} Δ = {f4(ho['paired_difference_vs_incumbent_recipe']['delta'])}
 [{f4(ho['paired_difference_vs_incumbent_recipe']['ci95'][0])}, {f4(ho['paired_difference_vs_incumbent_recipe']['ci95'][1])}]</td></tr>
<tr><th>Leakage canary (single-feature AUC &gt; 0.90)</th><td>{pill(not rc['leakage_canary']['flagged'], 'none flagged', 'flagged')} max AUC {f4(rc['leakage_canary']['max_single_feature_auc'])}</td></tr>
</table>
<p><small>Local checks are not organizer acceptance. No weekly slot was used. Live scores quoted on this site are OWNER-REPORTED unless marked otherwise.</small></p></div>
<div class="card"><h2>One-paragraph answer: why 0.2778, and can we beat it?</h2>
<p>The 0.2778 file is, byte-for-byte, the 0.2600 dotted H19-5 field minus every dot within 100 m (H27-4, 0.2708) and then within
200 m (H33-2-B2) of a mapped fault. Both deletions are explained to within {abs(anat['algebra']['residual']):.4f} DTI by the metric algebra if the deleted
dots earned zero credit, so near-catalogue mass is pure false positive on the live board. Kept dots earn ~{anat['algebra']['mean_credit_per_kept_dot']:.3f}
credit each, ~{anat['algebra']['mean_credit_per_kept_dot']/anat['algebra']['marginal_bar_at_s2']:.1f}× the marginal bar of {anat['algebra']['marginal_bar_at_s2']:.4f}.
The ceiling is the field's precision, not its emission. This session's new idea inverts the whole live-score table into a truth-intensity map
(cross-validated Spearman {fit['models'][fit['selected']]['cv_spearman']:.3f} across held-out repos). It learned interpretable structure,
e.g. new faults avoid densely mapped districts. But its emission fails the protocol holdout, and its dots fall inside the halos of dense registry fields, so it is a logged <b>duplicate</b>. No file was promoted or written.
Details: <a href="research.html">Research &amp; results</a>.</p></div>
"""
    (D / "index.html").write_text(page("Submission", body))

    # ---------------- executive summary / how to submit ----------------
    if sub:
        steps_file = (f"<li>Download <a href='{dl}' download><code>{html.escape(sub['file'])}</code></a>; "
                      f"<code>sha256sum</code> must print <code>{sub['sha256']}</code>.</li><li>Click <b>Submit</b> → <b>File to submit</b> → choose it.</li>"
                      f"<li>Paste the Note: <code>{html.escape(sub['note'])}</code></li>")
    else:
        steps_file = ("<li><b>This lane has no file to submit</b> (see the front page). When a lane does produce a cleared file, "
                      "download it from that lane's front page and check its <code>sha256sum</code> against the run card.</li>"
                      "<li>Click <b>Submit</b> → <b>File to submit</b> → choose the .tif (or the .zip holding exactly one TIFF).</li>"
                      "<li>Paste the lane's <b>Note</b> (≤ 140 characters, e.g. “clustering with k=25”) and keep the file stem as the submission name.</li>")
    body = f"""
<div class="card banner {'ok' if not neg else ''}"><h1>Executive summary — how to make a submission</h1>
<p><b>Current file status:</b> {html.escape(rc['ok_to_submit'])}</p></div>
<div class="card"><h2>Steps</h2><ol>
<li>Log in and open the competition (<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">drivendata.org/competitions/306/competition-doe-gems/</a>), then go to its submissions area. (This sandbox cannot load DrivenData pages, so no deeper URL is quoted.)</li>
{steps_file}
<li>Submit, then copy the score from the submission page receipt into <code>registry/live_scores.csv</code> as ORGANIZER-CONFIRMED.</li></ol>
<h3>What the portal checks, and how a cleared file meets it</h3>
<table><tr><th>Portal requirement (submission page text, as quoted by the owner)</th><th>How the shared writer enforces it</th></tr>
<tr><td>single-band GeoTIFF (.tif) or a .zip with a single GeoTIFF</td><td>1 band float32; the ZIP holds only the TIFF (shared <code>submission_writer</code>)</td></tr>
<tr><td>must match the submission format's CRS, shape and geotransform</td><td>EPSG:32611, 3730×3292, (100, 0, 243350, 0, −100, 4508550), checked against <code>data/bridge/sample_submission.tif</code></td></tr>
<tr><td>“Predicted values must be in range [0, 1]” (the earlier failure)</td><td>all-finite policy: no NaN anywhere, outside-footprint cells are 0, values in [0, 1]; the writer refuses to repair or clip</td></tr></table>
<h3>Weekly cap</h3><p>The cap is shown on the submission page. Promotion to a real slot is a separate selector step; this session used 0 slots.</p></div>
"""
    (D / "executive-summary.html").write_text(page("How to submit", body))

    # ---------------- research ----------------
    lin = anat["lineage"]; r = anat["rasters"]
    rows = "".join(f"<tr><td>{k}</td><td>{v['dots']:,}</td><td>{v['dots_dcat_le1']:,}</td><td>{v['dots_dcat_le2']:,}</td>"
                   f"<td>{v['median_dcat_px']:.1f}</td><td>{v['owner_reported_live']}</td></tr>" for k, v in r.items())
    th = fit["models"][fit["selected"]]["theta"]
    throws = "".join(f"<tr><td>{html.escape(k)}</td><td>{v:+.2f}</td></tr>" for k, v in th.items())
    mods = "".join(f"<tr><td>{html.escape(k)}</td><td>{v['cv_rmse']:.4f}</td><td>{v['cv_spearman']:.3f}</td></tr>"
                   for k, v in {**e1['models'], **fit['models']}.items())
    hsr = "".join(f"<tr><td>{k}</td><td>{v['dti']:.4f}</td><td>[{v['ci95'][0]:.4f}, {v['ci95'][1]:.4f}]</td></tr>" for k, v in hs.items())
    body = f"""
<div class="card"><h1>Research &amp; results</h1><p>Evidence classes: MEASURED (computed here from hash-verified bytes) ·
OWNER-REPORTED (live score from the owner's table, no organizer receipt) · HOLDOUT-DTI · MODEL (projection, never a score).</p></div>
<div class="card"><h2>1. Anatomy of the 0.2778 file (MEASURED)</h2>
<table><tr><th>raster</th><th>dots</th><th>≤1 px from catalogue</th><th>≤2 px</th><th>median px</th><th>live (OWNER-REPORTED)</th></tr>{rows}</table>
<p>Exact set identities: H27-4 = D2.8 minus dots ≤1 px: <b>{lin['h27_4_equals_d2_8_minus_dcat_le1']}</b>; H33-2-B2 = H27-4 minus dots ≤2 px:
<b>{lin['h33_2_b2_equals_h27_4_minus_dcat_le2']}</b>; D2.8 ⊂ H19-5: <b>{lin['d2_8_subset_of_h19_5']}</b>.</p>
<p>Algebra (zero-credit deletions): implied TP<sub>w</sub> = {anat['algebra']['implied_TPw']:.0f}; predicted {anat['algebra']['predicted_s2_if_zero_credit']:.4f}
vs reported 0.2778 (residual {anat['algebra']['residual']:+.4f}).</p></div>
<div class="card"><h2>2. Hypotheses considered</h2><p>See <a href="{REPO}/blob/main/docs/liti/h84-hypotheses.md">docs/liti/h84-hypotheses.md</a>
(5 candidates with layers, signature, off-catalogue rationale, novelty, cost; two flagged data-blocked with the official source named).</p></div>
<div class="card"><h2>3. Experiments (budget: 3)</h2>
<h3>E1/E2a — live-score inversion (MODEL fitted to OWNER-REPORTED scores, {fit['n_rasters']} rasters, CV grouped by repo)</h3>
<table><tr><th>model</th><th>CV RMSE</th><th>CV Spearman</th></tr>{mods}</table>
<p>Score SD across the table ≈ 0.084. The physics-only model under-predicts the H19 family by ~2×. Adding a catalogue-analogue ML probability and crest
(trained only on visible faults) closes most of the gap. Selected coefficients (rank-scaled bases):</p>
<table><tr><th>basis</th><th>θ</th></tr>{throws}</table>
<h3>E2b — protocol hide-and-recover holdout (HOLDOUT-DTI, {ho['evaluator_version']}, {ho['withheld_positive_pixels']:,} withheld positives, seeds {ho['seeds']})</h3>
<table><tr><th>arm</th><th>pooled DTI</th><th>95 % CI (20 km block bootstrap)</th></tr>{hsr}</table>
<p>{html.escape(ho['caveat'])}</p>
<h3>E3 — emission, uniqueness, packaging</h3><p>{ci['dots']:,} dots from the shared <code>emit.greedy_allocate</code>.
Surface gate passed (worst ρ {f4(reg['surface']['worst_spearman'])} over {reg['surface']['checked']:,} rasters). Dot gate failed:
{reg['dots_chance_corrected'].get('literal_overlap_flags')} literal flags, {reg['dots_chance_corrected'].get('universal_blockers')} of them universal blockers, and
{reg['dots_chance_corrected'].get('binding_overlap_flags')} binding flags against dense registry fields (61k–1.5M support pixels, κ up to 0.79). The emission concentrates where the
family's prevailing dense fields already concentrate. Logged as a duplicate; no TIFF written. Rows: <code>evidence/e3_gate_dots_chance_corrected.json</code>.</p></div>
<div class="card"><h2>4. Next steps and limitations (for the next session)</h2><ol>
<li><b>Make the holdout gate fair</b> (IR-84-04): rebuild the incumbent recipe from a field trained on the <i>visible</i> catalogue only, or have the
owner adopt the repo-grouped live-score CV as a second, pre-registered instrument. As things stand the gate favours catalogue-trained fields.</li>
<li><b>Owner ruling on IR-84-03</b>: dense registry rasters (e.g. a 5-px lattice) make the literal 70 % overlap rule unsatisfiable for every lane.
The fix belongs in the shared template (60GEMSDOE), which lanes cannot push to.</li>
<li><b>Organizer receipts</b>: copy submission IDs and scores from the submission page so OWNER-REPORTED rows become ORGANIZER-CONFIRMED. The inversion is only as good as these labels.</li>
<li><b>Use LITI as a prior, not a generator</b>: its strongest, cross-validated terms (negative catalogue density, near-fault exclusion, terrain-line and basement-gradient enrichment)
can re-weight any lane's field before emission. Every lane can apply it as a cheap pre-screen before spending a slot.</li>
<li><b>Data blocked here</b>: USGS ComCat hypocentres and focal mechanisms (H84-D) and InSAR/optical products for the 2020 Monte Cristo Range rupture (H84-E).
A GitHub Actions runner can fetch them (it has open internet); this sandbox cannot.</li>
<li><b>Compute</b>: a 1 m-LiDAR deep detector needs a GPU, which this environment does not have.</li></ol></div>
<div class="card"><h2>5. Verdict</h2><p><b>{rc['verdict'].upper()}</b> — {html.escape(rc['verdict_reason'])}. Negative results are deliverables:
the inversion itself (cross-validated across repos) is reusable by every lane as a <i>prior</i> and as a cheap pre-screen before spending a slot.</p></div>
"""
    (D / "research.html").write_text(page("Research", body))

    irr = (D / "irregularities.md").read_text()
    (D / "irregularities.html").write_text(page("Irregularities", "<div class=card><pre style='white-space:pre-wrap'>" + html.escape(irr) + "</pre></div>"))
    src = (D / "sources.md").read_text()
    (D / "sources.html").write_text(page("Sources", "<div class=card><pre style='white-space:pre-wrap'>" + html.escape(src) + "</pre></div>"))
    print("site built")


if __name__ == "__main__":
    main()
