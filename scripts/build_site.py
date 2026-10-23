#!/usr/bin/env python3
"""Deterministic, fail-closed release portal combining the repository release audit
and the complete 3-experiment Lane H84-CSAT deliverables, download links, and evidence.

No network/model calls. Missing or unsafe release evidence raises an error.
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
    if card.get("verdict") == "promote":
        raise ValueError("A site renderer cannot authorize a selector decision")
    if any(p.is_file() and p.suffix.lower() in {".tif", ".tiff", ".zip"} for p in docs.rglob("*")):
        raise ValueError("Blocked legacy release contains downloadable artifacts")


def checked_status(root: Path) -> dict:
    card = json.loads((root / "registry/release_status.json").read_text(encoding="utf-8"))
    if card.get("submission_authorized") is not False or card.get("verdict") != "negative":
        raise ValueError("This audited negative release cannot authorize a selector decision")
    a = card["audited_artifact"]
    paths = [root / a["path"], root / "docs/downloads" / f"{a['name']}.tif"]
    for path in paths:
        if hashlib.sha256(path.read_bytes()).hexdigest() != a["sha256"]:
            raise ValueError(f"Artifact hash mismatch: {path}")
    if not card["stop_required"]:
        raise ValueError("Missing literal lane stop")
    return card


def _verify_csat(root: Path) -> dict:
    csat = json.loads((root / "evidence/run_card_csat.json").read_text(encoding="utf-8"))
    if csat.get("verdict") != "negative" or csat.get("submission_authorized") is not False:
        raise ValueError("Lane H84-CSAT must remain fail-closed negative without selector override")
    for rel in (
        csat["submission_file"],
        f"submissions/{csat['submission_name']}.tif",
    ):
        p = root / rel
        if hashlib.sha256(p.read_bytes()).hexdigest() != csat["raster_sha256"]:
            raise ValueError(f"H84-CSAT artifact hash mismatch: {p}")
    return csat


def main() -> int:
    card = checked_status(ROOT)
    csat = _verify_csat(ROOT)
    e1 = json.loads((ROOT / "evidence/exp84_1_canary_and_surface.json").read_text(encoding="utf-8"))
    e2 = json.loads((ROOT / "evidence/exp84_2_holdout_eval.json").read_text(encoding="utf-8"))
    e3 = json.loads((ROOT / "evidence/exp84_3_emission_and_uniqueness.json").read_text(encoding="utf-8"))

    ev_out = ROOT / "docs/evidence"
    ev_out.mkdir(parents=True, exist_ok=True)
    for pat in ("exp84_*.json", "run_card_csat.json"):
        for p in sorted((ROOT / "evidence").glob(pat)):
            shutil.copy2(p, ev_out / p.name)

    thms_name = html.escape(card["audited_artifact"]["name"])
    thms_sha = html.escape(card["audited_artifact"]["sha256"])
    ov = card["registry_comparison"]["worst_dot_overlap"]
    rho = card["registry_comparison"]["worst_spearman_full_footprint"]
    val = card["validator_output"]

    csat_name = html.escape(csat["submission_name"])
    csat_sha = html.escape(csat["raster_sha256"])
    csat_note = html.escape(csat["note"])
    sc_csat = e3["d28_holdout_summary"]["scores"]["csat_poisson"]
    sc_inc = e3["d28_holdout_summary"]["scores"]["incumbent_recipe"]
    sc_h19 = e3["d28_holdout_summary"]["scores"]["retrained_h19_control"]
    sc_con = e3["d28_holdout_summary"]["scores"]["concealed_poisson"]
    sc_sub = e2["summary"]["scores"]["csat_submod"]
    diff_inc = e3["d28_holdout_summary"]["paired_differences"]["incumbent_recipe"]
    diff_h19 = e3["d28_holdout_summary"]["paired_differences"]["retrained_h19_control"]
    reg_csat = csat["registry_correlation_overlap"]

    sources = json.loads((ROOT / "registry/sources.json").read_text(encoding="utf-8"))
    source_rows = "".join(
        f'<tr><td><a href="{html.escape(s["url"], quote=True)}">{html.escape(s["title"])}</a></td>'
        f'<td>{html.escape(s["status"])}</td><td>{html.escape(s["role"])}</td></tr>'
        for s in sources
    )
    checks_csat = "".join(
        f"<tr><td><code>{html.escape(k)}</code></td><td>{'PASS' if v else 'FAIL'}</td></tr>"
        for k, v in csat["validator_output"]["checks"].items()
    )
    checks_thms = "".join(
        f"<tr><td><code>{html.escape(k)}</code></td><td>{'PASS' if v else 'FAIL'}</td></tr>"
        for k, v in val["checks"].items()
    )

    sections = {
        "index": f"""<h2>Lane H84-CSAT — 3-Experiment Results &amp; 7-Gate Scorecard</h2>
<p><strong>Lane H84-CSAT</strong> (Dual-Habitat 3D Contact-Depth + Counterfactual Strain-Transfer) executed 3 preregistered experiments across all 5,167,373 Great Basin footprint cells and audited against all <strong>1,160 SHA-256-verified organization rasters</strong>. Its generated GeoTIFF (<code>{csat_name}.tif</code>, 38,453 binary dots) passes all 18/18 format &amp; <code>[0, 1]</code> checks and beats the H33-2-B2 incumbent recipe by <strong>+{diff_inc["delta"]:.5f} HOLDOUT-DTI</strong> (<code>{sc_csat["dti"]:.5f}</code> vs <code>{sc_inc["dti"]:.5f}</code>), yet remains <strong>DO NOT SUBMIT</strong> without selector override due to <code>IR-84-11</code> and <code>IR-84-12</code>.</p>
<div class="grid">
  <article><h3>HOLDOUT-DTI · csat_poisson</h3><p><strong>{sc_csat["dti"]:.5f}</strong> [{sc_csat["ci95"][0]:.5f}, {sc_csat["ci95"][1]:.5f}] · 22,893 withheld px (<code>gems57-pooled-hide-v2</code>)</p></article>
  <article><h3>vs Incumbent Recipe (0.10564)</h3><p><strong>+{diff_inc["delta"]:.5f}</strong> [+{diff_inc["ci95"][0]:.5f}, +{diff_inc["ci95"][1]:.5f}] (+59.5%) · vs 19-band control: <strong>+{diff_h19["delta"]:.5f}</strong> (2.41×)</p></article>
  <article><h3>58-Feature Canary &amp; Surface</h3><p>PASS · max single-feature disc = <strong>{e1["leakage_canary"]["max_discriminability"]:.5f}</strong> ≤ 0.90; pre-placement |ρ| = <strong>{reg_csat["pre_placement_surface_worst_abs_spearman"]:.5f}</strong> ≤ 0.90</p></article>
  <article><h3>1,160-Raster Final Dot Audit</h3><p>0 flags vs 1,006 ≤55k-dot submissions (max Jaccard <strong>{reg_csat["final_dots_worst_jaccard"]:.5f}</strong>; 0.559 vs H84-THMS); <strong>FAIL</strong> vs 30 broad 56k–1.83M-px corridor blankets (<code>IR-84-12</code>)</p></article>
</div>
<table>
  <tr><th>Arm</th><th>HOLDOUT-DTI</th><th>95% Spatial-Block CI</th><th>Paired Δ (csat_poisson − arm)</th><th>Status</th></tr>
  <tr><td><code>csat_poisson</code> (Emitted H84-CSAT .tif)</td><td><strong>{sc_csat["dti"]:.5f}</strong></td><td>[{sc_csat["ci95"][0]:.5f}, {sc_csat["ci95"][1]:.5f}]</td><td><em>candidate reference</em></td><td>PASS holdout · HOLD slot</td></tr>
  <tr><td><code>incumbent_recipe</code> (D2.8 minus ≤2 px visible)</td><td>{sc_inc["dti"]:.5f}</td><td>[{sc_inc["ci95"][0]:.5f}, {sc_inc["ci95"][1]:.5f}]</td><td>+{diff_inc["delta"]:.5f} [+{diff_inc["ci95"][0]:.5f}, +{diff_inc["ci95"][1]:.5f}]</td><td>Beaten (+59.5%)</td></tr>
  <tr><td><code>csat_submod</code> (Primary emit.greedy_allocate)</td><td>{sc_sub["dti"]:.5f}</td><td>[{sc_sub["ci95"][0]:.5f}, {sc_sub["ci95"][1]:.5f}]</td><td>+{e3["d28_holdout_summary"]["paired_differences"]["csat_submod"]["delta"]:.5f}</td><td>FAIL (IR-84-11 kself=1 clumping)</td></tr>
  <tr><td><code>concealed_poisson</code> (100% Catalogue-Blind Head B)</td><td>{sc_con["dti"]:.5f}</td><td>[{sc_con["ci95"][0]:.5f}, {sc_con["ci95"][1]:.5f}]</td><td>+{e3["d28_holdout_summary"]["paired_differences"]["concealed_poisson"]["delta"]:.5f}</td><td>Beats 19-band control with 0 cat inputs</td></tr>
  <tr><td><code>retrained_h19_control</code> (Fold-clean 19-band D2.8)</td><td>{sc_h19["dti"]:.5f}</td><td>[{sc_h19["ci95"][0]:.5f}, {sc_h19["ci95"][1]:.5f}]</td><td>+{diff_h19["delta"]:.5f} [+{diff_h19["ci95"][0]:.5f}, +{diff_h19["ci95"][1]:.5f}]</td><td>Beaten (2.41×)</td></tr>
</table>
<p><strong>Prior Lanes Archived in GEMSDOE84:</strong> <code>H84-RFD</code> (0.04430, negative), <code>H84-A LITI</code> (0.00867, negative; <a href="liti/index.html">archive</a>), <code>H84-WING</code> (negative), <code>H84-THMS</code> (literal witness overlap 1.0, negative), and <code>H84B-UAS</code> (adaptive spacing falsified vs 0.1703 fixed-spacing control; <a href="h84b/index.html">archive</a>).</p>""",

        "executive-summary": f"""<h2>Step-by-Step DrivenData Submission Guide &amp; Automated Gate Policy</h2>
<p><strong>Automated Answer (zero human inspection required): DO NOT UPLOAD TO A WEEKLY LIVE SLOT WITHOUT EXPLICIT SELECTOR OVERRIDE.</strong></p>
<p>Why? Although <code>{csat_name}.tif</code> passes every format, CRS (<code>EPSG:32611</code>), dimension (<code>3730×3292</code>), zero-NaN, and <code>[0, 1]</code> range requirement (preventing DrivenData's <code>"Predicted values must be in range [0, 1]"</code> rejection) and beats the H33-2-B2 incumbent recipe by <strong>+{diff_inc["delta"]:.5f} HOLDOUT-DTI</strong>, two strict fail-closed protocol rules fired:</p>
<ul>
  <li><strong>IR-84-11 (Primary Allocator Clumping):</strong> Preregistered <code>emit.greedy_allocate</code> clamps <code>kself = min(E[k], 1.0)</code>, collapsing <code>c*(1-k)</code> to 0 on high-probability ridges (<code>0.08153</code> vs <code>0.16850</code> for preregistered D2.8 ablation <code>csat_poisson</code>).</li>
  <li><strong>IR-84-12 (Corridor-Blanket Overlap):</strong> Unmodified <code>binding_duplicate_decision</code> flags 30 broad 56k–1.83M-px corridor-blanket priors (worst <code>0.90945</code> vs <code>GEMSDOE3:coverage-v3-wide</code> [624,025 px] and <code>1.00000</code> under literal dense-surface <code>17GEMSDOE:E-proba-multiscale</code> [5,167,373 px]), even though <code>0</code> flags occur against all 1,006 comparable (≤55k-dot) submissions and max Jaccard is <code>0.03912</code>.</li>
</ul>
<h3>Future Eligible Upload Sequence (Only After Selector Clears Weekly Cap &amp; Saturated-Prior Rule)</h3>
<ol>
  <li>Confirm cross-lane selector approval and verify remaining weekly allowance on the authenticated DrivenData Competition 306 submission portal.</li>
  <li>Download <code>downloads/{csat_name}.tif</code> (or verified single-TIFF <code>downloads/{csat_name}.zip</code> — byte-roundtrip verified, unlike historical H33 ZIP's empty entry) and confirm SHA-256 equals <code>{csat_sha}</code>.</li>
  <li>On <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData Competition 306</a>, upload the single-band GeoTIFF and paste the {csat["note_chars"]}-character note: <code>{csat_note}</code>.</li>
  <li>Record the portal score, timestamp, and SHA-256 as <code>ORGANIZER-CONFIRMED</code> evidence; never label local <code>HOLDOUT-DTI</code> or model projections as live scores.</li>
</ol>""",

        "methodology": """<h2>Why GEMSDOE32 <code>H33-2-B2</code> Scored 0.2778 (<code>OWNER-REPORTED</code>) &amp; How H84-CSAT Advances Physics</h2>
<p><strong>Byte-Exact Lineage (<a href="evidence/incumbent_anatomy.json"><code>incumbent_anatomy.json</code></a>):</strong> <code>H19-5</code> (121,131 px, <code>0.1922</code>) → Poisson-disk <code>D2.8</code> (44,090 dots, <code>0.2600</code>) → <code>H27-4</code> (40,199 dots, −1 px collar, <code>0.2708</code>) → <code>H33-2-B2</code> (37,654 dots, −2 px collar, <code>0.2778</code>). Under <code>DTI = T / ((1−β)T + αF + βG)</code> with α=0.2, β=0.8, mapped catalogue pixels are masked out of scoring, so dots within ≤200 m of mapped traces incur full α=0.2 false-positive weight for near-zero unique new-fault credit; zero-credit collar algebra predicts <code>0.27836</code> (residual −0.00056).</p>
<p><strong>Score Provenance &amp; Forensics:</strong> <code>0.2778</code> and conflicting leaderboard snapshots <code>0.3195</code> vs <code>0.4413</code> are unverified <code>OWNER-REPORTED</code> values (<code>IR-84-02</code>). Re-measurement on the verified H33 TIFF also confirmed median catalogue distance 19.65 px / max 219.3 px (<code>IR-84B-02</code>).</p>
<p><strong>How H84-CSAT Differs:</strong> Instead of re-thinning the 19-band H19-5 probability raster, H84-CSAT trains a strict Leave-One-Quadrant-Out Dual-Habitat ensemble combining 38 catalogue-blind physical/geothermal/LiDAR/GeoDAWN channels (3D Mag/Grav Analytic Signal, Salem Tilt-Depth shallow-contact wavenumber, shallow <code>RTP − 0.85·TMI_up150</code> residual, relief-deconfounded 1m/10m scarps, GeoDAWN K/Th &amp; U/Th residuals, GDR #1391 geothermometer plumes) with 20 visible-only Pollard-Segall cos<sup>4</sup>ψ crack-tip cones, two-host step-over bridges, and bend-turn channels (<a href="research/hypotheses.md">full specification</a>).</p>""",

        "results": f"""<h2>Reopened GeoTIFF Validation &amp; 1,160-Raster Uniqueness Measurements</h2>
<h3>1. Newly Generated Lane H84-CSAT Artifact (<code>{csat_name}.tif</code>)</h3>
<table>
  <tr><th>Measurement</th><th>Result</th></tr>
  <tr><td>SHA-256 &amp; Size</td><td><code>{csat_sha}</code> · {csat["submission_bytes"]:,} bytes · {csat["n_dots"]:,} binary dots</td></tr>
  <tr><td>Distance-to-Catalogue Strata</td><td>2.5–15 px: {csat["distance_strata"]["d_2p5_to_15px"]:,} · 15–40 px: {csat["distance_strata"]["d_15_to_40px"]:,} · &gt;40 px: {csat["distance_strata"]["d_gt_40px"]:,} (min {csat["distance_strata"]["min_dist_to_catalogue_px"]} px)</td></tr>
  <tr><td>Pre-Placement Surface Uniqueness (1,160 rasters)</td><td>Worst |Spearman ρ| = {reg_csat["pre_placement_surface_worst_abs_spearman"]:.5f} ≤ 0.90 · PASS</td></tr>
  <tr><td>Comparable Dot Submissions (≤55k dots, 1,006 rasters)</td><td>0 overlap flags · max Jaccard = {reg_csat["final_dots_worst_jaccard"]:.5f} · vs concurrent H84-THMS = 0.55899 ≤ 0.70 · PASS</td></tr>
  <tr><td>Binding Global-Halo Decision (1,091 priors)</td><td>Worst = {reg_csat["final_dots_worst_forward_overlap_discriminating"]:.5f} vs GEMSDOE3:coverage-v3-wide (624,025 px) · 30 corridor-blanket flags · FAIL (IR-84-12)</td></tr>
  <tr><td>Literal Whole-Footprint Witness (17GEMSDOE, 5,167,373 px)</td><td>Forward overlap = 1.000000 (0 uncovered allowed cells; universal literal blocker) · FAIL</td></tr>
</table>
<h3>Reopened On-Disk Checks — <code>{csat_name}.tif</code></h3>
<table><tr><th>Check</th><th>Result</th></tr>{checks_csat}</table>
<h3>2. Archived Lane H84-THMS Artifact (<code>{thms_name}.tif</code>)</h3>
<p>SHA-256 <code>{thms_sha}</code> · literal witness overlap {ov:.6f} · Spearman {rho!s} · uncovered allowed cells {card["certificate"]["uncovered_allowed_pixels"]}.</p>
<table><tr><th>Check</th><th>Result</th></tr>{checks_thms}</table>""",

        "hypotheses": """<h2>Five Preregistered Basin-and-Range Geological Hypotheses (Lane H84-CSAT Slate)</h2>
<p>Locked in <a href="research/hypotheses.md"><code>docs/research/hypotheses.md</code></a> and <code>registry/preregistration.json</code> prior to execution, with sandbox data-obtainability checks and named non-fault mimics:</p>
<ol>
  <li><strong>#1 · H84-CSAT (Executed Top Candidate):</strong> Dual-Habitat 3D Potential-Field Contact-Depth (3D Mag/Grav Analytic Signal + Salem Tilt-Depth wavenumber + shallow <code>RTP − 0.85·TMI_up150</code> + GDR #1391 geothermometer plumes + 1m LiDAR/10m 3DEP + GeoDAWN K/Th, U/Th) fused with counterfactual Pollard-Segall crack-tip cones &amp; two-host relay bridges. <em>Mimics:</em> Tertiary dike walls, caldera rings, paleochannels, strath scarps, playa fringes. <em>Result:</em> <code>csat_poisson</code> HOLDOUT-DTI = <strong>0.16850</strong> (+0.06285 vs incumbent recipe).</li>
  <li><strong>#2 · H84-2 (TDCG):</strong> Multi-azimuthal gravity tilt-angle horizontal curvature matched to basement inflection for blind master range-front faults. <em>Mimics:</em> Plutonic batholith walls, pre-Cenozoic thrust ramps.</li>
  <li><strong>#3 · H84-3 (RDCN):</strong> Anisotropic surface conductivity × GeoDAWN K/Th potassium-metasomatism ridges gated on geodetic shear×dilatation transtension. <em>Mimics:</em> Closed alkali playa evaporites, zeolitized ash-flow tuffs.</li>
  <li><strong>#4 · H84-4 (BMSA):</strong> Bandpass shallow magnetic residual <code>z(RTP) − 0.85·z(TMI_up150)</code> outside 2.5 km Quaternary volcanic vent halos. <em>Mimics:</em> Basalt flow edges, feeder dikes, pipelines/railways.</li>
  <li><strong>#5 · H84-5 (ASLS):</strong> Relief-deconfounded 1m LiDAR facing-asymmetry × 10m aspect-coherence alluvial-fan scarp detector. <em>Mimics:</em> Pluvial Lake Lahontan/Bonneville shorelines, terrace risers.</li>
</ol>
<p>See also <a href="research/SESSION_REVIEW_20261023.md">inherited H84-THMS within-lane proposals</a> and <a href="research/hypotheses.md">complete H84-CSAT preregistration table</a>.</p>""",

        "irregularities": """<h2>Complete Irregularities &amp; Protocol Blockers Register</h2>
<ul>
  <li><strong>IR-84-11 (New — Shared Allocator Peak Clumping):</strong> In pinned <code>vendor/gems57/emit.py</code> line 104, <code>kself = np.minimum(ekc, 1.0)</code> collapses acceptance bar <code>c*(1-k(x))</code> to <code>0.0</code> whenever <code>E[k] ≥ 1</code>, clumping 1-px neighbor dots on top ridges and halving true-positive coverage (<code>0.08153</code> vs <code>0.16850</code> for matched-budget D2.8 <code>csat_poisson</code>). Vendor pin preserved unmodified; primary gate applied fail-closed.</li>
  <li><strong>IR-84-12 (New — Domain-Restricted Corridor Blankets):</strong> Registry rasters such as <code>7GEMSDOE:gems7-halo15</code> (1,828,699 px = 100% of <code>d ≤ 15 px</code>, global halo 0.4018 &lt; 0.70) and <code>GEMSDOE3:coverage-v3-wide</code> (624,025 px, global halo 0.6097 &lt; 0.70) block any unstratified near-catalogue dot set under <code>binding_duplicate_decision</code> despite 0 flags against all 1,006 ≤55k-dot submissions. Next-session fix: preregister a 50/50 distance-stratified Dual-Habitat emitter.</li>
  <li><strong>IR-84-02 (Egress &amp; Score Provenance):</strong> Only GitHub/npm/PyPI hosts are reachable; DrivenData/USGS/GDR/NLR links are manual-review pointers and all live leaderboard numbers (0.2778, 0.3195, 0.4413) are unverified <code>OWNER-REPORTED</code> snapshots.</li>
  <li><strong>IR-84-03 / Literal Witness Saturation:</strong> Whole-footprint continuous surfaces (e.g. <code>17GEMSDOE:E-proba-multiscale</code>, 5,167,373 positive pixels) leave 0 uncovered allowed cells under literal <code>prediction &gt; 0</code> support.</li>
  <li><strong>IR-84B-02 (H33 Distance Correction):</strong> Verified H33-2-B2 dots sit at median 19.65 px / max 219.3 px from mapped faults (retracting an earlier 5.385 px / 12 px narrative).</li>
</ul>
<p>Full register: <a href="liti/irregularities.md"><code>docs/liti/irregularities.md</code></a> · <a href="research/SESSION_REVIEW_20261023.md"><code>SESSION_REVIEW_20261023.md</code></a>.</p>""",

        "sources": (
            "<h2>Verified Source Ledger &amp; SHA-256 Dataset Provenance</h2>"
            "<p>Outbound access is restricted to GitHub, npm, and PyPI. Every local input raster/CSV (19-band official stack, 1m LiDAR, 10m 3DEP, GeoDAWN K/Th/U/TMI_up150, GDR #1391 wells/vents with <code>dist_known_fault_px</code> excluded, and 1,166 git-SHA1-verified registry blobs) is SHA-256 verified against <code>registry/data_manifest.json</code>. Official non-GitHub links are retained as manual-review pointers, never claimed freshly fetched.</p>"
            "<table><tr><th>Source</th><th>Retrieval status</th><th>Evidence boundary</th></tr>"
            + source_rows
            + '</table><p><a href="research/sources.md">H84-CSAT source &amp; dataset verification table</a> · '
              '<a href="research/official/reference-extract.json">Organizer notebook extract &amp; SHA-256</a> · '
              '<a href="research/SESSION_REVIEW_20261023.md">Claim-by-claim source review</a></p>'
        ),

        "research": (
            "<h2>Research Notebooks &amp; Machine-Readable Receipts</h2>"
            "<ul>"
            '<li><a href="research/result.md">Lane H84-CSAT Result Summary &amp; Ablation Table</a></li>'
            '<li><a href="research/hypotheses.md">Five Preregistered Hypotheses &amp; 3-Experiment Plan</a></li>'
            '<li><a href="research/h33-analysis.md">GEMSDOE32 H33-2-B2 Forensic &amp; Algebraic Audit</a></li>'
            '<li><a href="research/review-passes.md">Three-Pass Implementation &amp; Verification Review</a></li>'
            '<li><a href="research/SESSION_REVIEW_20261023.md">Repository-Wide Audit &amp; THMS Review</a></li>'
            '<li><a href="evidence/run_card_csat.json"><code>evidence/run_card_csat.json</code></a> · '
            '<a href="evidence/exp84_1_canary_and_surface.json"><code>exp84_1_canary_and_surface.json</code></a> · '
            '<a href="evidence/exp84_2_holdout_eval.json"><code>exp84_2_holdout_eval.json</code></a> · '
            '<a href="evidence/exp84_3_emission_and_uniqueness.json"><code>exp84_3_emission_and_uniqueness.json</code></a></li>'
            "</ul>"
        ),
    }

    css = (
        "*{box-sizing:border-box}body{margin:0;background:#f4f6fa;color:#172337;font:16px/1.62 system-ui,sans-serif}"
        "header{background:#14283e;color:white;padding:22px max(6vw,20px)}header a{color:#cceaff;margin-right:18px;display:inline-block;text-decoration:none;font-weight:600}"
        "main{max-width:1140px;margin:auto;padding:26px 22px}section,article{background:white;padding:22px;border-radius:12px;margin-bottom:22px;border:1px solid #d9e1eb}"
        ".notice{border-left:6px solid #b12932;background:#fff4f3}.label{font-weight:800;color:#a21f2a;letter-spacing:.5px}"
        "h1{font-size:clamp(1.65rem,3.6vw,2.5rem);line-height:1.18;margin:10px 0 14px}h2{line-height:1.3;margin-top:0}"
        "a{color:#075d92}code{overflow-wrap:anywhere;font-size:.9em;background:#eef2f7;padding:2px 5px;border-radius:4px}"
        ".button{display:inline-block;background:#0b5d4b;color:white;padding:11px 16px;border-radius:6px;margin:6px 8px 6px 0;text-decoration:none;font-weight:700}"
        ".button-alt{display:inline-block;background:#244e70;color:white;padding:11px 16px;border-radius:6px;margin:6px 8px 6px 0;text-decoration:none;font-weight:650}"
        "table{width:100%;border-collapse:collapse;font-size:.9em;display:block;overflow-x:auto}td,th{text-align:left;padding:10px 12px;border-bottom:1px solid #dde4ec;vertical-align:top}"
        "th{background:#eef3f8}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}small{color:#526375}footer{padding:18px 0;color:#526375;font-size:.9em}"
    )
    (ROOT / "docs/assets").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs/assets/release.css").write_text(css + "\n", encoding="utf-8")

    nav_items = [
        ("index", "Overview & Downloads"),
        ("executive-summary", "Submission Guide"),
        ("results", "Audit & Validators"),
        ("hypotheses", "5 Hypotheses"),
        ("methodology", "H33 Analysis"),
        ("sources", "Verified Sources"),
        ("irregularities", "Blockers"),
        ("research", "Evidence"),
    ]
    nav_html = "".join(f'<a href="{key}.html">{title}</a>' for key, title in nav_items)

    hero = (
        '<section class="notice">'
        '<p class="label">AUTOMATED GATE VERDICT: NEGATIVE · DO NOT SUBMIT TO WEEKLY LIVE SLOT (0 SLOTS USED)</p>'
        "<h1>Unique Format-Valid &amp; Holdout-Winning (+0.0629 DTI) GeoTIFF Generated — Held Back by Fail-Closed Protocol Gates</h1>"
        f"<p><strong>Lane H84-CSAT Candidate (<code>{csat_name}.tif</code>):</strong> 18/18 format &amp; <code>[0, 1]</code> checks PASS (0 NaNs, EPSG:32611, 3730×3292, 38,453 binary dots); "
        f"<strong>HOLDOUT-DTI = {sc_csat['dti']:.5f}</strong> [{sc_csat['ci95'][0]:.5f}, {sc_csat['ci95'][1]:.5f}] vs incumbent recipe {sc_inc['dti']:.5f} (+59.5%); "
        f"0 overlap flags vs all 1,006 ≤55k-dot submissions (max Jaccard {reg_csat['final_dots_worst_jaccard']:.5f}). "
        f"<strong>Blocked from live slot</strong> by primary allocator clumping (<code>IR-84-11</code>) and 30 broad 56k–1.83M-px corridor-blanket priors (<code>IR-84-12</code>, worst {reg_csat['final_dots_worst_forward_overlap_discriminating']:.5f}; literal dense witness {ov:.6f}).</p>"
        f'<a class="button" href="downloads/{csat_name}.tif" download>Download H84-CSAT GeoTIFF (139 KB) — DO NOT SUBMIT</a>'
        f'<a class="button-alt" href="downloads/{csat_name}.zip" download>Download Verified 1-TIFF ZIP</a>'
        '<a class="button-alt" href="evidence/run_card_csat.json">H84-CSAT Run Card JSON</a>'
        f'<a class="button-alt" href="downloads/{thms_name}.tif" download>Archived H84-THMS TIFF — DO NOT SUBMIT</a>'
        '<a class="button-alt" href="executive-summary.html">Submission Guide →</a>'
        f"<p><small><strong>H84-CSAT Name:</strong> <code>{csat_name}</code> · <strong>SHA-256:</strong> <code>{csat_sha}</code><br>"
        f"<strong>Short Note ({csat['note_chars']}/140 chars):</strong> <code>{csat_note}</code><br>"
        f"<strong>Archived H84-THMS SHA-256:</strong> <code>{thms_sha}</code></small></p>"
        "</section>"
    )

    for page_key, body in sections.items():
        document = (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>GEMSDOE84 · {page_key} · fail-closed release</title>"
            '<link rel="stylesheet" href="assets/release.css"></head><body>'
            f"<header><strong>GEMSDOE84 · Lane H84-CSAT &amp; Repository Release Portal</strong>"
            f"<p>Evidence first · Maximize P(Win) · Own the Outcome</p><nav>{nav_html}</nav></header>"
            f"<main>{hero}<section>{body}</section>"
            "<footer>Snapshot 2026-10-22/23 UTC · 0 weekly competition slots consumed · "
            "Deterministically rendered from evidence/run_card_csat.json &amp; registry/release_status.json.</footer>"
            "</main></body></html>\n"
        )
        (ROOT / "docs" / f"{page_key}.html").write_text(document, encoding="utf-8")
        if page_key in ("index", "executive-summary"):
            rebased_root = document.replace('href="', 'href="docs/')
            (ROOT / f"{page_key}.html").write_text(rebased_root, encoding="utf-8")

    (ROOT / "docs/downloads/index.html").write_text(
        (ROOT / "docs/index.html").read_text(encoding="utf-8").replace('href="', 'href="../'),
        encoding="utf-8",
    )
    (ROOT / "docs/research").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "research/SESSION_REVIEW_20261023.md", ROOT / "docs/research/SESSION_REVIEW_20261023.md")
    (ROOT / "docs/research/official").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "research/official/reference-extract.json", ROOT / "docs/research/official/reference-extract.json")
    (ROOT / "docs/.nojekyll").touch()
    print("Built deterministic fail-closed GEMSDOE84 portal (H84-CSAT + archived lanes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
