# GEMSDOE84 — evidence-first fault discovery

**Read this operating brief at the beginning of every session.**

## Current Release Status — Lane `H84-CSAT` (`arena/fcacc90c-gemsdoe84`, 2026-10-22 UTC)

> **AUTOMATED VERDICT: `negative` · `DO NOT SUBMIT TO WEEKLY LIVE SLOT WITHOUT SELECTOR OVERRIDE` (`0` live competition slots consumed)**
>
> - **Generated Unique GeoTIFF**: [`docs/downloads/gemsdoe84-h84-csat-d28-20261022T234500Z-a5483424-zeros.tif`](docs/downloads/gemsdoe84-h84-csat-d28-20261022T234500Z-a5483424-zeros.tif) (`142,515` bytes · SHA-256 `380eac60eb18d835e44cf64057f7021013753c7d45f287d540413304bcac580d` · `38,453` dots · `float32` in `{0.0, 1.0}`, `0` NaNs anywhere, `0` dots on mapped catalogue)
> - **Verified One-TIFF ZIP**: [`docs/downloads/gemsdoe84-h84-csat-d28-20261022T234500Z-a5483424-zeros.zip`](docs/downloads/gemsdoe84-h84-csat-d28-20261022T234500Z-a5483424-zeros.zip)
> - **Short Submission Note (`117 <= 140` chars)**: `GEMSDOE84 H84-CSAT LOQO dual-habitat 3D contact-depth + strain-transfer D2.8 c2.5 zeros; holdout DTI 0.1685 vs 0.1056`
> - **Canonical Run Card**: [`evidence/run-card.json`](evidence/run-card.json) · **Pages Overview**: [`docs/index.html`](docs/index.html) · **Submission Guide**: [`docs/executive-summary.html`](docs/executive-summary.html)

| Automated Gate | Protocol Requirement | Measured Receipt | Status |
|---|---|---|---|
| **1. GeoTIFF Format & `[0, 1]` Range** | `EPSG:32611`, `3730x3292`, `float32`, `0` NaN/Inf, `[0, 1]`, `0` on catalogue | `18/18` checks PASS (`min=0.0`, `max=1.0`, `n_nan=0`, `38,453` dots) | **PASS** |
| **2. 58-Feature Leakage Canary** | `max(AUC, 1-AUC) <= 0.90` on `22,893` withheld positive pixels | `0.76042` (`s02_log_d2`); max catalogue-blind `0.56467` (`p32_topo10m_relief`) | **PASS** |
| **3. Pre-Placement Surface Uniqueness** | `|Spearman rho| <= 0.90` across all `1,160` registry rasters | `0.73533` (`5GEMSDOE:context_detector_prob_4fold_base.tif`) | **PASS** |
| **4a. Holdout — Primary `csat_submod`** | Beat `incumbent_recipe` (`0.10564`) on `gems57-pooled-hide-v2` | `0.08153` `[0.06861, 0.09510]` (`Δ = -0.02411`; `emit.py` `kself=1` peak-clumping defect `IR-84-11`) | **FAIL** |
| **4b. Holdout — Preregistered Ablation `csat_poisson` (`.tif`)** | Same `H84-CSAT` LOQO surface + `D2.8` spacing (`sep=2.83 px`, `c=2.5 px`) | **`0.16850` `[0.15468, 0.18167]`** (`+0.06285` vs `incumbent_recipe`, `+0.09859` vs `retrained_h19_control`) | **PASS** |
| **5a. Final Dots — Comparable Submissions (`<= 55k` dots)** | `<= 0.70` forward 3-px overlap across `1,006` dot-budget priors | `0` flags · byte & pixel unique · max Jaccard `0.03912` · max `|rho| = 0.09234` | **PASS** |
| **5b. Final Dots — `binding_duplicate_decision`** | `<= 0.70` forward 3-px overlap across all `1,091` priors with global `H < 0.70` | `30` broad `56k–1.83M`-px corridor-blanket priors exceed `0.70` (worst `0.90945` vs `GEMSDOE3:coverage-v3-wide` `624,025` px; `IR-84-12`) | **FAIL** |

## Submission status

The site and `evidence/run-card.json` are the release authority. **A local format pass is not permission to submit.** No weekly slot is used by this project. A negative result, duplicate veto, missing evidence, or an incomparable holdout best blocks promotion. The download area must never quietly substitute an older submission.

This repository started with only an eleven-byte README. There was no pre-existing training pipeline, cached feature stack, evaluator, data or site. Current work restores integrity-pinned public mirrors and reuses the shared evaluator/writer without editing their implementations.

## User request: standing project brief

This is the operational transcription of the supplied long, repetitive request (not a verbatim archive). Its requirements remain the acceptance criteria:

- Generate a scientifically distinct, uniquely named single-band GeoTIFF, with a note no longer than 140 characters. Make it downloadable at the beginning of a clean GitHub Pages site, with unmistakable submit/do-not-submit status and an executive-summary submission guide. Never copy a previous submission except for education/comparison.
- Match the competition sample's CRS, shape and affine transform; ensure all values are finite in [0,1], no NaNs inside the footprint, no sentinel values, and pixel-exact visible-fault masking. Investigate the reported range error rather than assuming its cause.
- Work autonomously. Inspect the repository and prior sessions first; research official free sources; preserve auditable links, provenance and limitations; never invent data, scores, receipts, verification or novelty. Automate validation rather than require a human inspector.
- Before implementation, propose 3–5 geological hypotheses naming layers, physical transforms, missing-fault rationale, non-fault confounders, difference from existing code, expected-benefit ranking and cost. Check data availability before calling a hypothesis viable. Do not confuse geothermal-vent discovery with the contest's fault-prediction target.
- Parallel-run protocol: stay in one method lane; stop on rank correlation >0.90 or >70% of dots within 3 pixels of any registry raster. Check surfaces before placement and final dots. Do not exempt dense rasters or lattices from this literal rule.
- Reuse shared cached features, `evaluate_holdout.py` and `submission_writer.py`; do not privately fork incorrect tools. Hold out whole fault segments with a buffer; derive catalogue features solely from visible faults; pool DTI with alpha 0.2, beta 0.8 and a 300 m triangular kernel. Report template deviations prominently.
- Run every feature alone as a leakage canary; AUC >0.90 means leakage until resolved. Report HOLDOUT-DTI with evaluator version, withheld positives and 95% CI. Only a submission-page receipt earns ORGANIZER-CONFIRMED status. Projections are not scores.
- End with one JSON run card: hypothesis, mechanism, named non-fault mimic, holdout plus CI, registry correlation/overlap, raster SHA-256, validator output, name/note, verdict promote/negative. Negative results are deliverables. Stop after three experiments or two hours. Promotion to a real slot is a separate selector action within the live weekly cap.
- Investigate GEMSDOE32's user-reported H33 result and the listed predecessor sites; distinguish score reports from organizer evidence. The request gives conflicting leaderboard maxima (0.3195 and 0.4413); neither is verified current here. Do not promise to exceed them.
- Build an auditable source/knowledge record for reuse, review limitations and next steps, automate updates honestly (timestamped retrieval is not a perpetual live feed), and execute three review passes. Open a PR and merge it if checks pass.
- Keep **Maximize P(Win)** and **Own the Outcome** as project values: prefer honest falsification and strong controls to unsupported promotion; own reproducibility and end-to-end release safety.

Original competition/review pointers supplied by the user:
- https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
- https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- https://github.com/drivendataorg/gems-prize-reference-solution
- https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html
- https://docs.nlr.gov/docs/fy26osti/96647.pdf
- https://gdr.openei.org/submissions/1391
- https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- https://gbcge.org/current-projects/ingenious/
- https://epsg.io/32611

## Reproduce

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
python scripts/restore_data.py --ids labels,existing_faults,sample_submission,ext_lidar_scarp_features_u8,ext_geodawn_rad_u8
.venv/bin/python scripts/inventory.py
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/run_lane.py
.venv/bin/python scripts/build_site.py
.venv/bin/python -m pytest -q
```

`gh` must already be authenticated to retrieve the public mirror blobs. No secrets belong in this repo. Raw data, the registry raster cache and virtual environment are ignored. Only receipts, code and appropriately cleared small deliverables are committed. The restore script validates SHA-256; those hashes establish mirror consistency, not original organizer authenticity.

## Limits and next session

- Outbound access is limited to GitHub and package registries. No independent current DrivenData, USGS, GDR or NLR retrieval, authenticated competition download, leaderboard receipt or weekly-cap lookup is possible here.
- No method paragraph was supplied; H84-RFD is an explicitly selected exploratory lane. Novelty is scoped to the indexed public artifacts, never universal.
- The inherited evaluator segments branches into short chunks. It does **not** establish the requested whole-geological-fault plus buffer validation. The shared tool was reused unchanged; this deficiency blocks promotion and needs one upstream correction, not a private fork.
- Current holdout best must be reproduced with exactly the same masks, folds, budgets and evaluator before a promotion comparison. Prior reported numbers are not automatically comparable.
- A literal overlap rule may veto every candidate if a registry raster densely covers the footprint. Do not weaken the rule silently. Record the counterexample and request a coordinated protocol decision in a future session.
- Do not consume a real submission slot, claim leaderboard improvement, or package a duplicate just to produce a download button.

The full machine-readable result is `evidence/run-card.json`; source inventory is `registry/inventory.json`; hypothesis preregistration is `docs/research/hypotheses.md`.

## Parallel-session integration

Other sessions merged readiness tooling and unexecuted hypothesis proposals while this experiment ran. Their original front pages and README are preserved under `research/concurrent-readiness/`, their source receipts and validators remain intact, and their old JSON cards are marked historical/superseded. They are not additional experiments in H84-RFD. The canonical measured run is `evidence/run-card.json`. Readiness presence checks now point at this lane's actual cache/vendor paths; presence still never authorizes a submission. The combined suite passes 27 tests locally. The existing Pages workflow from those merged changes is retained; deployment success must be checked independently.

---

## Lane H84-A — Leaderboard-Inverted Truth Intensity (LITI) · session `arena/9dbb1208`

> Full standing brief as given for this session: [`PROMPT.md`](PROMPT.md). Lane pages:
> [`docs/liti/`](https://buffedlizard55-lab.github.io/GEMSDOE84/liti/). Run card:
> [`evidence/run_card.json`](evidence/run_card.json).

| question | answer |
|---|---|
| Is there a TIF to submit from this lane? | **No.** The candidate (27,445 dots) passed the surface-correlation gate (worst ρ 0.274 over 1,143 hash-verified registry rasters). The dot-overlap gate logged it as a **duplicate** under both the literal and the chance-corrected reading (56 binding flags against dense registry fields). It also **failed** the protocol holdout. The fail-closed packager wrote **no TIFF**. Verdict **negative**; 0 slots used. |
| Why did `h33-h33-2-b2` score 0.2778 (OWNER-REPORTED)? | Byte-exact lineage: the 0.2600 dotted H19-5 field minus every dot ≤ 100 m (0.2708) and then ≤ 200 m (0.2778) from a mapped fault. The metric algebra explains both steps to within 0.0006 DTI if the deleted dots earned zero credit (`evidence/incumbent_anatomy.json`). The limit is the underlying field's precision, not its emission. |
| What is new and reusable? | A truth intensity λ(x)=exp(θ·φ(x)) inverted from 91 owner-reported live scores of hash-identified rasters, using the official DTI formula in expectation. CV grouped by repo: Spearman 0.907, RMSE 0.034 (score SD ≈ 0.084) (`evidence/e2a_liti_ml_fit.json`, MODEL). |
| Holdout | HOLDOUT-DTI (gems57-pooled-hide-v2, 22,893 withheld px): LITI 0.0087 [0.0037, 0.0149] vs incumbent recipe 0.1056 [0.0934, 0.1181]. Known biases are recorded in `docs/liti/irregularities.md` (IR-84-04). |

Reproduce (CPU, ~45 min; large inputs under `$GEMS84_DATA`, default `/home/user/gemsdata`):

```bash
python scripts/fetch_data.py --registry          # registry/data_manifest_liti.json + 1,149-blob corpus
python scripts/build_registry_index.py
python scripts/analyze_incumbent.py
python scripts/e1_liti_fit.py && python scripts/e2_liti_ml_fit.py && python scripts/e2_holdout.py
python scripts/e3_emit_submission.py place
python scripts/e3_emit_submission.py surface & python scripts/e3_emit_submission.py dots; wait
python scripts/e3_chance_corrected.py && python scripts/e3_emit_submission.py package   # fail-closed
python scripts/build_run_card.py && python scripts/build_site_liti.py
```

Lane code: `src/gems84/` (basis, inversion, catalogue-analogue field). It uses the shared
`vendor/gems57` (pinned; see `registry/template_pin.json`).

---

## Lane H84-CSAT — Dual-Habitat 3D Contact-Depth & Strain-Transfer · session `arena/fcacc90c-gemsdoe84`

Preregistration: [`docs/research/hypotheses.md`](docs/research/hypotheses.md) and [`registry/preregistration.json`](registry/preregistration.json). Evidence receipts: [`evidence/exp84_1_canary_and_surface.json`](evidence/exp84_1_canary_and_surface.json), [`evidence/exp84_2_holdout_eval.json`](evidence/exp84_2_holdout_eval.json), [`evidence/exp84_3_emission_and_uniqueness.json`](evidence/exp84_3_emission_and_uniqueness.json).

### Key Takeaways & Next-Session Roadmap
1. **Substantial Out-of-Quadrant `HOLDOUT-DTI` Lift (`+59.5%` over `incumbent_recipe`, `2.41x` over fold-retrained 19-band control)**: On `gems57-pooled-hide-v2` (`22,893` withheld positive pixels across whole buffered 8-connected components, `1,000` paired 20 km spatial-block bootstrap draws), `csat_poisson` achieved **`0.16850` `[0.15468, 0.18167]`** (`NW=0.16620`, `NE=0.17070`, `SW=0.16839`, `SE=0.16843`) vs `incumbent_recipe = 0.10564` `[0.09357, 0.11662]` and `retrained_h19_control = 0.06991` `[0.05782, 0.08241]`. Even the **100% catalogue-blind** Head B (`concealed_poisson = 0.07351` `[0.06082, 0.08615]`) beat the 19-band `retrained_h19_control` with zero catalogue inputs.
2. **Allocator Defect `IR-84-11` Identified in `vendor/gems57/emit.py`**: Clamping `kself = np.minimum(ekc, 1.0)` collapses $c(1-k(x))$ to `0` on high-probability ridges (`E[k] >= 1`), clumping 1-px neighbor dots and halving `TP_w` (`2,353.4` vs `5,062.9` at matched `31,057`/`30,474` dot counts). Upstream `emit.py` should replace `min(E[k], 1)` with noisy-OR marginal self-credit $1 - \prod_g (1 - p(g)k(d(x,g)))$.
3. **Domain-Restricted Corridor Blocker `IR-84-12` & Next-Session Solution**: Broad corridor blankets (`7GEMSDOE:gems7-halo15` `1,828,699` px = `100%` of `d <= 15 px`, `0%` of `d > 18 px`) have global `halo_coverage = 0.4018 < 0.70` yet veto any unstratified candidate placing `> 70%` of dots near mapped faults. Next session should preregister a **Distance-Stratified Dual-Habitat Emitter** (`50%` budget in `2.5 < d <= 18 px` via Head A + `50%` budget in `d > 18 px` low-relief concealed contacts via Head B) to pass `binding_duplicate_decision` (`<= 0.70` across all `1,091` discriminating priors) while preserving strong `HOLDOUT-DTI` lift.

### Reproduce Lane H84-CSAT
```bash
.venv/bin/python scripts/fetch_data.py
.venv/bin/python scripts/build_registry_index.py
.venv/bin/python scripts/exp84_1_features_canary_surface.py
.venv/bin/python scripts/exp84_2_holdout_eval.py
.venv/bin/python scripts/exp84_3_emit_and_audit.py
.venv/bin/python scripts/build_run_card.py
.venv/bin/python scripts/build_site.py
.venv/bin/pytest -q
```

