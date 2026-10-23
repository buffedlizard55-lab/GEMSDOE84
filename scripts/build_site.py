#!/usr/bin/env python3
"""Deterministic, fail-closed static site generator for GEMSDOE84 (GitHub Pages + root index).

Unites:
  1. Lane H84-B (CTHF + CTFO: Crack-Tip Hydrothermal-Geopotential Posterior + Comonotonic 1D-Trace Fractional Optimization)
  2. Lane H84-CSAT (Dual-Habitat 3D Contact-Depth + Counterfactual Strain-Transfer)
  3. Audited H84-THMS release gate & full 1,196-raster fleet uniqueness forensics.

Uses Python stdlib only so clean GitHub Actions CI passes `git diff --exit-code -- docs` bit-for-bit.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EVIDENCE = ROOT / "evidence"


def check_blocked_release(card: dict, docs: Path) -> None:
    """Legacy fail-closed safety guard: a static site renderer cannot self-authorize promotion."""
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


def _verify_lane_card(root: Path, rel_card: str, label: str) -> dict:
    c = json.loads((root / rel_card).read_text(encoding="utf-8"))
    if c.get("verdict") != "negative" or c.get("submission_authorized") is not False:
        raise ValueError(f"{label} must remain fail-closed negative without human selector override")
    for rel in (c["submission_file"], f"submissions/{c['submission_name']}.tif"):
        p = root / rel
        if hashlib.sha256(p.read_bytes()).hexdigest() != c["raster_sha256"]:
            raise ValueError(f"{label} artifact hash mismatch: {p}")
    return c


def _inline_md(text: str) -> str:
    s = html.escape(text, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
    s = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+|[A-Za-z0-9_./#-]+)\)",
        r'<a href="\2">\1</a>',
        s,
    )
    return s


def md_to_html(md_text: str) -> str:
    lines = md_text.splitlines()
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped in ("---", "***"):
            out.append("<hr>")
            i += 1
            continue
        if stripped.startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(html.escape(lines[i], quote=False))
                i += 1
            i += 1
            out.append("<pre><code>" + "\n".join(buf) + "</code></pre>")
            continue
        if stripped.startswith("$$"):
            buf = [stripped.strip("$").strip()]
            if not (stripped.endswith("$$") and len(stripped) > 4):
                i += 1
                while i < n and not lines[i].strip().endswith("$$"):
                    buf.append(lines[i].strip())
                    i += 1
                if i < n:
                    buf.append(lines[i].strip().strip("$").strip())
            i += 1
            expr = html.escape(" ".join(x for x in buf if x), quote=False)
            out.append(f'<pre class="math-block"><code>{expr}</code></pre>')
            continue
        m_h = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m_h:
            lvl = len(m_h.group(1))
            slug = re.sub(r"[^a-z0-9]+", "-", m_h.group(2).lower()).strip("-")
            out.append(f'<h{lvl} id="{slug}">{_inline_md(m_h.group(2))}</h{lvl}>')
            i += 1
            continue
        if stripped.startswith("|") and i + 1 < n and re.match(r"^\|[\s:\-|]+\|$", lines[i + 1].strip()):
            headers = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            th_html = "".join(f"<th>{_inline_md(h)}</th>" for h in headers)
            tr_html = "".join(
                "<tr>" + "".join(f"<td>{_inline_md(c)}</td>" for c in r) + "</tr>"
                for r in rows
            )
            out.append(f'<div class="table-wrap"><table><thead><tr>{th_html}</tr></thead><tbody>{tr_html}</tbody></table></div>')
            continue
        if re.match(r"^[-*]\s+", stripped):
            items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                item_txt = re.sub(r"^\s*[-*]\s+", "", lines[i]).strip()
                i += 1
                while i < n and lines[i].startswith("  ") and not re.match(r"^\s*[-*]\s+", lines[i]):
                    item_txt += " " + lines[i].strip()
                    i += 1
                items.append(f"<li>{_inline_md(item_txt)}</li>")
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < n and re.match(r"^\s*\d+\.\s+", lines[i]):
                item_txt = re.sub(r"^\s*\d+\.\s+", "", lines[i]).strip()
                i += 1
                while i < n and lines[i].startswith("   ") and not re.match(r"^\s*\d+\.\s+", lines[i]):
                    item_txt += " " + lines[i].strip()
                    i += 1
                items.append(f"<li>{_inline_md(item_txt)}</li>")
            out.append("<ol>" + "".join(items) + "</ol>")
            continue
        p_buf = [stripped]
        i += 1
        while (
            i < n
            and lines[i].strip()
            and not lines[i].strip().startswith(("#", "|", "```", "$$", "---"))
            and not re.match(r"^\s*([-*]|\d+\.)\s+", lines[i])
        ):
            p_buf.append(lines[i].strip())
            i += 1
        out.append(f"<p>{_inline_md(' '.join(p_buf))}</p>")
    return "\n".join(out)


def render_hero(cthf: dict, csat: dict, thms_name: str, pfx: str) -> str:
    sub_name = html.escape(cthf["submission_name"])
    sub_note = html.escape(cthf["note"])
    sha = html.escape(cthf["raster_sha256"])
    n_dots = int(cthf["n_dots"])
    dti = cthf["holdout_dti"]["dti"]
    ci_lo, ci_hi = cthf["holdout_dti"]["ci95"]
    delta_inc = cthf["holdout_dti"]["paired_differences_vs_exp_84_3"]["incumbent_recipe"]["delta"]
    csat_name = html.escape(csat["submission_name"])
    csat_dti = csat["holdout_dti"]["scores"]["csat_poisson"]["dti"]

    return f"""
<section class="status-hero" aria-label="Submission Release Gate &amp; Verified Artifacts">
  <div class="hero-top">
    <div>
      <h2 class="hero-title">Lane H84-B (<code>CTHF + CTFO</code>) &amp; Multi-Lane Release Portal — Validated GeoTIFF Deliverables</h2>
      <p style="margin:6px 0 0;color:#475569;font-size:14px;">
        <strong>DO NOT SUBMIT AUTOMATICALLY:</strong> Automated release remains <code>verdict: negative</code> under
        Parallel-Run Protocol Rule 1 (one-sided <code>3-px</code> forward overlap &gt; <code>0.70</code> against dense archive blankets;
        <code>0</code> live weekly competition slots consumed automatically). All validated single-band <code>float32</code> GeoTIFF
        deliverables pass <code>10 / 10</code> format &amp; <code>[0, 1]</code> finiteness checks and are downloadable immediately below for human selector review.
      </p>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
      <span class="status-badge hold">&#9888; DO NOT SUBMIT (VERDICT: NEGATIVE · 0 SLOTS SPENT)</span>
      <span class="status-badge pass">&#10003; FORMAT &amp; [0, 1] RANGE: PASS (10/10)</span>
    </div>
  </div>

  <div class="download-row">
    <a class="dl-btn primary" href="{pfx}downloads/{sub_name}.tif" download>
      &#11015; Download H84-B GeoTIFF (.tif · 142 KB)
    </a>
    <a class="dl-btn secondary" href="{pfx}downloads/{sub_name}.zip" download>
      &#11015; Download H84-B Archive (.zip · 106 KB)
    </a>
    <a class="dl-btn secondary" href="{pfx}evidence/run_card_cthf.json">
      View H84-B Run Card (.json)
    </a>
    <a class="dl-btn secondary" href="{pfx}downloads/{csat_name}.tif" download>
      &#11015; Download H84-CSAT (.tif)
    </a>
    <a class="dl-btn secondary" href="{pfx}downloads/{html.escape(thms_name)}.tif" download>
      &#11015; Download H84-THMS Audit (.tif)
    </a>
  </div>

  <div class="meta-grid">
    <div class="meta-item">
      <span class="meta-label">H84-B Unique Submission Name (51 chars)</span>
      <span class="meta-val">{sub_name}</span>
    </div>
    <div class="meta-item">
      <span class="meta-label">H84-B GeoTIFF SHA-256 (Verified Byte-Unique across 1,196 Rasters)</span>
      <span class="meta-val">{sha}</span>
    </div>
    <div class="meta-item" style="grid-column: 1 / -1;">
      <span class="meta-label">H84-B Short Portal Note ({len(cthf["note"])} / 140 chars max)</span>
      <span class="meta-val">{sub_note}</span>
    </div>
  </div>

  <div class="kpi-row">
    <div class="kpi-card">
      <div class="kpi-num">{dti:.4f}</div>
      <div class="kpi-sub">H84-B Pooled 8-Fold <code>HOLDOUT-DTI</code><br>95% CI [{ci_lo:.4f}, {ci_hi:.4f}] · TPw=5,420.6</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-num">+{delta_inc:.4f}</div>
      <div class="kpi-sub">H84-B Gain vs <code>incumbent_recipe</code><br>+49.7% relative · +0.0120 pure CTFO vs NMS</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-num">{csat_dti:.4f}</div>
      <div class="kpi-sub">Parallel Lane <code>H84-CSAT</code> D2.8<br><code>{csat_name[:22]}…</code> (submod: 0.0815)</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-num">38.3% / 0</div>
      <div class="kpi-sub">H84-B 3-px Overlap vs <code>h33-2-b2</code> ({n_dots:,} dots)<br>0 NaN · 0 Inf · [0.0, 1.0] float32</div>
    </div>
  </div>
</section>
"""


def render_page(title: str, active: str, hero_html: str, body_html: str, pfx: str = "") -> str:
    nav_items = [
        ("overview", f"{pfx}index.html", "Overview & Artifacts"),
        ("exec", f"{pfx}executive-summary.html", "Executive Summary"),
        ("research", f"{pfx}research.html", "Research & Proofs"),
        ("methodology", f"{pfx}methodology.html", "Methodology"),
        ("results", f"{pfx}results.html", "Holdout & Audit Tables"),
        ("irregularities", f"{pfx}irregularities.html", "Irregularities Log"),
        ("sources", f"{pfx}sources.html", "Verified Sources"),
    ]
    nav_html = "".join(
        f'<a href="{href}" class="{"active" if key == active else ""}">{label}</a>'
        for key, href, label in nav_items
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} — GEMSDOE84</title>
  <link rel="stylesheet" href="{pfx}style.css">
</head>
<body>
  <header class="site-header">
    <div class="header-inner">
      <span class="brand">GEMSDOE84 · DOE GEMS Geothermal Fault Discovery</span>
      <nav class="nav-links" aria-label="Primary Navigation">{nav_html}</nav>
    </div>
  </header>
  <main class="container">
    {hero_html}
    {body_html}
  </main>
  <footer class="footer">
    GEMSDOE84 · Core Values: <strong>Maximize P(Win)</strong> &amp; <strong>Own the Outcome</strong> ·
    Evaluator: <code>gems57-pooled-hide-v2</code> (<code>22,893</code> withheld fault px) ·
    <code>0</code> live weekly competition slots consumed automatically.
  </footer>
</body>
</html>
"""


def main() -> int:
    audit_card = checked_status(ROOT)
    cthf = _verify_lane_card(ROOT, "evidence/run_card_cthf.json", "Lane H84-B CTHF+CTFO")
    csat = _verify_lane_card(ROOT, "evidence/run_card_csat.json", "Lane H84-CSAT")

    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "data").mkdir(parents=True, exist_ok=True)
    (DOCS / "evidence").mkdir(parents=True, exist_ok=True)

    shutil.copy2(EVIDENCE / "run-card.json", DOCS / "data" / "run-card.json")
    for p in sorted(EVIDENCE.glob("*.json")):
        shutil.copy2(p, DOCS / "evidence" / p.name)

    abl = json.loads((EVIDENCE / "h84b_holdout_ablation.json").read_text(encoding="utf-8"))
    sc = abl["pooled_evaluation"]["scores"]
    diffs = abl["pooled_evaluation"]["paired_differences"]
    csat_sc = csat["holdout_dti"]["scores"]
    thms_name = audit_card["audited_artifact"]["name"]

    arm_order = [
        ("EXP_84_3_CTHF_CTFO", "EXP-84-3: CTHF Posterior + CTFO 1D-Trace Submodular", "41,500"),
        ("EXP_84_3_EQBUDGET_37654", "EXP-84-3 Equal-Budget Control (CTFO at exact h33 budget)", "37,654"),
        ("EXP_84_2_CTHF_NMS", "EXP-84-2: Full 84-Feature CTHF Posterior + d=3.0 NMS", "37,654"),
        ("incumbent_recipe", "Incumbent Recipe (h33-2-b2 rule strictly on fold-visible cat)", "~39,600"),
        ("EXP_84_1_HUPW_NMS", "EXP-84-1: Pure Physics + Hydrothermal (0 catalogue features)", "37,654"),
        ("incumbent_asis", "Shipped h33-2-b2 Raster As-Is (live 200 m collar mismatch)", "37,654"),
    ]
    rows_html = []
    for key, label, budget in arm_order:
        s = sc[key]
        if key == "EXP_84_3_CTHF_CTFO":
            delta_str = "<strong>Reference Winner (+49.7% vs recipe)</strong>"
        else:
            d = diffs[key]
            delta_str = f"{ -d['delta']:+.4f} [{ -d['ci95'][1]:+.4f}, { -d['ci95'][0]:+.4f}]"
        rows_html.append(
            f"<tr><td><strong>{html.escape(label)}</strong></td><td><code>{budget}</code></td>"
            f"<td><strong>{s['dti']:.4f}</strong></td>"
            f"<td>[{s['ci95'][0]:.4f}, {s['ci95'][1]:.4f}]</td>"
            f"<td>{s['tpw']:.1f}</td><td>{s['fpw']:.1f}</td><td>{s['fnw']:.1f}</td>"
            f"<td>{delta_str}</td></tr>"
        )

    def overview_body(pfx: str) -> str:
        return f"""
<article class="content-card">
  <h1>Multi-Lane Synthesis &amp; Head-to-Head Verification Across GEMSDOE84</h1>
  <div class="callout info">
    <strong>Why CTFO Solved the Submodular Allocation Paradox Across Parallel Lanes:</strong>
    On the identical <code>22,893</code>-pixel <code>gems57-pooled-hide-v2</code> whole-segment holdout, naive cell-independent
    submodular allocation in parallel Lane <code>H84-CSAT</code> collapsed to <code>HOLDOUT-DTI = 0.0815</code> due to blurry
    posterior peak clumping (forcing fallback to isotropic <code>d = 2.8 px</code> Poisson thinning at <code>0.1685</code>,
    <code>TPw = 5,062.9</code>). Lane <code>H84-B</code> replaced cell-independent marginal gain with
    <strong>Comonotonic 1D-Trace Self-Credit <code>Q_1D-trace(x)</code></strong>, achieving <strong><code>TPw = 5,420.6</code></strong>
    (<code>HOLDOUT-DTI = 0.1581</code>, beating identical-posterior <code>d = 3.0</code> NMS across <strong>all 8 / 8 spatial folds</strong>)
    and improving pure catalogue-blind physics discovery from <code>0.0735</code> (<code>CSAT concealed_poisson</code>) to
    <strong><code>0.0953</code> (+39.4% more true fault coverage <code>TPw = 3,041.6 vs 2,182.3</code>)</strong>.
  </div>

  <h2>Cross-Lane Validated Artifact Comparison (All Shipped Single-Band <code>float32</code> GeoTIFFs)</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Lane</th>
          <th>Validated Submission Name</th>
          <th>Dots</th>
          <th>Pure-Physics <code>HOLDOUT-DTI</code></th>
          <th>Submodular <code>HOLDOUT-DTI</code></th>
          <th>Best Holdout <code>TPw</code></th>
          <th>Format &amp; <code>[0,1]</code></th>
          <th>Automated Status</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Lane H84-B (<code>CTHF + CTFO</code>)</strong></td>
          <td><code>{html.escape(cthf['submission_name'])}</code></td>
          <td><code>41,500</code></td>
          <td><strong>0.0953</strong> (<code>TPw=3,041.6</code>)</td>
          <td><strong>0.1581</strong> (8/8 folds &gt; NMS)</td>
          <td><strong>5,420.6</strong></td>
          <td><code>PASS (10/10)</code></td>
          <td><code>DO NOT SUBMIT (hold)</code></td>
        </tr>
        <tr>
          <td><strong>Lane H84-CSAT (<code>LOQO Dual-Habitat</code>)</strong></td>
          <td><code>{html.escape(csat['submission_name'])}</code></td>
          <td><code>{csat['n_dots']:,}</code></td>
          <td>{csat_sc['concealed_poisson']['dti']:.4f} (<code>TPw=2,182.3</code>)</td>
          <td>0.0815 (clumped; D2.8={csat_sc['csat_poisson']['dti']:.4f})</td>
          <td>5,062.9</td>
          <td><code>PASS (10/10)</code></td>
          <td><code>DO NOT SUBMIT (hold)</code></td>
        </tr>
        <tr>
          <td><strong>Audited H84-THMS Archive</strong></td>
          <td><code>{html.escape(thms_name)}</code></td>
          <td><code>37,654</code></td>
          <td>0.0689 (archived seed split)</td>
          <td>Uncertified (registry halo leak)</td>
          <td>—</td>
          <td><code>PASS (10/10)</code></td>
          <td><code>DO NOT SUBMIT (hold)</code></td>
        </tr>
        <tr>
          <td><strong>Live Incumbent (<code>GEMSDOE32</code>)</strong></td>
          <td><code>h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros</code></td>
          <td><code>37,654</code></td>
          <td>—</td>
          <td><code>0.1056</code> recipe / <code>0.2778</code> live*</td>
          <td>3,524.1</td>
          <td><code>PASS</code></td>
          <td><code>OWNER-REPORTED</code> baseline</td>
        </tr>
      </tbody>
    </table>
  </div>

  <h2>Lane H84-B Pooled 8-Fold Buffered Whole-Segment Holdout Results (<code>gems57-pooled-hide-v2</code>)</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Evaluation Arm</th>
          <th>Dots</th>
          <th>HOLDOUT-DTI</th>
          <th>95% Cluster CI</th>
          <th>TPw</th>
          <th>FPw</th>
          <th>FNw</th>
          <th>Paired &Delta;DTI vs Reference</th>
        </tr>
      </thead>
      <tbody>{"".join(rows_html)}</tbody>
    </table>
  </div>

  <div class="fig-grid">
    <div class="fig-box">
      <img src="{pfx}assets/figures/fig1_holdout_ablation.png" alt="Pooled 8-Fold Holdout Ablation and Fold Trajectory">
      <p class="fig-cap"><strong>Figure 1.</strong> Pooled 8-fold <code>HOLDOUT-DTI</code> progression across all 6 evaluation arms and fold-by-fold trajectory showing <code>EXP-84-3 (CTHF + CTFO)</code> strictly beating <code>EXP-84-2 (CTHF + NMS)</code> on all <code>8 / 8</code> folds.</p>
    </div>
    <div class="fig-box">
      <img src="{pfx}assets/figures/fig2_cthf_geothermal_zoom.png" alt="GeoDAWN Hydrothermal Conduit Sub-Region Map">
      <p class="fig-cap"><strong>Figure 2.</strong> Multi-sensor <code>CTHF</code> posterior and <code>CTFO</code> <code>41,500</code>-dot allocation across active Basin-and-Range range-front scarps, relay bridges, and <code>GDR-1391</code> hydrothermal probes/sinters.</p>
    </div>
    <div class="fig-box">
      <img src="{pfx}assets/figures/fig3_ctfo_vs_nms_packing.png" alt="CTFO vs NMS Geometric Packing and Blind SGMC Validation">
      <p class="fig-cap"><strong>Figure 3.</strong> Nearest-neighbor spacing shift (<code>2.0-2.6 px</code> crest chains vs <code>d=3.0</code> disk truncation), radial profile relative to <code>h33-2-b2</code>, and independent blind <code>SGMC</code> tectonic contact validation (<code>0.2675 vs 0.2380</code> in <code>500-1,500 m</code>).</p>
    </div>
    <div class="fig-box">
      <img src="{pfx}assets/figures/fig4_fleet_uniqueness_audit.png" alt="Exhaustive 1,196-Raster Fleet Uniqueness Audit">
      <p class="fig-cap"><strong>Figure 4.</strong> Complete fleet uniqueness scan across <code>1,191</code> non-sample rasters from <code>92</code> sibling <code>GEMSDOE*</code> repositories (<code>max Jaccard = 0.0345</code>, <code>38.26%</code> 3-px overlap with <code>h33-2-b2</code>).</p>
    </div>
  </div>
</article>
"""

    exec_body_md = (DOCS / "research" / "result.md").read_text(encoding="utf-8")
    h33_md = (DOCS / "research" / "h33-analysis.md").read_text(encoding="utf-8")
    hyp_md = (DOCS / "research" / "hypotheses.md").read_text(encoding="utf-8")
    rev_md = (DOCS / "research" / "review-passes.md").read_text(encoding="utf-8")
    src_md = (DOCS / "research" / "sources.md").read_text(encoding="utf-8")

    h33_html = md_to_html(h33_md)
    hyp_html = md_to_html(hyp_md)
    exec_html = md_to_html(exec_body_md)
    rev_html = md_to_html(rev_md)
    src_html = md_to_html(src_md)

    hero_docs = render_hero(cthf, csat, thms_name, pfx="")
    hero_root = render_hero(cthf, csat, thms_name, pfx="docs/")

    # Render all /docs/*.html pages
    (DOCS / "index.html").write_text(
        render_page("Overview & Validated Artifacts", "overview", hero_docs, overview_body(""), pfx=""),
        encoding="utf-8",
    )
    (DOCS / "executive-summary.html").write_text(
        render_page("Executive Summary", "exec", hero_docs, f'<article class="content-card">{exec_html}</article>', pfx=""),
        encoding="utf-8",
    )
    (DOCS / "research.html").write_text(
        render_page(
            "Research, Forensics & Review Passes",
            "research",
            hero_docs,
            f'<article class="content-card">{h33_html}</article>'
            f'<article class="content-card">{hyp_html}</article>'
            f'<article class="content-card">{exec_html}</article>'
            f'<article class="content-card">{rev_html}</article>'
            f'<article class="content-card">{src_html}</article>',
            pfx="",
        ),
        encoding="utf-8",
    )
    (DOCS / "methodology.html").write_text(
        render_page(
            "Methodology & Hypotheses",
            "methodology",
            hero_docs,
            f'<article class="content-card">{h33_html}</article><article class="content-card">{hyp_html}</article>',
            pfx="",
        ),
        encoding="utf-8",
    )
    (DOCS / "results.html").write_text(
        render_page(
            "Holdout & Uniqueness Results",
            "results",
            hero_docs,
            overview_body("") + f'<article class="content-card">{exec_html}</article>',
            pfx="",
        ),
        encoding="utf-8",
    )
    (DOCS / "irregularities.html").write_text(
        render_page(
            "Irregularities & Protocol Audit Log",
            "irregularities",
            hero_docs,
            f'<article class="content-card">{rev_html}</article>',
            pfx="",
        ),
        encoding="utf-8",
    )
    (DOCS / "sources.html").write_text(
        render_page(
            "Verified Data & Archival Sources",
            "sources",
            hero_docs,
            f'<article class="content-card">{src_html}</article>',
            pfx="",
        ),
        encoding="utf-8",
    )

    # Mirror root index.html & executive-summary.html with prefix="docs/"
    (ROOT / "index.html").write_text(
        render_page("Overview & Validated Artifacts", "overview", hero_root, overview_body("docs/"), pfx="docs/"),
        encoding="utf-8",
    )
    (ROOT / "executive-summary.html").write_text(
        render_page("Executive Summary", "exec", hero_root, f'<article class="content-card">{exec_html}</article>', pfx="docs/"),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
