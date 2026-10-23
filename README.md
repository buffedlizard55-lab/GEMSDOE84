# GEMSDOE84 — evidence-first fault prediction for geothermal exploration

## Executive summary: DO NOT SUBMIT

**No new unique submission TIFF was generated this session.** The required literal duplicate-stop rule fired before new placement. We did not rename or copy an old file and call it new. No weekly competition slot was used or authorized.

**[Download the existing TIFF — RESEARCH ONLY, DO NOT SUBMIT](docs/downloads/gems84-h84-thms-dink300-37654dots-20261022-2f4190b4-zeros.tif)**

- Archived name: `gems84-h84-thms-dink300-37654dots-20261022-2f4190b4-zeros`.
- SHA-256: `509fa4971a3cdf119a0ae7140b0fac31860d063af9bcc914266d98294f2ba7b5`.
- Local reopened TIFF checks pass: single-band float32, finite values everywhere in `[0,1]`, no NaN in the footprint, reference CRS/shape/transform match, zero positive pixels on the mapped catalogue.
- **Literal registry uniqueness fails:** forward 3-pixel overlap is **1.0**, above **0.70**, against a freshly retrieved immutable registry witness. Its halo covers every allowed cell. Under this positive-support interpretation no nonempty candidate can pass. This is a protocol stop, not proof of copying.
- **No new HOLDOUT-DTI or ORGANIZER-CONFIRMED score is claimed.** The archived production-like holdout has a full-catalogue registry dependency and is not certified leakage-free. A prediction or expected objective is never a competition score.

[Submission guide](docs/executive-summary.html) · [Current audit / run card](run_card.json) · [Machine-readable status](registry/release_status.json) · [Scientific review and four ranked hypotheses](research/SESSION_REVIEW_20261023.md) · [Source ledger](registry/sources.json)

## Parallel session 2026-10-22/23 — Lane H84-CSAT (Holdout +0.0629 DTI; NEGATIVE / DO NOT SUBMIT)

A parallel session executed preregistered lane **H84-CSAT** (Out-of-Quadrant Dual-Habitat 3D Contact-Depth + Counterfactual Strain-Transfer across 58 physical/geothermal/LiDAR/GeoDAWN/strain-transfer features, 3-experiment cap respected): run card [`evidence/run_card_csat.json`](evidence/run_card_csat.json), 5 preregistered hypotheses [`docs/research/hypotheses.md`](docs/research/hypotheses.md), results [`docs/research/result.md`](docs/research/result.md), and irregularities [`docs/liti/irregularities.md`](docs/liti/irregularities.md).

- **New unique GeoTIFF generated (`DO NOT SUBMIT`):** [`docs/downloads/gemsdoe84-h84-csat-d28-20261022T234500Z-a5483424-zeros.tif`](docs/downloads/gemsdoe84-h84-csat-d28-20261022T234500Z-a5483424-zeros.tif) (`142,515` B, SHA-256 `380eac60eb18d835e44cf64057f7021013753c7d45f287d540413304bcac580d`, `38,453` binary dots in `{0.0, 1.0}`, verified 1-TIFF [`docs/downloads/gemsdoe84-h84-csat-d28-20261022T234500Z-a5483424-zeros.zip`](docs/downloads/gemsdoe84-h84-csat-d28-20261022T234500Z-a5483424-zeros.zip), 117-char note `"GEMSDOE84 H84-CSAT LOQO dual-habitat 3D contact-depth + strain-transfer D2.8 c2.5 zeros; holdout DTI 0.1685 vs 0.1056"`). Passes 18/18 format/CRS/range checks (`0` NaNs, `[0.0, 1.0]`, `EPSG:32611`, `3730x3292`, `0` dots on mapped catalogue).
- **Leakage canary & 1,160-raster surface gate (`EXP-84-1`):** 58-feature canary **PASS** (`max(AUC, 1-AUC) = 0.76042 <= 0.90`; max catalogue-blind `0.56467`). Pre-placement surface vs `1,160 / 1,160` organization rasters **PASS** (`max |Spearman rho| = 0.73533 <= 0.90`).
- **Paired `HOLDOUT-DTI` (`gems57-pooled-hide-v2`, `22,893` withheld+, 158 20-km clusters):** `csat_poisson` **`0.16850` `[0.15468, 0.18167]`** vs `incumbent_recipe` `0.10564` (`+0.06285` `[+0.04793, +0.07900]`, `+59.5%`) and vs fold-clean 19-band `retrained_h19_control` `0.06991` (`+0.09859`, `2.41x`). Purely catalogue-blind `concealed_poisson` (`0.07351`) beats the 19-band control with zero fault-catalogue inputs at inference.
- **Why `verdict = "negative"` (`0` weekly slots used):** (1) **`IR-84-11`:** Primary preregistered allocator `csat_submod` (`vendor/gems57/emit.py::greedy_allocate`) clamps `kself = min(E[k], 1.0)`, collapsing `c*(1-k)` to `0` (`0.08153` vs `0.16850`). (2) **`IR-84-12`:** Although `0` overlap flags occur across all `1,006` comparable (`<=55k`-dot) submissions (max Jaccard `0.03912`, `0.55899 <= 0.70` vs `H84-THMS`), `binding_duplicate_decision` flags `30` broad `56k-1.83M`-px corridor-blanket priors (worst `0.90945` vs `GEMSDOE3:coverage-v3-wide` `[624,025 px]`, plus `1.00000` vs literal dense `17GEMSDOE`).

## Parallel session 2026-10-23 — Lane H84B-UAS (also NEGATIVE / DO NOT SUBMIT)

A parallel session from the same prompt ran a new preregistered lane **H84B-UAS** (uncertainty-adaptive dot spacing on a distance-blind 59-channel bagged-HGB surface) to completion: 3 experiments, run card [`registry/run_card_h84b.json`](registry/run_card_h84b.json), analysis [`research/h84b_results_and_h33_correction.md`](research/h84b_results_and_h33_correction.md); site page: [`docs/h84b/index.html`](docs/h84b/index.html) (kept outside the generated portal pages; the parallel review's 'no new submission generated' statement covers its own session).

- **New unique GeoTIFF generated:** `gems84b-uas-ctrl-37654dots-20261023-2f774850-zeros` (sha256 `38f0e886…`, in `submissions/` only — kept out of `docs/downloads/` by the archived-only downloads test) — locally format-valid (15/15: binary {0,1}, 0 NaN, [0,1] guaranteed, CRS/shape/transform match, 0 dots on catalogue) and distinct from every *dotted/binary* registry entry measured (max 3-px overlap 0.444, max |ρ| 0.084 vs 7-raster subset incl. H33). **It is nevertheless DO NOT SUBMIT:** (a) the lane hypothesis is falsified (below), so the file is the control-arm surface; (b) its literal forward overlap vs the space-filling 17GEMSDOE witness measures **1.0 > 0.70** (independently re-measured this session), so it is blocked by the same protocol stop as H84-THMS. Research download only.
- **Holdout (all HOLDOUT-DTI, whole-segment block holdout, 59,282 withheld px, budget-matched):** fixed-2.83px control **0.1703 [0.1457, 0.1983]** (reproduced exactly) · σ-adaptive spacing 0.1570 · sharpness-adaptive 0.1561 · soft-fractional 0.1356 — both adaptive mechanisms **falsified**; leakage canary PASS (max AUC 0.5735). Programme finding: H33-style fixed ≈kernel-radius spacing is near-optimal; remaining headroom is top-tail ranking quality, not emission geometry.
- **IR-84B-02 (critical):** prior promotion docs claimed H33 dots at median 5.385 px / max 12 px from the catalogue. Re-measurement on the SHA-verified H33 file: **median 19.65 px, max 219.3 px** — the "1.2 km truncation" narrative is retracted. H33 genealogy/score-chain claims remain owner-supplied, not re-verified (see `research/SESSION_REVIEW_20261023.md`).

**Unblock condition (applies to every lane):** an explicit owner protocol revision of the duplicate gate's support definition (e.g. support := each registry raster's own emitted dots / top-budget support, instead of literal `>0` on continuous surfaces). Until then the gate is mathematically unsatisfiable and no slot may be spent.

## What changed in this review

Three passes: inspect/reproduce; test and repair; rebuild/check against the brief.

1. Retrieved an immutable registry witness and used the **unchanged shared literal comparator and saturation certificate** to refute the earlier promotion. Dense priors were previously truncated/exempted, contrary to the literal rule. No new scientific lane was selected; this review stays with inherited H84-THMS.
2. Reopened the archived TIFF and independently checked its grid/range. Local format validity does not mean organizer acceptance or permission to spend a slot.
3. Fixed broken evaluator/writer command wrappers that imported nonexistent shared functions. The original tests passed while those commands failed. CLI smoke tests now cover them.
4. Removed full-catalogue registry halos from the holdout A5 emission path and invalidated its old cached-report policy. **No replacement score has been run or claimed.** The existing archived evidence is preserved as historical, not silently upgraded to clean evidence.
5. Rebuilt every public HTML entry point with an explicit research-only download, executive submission guide, current blockers and source retrieval statuses. One audit drives all current run-card projections. Historical scores and claimed source verification are not treated as fresh receipts.
6. Guarded legacy generation commands against the recorded lane stop. Added regression tests and generated-site drift checks to CI/deployment.

## H33 analysis and scientific next steps

The upstream H33 evidence starts from an inherited GEMSDOE28 base and prunes near-catalogue dots. Reducing redundant prediction mass can improve a distance-aware Tversky precision/coverage tradeoff. This explains a plausible mechanism, **not the exact hidden credit or a guaranteed future leaderboard gain**. Its supplied result has no organizer receipt here. Neither conflicting leaderboard target is freshly verified.

Ranked within-lane proposals: (1) transport/elevation-residual thermal plume heads; (2) azimuthal MT clay-cap breaches; (3) reactivated seal versus fossil outflow matched controls; (4) replicated thermal/scarp breaks across independent catchments. These are qualitative expected-utility rankings, not projected scores. Specific layers, signatures, mimics, differences and data limitations are in the [current review](research/SESSION_REVIEW_20261023.md). None is claimed globally novel, executable with missing inputs, or validated after a duplicate stop.

Fault prediction is an exploration proxy, not direct proof of a geothermal vent, sustainable flow or a commercial resource.

## Reproduce the audit and site

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
mkdir -p .cache/audit
# Immutable public team-registry witness, not training data or a copied candidate.
gh api repos/buffedlizard55-lab/17GEMSDOE/git/blobs/374c88b1da2b803e2ed160de467fd71ae114010d \
  -H 'Accept: application/vnd.github.raw' > .cache/audit/registry-witness.tif
.venv/bin/python scripts/audit_release.py  # expected exit 2: NEGATIVE, mandatory stop
.venv/bin/python scripts/build_run_card.py
.venv/bin/python scripts/build_site.py
.venv/bin/python scripts/evaluate_holdout.py  # clearly labelled archived report, not a rerun
.venv/bin/python scripts/submission_writer.py # inspect existing file only, no generation
.venv/bin/python -m pytest -q
```

The witness SHA-256 must be `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`; corruption or grid mismatch raises an error. Missing witness/evidence is a blocker, never clearance. The single-witness scan can prove failure, not uniqueness. New generation commands fail before fitting/placement while `stop_required` is true.

The existing `scripts/download_competition_data.sh` restores hash-pinned **team mirrors**, not authenticated organizer downloads. It is not sufficient for every optional THMS input. Training/external caches are absent here. Do not overwrite archived experiment reports or claim all-feature reproducibility from file presence alone. Use `.venv/bin` on `PATH` when invoking shell scripts.

## Access limits, sources and ownership

Only GitHub/API/codeload, npm and PyPI domains are reachable. The official reference repository was retrieved; official DrivenData pages, rules PDF, USGS/GDR data and live cap/leaderboard could not be retrieved under this policy. Their links are retained for review, **not labelled verified**. The competition ID conflict in prior records remains unresolved. GitHub Pages is already configured for legacy main/root publishing. Switching to workflow mode returned a settings-permission 403; the workflow detects legacy mode instead of attempting an incompatible deployment. Root and docs entry points are consistent. No credentials were requested or stored.

**Next session:** the protocol owner/selector must explicitly resolve the saturated-registry definition before any nonempty TIFF can qualify. A representation-aware rule would be a policy change, not silently binding now. Then restore/authenticate all source metadata, freeze a comparable buffered whole-segment holdout, run individual canaries and the top residual-thermal proposal without full-catalogue registry side channels, report pooled DTI with CI/count/version, and run complete surface/final-dot audits before packaging. Promotion is a separate selector decision within the **currently verified** weekly cap, which is unknown here.

Core values: **Maximize P(Win)** means protecting scarce slots from invalid evidence. **Own the Outcome** means fixing automatic false readiness, not replacing verification with confident language.

## Standing prompt — read at the start of every session

The following operational brief is reproduced from `PROMPT.md`, with duplicate project requirements consolidated there. It is **not an exact transcript of the long repeated user message**. Full historical conversation remains outside this repository; do not describe earlier abridgements as verbatim. The user supplied-results table is retained in `registry/live_scores.csv` as user-reported, not official receipts.

<!-- STANDING_BRIEF_START -->
# Standing brief (read at the start of every session)

> Copied from the project owner's session prompt (2026-10-22). Treat it as the
> requirements spec. Scores below are **OWNER-REPORTED** unless an organizer
> receipt is attached; the leaderboard values quoted (0.4413 current GEMSDOE-listed
> high score, 0.3195 earlier public leader) could not be re-read from this sandbox
> because drivendata.org is outside the egress allow-list (see `docs/irregularities.md`).

## Highest urgency

MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS
SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. IT MUST BE OBVIOUS WHETHER IT IS
OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.

There should be an easy to download submission tif file as described by the prompt.
The inspection needs to be done through the project and needs to be validated for
submission without human intervention.

## PARALLEL-RUN PROTOCOL — read first

This session is one of several running from this same prompt.

1. **LANE.** Your lane is the single method paragraph below. Stay inside it. If your
   raster's rank-correlation with any registry raster exceeds 0.90, or more than 70%
   of your dots fall within 3 px of one registry raster's dots, you have drifted into
   another lane: log it as a duplicate and stop. Check this on the surface before
   placement AND on the final dots.
2. **REUSE, DON'T REBUILD.** Use the template's cached feature stack,
   `evaluate_holdout.py` and `submission_writer.py`. Holdout = hide-and-recover:
   withhold whole fault segments with a buffer, derive every catalogue-based feature
   only from the visible faults, mask visible faults pixel-exactly, score pooled DTI
   (alpha 0.2, beta 0.8, 300 m triangular kernel). If a shared tool is wrong, fix it
   once in the template and report it; never keep a private fork.
3. **LABEL EVERY NUMBER** as HOLDOUT-DTI (evaluator version, number of withheld
   positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt).
   A projection is never written as a score.
4. **LEAKAGE CANARY.** Test each feature alone on the holdout before trusting any
   result. AUC above 0.90 means leakage until proven otherwise.
5. **RUN CARD.** End with one JSON card: hypothesis; mechanism; the named non-fault
   process that could mimic it; holdout DTI + CI; correlation/overlap vs registry;
   raster sha256; validator output (no NaN inside the footprint, values in [0,1],
   CRS/shape/transform match); submission name + note of at most 140 characters;
   verdict promote / negative. Negative results are deliverables.
6. **BUDGET.** Stop after 3 experiments or 2 hours. Do not pick submissions:
   promotion to a real slot is a separate selector step, within the weekly cap shown
   on the submission page.

## Questions to answer

* Study the highest family score — GEMSDOE32
  `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778`
  (<https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html>).
  Why and how did it get the highest score, and can we generate a submission that
  scores higher? Answer with PhD-level judgement, then use the answer to generate a
  unique TIF unlike any on the GEMSDOE sites. Verify line by line, no hallucinations.
* Before implementing, generate 3–5 untried geological hypotheses, each naming the
  layer(s), the physical signature, why it should catch a fault missing from the
  USGS/INGENIOUS catalogue, and how it differs from anything already implemented.
  Rank by expected DTI improvement and cost. Validate the top candidate on the
  spatially-blocked holdout before touching a weekly slot. If a candidate needs new
  external data, name the free official source and check it is obtainable.
* Do deep research on the scientific discovery of geothermal systems, store the
  knowledge from official sources, be contrarian but grounded.
* The site must make the downloadable TIF obvious (executive summary at the very top),
  with a unique name and a short note (e.g. "clustering with k=25"); an executive
  summary subpage must explain exactly how to submit. A previous download failed
  with "Predicted values must be in range [0, 1]" — every file must be all-finite and
  in [0, 1].
* Submission page text: "You can submit a single-band GeoTIFF (.tif) file, or a .zip
  file containing a single GeoTIFF, with your predictions. It must match the
  submission format's CRS, shape, and geotransform."
* Core values: **Maximize P(Win)** and **Own the Outcome**.
* Multi-pass: implement + verify; review for bugs/assumptions/edge cases; re-check
  against the request. Then open a PR, merge it to main, and list remaining work and
  limitations.

## Family results supplied by the owner (OWNER-REPORTED live scores)

The complete table (103 scored rows, GEMSDOE … GEMSDOE77) is machine-readable in
[`registry/live_scores.csv`](registry/live_scores.csv); rows for GEMSDOE78–88 were
listed without scores. Key rows: GEMSDOE32 h33-2-b2 0.2778 · GEMSDOE36 Anderson PINN
0.2750 · GEMSDOE28 h36-1 0.2710 / h27-4 0.2708 · GEMSDOE25 d2.8 0.2600 ·
GEMSDOE70 0.2478 · GEMSDOE24 d1.5 0.2477.

## Official links

* Competition: <https://www.drivendata.org/competitions/306/competition-doe-gems/>
* Problem description (metric): <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
* About: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/>
* Data (login): <https://www.drivendata.org/competitions/306/competition-doe-gems/data/>
* Leaderboard: <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>
* Rules PDF: <https://docs.nlr.gov/docs/fy26osti/96647.pdf>
* Reference solution: <https://github.com/drivendataorg/gems-prize-reference-solution>
* GeoDAWN surveys: <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>
* INGENIOUS: <https://gbcge.org/current-projects/ingenious/> · GDR 1391: <https://gdr.openei.org/submissions/1391>
* EPSG:32611: <https://epsg.io/32611> · Tversky index: <https://en.wikipedia.org/wiki/Tversky_index>

<!-- STANDING_BRIEF_END -->
