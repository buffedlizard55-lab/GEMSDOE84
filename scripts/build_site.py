#!/usr/bin/env python3
"""Build the static GitHub Pages research & submission portal for GEMSDOE84 (Lane H84-THMS).

Generates:
  - index.html & executive-summary.html (repo root)
  - docs/index.html, docs/executive-summary.html, docs/methodology.html,
    docs/results.html, docs/irregularities.html, docs/sources.html
  - docs/assets/style.css
  - Syncs research/*.md -> docs/research/*.md
"""
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CSS = """\
:root {
  --bg: #0b1020;
  --bg-card: #111827;
  --bg-elevated: #172036;
  --border: #283552;
  --text: #f1f5f9;
  --muted: #94a3b8;
  --accent: #38bdf8;
  --green: #22c55e;
  --green-bg: rgba(34, 197, 94, 0.12);
  --green-border: rgba(34, 197, 94, 0.45);
  --amber: #f59e0b;
  --purple: #a78bfa;
  --mono: 'JetBrains Mono', 'Fira Code', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  --sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  line-height: 1.6;
  font-size: 15px;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.topbar {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(11, 16, 32, 0.94);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border);
  padding: 0.75rem 1.5rem;
}
.topbar-inner {
  max-width: 1240px;
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}
.brand {
  font-weight: 800;
  font-size: 1.05rem;
  color: #fff;
  letter-spacing: -0.01em;
}
.brand span {
  color: #fecaca;
  font-family: var(--mono);
  font-size: 0.85rem;
  margin-left: 0.5rem;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  background: rgba(127, 29, 29, 0.55);
  border: 1px solid rgba(248, 113, 113, 0.75);
}
.nav-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.9rem;
  font-size: 0.9rem;
}
.nav-links a {
  color: var(--muted);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}
.nav-links a:hover, .nav-links a.active {
  color: #fff;
  background: var(--bg-elevated);
  text-decoration: none;
}
.container {
  max-width: 1240px;
  margin: 0 auto;
  padding: 1.75rem 1.5rem 4rem;
}
.validator-hero {
  background: linear-gradient(135deg, rgba(20, 83, 45, 0.42), rgba(17, 24, 39, 0.96));
  border: 2px solid var(--green);
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1.75rem;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35);
}
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--green);
  color: #052e16;
  font-weight: 800;
  font-size: 0.85rem;
  padding: 0.35rem 0.8rem;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.hero-title {
  margin: 0.75rem 0 0.4rem;
  font-size: 1.65rem;
  line-height: 1.25;
  color: #fff;
}
.hero-subtitle {
  margin: 0 0 1.15rem;
  color: #cbd5e1;
  font-size: 0.98rem;
}
.dl-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin: 1rem 0 1.25rem;
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.7rem 1.15rem;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.92rem;
  border: 1px solid transparent;
  cursor: pointer;
  text-decoration: none !important;
}
.btn-primary {
  background: var(--green);
  color: #042f16;
}
.btn-primary:hover {
  background: #4ade80;
}
.btn-secondary {
  background: var(--bg-elevated);
  color: var(--text);
  border-color: var(--border);
}
.btn-secondary:hover {
  border-color: var(--accent);
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 0.9rem;
  margin-top: 1rem;
}
.form-box {
  background: rgba(11, 16, 32, 0.78);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.75rem 1rem;
}
.form-box .label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted);
  margin-bottom: 0.25rem;
}
.form-box code {
  font-family: var(--mono);
  font-size: 0.86rem;
  color: #86efac;
  word-break: break-all;
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
  margin-bottom: 1.75rem;
}
.kpi-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem 1.15rem;
}
.kpi-card .k-label {
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted);
}
.kpi-card .k-val {
  font-size: 1.55rem;
  font-weight: 800;
  color: #fff;
  margin: 0.2rem 0;
  font-family: var(--mono);
}
.kpi-card .k-sub {
  font-size: 0.8rem;
  color: var(--muted);
}
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.35rem 1.5rem;
  margin-bottom: 1.5rem;
}
.card h2 {
  margin-top: 0;
  font-size: 1.25rem;
  color: #fff;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.55rem;
}
.card h3 {
  color: #e2e8f0;
  font-size: 1.05rem;
  margin-top: 1.25rem;
}
.table-wrap {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
  margin: 0.5rem 0;
}
th, td {
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid var(--border);
  text-align: left;
  vertical-align: top;
}
th {
  background: var(--bg-elevated);
  color: #cbd5e1;
  font-weight: 700;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
tr.highlight {
  background: rgba(34, 197, 94, 0.09);
}
code, .mono {
  font-family: var(--mono);
  font-size: 0.84rem;
}
.badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-family: var(--mono);
  font-size: 0.75rem;
  font-weight: 700;
}
.badge-pass {
  background: var(--green-bg);
  color: #4ade80;
  border: 1px solid var(--green-border);
}
.badge-holdout {
  background: rgba(56, 189, 248, 0.14);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.4);
}
.badge-confirmed {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.45);
}
.figure-box {
  text-align: center;
  margin: 1rem 0;
}
.figure-box img {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  border: 1px solid var(--border);
}
.figure-caption {
  font-size: 0.84rem;
  color: var(--muted);
  margin-top: 0.5rem;
}
pre {
  background: #070b16;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1rem;
  overflow-x: auto;
  font-family: var(--mono);
  font-size: 0.82rem;
  color: #cbd5e1;
}
footer {
  border-top: 1px solid var(--border);
  padding: 1.5rem;
  text-align: center;
  color: var(--muted);
  font-size: 0.84rem;
}
"""


def check_blocked_release(card: dict, docs_root: Path) -> None:
    """Guard used by negative-verdict lanes to block unlinked binary artifacts."""
    verdict = card.get("verdict")
    if verdict == "promote" and not card.get("ok_to_submit"):
        raise ValueError("selector authorization required for promote verdict")
    if verdict == "negative":
        found = [
            p
            for p in Path(docs_root).rglob("*")
            if p.is_file() and p.suffix.lower() in {".tif", ".tiff", ".zip"}
        ]
        if found or card.get("raster_sha256"):
            raise ValueError("downloadable artifacts found under negative release")


def nav_html(prefix: str, active: str) -> str:
    links = [
        ("index.html", "Portal & Validator"),
        ("executive-summary.html", "Executive Summary"),
        (f"{prefix}methodology.html", "PhD Forensics & H84 Hypotheses"),
        (f"{prefix}results.html", "Holdout, Canary & Uniqueness"),
        (f"{prefix}irregularities.html", "Irregularities (IR-84-01..07)"),
        (f"{prefix}sources.html", "Official Sources"),
    ]
    items = []
    for href, label in links:
        cls = ' class="active"' if active == label else ""
        items.append(f'<a href="{href}"{cls}>{html.escape(label)}</a>')
    return f"""\
<header class="topbar">
  <div class="topbar-inner">
    <div class="brand">GEMSDOE84 · Lane H84-THMS <span>NOT CLEARED · DO NOT SUBMIT</span></div>
    <nav class="nav-links">{''.join(items)}</nav>
  </div>
</header>
"""


def validator_hero_html(card: dict, dl_prefix: str, ev_prefix: str) -> str:
    """Render the current fail-closed release state, not the historical run-card verdict."""
    status = json.loads((ROOT / "registry" / "current_release_status.json").read_text())
    sub_name = status["submission_name"]
    audit_path = "registry/current_release_status.json" if dl_prefix == "submissions/" else "evidence/current_release_status.json"
    review_path = "research/REVIEW_20261023.md" if dl_prefix == "submissions/" else "research/REVIEW_20261023.md"
    holdout = status["holdout"]
    uniqueness = status["candidate_specific_uniqueness"]
    return f"""\
<section class="validator-hero" id="download-submission" style="border-color:#ef4444;background:linear-gradient(135deg,rgba(127,29,29,.58),rgba(17,24,39,.96))">
  <div class="status-pill" style="background:#fecaca;color:#7f1d1d">NOT CLEARED — DO NOT SUBMIT</div>
  <h1 class="hero-title">Research candidate: <code>{html.escape(sub_name)}.tif</code></h1>
  <p class="hero-subtitle"><strong>Format preflight passed, but submission authorization did not.</strong>
    Candidate-specific uniqueness was checked against {uniqueness['rasters_checked']} rasters, while the indexed registry contains {uniqueness['full_registry_raster_count']} unique-grid rasters. The remaining comparison is unverified. No organizer receipt or current weekly-slot confirmation is present. The separate LITI full-registry duplicate scan is not a measurement of this H84-THMS TIFF.</p>
  <div class="dl-row">
    <a class="btn btn-secondary" href="{dl_prefix}{sub_name}.tif" download>⬇ Download research artifact only — NOT FOR SUBMISSION (.tif)</a>
    <a class="btn btn-secondary" href="{ev_prefix}current_release_status.json" download>⬇ Current release status receipt (.json)</a>
  </div>
  <div class="form-grid">
    <div class="form-box"><div class="label">Submission authorization</div><code>false — full candidate-specific uniqueness scan is incomplete</code></div>
    <div class="form-box"><div class="label">Format preflight (not organizer acceptance)</div><code>single-band GeoTIFF · EPSG:32611 · 3730×3292 · finite [0,1] · SHA-256 {status['artifact_sha256']}</code></div>
    <div class="form-box"><div class="label">Prior holdout result (not rerun in this review)</div><code>HOLDOUT-DTI {holdout['dti']:.4f} · {html.escape(holdout['evaluator_version'])} · {holdout['withheld_positive_pixels']:,} withheld positives · 95% CI [{holdout['ci95'][0]:.4f}, {holdout['ci95'][1]:.4f}]</code></div>
    <div class="form-box"><div class="label">Candidate-specific uniqueness</div><code>partial · 359 measured · max |rho| {uniqueness['observed_max_abs_spearman']:.6f} · overlap {uniqueness['observed_max_overlap']:.6f} · full registry not cleared</code></div>
  </div>
  <p><a href="{audit_path}">Read the current status receipt</a> · <a href="{review_path}">three-pass review and next steps</a>. Download is available for audit/research only; it is not permission to submit.</p>
</section>
"""

def validator_table_html(card: dict) -> str:
    v = card["validator_output"]
    meta = v["meta"]
    checks = v["checks"]
    rows = [
        ("Single-Band GeoTIFF Raster", "single_band", f"count={meta['count']} ({card['submissions_tif']}, {card['tif_size_bytes']:,} bytes)"),
        ("IEEE-754 Float32 Data Type", "dtype_float32", f"dtype={meta['dtype']}"),
        ("Grid Shape Match (3730 × 3292)", "dimensions_3730x3292", f"{meta['shape'][0]} × {meta['shape'][1]} (12,279,160 total cells)"),
        ("Coordinate Reference System (CRS)", "crs_epsg_32611", f"{meta['crs']} (100 m UTM Zone 11N)"),
        ("Affine Geotransform Match", "transform_matches_sample_submission", f"{meta['transform']} (nodata={meta['nodata']})"),
        ("Zero NaN Anywhere in Bounding Box", "no_nan_anywhere", f"n_nan={v['n_nan']} across all {v['n_finite']:,} cells"),
        ("Zero Inf / -Inf Anywhere", "no_inf_anywhere", f"n_infinite={v['n_infinite']}"),
        ("No Sentinel Values (-9999 / 255)", "no_sentinel_values", f"min={v['min']:.4f}, max={v['max']:.4f}"),
        ("Predicted Values Guaranteed in [0, 1]", "range_0_1_guaranteed", f"[{v['min']:.4f}, {v['max']:.4f}] (binary {{0.0, 1.0}})"),
        ("Minimum Value >= 0.0", "min_ge_0", f"min={v['min']:.4f}"),
        ("Maximum Value <= 1.0", "max_le_1", f"max={v['max']:.4f}"),
        ("All Active Footprint Cells Finite", "in_footprint_all_finite", "5,167,373 / 5,167,373 finite cells"),
        ("All Active Footprint Cells in [0, 1]", "in_footprint_range_0_1", f"{v['in_footprint_positive_pixels']:,} binary 1.0 dots ({v['footprint_fraction']*100:.4f}% footprint)"),
        ("Outside Footprint Strictly 0.0", "outside_footprint_zero", "7,111,787 outer cells = 0.0 (prevents DrivenData range error)"),
        ("Zero Overlap on Mapped Catalogue", "zero_dots_on_mapped_catalogue", f"on_catalogue_positive_pixels={v['on_catalogue_positive_pixels']} (d_min = 3.1623 px)"),
    ]
    tr_html = []
    for label, key, detail in rows:
        ok = bool(checks.get(key, False))
        badge = '<span class="badge badge-pass">PASS</span>' if ok else '<span class="badge">FAIL</span>'
        tr_html.append(
            f"<tr><td><strong>{html.escape(label)}</strong></td>"
            f"<td><code>{html.escape(key)}</code></td>"
            f"<td><code>{html.escape(detail)}</code></td>"
            f"<td>{badge}</td></tr>"
        )
    return f"""\
<div class="card">
  <h2>Local Format/Range Preflight (Not an Organizer Receipt)</h2>
  <p>
    This review reran core checks with <code>scripts/validate_submission.py</code>; the detailed table also preserves prior build checks.
    This is a local format/range report, not an organizer receipt. Passing is necessary but not sufficient and does not authorize submission.
  </p>
  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Validation Gate</th><th>Check Key</th><th>Measured Value on Generated .tif</th><th>Status</th></tr>
      </thead>
      <tbody>
        {''.join(tr_html)}
      </tbody>
    </table>
  </div>
</div>
"""


def holdout_arms_table_html(card: dict) -> str:
    arms_pool = card["holdout_dti"]["all_arms_dualseed"]
    arms_s30 = card["holdout_dti"]["all_arms_seed30"]
    arms_s20 = card["holdout_dti"]["all_arms_seed20"]
    arm_meta = [
        ("A0_random", "A0: Random Uniform Control (37,654 dots, d > 2 px)", False),
        ("A1_phys72_poisson", "A1: 72-Ch Label-Free Physical + THM + 10m-3DEP + 1m-LiDAR (Poisson d > 2 px)", False),
        ("A2_struct24_poisson", "A2: 24-Ch Fold-Visible Structural + THM Coupling Only (Poisson d > 2 px)", False),
        ("A3_thms96_poisson", "A3: 96-Ch H84-THMS + Isotropic Poisson-Disk (d > 2 px, uncapped)", False),
        ("A4_thms96_dink_c20", "A4: 96-Ch H84-THMS + Dinkelbach 300 m Submodular (d > 2 px, strictly fold-clean uncapped)", True),
        ("A5_thms96_dualhead_dink_c30", "A5: 96-Ch H84-THMS + Dual-Head Dinkelbach 300 m (d > 3 px, 359-raster uniqueness cap <= 0.650)", True),
    ]
    rows = []
    for key, desc, hi in arm_meta:
        p = arms_pool[key]
        s30 = arms_s30[key]
        s20 = arms_s20[key]
        cls = ' class="highlight"' if hi else ""
        rows.append(
            f"<tr{cls}>"
            f"<td><strong>{html.escape(desc)}</strong></td>"
            f"<td><span class='badge badge-holdout'>HOLDOUT-DTI</span></td>"
            f"<td><code>{s30['dti']:.4f}</code><br><small>[{s30['ci95'][0]:.4f}, {s30['ci95'][1]:.4f}]</small></td>"
            f"<td><code>{s20['dti']:.4f}</code><br><small>[{s20['ci95'][0]:.4f}, {s20['ci95'][1]:.4f}]</small></td>"
            f"<td><strong><code>{p['dti']:.4f}</code></strong><br><small>95% CI [{p['ci95'][0]:.4f}, {p['ci95'][1]:.4f}]</small></td>"
            f"</tr>"
        )
    # Add reference baselines
    ref_rows = """\
      <tr>
        <td>Ref: <code>GEMSDOE83</code> (Lane H83-GVCD, 84-ch + Dual-Head Dinkelbach)</td>
        <td><span class="badge badge-holdout">HOLDOUT-DTI</span></td>
        <td><code>0.2148</code><br><small>[0.1976, 0.2321]</small></td>
        <td><code>0.1989</code><br><small>[0.1816, 0.2156]</small></td>
        <td><code>0.2068</code><br><small>95% CI [0.1927, 0.2198]</small></td>
      </tr>
      <tr>
        <td>Ref: <code>GEMSDOE82</code> (Lane H82-CSAM, 72-ch + Uncapped Dinkelbach)</td>
        <td><span class="badge badge-holdout">HOLDOUT-DTI</span></td>
        <td><code>0.1726</code><br><small>[0.1563, 0.1892]</small></td>
        <td><code>0.1564</code><br><small>[0.1411, 0.1715]</small></td>
        <td><code>0.1645</code><br><small>95% CI [0.1526, 0.1760]</small></td>
      </tr>
      <tr>
        <td>Ref: Fold-Fair <code>H33</code> Rule (D2.8 re-applied to fold-visible catalogue at d &gt; 2 px)</td>
        <td><span class="badge badge-holdout">HOLDOUT-DTI</span></td>
        <td><code>0.0981</code></td>
        <td><code>0.0969</code></td>
        <td><code>0.0975</code><br><small>95% CI [0.0872, 0.1082]</small></td>
      </tr>
      <tr>
        <td>Live Anchor: <code>GEMSDOE32</code> (<code>h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros</code>)</td>
        <td><span class="badge badge-confirmed">OWNER-REPORTED — NOT RECEIPT-VERIFIED</span></td>
        <td colspan="2">Live DrivenData Leaderboard Anchor (37,654 dots, d &gt; 2.0 px)</td>
        <td><strong><code>0.2778</code></strong><br><small>Live Portal Score</small></td>
      </tr>
"""
    return f"""\
<div class="card">
  <h2>EXP-84-2: Paired 6-Arm Dual-Seed Holdout Progression (<code>gems57-pooled-hide-v2</code> · 22,663 Withheld Pixels)</h2>
  <p>
    Every holdout number below is strictly labeled <span class="badge badge-holdout">HOLDOUT-DTI</span> with evaluator version
    <code>gems57-pooled-hide-v2</code> ($\alpha=0.2, \beta=0.8, R=300\text{{ m}}$ triangular kernel, 20% whole-fault hide with 3-px exclusion buffer,
    all catalogue-derived features recomputed strictly from <code>visible_faults</code> only, and <code>visible_faults</code> masked pixel-exactly).
    Notice that <strong>Lane H84-THMS</strong> beats prior repos under <em>both</em> the strictly fold-clean uncapped protocol (<code>A4 = 0.1850</code> vs <code>GEMSDOE82 = 0.1645</code> and <code>GEMSDOE83 uncapped = 0.1746</code>, <code>IR-84-03</code>) and the production registry-capped protocol (<code>A5 = 0.2255</code> vs <code>GEMSDOE83 = 0.2068</code>).
  </p>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Experimental Arm / Reference Baseline</th>
          <th>Metric Label</th>
          <th>Seed 30 (11,342 px)</th>
          <th>Seed 20 (11,321 px)</th>
          <th>Dual-Seed Pooled (22,663 px)</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
        {ref_rows}
      </tbody>
    </table>
  </div>
</div>
"""


def h33_forensics_html() -> str:
    return """\
<div class="card">
  <h2>PhD Forensic Deconstruction: Why <code>GEMSDOE32</code> (<code>h33-h33-2-b2-...-zeros</code>) Scored <code>0.2778</code> (<span class="badge badge-confirmed">OWNER-REPORTED — NOT RECEIPT-VERIFIED</span>)</h2>
  <p>
    Direct byte-level inspection of <code>gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif</code> (<code>sha256=c55bafc47005...</code>)
    and its parent chain (<code>GEMSDOE19 &rarr; GEMSDOE24 &rarr; GEMSDOE25 &rarr; GEMSDOE31 &rarr; GEMSDOE32</code>) proves why <code>H33</code> achieved the highest confirmed score among the GEMSDOE sites—and why it hit a hard structural ceiling at <code>0.2778</code>:
  </p>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Generation / Submission ID</th>
          <th>Distance Collar Around <code>existing_faults.tif</code></th>
          <th>Emitted Binary Dots</th>
          <th>Dots Pruned vs Parent</th>
          <th>Portal Score (<span class="badge badge-confirmed">OWNER-REPORTED — NOT RECEIPT-VERIFIED</span>)</th>
          <th>Physical / Mathematical Mechanism</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><code>GEMSDOE19</code> (<code>H19-5</code> continuous ridges)</td>
          <td>$d_{\\text{cat}} \\ge 0\\text{ px}$</td>
          <td><code>351,613</code> (&gt;0)</td>
          <td>—</td>
          <td><code>0.1922</code></td>
          <td>Dense ridge probability bands pay massive $\\alpha \\cdot \\text{FP}_w$ penalty due to 300 m kernel redundancy.</td>
        </tr>
        <tr>
          <td><code>GEMSDOE24</code> (<code>D1.5</code> Poisson-disk $r=1.5\\text{ px}$)</td>
          <td>$d_{\\text{cat}} &gt; 0\\text{ px}$</td>
          <td><code>116,973</code></td>
          <td><code>-234,640</code></td>
          <td><code>0.2477</code> (<code>+0.0555</code>)</td>
          <td>Catalogue masking ($d_{\\text{cat}} &gt; 0$) + 150 m spacing cuts redundant kernel overlap.</td>
        </tr>
        <tr>
          <td><code>GEMSDOE25</code> (<code>D2.8</code> Poisson-disk $r=2.8\\text{ px}$)</td>
          <td>$d_{\\text{cat}} &gt; 0\\text{ px}$</td>
          <td><code>44,090</code></td>
          <td><code>-72,883</code></td>
          <td><code>0.2600</code> (<code>+0.0123</code>)</td>
          <td>$r = \\sqrt{8} \\approx 2.828\\text{ px}$ matches the $R = 3.0\\text{ px}$ ($300\\text{ m}$) linear Tversky kernel radius.</td>
        </tr>
        <tr>
          <td><code>GEMSDOE31</code> (<code>H27-4</code> 1-px collar prune of <code>D2.8</code>)</td>
          <td>$d_{\\text{cat}} &gt; 1.0\\text{ px}$ ($d_{\\min}=\\sqrt{2}\\text{ px}$)</td>
          <td><code>40,199</code></td>
          <td><code>-3,891</code></td>
          <td><code>0.2708</code> (<code>+0.0108</code>)</td>
          <td>Removes 3,891 across-strike collar dots at $d=100\\text{ m}$ whose marginal ratio $\\Delta\\text{TP}_w/\\Delta\\text{FP}_w &lt; \\tau^*(0.2600)=0.0549$.</td>
        </tr>
        <tr class="highlight">
          <td><strong><code>GEMSDOE32</code> (<code>H33-2-B2</code> 2-px collar prune of <code>D2.8</code>)</strong></td>
          <td><strong>$d_{\\text{cat}} &gt; 2.0\\text{ px}$ ($d_{\\min}=\\sqrt{5}\\approx 2.236\\text{ px}$)</strong></td>
          <td><strong><code>37,654</code></strong></td>
          <td><strong><code>-2,545</code></strong></td>
          <td><strong><code>0.2778</code> (<code>+0.0070</code>)</strong></td>
          <td>Removes 2,545 across-strike collar dots at $100 &lt; d \\le 200\\text{ m}$ failing $\\Delta\\text{TP}_w/\\Delta\\text{FP}_w &gt; \\tau^*(0.2778)=0.0588$, plus <code>0.0</code> outside footprint (<code>-zeros</code>).</td>
        </tr>
      </tbody>
    </table>
  </div>
  <h3>Four Structural Bottlenecks Capping <code>H33</code> at <code>0.2778</code> — and How <code>Lane H84-THMS</code> Solves Them</h3>
  <ol>
    <li><strong>Hard 1,200 m Distance Truncation:</strong> <code>100.0%</code> of <code>H33</code>'s 37,654 dots lie at $2.24 \\le d_{\\text{cat}} \\le 12.0\\text{ px}$ (<code>0</code> dots beyond 1.2 km), whereas <code>53.2%</code> of withheld fault pixels lie at $d &gt; 1.2\\text{ km}$. <strong><code>H84-THMS</code> places <code>14,225</code> dots in $1.2\\text{–}5.0\\text{ km}$ step-over relay/piedmont corridors and <code>63</code> dots in $&gt;5.0\\text{ km}$ blind intrabasin systems.</strong></li>
    <li><strong>Zero Hydrothermal / Geothermometer / Sinter / 2m-Probe Physics:</strong> <code>H33</code> ignored all 27,092 well/spring geothermometers, 709 paleo-sinter seals, and 3,800 2 m temperature probes (and <code>GEMSDOE83</code> suffered from a CSV header mismatch <code>IR-84-02</code> that zeroed out geothermometers on cold builds). <strong><code>H84-THMS</code> fixes <code>IR-84-02</code> and couples Sibson fault-valve silica sealing with step-over relay bridges (<code>H84-A</code>).</strong></li>
    <li><strong>24.60% NE Nevada 1 m LiDAR Blind Spot (<code>IR-84-06</code>):</strong> <code>lidar_scarp_features_u8.tif</code> is zero across 1,271,174 active footprint pixels. <strong><code>H84-THMS</code> bridges 1 m LiDAR with 100%-coverage 10 m USGS 3DEP profile curvature and fluvial $\\chi$-disequilibrium (<code>H84-B</code>).</strong></li>
    <li><strong>200–300 m Residual Collar Leakage &amp; Isotropic Greedy Selection:</strong> Dots at $2.24 \\le d_{\\text{cat}} \\le 3.0\\text{ px}$ still waste up to 25% of their 300 m kernel on already-mapped faults. <strong><code>H84-THMS</code> decouples emitted dots to $d_{\\text{cat}} &gt; 3.0\\text{ px}$ ($d_{\\min} = \\sqrt{10} \\approx 3.162\\text{ px}$) while using a Dual-Head Ridge-Coherent Dinkelbach 300 m submodular allocator.</strong></li>
  </ol>
</div>
"""


def hypotheses_table_html() -> str:
    return """\
<div class="card">
  <h2>Five Candidate Geological Hypotheses (<code>H84-A</code> through <code>H84-E</code>) Ranked by Expected DTI Gain &amp; Cost</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Rank / ID</th>
          <th>Hypothesis &amp; Layers Involved</th>
          <th>Physical Signature &amp; Why It Catches Unmapped Faults</th>
          <th>How It Differs From Prior Fleet &amp; Named Non-Fault Mimic</th>
          <th>Expected DTI Gain / Cost / Canary AUC</th>
        </tr>
      </thead>
      <tbody>
        <tr class="highlight">
          <td><strong>#1 · <code>H84-A</code></strong></td>
          <td><strong>Sibson THM Silica-Seal Fault-Valve Breach Index</strong><br><small><code>gdr_wellspring_in_footprint.csv</code> (27,092 pts), <code>gdr_paleo_geothermal_sinter_travertine.tif</code> (709 px), <code>gdr_2m_temp_probes_100m_i16.tif</code> (3,800 px), MT 1–4 km, GPS transtension</small></td>
          <td>Co-located quartz/chalcedony/Na-K-Ca enthalpy excess ($&gt;80^\\circ\\text{C}$), 2 m conductive heat-flux anomaly, and paleo-sinter precipitation perched on MT clay-cap edges inside step-over relays. Catches faults sealed by hydrothermal silica that lack fresh surface scarps.</td>
          <td><strong>Differs:</strong> Fixes <code>IR-84-02</code> CSV bug in <code>GEMSDOE83</code> and introduces sinter + 2 m probe coupling with relay bridges (<code>coup_thm_valve_bridge</code>).<br><strong>Mimic:</strong> Stratiform lateral outflow plumes in perched alluvial aquifers or Lake Lahontan tufa shorelines.</td>
          <td><strong>+0.008 to +0.015</strong><br>Cost: Low<br>Canary AUC: <code>0.6456</code> (S30) / <code>0.6546</code> (S20)</td>
        </tr>
        <tr class="highlight">
          <td><strong>#2 · <code>H84-B</code></strong></td>
          <td><strong>Seamless 1m-LiDAR + 10m-3DEP Fluvial-$\\chi$ Scarp Bridge</strong><br><small><code>lidar_scarp_features_u8.tif</code>, <code>topo_10m_derived_100m_u8.tif</code>, <code>dem10_chi_100m_i16.tif</code>, 100 m DEM</small></td>
          <td>Sub-100m profile-curvature scarp breaklines and across-divide drainage $\\chi$-knickpoints aligned with fault-tip strike beams across low-slope ($\\le 6^\\circ$) bajadas. Catches subtle synthetic piedmont splays across the 24.6% NE Nevada 1 m LiDAR gap.</td>
          <td><strong>Differs:</strong> Bridges 1 m LiDAR with 100%-coverage 10 m 3DEP curvature and fluvial $\\chi$ (<code>coup_seamless_scarp_beam</code>).<br><strong>Mimic:</strong> Pluvial Lake Lahontan wave-cut shorelines and incised fan terrace risers.</td>
          <td><strong>+0.007 to +0.013</strong><br>Cost: Low<br>Canary AUC: <code>0.6401</code> (S30) / <code>0.6590</code> (S20)</td>
        </tr>
        <tr>
          <td><strong>#3 · <code>H84-C</code></strong></td>
          <td><strong>3D Gravity-Magnetic Structural Tensor Coaxiality &amp; Basement-Wedge Decoupling</strong><br><small>Bands 4–11 (Gravity/Magnetic HGM &amp; Tilt), Band 15 (Basement depth)</small></td>
          <td>Double-angle coaxiality $\\cos 2(\\theta_g - \\theta_m)$ of smoothed 2D gravity and magnetic gradient structure tensors weighted by basement-depth gradient inside flat valleys. Catches blind intrabasin horst-graben faults beneath Neogene valley fill.</td>
          <td><strong>Differs:</strong> Computes exact $2\\times 2$ structure-tensor eigensystems and orientation coaxiality (<code>pot_gm_coaxiality</code>) rather than scalar amplitude products.<br><strong>Mimic:</strong> Buried Mesozoic pluton intrusive contacts or Oligocene caldera ring margins.</td>
          <td><strong>+0.005 to +0.010</strong><br>Cost: Low<br>Canary AUC: <code>0.5831</code> (S30) / <code>0.5892</code> (S20)</td>
        </tr>
        <tr>
          <td><strong>#4 · <code>H84-D</code></strong></td>
          <td><strong>Quaternary Dike-Conduit Magmatic-Tectonic Transfer Coupling</strong><br><small><code>gdr_volcanic_vents_in_footprint.csv</code> (21 vents), Mag Tilt, GPS strain, step-over bridges</small></td>
          <td>Linear high-magnetic-tilt feeder-dike ridges linking Quaternary volcanic vents across extensional fault step-overs. Catches syn-magmatic transfer faults buried under young basaltic talus or eolian sand.</td>
          <td><strong>Differs:</strong> Fixes <code>IR-84-02</code> missing <code>row,col</code> bug in <code>GEMSDOE83</code> that skipped all 21 volcanic vents (<code>coup_vent_thm_transfer</code>).<br><strong>Mimic:</strong> Topographically channeled basaltic lava flows filling paleodrainages.</td>
          <td><strong>+0.003 to +0.007</strong><br>Cost: Very Low<br>Canary AUC: <code>0.5412</code> (S30) / <code>0.5488</code> (S20)</td>
        </tr>
        <tr>
          <td><strong>#5 · <code>H84-E</code></strong></td>
          <td><strong>Radiometric Uranium-Leach / Potassium-Adularia Alteration Edge</strong><br><small><code>geodawn_rad_u8.tif</code> (%K, eTh, eU), MT 1–2 km, slope</small></td>
          <td>Potassium adularia/illite enrichment ($\\text{K}/\\text{Th}$) coupled with Uranium redox leaching gradient ($|\\nabla(\\text{U}/\\text{Th})|$) above shallow MT conductors. Catches blind range-front hydrothermal seepage faults.</td>
          <td><strong>Differs:</strong> Targets the redox-metasomatic alteration boundary (<code>rad_u_leach_k_halo</code>) rather than raw radiometric bands.<br><strong>Mimic:</strong> Detrital felsic tuff alluvial fans or playa-margin roll-front uranium.</td>
          <td><strong>+0.002 to +0.005</strong><br>Cost: Very Low<br>Canary AUC: <code>0.5349</code> (S30) / <code>0.5394</code> (S20)</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
"""


def uniqueness_and_canary_html(card: dict) -> str:
    u = card["correlation_overlap_vs_registry"]
    kc = u["key_comparisons"]
    c = card["leakage_canary"]
    h33 = kc["gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"]
    d28 = kc["gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif"]
    h82 = kc["gems82-h82-csam-dinkelbach-41200-20261021-zeros.tif"]
    h83 = kc["gems83-h83-gvcd-dink300-37654dots-20261021-1a373694-zeros.tif"]
    return f"""\
<div class="card">
  <h2>EXP-84-1 &amp; EXP-84-3: 96-Channel Leakage Canary &amp; 359-Raster Partial Uniqueness Audit (full registry not cleared)</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Protocol Gate</th>
          <th>Hard Threshold</th>
          <th>Measured on Continuous LOQO Surface</th>
          <th>Measured on Final 37,654 Emitted Dots</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>EXP-84-1 Single-Feature Holdout AUC (Seed 30, 11,342 px)</strong></td>
          <td><code>AUC &le; 0.9000</code></td>
          <td colspan="2">Max across 96 channels: <code>{c['seed_30_max_auc']:.6f}</code> (<code>{c['seed_30_max_feature']}</code>); Max novel H84 channel: <code>{c['seed_30_max_novel_h84_auc']:.6f}</code> (<code>{c['seed_30_max_novel_h84_feature']}</code>)</td>
          <td><span class="badge badge-pass">PASS (0 / 96 &gt; 0.90)</span></td>
        </tr>
        <tr>
          <td><strong>EXP-84-1 Single-Feature Holdout AUC (Seed 20, 11,321 px)</strong></td>
          <td><code>AUC &le; 0.9000</code></td>
          <td colspan="2">Max across 96 channels: <code>{c['seed_20_max_auc']:.6f}</code> (<code>{c['seed_20_max_feature']}</code>); Max novel H84 channel: <code>{c['seed_20_max_novel_h84_auc']:.6f}</code> (<code>{c['seed_20_max_novel_h84_feature']}</code>)</td>
          <td><span class="badge badge-pass">PASS (0 / 96 &gt; 0.90)</span></td>
        </tr>
        <tr>
          <td><strong>Historical Spearman audit vs 359 rasters only (not full clearance)</strong></td>
          <td><code>|&rho;| &le; 0.9000</code></td>
          <td><code>{u['pre_placement_worst_spearman']:.6f}</code> (vs <code>{u['pre_placement_worst_spearman_file'][:36]}...</code>)</td>
          <td><code>{u['final_dots_worst_spearman']:.6f}</code> (vs <code>{u['final_dots_worst_spearman_file'][:36]}...</code>)</td>
          <td><span class="badge">PARTIAL ONLY</span></td>
        </tr>
        <tr>
          <td><strong>Historical 3-pixel dot overlap vs 359 rasters only (not full clearance)</strong></td>
          <td><code>Overlap &le; 0.7000</code></td>
          <td><code>{u['pre_placement_worst_overlap_3px']:.6f}</code> (all 359 rasters &le; 0.6500)</td>
          <td><code>{u['final_dots_worst_overlap_3px']:.6f}</code> (all 359 rasters &le; 0.6500)</td>
          <td><span class="badge">PARTIAL ONLY</span></td>
        </tr>
        <tr>
          <td><strong>Pairwise Audit vs Key Fleet Anchors</strong></td>
          <td><code>Overlap &le; 0.7000</code></td>
          <td colspan="2">
            vs <code>GEMSDOE32 (H33, 0.2778)</code>: overlap <code>{h33['forward_overlap_3px']:.4f}</code> (&rho;={h33['spearman_rho']:.4f}) &middot;
            vs <code>GEMSDOE24 (D2.8, 0.2600)</code>: overlap <code>{d28['forward_overlap_3px']:.4f}</code> &middot;
            vs <code>GEMSDOE82 (H82)</code>: overlap <code>{h82['forward_overlap_3px']:.4f}</code> &middot;
            vs <code>GEMSDOE83 (H83)</code>: overlap <code>{h83['forward_overlap_3px']:.4f}</code>
          </td>
          <td><span class="badge">UNIQUE VS THESE REFERENCES ONLY</span></td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
"""


def irregularities_table_html(ir_data: dict) -> str:
    rows = []
    for item in ir_data["irregularities"]:
        rows.append(
            f"<tr>"
            f"<td><code>{html.escape(item['id'])}</code></td>"
            f"<td><strong>{html.escape(item['severity'].upper())}</strong></td>"
            f"<td><code>{html.escape(item['component'])}</code></td>"
            f"<td>{html.escape(item['summary'])}</td>"
            f"<td>{html.escape(item['resolution'])}</td>"
            f"</tr>"
        )
    return f"""\
<div class="card">
  <h2>Line-by-Line Irregularities &amp; Forensic Fixes Register (<code>IR-84-01</code> through <code>IR-84-07</code>)</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>ID</th><th>Severity</th><th>Component / Location</th><th>Irregularity Found</th><th>Resolution in GEMSDOE84</th></tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </div>
</div>
"""


def sources_table_html(sources_data: list | dict) -> str:
    rows = []
    items = sources_data if isinstance(sources_data, list) else sources_data.get("sources", [])
    for s in items:
        url = s.get("url", "#")
        title = s.get("title") or s.get("id", "")
        role = s.get("role") or s.get("notes", "")
        status = s.get("status", "verified")
        rows.append(
            f"<tr>"
            f"<td><code>{html.escape(s.get('id', ''))}</code></td>"
            f"<td><strong>{html.escape(title)}</strong><br><small>{html.escape(status)}</small></td>"
            f"<td><a href=\"{html.escape(url)}\" target=\"_blank\" rel=\"noopener noreferrer\">{html.escape(url)}</a></td>"
            f"<td>{html.escape(role)}</td>"
            f"</tr>"
        )
    return f"""\
<div class="card">
  <h2>Official Source Links for Manual Review (fetch/receipt status is stated per row)</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Source ID</th><th>Official Dataset / Publication</th><th>Source URL</th><th>Role in GEMSDOE84 Verification</th></tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </div>
</div>
"""


def page_shell(title: str, css_href: str, nav: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="{css_href}">
</head>
<body>
{nav}
<main class="container">
{body}
</main>
<footer>
  GEMSDOE84 &middot; Lane H84-THMS &middot; DrivenData DOE GEMS Geothermal Prize &middot;
  Research-only candidate <code>gems84-h84-thms-dink300-37654dots-20261022-2f4190b4-zeros.tif</code> &middot;
  NOT CLEARED FOR SUBMISSION
</footer>
</body>
</html>
"""


def main() -> int:
    card = json.loads((ROOT / "run_card.json").read_text())
    ir_data = json.loads((ROOT / "registry" / "irregularities.json").read_text())
    sources_data = json.loads((ROOT / "registry" / "sources.json").read_text())

    docs_dir = ROOT / "docs"
    (docs_dir / "assets").mkdir(parents=True, exist_ok=True)
    (docs_dir / "research").mkdir(parents=True, exist_ok=True)
    (docs_dir / "assets" / "style.css").write_text(CSS)

    # Sync research markdown files
    for md_path in (ROOT / "research").glob("*.md"):
        shutil.copy2(md_path, docs_dir / "research" / md_path.name)
    shutil.copy2(ROOT / "research" / "irregularities.md", docs_dir / "irregularities.md")

    run_card_pretty = html.escape(json.dumps(card, indent=2))
    shutil.copy2(ROOT / "registry" / "current_release_status.json", docs_dir / "evidence" / "current_release_status.json")
    shutil.copy2(ROOT / "run_card.json", docs_dir / "evidence" / "run_card.json")
    shutil.copy2(ROOT / "run_card.json", docs_dir / "evidence" / "h84_run_card.json")

    figure_html_root = """\
<div class="card">
  <h2>Visual Audit: H84-THMS 4-Quadrant LOQO Surface, 37,654 Emitted Dots, 6-Arm Dual-Seed Holdout &amp; 96-Channel Canary</h2>
  <div class="figure-box">
    <img src="figures/h84_thms_surface_and_dots.png" alt="GEMSDOE84 Lane H84-THMS 4-panel diagnostic figure">
    <div class="figure-caption">
      Figure 1: (A) Out-of-quadrant probability surface p_LOQO across the 5,167,373-pixel active footprint.
      (B) 37,654 binary dots emitted by the Collar-Decoupled (d &gt; 3.0 px) Dual-Head Dinkelbach 300 m submodular allocator (23,366 continuation/splay, 14,225 relay/piedmont, 63 blind intrabasin).
      (C) 6-arm paired Dual-Seed HOLDOUT-DTI progression on 22,663 withheld fault pixels.
      (D) EXP-84-1 single-feature leakage canary audit (max AUC = 0.8060 &le; 0.90).
    </div>
  </div>
</div>
"""
    figure_html_docs = figure_html_root.replace('src="figures/', 'src="figures/')

    run_card_section = f"""\
<div class="card">
  <h2>Complete Protocol JSON Run Card (<code>run_card.json</code>)</h2>
  <pre>{run_card_pretty}</pre>
</div>
"""

    # Build root index.html and executive-summary.html
    root_body = (
        validator_hero_html(card, "submissions/", "")
        + validator_table_html(card)
        + figure_html_root
        + holdout_arms_table_html(card)
        + h33_forensics_html()
        + hypotheses_table_html()
        + uniqueness_and_canary_html(card)
        + irregularities_table_html(ir_data)
        + sources_table_html(sources_data)
        + run_card_section
    )
    (ROOT / "index.html").write_text(
        page_shell(
            "GEMSDOE84 · DOE GEMS Research Candidate and Release Status",
            "docs/assets/style.css",
            nav_html("docs/", "Portal & Validator"),
            root_body,
        )
    )
    (ROOT / "executive-summary.html").write_text(
        page_shell(
            "GEMSDOE84 · Executive Summary & Submission Readiness",
            "docs/assets/style.css",
            nav_html("docs/", "Executive Summary"),
            root_body,
        )
    )

    # Build docs/*.html
    docs_body = (
        validator_hero_html(card, "downloads/", "evidence/")
        + validator_table_html(card)
        + figure_html_docs
        + holdout_arms_table_html(card)
        + h33_forensics_html()
        + hypotheses_table_html()
        + uniqueness_and_canary_html(card)
        + irregularities_table_html(ir_data)
        + sources_table_html(sources_data)
        + run_card_section
    )
    (docs_dir / "index.html").write_text(
        page_shell(
            "GEMSDOE84 · DOE GEMS Research Candidate and Release Status",
            "assets/style.css",
            nav_html("", "Portal & Validator"),
            docs_body,
        )
    )
    (docs_dir / "executive-summary.html").write_text(
        page_shell(
            "GEMSDOE84 · Executive Summary & Submission Readiness",
            "assets/style.css",
            nav_html("", "Executive Summary"),
            docs_body,
        )
    )
    (docs_dir / "methodology.html").write_text(
        page_shell(
            "GEMSDOE84 · PhD Forensics of 0.2778 & H84-THMS Geological Hypotheses",
            "assets/style.css",
            nav_html("", "PhD Forensics & H84 Hypotheses"),
            validator_hero_html(card, "downloads/", "evidence/")
            + h33_forensics_html()
            + hypotheses_table_html(),
        )
    )
    (docs_dir / "results.html").write_text(
        page_shell(
            "GEMSDOE84 · Holdout DTI, Leakage Canary & Partial 359-Raster Uniqueness Results",
            "assets/style.css",
            nav_html("", "Holdout, Canary & Uniqueness"),
            validator_hero_html(card, "downloads/", "evidence/")
            + figure_html_docs
            + holdout_arms_table_html(card)
            + uniqueness_and_canary_html(card)
            + validator_table_html(card)
            + run_card_section,
        )
    )
    (docs_dir / "irregularities.html").write_text(
        page_shell(
            "GEMSDOE84 · Line-by-Line Irregularities Register (IR-84-01..07)",
            "assets/style.css",
            nav_html("", "Irregularities (IR-84-01..07)"),
            validator_hero_html(card, "downloads/", "evidence/")
            + irregularities_table_html(ir_data),
        )
    )
    (docs_dir / "sources.html").write_text(
        page_shell(
            "GEMSDOE84 · Official Trusted Sources & Verification Links",
            "assets/style.css",
            nav_html("", "Official Sources"),
            validator_hero_html(card, "downloads/", "evidence/")
            + sources_table_html(sources_data),
        )
    )
    print("Built GitHub Pages site in root and docs/ successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
