# Three-Pass Implementation, Audit & Verification Record (`GEMSDOE84`)

## Pass 1 — Research, Pre-Registered Hypotheses, & Full 3-Experiment Execution

1. **Repository & Family Forensics:** Merged outstanding PRs #1–#7 into `arena/825b0be4-gemsdoe84`, verified SHA-256 pins on `vendor/gems57/*` (`registry/template_pin.json`) and archival files (`research/source-receipts.json`), reconstructed `GEMSDOE32` `H33-2-B2` (`0.2778` `OWNER-REPORTED`) algebraically (`evidence/incumbent_anatomy.json`), and live-verified DrivenData leaderboard (`#1 = 0.4413` `ORGANIZER-CONFIRMED`), Problem Description, About, DOE/NLR Official Rules PDF (`NREL/TP-5700-96647`), USGS GeoDAWN (`10.5066/P93LGLVQ`), and DOE GDR 1391 (`10.15121/1881483`).
2. **Pre-Implementation Hypotheses (`docs/research/hypotheses.md`):** Registered 5 falsifiable structural/geophysical hypotheses (`H84-B`..`H84-F`), ranked by expected DTI gain vs compute cost, and locked onto single coherent lane **`H84-B` (`H84-TCDH`)**.
3. **Smart-HTTP Hydration & Leakage-Safe Feature Stack (`src/gems84/tcdh.py`):** Hydrated SHA-256-verified training/external stacks and **1,163** unique registry GeoTIFFs via smart-HTTP blob-less clones (`0` GitHub REST API calls), neutralized `-3.4028235e+38` finite sentinels (`IR-84-12`), dropped precomputed `dist_known_fault_px` columns (`IR-84-13`), masked `!= -32768` on `dem10_chi_100m_i16.tif`, and verified all 52 single-feature symmetric holdout AUCs `<= 0.7724 <= 0.90` (`EXP-84B-1`).
4. **Controlled Validation, Uniqueness Resolution, & Automated Packaging (`EXP-84B-1..3`):**
   - `EXP-84B-1` (`evidence/exp84b1_ablation.json`): Proved 2-stage 4-quadrant LOQO `H84-TCDH` beats both `incumbent_h33_b2_recipe` (`+0.0195`, `95% CI [+0.0062, +0.0339]`) and `ctrl_base19_anat` (`+0.0042`, `95% CI [+0.0018, +0.0067]`).
   - `EXP-84B-2` & `EXP-84B-3`: Caught and transparently logged unstratified `alloc_fixed_nms3_37k`'s Gate 3B stop (`0.8955 > 0.70` due to wide-swath `< 0.70` halo priors; `evidence/exp84b3_unstratified_gate3b_stop.json`), resolved structurally via pure sensor-derived Two-Stratum `alloc_twostrat_nms3_39k` (`24,500` corridor/relay/tip + `14,500` concealed low-relief basin interior = `39,000` dots), clearing Gate 3A (`0.2629 <= 0.90`), Gate 3B (`0.6760 <= 0.70` across all 1,092 discriminating priors), and pooled `HOLDOUT-DTI` (`0.1234` vs `0.1056`, `Δ = +0.0178`, `95% CI [+0.0040, +0.0321]`), and packaged `gems84-h84b-tcdh-twostrat-39000d-20261022T235800Z-zeros.{tif,zip,json}`.

## Pass 2 — Deep Bug, Edge-Case, CI, & Link Review

1. **GitHub Actions CI Idempotency Fix (`.github/workflows/ci.yml`):** Discovered `ci.yml` executes `pip install -r requirements.txt`, `python -m pytest -q`, `python scripts/build_site.py`, and `git diff --exit-code -- docs`. Added `pandas>=2.2,<3` to `requirements.txt` and replaced the legacy negative-only `scripts/build_site.py` with a 100% deterministic standard-library generator producing zero diff on re-run.
2. **Visual Inspection of All 4 Diagnostic Figures:** Inspected `docs/assets/figures/fig1..4.png` directly and fixed label spacing in `fig3` (deduplicated sibling registry mirrors, separated `d1-5`/`B1` annotations, padded bottom legend whitespace) and `fig4` (3-line x-axis category labels and subplot `wspace`).
3. **GitHub Pages Root Serving Mode (`main:/`):** Inspected `gh api repos/buffedlizard55-lab/GEMSDOE84/pages` (`build_type: "legacy"`, `source: main:/`). Added `/.nojekyll` at repo root and upgraded root `index.html` redirect + fallback download card so both `/GEMSDOE84/` and `/GEMSDOE84/docs/index.html` land immediately on the promoted portal.
4. **Stale Markdown Cleanup:** Updated leftover PR #5 markdown notes in `docs/research/{result,h33-analysis,sources,review-passes}.md` and synchronized all 7 JSON run-card copies to identical SHA-256 digests.

## Pass 3 — Final Line-by-Line Prompt Audit & Polish

1. **Prompt Acceptance Criteria Audit:** Verified every single requirement from the user's brief:
   - Unique `.tif` + `.zip` downloadable right at the top of `docs/index.html` and `docs/executive-summary.html` with unmistakable `OK TO DOWNLOAD & SUBMIT` status? **Verified.**
   - Dedicated Executive Summary subpage (`docs/executive-summary.html`) explaining step-by-step how to submit, DOE Official Rules §3.2 AI disclosure + 3/week limit, and how `"Predicted values must be in range [0, 1]"` was fixed? **Verified.**
   - Every validation check automated in `pytest` (`35 passed`) without requiring human inspection? **Verified.**
   - Strict `HOLDOUT-DTI` (with `gems57-pooled-hide-v2`, `22,893` withheld positives, 95% CI) vs `ORGANIZER-CONFIRMED` vs `OWNER-REPORTED` labels, zero projections presented as scores? **Verified.**
   - Original prompt preserved in `README.md` (and `PROMPT.md`), `vendor/gems57/*` and `research/source-receipts.json` pins 100% intact, `data/raw` absent? **Verified.**
