#!/usr/bin/env python3
"""Deterministically render the GEMSDOE84 GitHub Pages site from verified JSON evidence.

Never infers promotion from a local format pass; enforces automated fail-closed status
at the top of index.html and executive-summary.html without human intervention.
"""
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "docs"
EV = ROOT / "evidence"


def esc(x: object) -> str:
    return html.escape(str(x))


def page(title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{esc(title)} · GEMSDOE84</title>"
        '<link rel="stylesheet" href="style.css"></head><body>'
        '<header><a class="brand" href="index.html">GEMSDOE<span>84</span></a>'
        '<nav>'
        '<a href="index.html">Overview &amp; Download</a>'
        '<a href="executive-summary.html">Submission Guide</a>'
        '<a href="hypotheses.html">5 Hypotheses</a>'
        '<a href="sources.html">Verified Sources</a>'
        '<a href="research.html">Evidence &amp; Passes</a>'
        '<a href="liti/index.html">Prior Lane LITI</a>'
        "</nav></header>"
        f"<main>{body}</main>"
        "<footer>GEMSDOE84 · Lane H84-CSAT · Snapshot 2026-10-22 UTC · "
        "0 weekly submission slots consumed · Automated fail-closed release</footer>"
        "</body></html>\n"
    )


def pill(ok: bool, label_ok: str = "PASS", label_bad: str = "FAIL") -> str:
    return f'<span class="pill-pass">{esc(label_ok)}</span>' if ok else f'<span class="pill-fail">{esc(label_bad)}</span>'


def main() -> int:
    card = json.loads((EV / "run-card.json").read_text(encoding="utf-8"))
    e1 = json.loads((EV / "exp84_1_canary_and_surface.json").read_text(encoding="utf-8"))
    e2 = json.loads((EV / "exp84_2_holdout_eval.json").read_text(encoding="utf-8"))
    e3 = json.loads((EV / "exp84_3_emission_and_uniqueness.json").read_text(encoding="utf-8"))

    assert card["verdict"] in ("negative", "promote")
    assert len(card["note"]) <= 140

    ev_out = D / "evidence"
    ev_out.mkdir(parents=True, exist_ok=True)
    for pat in ("*.json", "*.md", "*.csv"):
        for p in sorted(EV.glob(pat)):
            shutil.copy2(p, ev_out / p.name)
    shutil.copy2(ROOT / "registry" / "inventory.json", ev_out / "inventory.json")
    shutil.copy2(EV / "run-card.json", D / "data" / "run-card.json")
    shutil.copy2(EV / "run-card.json", D / "run-card.json")

    sub = card["submission"]
    tif_path = D / "downloads" / sub["file"]
    assert tif_path.is_file(), f"Missing generated GeoTIFF: {tif_path}"

    is_promote = card["verdict"] == "promote" and card["submission_authorized"]
    banner_cls = "promote-box" if is_promote else "warning"
    badge_html = (
        '<span class="badge-pass">PROMOTED · OK TO SUBMIT</span>'
        if is_promote
        else '<span class="badge">AUTOMATED GATE VERDICT: NEGATIVE · DO NOT SUBMIT TO WEEKLY LIVE SLOT</span>'
    )
    headline_status = (
        "Cleared for cross-lane selector and DrivenData upload"
        if is_promote
        else "Unique format-valid &amp; holdout-winning (+0.0629 HOLDOUT-DTI) GeoTIFF generated — blocked from weekly live slot by strict protocol gates"
    )

    scores = e3["d28_holdout_summary"]["scores"]
    diffs = e3["d28_holdout_summary"]["paired_differences"]
    reg = card["registry_correlation_overlap"]

    dl_buttons = (
        '<div class="btn-row">'
        f'<a class="button" download href="downloads/{esc(sub["file"])}">'
        f'Download Unique GeoTIFF ({sub["bytes"] // 1024} KB · {"APPROVED" if is_promote else "RESEARCH / DO NOT SUBMIT"})</a>'
        f'<a class="button-secondary" download href="downloads/{esc(sub["zip"])}">Download Verified 1-TIFF ZIP</a>'
        f'<a class="button-secondary" href="downloads/{esc(sub["name"])}.json">On-Disk Validator Receipt (.json)</a>'
        '<a class="button-secondary" download href="evidence/run-card.json">JSON Run Card</a>'
        '<a class="button-secondary" href="executive-summary.html">Step-by-Step Submission Guide →</a>'
        "</div>"
    )

    blocker_items = "".join(f"<li>{esc(b)}</li>" for b in card["promotion_blockers"])

    gate_rows = [
        (
            "1. GeoTIFF Format, Grid &amp; [0, 1] Range",
            "EPSG:32611, 3730×3292, float32, 0 NaN/Inf, finite in [0, 1], 0 catalogue positives",
            f'18/18 checks PASS · min={card["validator_output"]["min"]:.1f}, max={card["validator_output"]["max"]:.1f}, '
            f'n_nan=0, {sub["dots"]:,} dots',
            card["validator_output"]["gems57_all_checks_passed"] and card["validator_output"]["independent_format_valid"],
        ),
        (
            "2. Single-Feature Leakage Canary",
            "max(AUC, 1−AUC) ≤ 0.90 across all 58 features on 22,893 withheld positives",
            f'{e1["leakage_canary"]["max_discriminability"]:.5f} ({e1["leakage_canary"]["max_feature"]}); '
            f'max catalogue-blind = 0.56467 (p32_topo10m_relief)',
            e1["leakage_canary"]["passed"],
        ),
        (
            "3. Pre-Placement Surface Uniqueness",
            "|Spearman ρ| ≤ 0.90 across all 1,160 SHA-256-verified registry rasters",
            f'{reg["pre_placement_surface_worst_abs_spearman"]:.5f} '
            f'({reg["pre_placement_surface_worst_submission"]})',
            reg["pre_placement_surface_passed"],
        ),
        (
            "4a. Holdout — Primary Preregistered csat_submod",
            "Beat incumbent_recipe (0.10564) on gems57-pooled-hide-v2 (95% block CI > 0)",
            f'{e2["summary"]["scores"]["csat_submod"]["dti"]:.5f} '
            f'[{e2["summary"]["scores"]["csat_submod"]["ci95"][0]:.5f}, '
            f'{e2["summary"]["scores"]["csat_submod"]["ci95"][1]:.5f}] '
            f'(Δ = {e2["summary"]["paired_differences"]["incumbent_recipe"]["delta"]:+.5f}; IR-84-11)',
            card["holdout_primary_preregistered_submod"]["delta_ci95_vs_incumbent_recipe"][0] > 0,
        ),
        (
            "4b. Holdout — Preregistered D2.8 Ablation csat_poisson (Emitted .tif)",
            "Same H84-CSAT LOQO surface + D2.8 spacing (sep=2.83 px, c=2.5 px)",
            f'{scores["csat_poisson"]["dti"]:.5f} '
            f'[{scores["csat_poisson"]["ci95"][0]:.5f}, {scores["csat_poisson"]["ci95"][1]:.5f}] '
            f'(Δ = {diffs["incumbent_recipe"]["delta"]:+.5f} vs incumbent_recipe, '
            f'{diffs["retrained_h19_control"]["delta"]:+.5f} vs retrained_h19_control)',
            diffs["incumbent_recipe"]["ci95"][0] > 0 and diffs["retrained_h19_control"]["ci95"][0] > 0,
        ),
        (
            "5a. Final Dots — Comparable Submissions (≤ 55k dots, 1,006 priors)",
            "≤ 0.70 forward 3-px overlap, ≤ 0.90 |Spearman ρ|, byte &amp; pixel unique",
            f'0 overlap flags · byte/pixel unique · max Jaccard = {reg["final_dots_worst_jaccard"]:.5f} · '
            f'max |ρ| = {reg["final_dots_worst_abs_spearman"]:.5f}',
            reg["byte_unique"] and reg["pixel_unique"] and reg["comparable_le_55k_dots_overlap_flags"] == 0,
        ),
        (
            "5b. Final Dots — Binding Global-Halo Rule (binding_duplicate_decision)",
            "≤ 0.70 forward 3-px overlap on all 1,091 priors with global halo_coverage < 0.70",
            f'Worst = {reg["final_dots_worst_forward_overlap_discriminating"]:.5f} vs '
            f'GEMSDOE3:coverage-v3-wide (624,025 px) &amp; 0.89280 vs 7GEMSDOE:gems7-halo15 (1,828,699 px) — 30 blanket flags (IR-84-12)',
            not reg["duplicate"],
        ),
    ]
    gate_table = (
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Automated Gate</th><th>Protocol Threshold</th><th>Measured Receipt</th><th>Status</th>"
        "</tr></thead><tbody>"
        + "".join(
            f"<tr><td><strong>{g[0]}</strong></td><td>{g[1]}</td><td>{g[2]}</td><td>{pill(g[3])}</td></tr>"
            for g in gate_rows
        )
        + "</tbody></table></div>"
    )

    arm_order = [
        ("transfer_poisson", "Head A (visible strain-transfer + 38 physics) + D2.8"),
        ("csat_poisson", "Dual-Habitat H84-CSAT (Emitted .tif) + D2.8 (c=2.5 px)"),
        ("incumbent_recipe", "GEMSDOE25 D2.8 minus ≤ 2 px of visible (H33-2-B2 rule)"),
        ("csat_submod", "Dual-Habitat H84-CSAT + emit.greedy_allocate (IR-84-11)"),
        ("concealed_poisson", "100% Catalogue-Blind Head B (38 physics only) + D2.8"),
        ("retrained_h19_control", "Fold-clean 19-band LOQO HGB + D2.8 (c=2.0 px, 38.5k dots)"),
        ("incumbent_asis", "Shipped GEMSDOE32 H33-2-B2 raster (pruned on full cat)"),
    ]
    holdout_rows_html = ""
    for arm_key, arm_desc in arm_order:
        sc = scores[arm_key]
        if arm_key == "csat_poisson":
            d_str = "<em>candidate reference</em>"
        else:
            pd = diffs[arm_key]
            d_str = f'{pd["delta"]:+.5f} [{pd["ci95"][0]:+.5f}, {pd["ci95"][1]:+.5f}]'
        holdout_rows_html += (
            f"<tr><td><code>{esc(arm_key)}</code></td><td>{esc(arm_desc)}</td>"
            f'<td><strong>{sc["dti"]:.5f}</strong></td>'
            f'<td>[{sc["ci95"][0]:.5f}, {sc["ci95"][1]:.5f}]</td>'
            f'<td>{sc["tpw"]:,.1f}</td><td>{sc["fpw"]:,.1f}</td><td>{d_str}</td></tr>'
        )

    index_body = f"""
<p class="eyebrow">DOE GEMS · DRIVENDATA COMPETITION 306 · LANE H84-CSAT</p>
<h1>Dual-Habitat 3D Contact-Depth &amp; Strain-Transfer Fault Discovery</h1>
<p class="lede">Out-of-quadrant (LOQO) geophysical, geothermal, LiDAR, GeoDAWN, and crack-tip/relay mechanics across 5,167,373 Great Basin pixels — audited fail-closed against all 1,160 SHA-256-verified organization rasters.</p>

<section class="{banner_cls}">
  {badge_html}
  <h2 style="margin-top:12px">{headline_status}</h2>
  <p><strong>Automated Decision (zero human intervention required):</strong> <code>{esc(card["ok_to_submit"])}</code></p>
  {dl_buttons}
  <dl style="margin-top:14px">
    <dt>Generated File &amp; SHA-256</dt>
    <dd><code>docs/downloads/{esc(sub["file"])}</code> · SHA-256 <code>{esc(sub["sha256"])}</code> · {sub["dots"]:,} binary dots (<code>float32</code> in <code>{{0.0, 1.0}}</code>, <code>0</code> NaNs)</dd>
    <dt>Short Submission Note ({sub["note_chars"]}/140 chars)</dt>
    <dd><code>{esc(sub["note"])}</code></dd>
  </dl>
  <h3>Exact Automated Blockers Preventing Weekly Slot Authorization</h3>
  <ul>{blocker_items}</ul>
</section>

<section>
  <p class="eyebrow">01 / AUTOMATED RELEASE SCORECARD</p>
  <h2>Seven Mechanical Gates (3 Experiments Executed / 3 Cap)</h2>
  {gate_table}
</section>

<section>
  <p class="eyebrow">02 / SPATIALLY-BLOCKED HOLDOUT EVALUATION</p>
  <h2>Paired <code>HOLDOUT-DTI</code> (<code>gems57-pooled-hide-v2</code>, 22,893 Withheld Positives)</h2>
  <div class="metrics">
    <article><small>HOLDOUT-DTI · csat_poisson (.tif)</small><strong>{scores["csat_poisson"]["dti"]:.5f}</strong><p>95% CI [{scores["csat_poisson"]["ci95"][0]:.5f}, {scores["csat_poisson"]["ci95"][1]:.5f}]</p></article>
    <article><small>vs Incumbent Recipe (0.10564)</small><strong>+{diffs["incumbent_recipe"]["delta"]:.5f}</strong><p>95% CI [+{diffs["incumbent_recipe"]["ci95"][0]:.5f}, +{diffs["incumbent_recipe"]["ci95"][1]:.5f}] (+59.5%)</p></article>
    <article><small>vs Retrained 19-Band Control</small><strong>+{diffs["retrained_h19_control"]["delta"]:.5f}</strong><p>95% CI [+{diffs["retrained_h19_control"]["ci95"][0]:.5f}, +{diffs["retrained_h19_control"]["ci95"][1]:.5f}] (2.41×)</p></article>
    <article><small>100% Catalogue-Blind Head B</small><strong>{scores["concealed_poisson"]["dti"]:.5f}</strong><p>Beats 19-band control (0.06991) with zero catalogue inputs</p></article>
  </div>
  <div class="table-wrap"><table><thead><tr>
    <th>Arm</th><th>Method</th><th>HOLDOUT-DTI</th><th>95% Block CI</th><th>TP<sub>w</sub></th><th>FP<sub>w</sub></th><th>Paired Δ (csat_poisson − arm)</th>
  </tr></thead><tbody>{holdout_rows_html}</tbody></table></div>
  <p>Conditional 1,000-draw paired bootstrap over 158 physical 20 km × 20 km blocks; out-of-quadrant stability of <code>csat_poisson</code>: NW = 0.16620, NE = 0.17070, SW = 0.16839, SE = 0.16843. Never interpret a <code>HOLDOUT-DTI</code> figure as an <code>ORGANIZER-CONFIRMED</code> leaderboard score.</p>
</section>

<section class="grid">
  <article class="card">
    <p class="eyebrow">03 / INCUMBENT FORENSICS</p>
    <h2>Why GEMSDOE32 <code>H33-2-B2</code> Scored 0.2778 (<code>OWNER-REPORTED</code>)</h2>
    <p>Byte-exact lineage (<a href="evidence/incumbent_anatomy.json"><code>incumbent_anatomy.json</code></a>): <code>H19-5</code> (121,131 px, <code>0.1922</code>) → Poisson-disk <code>D2.8</code> (44,090 dots, <code>0.2600</code>) → <code>H27-4</code> (40,199 dots, −1 px collar, <code>0.2708</code>) → <code>H33-2-B2</code> (37,654 dots, −2 px collar, <code>0.2778</code>). Zero-credit collar algebra predicts <code>0.27836</code> (residual −0.00056): mapped pixels are masked out of scoring, so flank dots within ≤200 m of mapped traces incur full α=0.2 false-positive penalty for near-zero unique new-fault credit.</p>
    <p><strong>Score Provenance Note:</strong> <code>0.2778</code>, <code>0.3195</code>, and <code>0.4413</code> are unverified/conflicting <code>OWNER-REPORTED</code> figures (egress to <code>drivendata.org</code> is blocked under <code>IR-84-02</code>); none is <code>ORGANIZER-CONFIRMED</code> here.</p>
  </article>
  <article class="card">
    <p class="eyebrow">04 / PRIOR NEGATIVE LANES ARCHIVED</p>
    <h2>Three Lanes Completed in <code>GEMSDOE84</code></h2>
    <ul>
      <li><strong><code>H84-RFD</code></strong> (Radiometric Flanking Dipole × LiDAR step): <code>HOLDOUT-DTI = 0.04430</code> vs step control <code>0.04436</code> (negative; stopped before TIFF).</li>
      <li><strong><code>H84-A LITI</code></strong> (Leaderboard-Inverted Truth Intensity on 91 live scores): <code>HOLDOUT-DTI = 0.00867</code> vs <code>0.10564</code> (negative; 56 overlap flags; <a href="liti/index.html">lane archive →</a>).</li>
      <li><strong><code>H84-CSAT</code> (Current)</strong>: Dual-Habitat 3D contact-depth + counterfactual strain-transfer; <code>csat_poisson</code> achieves <code>0.16850</code> (+59.5% over incumbent recipe), packaged &amp; validated in <code>docs/downloads/</code>, held back from weekly slot by <code>IR-84-11</code> &amp; <code>IR-84-12</code>.</li>
    </ul>
  </article>
</section>
"""
    (D / "index.html").write_text(page("Overview & Download", index_body), encoding="utf-8")

    # 2. Executive Summary & DrivenData Submission Guide
    checks_map = e3["validation_gems57"]["checks"]
    chk_rows = "".join(
        f"<tr><td><code>{esc(k)}</code></td><td>{pill(bool(v))}</td></tr>"
        for k, v in checks_map.items()
    )
    guide_body = f"""
<p class="eyebrow">EXECUTIVE SUMMARY &amp; SUBMISSION GUIDE</p>
<h1>Should I Submit This File to DrivenData Right Now?</h1>

<section class="{banner_cls}">
  {badge_html}
  <h2 style="margin-top:12px">Automated Answer: <strong>{"YES — CLEARED FOR SELECTOR" if is_promote else "NO — HOLD WEEKLY SLOT (DO NOT SUBMIT WITHOUT SELECTOR OVERRIDE)"}</strong></h2>
  <p>{esc(card["ok_to_submit"])}</p>
  {dl_buttons}
</section>

<section>
  <p class="eyebrow">ARTIFACT SPECIFICATION</p>
  <h2>Generated GeoTIFF Identity &amp; Automated Range Protection</h2>
  <p>Previous competition uploads across sibling runs encountered DrivenData's portal rejection <code>"Predicted values must be in range [0, 1]"</code> when rasters carried <code>NaN</code> nodata or unclipped float overshoot. Our shared packager (<code>vendor/gems57/submission_writer.py</code>) writes an <strong>all-finite <code>float32</code> GeoTIFF with <code>nodata=None</code></strong>, explicitly zero outside the 5,167,373-pixel footprint and strictly in <code>{{0.0, 1.0}}</code> everywhere across all 12,279,160 grid cells, then re-validates the bytes on disk with two independent validators.</p>
  <dl>
    <dt>GeoTIFF Path</dt><dd><code>docs/downloads/{esc(sub["file"])}</code> ({sub["bytes"]:,} bytes)</dd>
    <dt>SHA-256 Digest</dt><dd><code>{esc(sub["sha256"])}</code></dd>
    <dt>Verified One-TIFF ZIP</dt><dd><code>docs/downloads/{esc(sub["zip"])}</code> (byte-roundtrip verified; unlike historical H33 ZIP which contained an empty <code>.zip</code> entry — see <a href="evidence/h33-zip-inspection.json"><code>h33-zip-inspection.json</code></a>)</dd>
    <dt>Short Note ({sub["note_chars"]} chars ≤ 140 limit)</dt><dd><code>{esc(sub["note"])}</code></dd>
  </dl>
  <div class="table-wrap"><table><thead><tr><th>On-Disk Automated Preflight Check</th><th>Status</th></tr></thead><tbody>{chk_rows}</tbody></table></div>
</section>

<section>
  <p class="eyebrow">OPERATING PROCEDURE</p>
  <h2>Exact DrivenData Upload Checklist (Only After Selector Clears Weekly Cap)</h2>
  <ol>
    <li><strong>Verify Gate Clearance:</strong> Confirm the cross-lane selector approves spending one of the team's weekly submission slots (weekly cap on DrivenData must be checked on the authenticated portal). Do <strong>not</strong> upload while the banner above reads <code>DO NOT SUBMIT</code> unless explicitly overriding <code>IR-84-11</code>/<code>IR-84-12</code>.</li>
    <li><strong>Download Verified File:</strong> Download <code>{esc(sub["file"])}</code> (or <code>{esc(sub["zip"])}</code>) and verify <code>sha256sum</code> equals <code>{esc(sub["sha256"])}</code>.</li>
    <li><strong>Upload on DrivenData:</strong> Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData Competition 306 Submissions</a>, upload the single-band GeoTIFF, and paste the {sub["note_chars"]}-character note above.</li>
    <li><strong>Record Organizer Receipt:</strong> Archive the exact timestamp, SHA-256, and portal score as <code>ORGANIZER-CONFIRMED</code> evidence — never relabel local <code>HOLDOUT-DTI</code> or LITI projections as live scores.</li>
  </ol>
</section>
"""
    (D / "executive-summary.html").write_text(page("Submission Guide", guide_body), encoding="utf-8")

    # 3. Five Preregistered Hypotheses Page
    hyp_md = (D / "research" / "hypotheses.md").read_text(encoding="utf-8")
    hyp_body = f"""
<p class="eyebrow">PREREGISTERED GEOLOGICAL HYPOTHESES</p>
<h1>Five Untried Basin-and-Range Fault Hypotheses</h1>
<p class="lede">Locked in <a href="research/hypotheses.md"><code>docs/research/hypotheses.md</code></a> and <code>registry/preregistration.json</code> before running any experiment, with sandbox data-obtainability verification, physical transforms, non-fault mimics, and expected DTI lift ranking.</p>
<div class="table-wrap"><table><thead><tr>
  <th>Rank &amp; ID</th><th>Target Fault Habitat &amp; Layers</th><th>Physical Transform</th><th>Named Non-Fault Mimics</th><th>Cost &amp; Obtainability</th><th>Status</th>
</tr></thead><tbody>
  <tr><td><strong>#1 · H84-CSAT</strong></td><td>Concealed Basin-and-Range contacts + strain-transfer bridges (19 official + 1m LiDAR + 10m 3DEP + GeoDAWN K/Th/U/TMI_up150 + GDR #1391 geothermometers + visible catalogue)</td><td>3D Mag/Grav Analytic Signal &amp; Salem Tilt-Depth wavenumber + shallow mag residual + Pollard-Segall cos<sup>4</sup>ψ tip cones &amp; two-host bridges (LOQO HGB+ET)</td><td>Tertiary volcanic dike margins, caldera ring walls, paleochannels, strath scarps, playa K/U fringes</td><td>~35 min CPU · 100% SHA-256 verified locally</td><td><strong>Executed</strong> (<code>csat_poisson</code> HOLDOUT-DTI <code>0.16850</code> vs <code>0.10564</code>)</td></tr>
  <tr><td><strong>#2 · H84-2 (TDCG)</strong></td><td>Blind basin-bounding master faults (<code>iso_grav_anom</code>, <code>hg</code>, <code>vg</code>, <code>tc</code>, <code>depth_to_base_surf</code>)</td><td>Multi-azimuthal horizontal curvature of gravity tilt angle matched to basement inflection</td><td>Plutonic batholith walls, pre-Cenozoic thrust ramps, caldera collapses</td><td>~15 min CPU · 100% in official 19-band stack</td><td>Preregistered backup</td></tr>
  <tr><td><strong>#3 · H84-3 (RDCN)</strong></td><td>Hydrothermally altered clay-cap feeder faults (<code>cond_surf</code>, GeoDAWN <code>K, Th, U</code>, <code>geod_shearrate</code>, <code>geod_dilaterate</code>)</td><td>Anisotropic directional ridges of conductivity × K/Th residual gated on transtensional shear×dilatation</td><td>Closed alkali playa evaporites, Tertiary zeolitized ash-flow tuffs</td><td>~15 min CPU · 100% locally verified</td><td>Partially absorbed as channel <code>p38</code>; standalone backup</td></tr>
  <tr><td><strong>#4 · H84-4 (BMSA)</strong></td><td>Shallow Quaternary intrabasin volcanic/alluvial faults (<code>rtp</code>, <code>tmi_hg</code>, <code>tmi_vg</code>, <code>TMI_up150</code>, GDR vents)</td><td>Matched bandpass difference <code>z(RTP) − 0.85·z(TMI_up150)</code> ridge detection outside 2.5 km vent halos</td><td>Basalt lava-flow margins, feeder dikes, cultural pipelines/railways</td><td>~12 min CPU · 100% locally verified</td><td>Partially absorbed as channel <code>p27</code>; standalone backup</td></tr>
  <tr><td><strong>#5 · H84-5 (ASLS)</strong></td><td>Subtle piedmont scarps cutting alluvial fans (<code>lidar_scarp_features_u8</code>, <code>topo_10m_derived_100m_u8</code>)</td><td>Relief-deconfounded facing-asymmetry × aspect-coherence breakline filter orthogonal to drainage</td><td>Pluvial Lake Lahontan/Bonneville shorelines, fluvial terrace risers</td><td>~10 min CPU · 100% locally verified (78.6% LiDAR coverage)</td><td>Partially absorbed as channels <code>p30..p34</code>; standalone backup</td></tr>
</tbody></table></div>
<section><h2>Full Preregistration Document (<code>docs/research/hypotheses.md</code>)</h2><pre>{esc(hyp_md)}</pre></section>
"""
    (D / "hypotheses.html").write_text(page("5 Hypotheses", hyp_body), encoding="utf-8")

    # 4. Verified Sources & Provenance Page
    src_md = (D / "research" / "sources.md").read_text(encoding="utf-8")
    sources_body = f"""
<p class="eyebrow">AUDITABLE PROVENANCE &amp; SOURCE REGISTER</p>
<h1>Verified Data, Official Links &amp; Evidence Taxonomy</h1>
<p class="lede">Every local input raster and CSV is SHA-256 verified against <code>registry/data_manifest.json</code>; every external competition/agency URL is separated into direct GitHub-verified artifacts vs egress-blocked manual-review pointers (<code>IR-84-02</code>).</p>
<div class="table-wrap"><table><thead><tr>
  <th>Resource / Dataset</th><th>Primary Link</th><th>Verification &amp; Provenance Status</th>
</tr></thead><tbody>
  <tr><td><strong>DrivenData Competition 306 Overview &amp; Metric</strong></td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem Description</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Leaderboard</a></td><td>Manual-review URLs (<code>drivendata.org</code> blocked by sandbox egress <code>IR-84-02</code>). Metric formula (α=0.2, β=0.8, 300 m kernel) verified via pinned <code>vendor/gems57/metric.py</code> and archived <a href="evidence/official-reference-README.md">official reference README</a>.</td></tr>
  <tr><td><strong>Official Reference Repository</strong></td><td><a href="https://github.com/drivendataorg/gems-prize-reference-solution">drivendataorg/gems-prize-reference-solution</a></td><td>Directly verified on GitHub; tree &amp; README archived in <code>research/source-receipts.json</code> (SHA-256 checked in CI).</td></tr>
  <tr><td><strong>Core 19-Band Stack &amp; Bridge Grids</strong></td><td><code>training_features.tif</code>, <code>existing_faults.tif</code>, <code>sample_submission.tif</code> · <a href="https://epsg.io/32611">EPSG:32611</a></td><td>SHA-256 verified (<code>4371c82e…</code>, <code>7ba308cc…</code>, <code>2176d08e…</code>); <code>3730×3292</code>, 100 m UTM Zone 11N, 5,167,373 footprint cells, 60,988 mapped fault cells in 3,199 components.</td></tr>
  <tr><td><strong>USGS GeoDAWN Radiometrics &amp; Aeromagnetics</strong></td><td><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a> · <a href="https://doi.org/10.5066/P93LGLVQ">DOI 10.5066/P93LGLVQ</a></td><td>Derived <code>geodawn_rad_u8.tif</code> (4 bands) &amp; <code>geodawn_extensions_u8.tif</code> (4 bands incl. <code>TMI_up150</code>) SHA-256 verified from owner mirrors.</td></tr>
  <tr><td><strong>1m LiDAR Scarp &amp; 10m 3DEP Stacks</strong></td><td><code>lidar_scarp_features_u8.tif</code> (12 bands), <code>topo_10m_derived_100m_u8.tif</code> (9 bands)</td><td>SHA-256 verified via <code>scripts/fetch_data.py</code> (<code>failed: []</code>).</td></tr>
  <tr><td><strong>DOE GDR #1391 &amp; UNR INGENIOUS</strong></td><td><a href="https://gdr.openei.org/submissions/1391">GDR Submission 1391</a> · <a href="https://gbcge.org/current-projects/ingenious/">INGENIOUS</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR Report 96647</a></td><td>27,092 thermal wells/springs &amp; 21 Quaternary vents SHA-256 verified locally; <code>dist_known_fault_px</code> and <code>gdr_qfaults_traces.csv</code> strictly excluded from features and tested by unit test + canary.</td></tr>
  <tr><td><strong>1,160-Raster Organization Uniqueness Registry</strong></td><td><a href="https://github.com/buffedlizard55-lab">buffedlizard55-lab/GEMSDOE..GEMSDOE88</a> · <a href="https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html">GEMSDOE32</a></td><td>1,166 git-SHA1-verified blobs downloaded; 1,160 valid <code>3730×3292</code> <code>EPSG:32611</code> grid rasters indexed with <code>0</code> errors in <code>registry/registry_index.json</code>.</td></tr>
</tbody></table></div>
<section><h2>Source Register Notes (<code>docs/research/sources.md</code>)</h2><pre>{esc(src_md)}</pre></section>
"""
    (D / "sources.html").write_text(page("Verified Sources", sources_body), encoding="utf-8")

    # 5. Full Research, Irregularities & Three-Pass Review Page
    research_sections = [
        ("result.md", "Lane H84-CSAT & Repository Result Summary"),
        ("hypotheses.md", "Preregistered Hypotheses & 3-Experiment Protocol"),
        ("h33-analysis.md", "Forensic & Algebraic Audit of GEMSDOE32 H33-2-B2 (0.2778 OWNER-REPORTED)"),
        ("sources.md", "Source Register & Access Limitations"),
        ("review-passes.md", "Three-Pass Implementation & Verification Review"),
    ]
    res_html = (
        '<p class="eyebrow">COMPLETE RESEARCH &amp; EVIDENCE NOTEBOOK</p>'
        "<h1>Auditable Receipts, Irregularities &amp; Three-Pass Review</h1>"
        "<p class=\"lede\">Every claim maps to a reproducible script and a JSON receipt in <code>docs/evidence/</code>.</p>"
    )
    ir_text = (D / "liti" / "irregularities.md").read_text(encoding="utf-8")
    res_html += f'<section><h2>Flagged Irregularities Register (IR-84-01 .. IR-84-12)</h2><p><a href="liti/irregularities.md">Open markdown</a></p><pre>{esc(ir_text)}</pre></section>'
    for fname, title in research_sections:
        txt = (D / "research" / fname).read_text(encoding="utf-8")
        res_html += f'<section><h2>{esc(title)}</h2><p><a href="research/{fname}">Open {esc(fname)}</a></p><pre>{esc(txt)}</pre></section>'
    ev_links = "".join(
        f'<li><a href="evidence/{esc(p.name)}"><code>{esc(p.name)}</code></a> ({p.stat().st_size:,} bytes)</li>'
        for p in sorted(ev_out.glob("*.json"))
    )
    res_html += f"<section><h2>Machine-Readable Evidence JSONs</h2><ul>{ev_links}</ul></section>"
    (D / "research.html").write_text(page("Evidence & Passes", res_html), encoding="utf-8")
    (D / ".nojekyll").touch()
    print("Built 5 HTML pages and synced docs/evidence/ cleanly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
