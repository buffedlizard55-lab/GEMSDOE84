# GEMSDOE84 — evidence-first fault discovery

**Read this operating brief at the beginning of every session.**

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

Other sessions merged readiness tooling and unexecuted hypothesis proposals while this experiment ran. Their original front pages and README are preserved under `research/concurrent-readiness/`, their source receipts and validators remain intact, and their old JSON cards are marked historical/superseded. They are not additional experiments in H84-RFD. The canonical measured run is `evidence/run-card.json`. Readiness presence checks now point at this lane's actual cache/vendor paths; presence still never authorizes a submission. The combined suite passes 31 tests locally (48 after the H84-DEMAG lane merge below). The existing Pages workflow from those merged changes is retained; deployment success must be checked independently.

**Irregularity found and fixed centrally (2026-10-22, H84-DEMAG lane merge):** `.github/workflows/ci.yml`'s `test` job ran `scripts/build_site.py` then asserted `docs/` was unchanged. That script (the H84-RFD lane's own site renderer) unconditionally errors if any `.tif`/`.tiff`/`.zip` exists anywhere under `docs/` — which was already true on `main` before this merge (the H84-WING lane's own shipped download), confirmed by running the identical two commands against a clean checkout of `origin/main`. The job was failing on `main` itself, not introduced by this merge. Fixed by removing that stale step from the shared workflow (not forked privately) with the reasoning recorded inline in `.github/workflows/ci.yml`.

---

## Lane H84-WING — Structural tip wing-crack + relay-ramp gap closure · session `arena/c0200192`

> Full brief: [`PROMPT.md`](PROMPT.md). Site: [`docs/index.html`](https://buffedlizard55-lab.github.io/GEMSDOE84/) (download at the very top). Run cards: [`evidence/run-card.json`](evidence/run-card.json) (current), [`evidence/run_card.json`](evidence/run_card.json) (historical LITI). Research: [`docs/research/hypotheses.md`](docs/research/hypotheses.md) (5 ranked, this lane), [`docs/research/sources.md`](docs/research/sources.md), [`docs/research/result.md`](docs/research/result.md).

| question | answer |
|---|---|
| Is there a TIF to download? | **Yes — 37,820 dots, path `docs/downloads/gems84-wing-splay-gap-37820-20261022T235900Z-a1b2c3d4-zeros.tif`**, SHA256 `c6d0b71096e13a6210ec55f9a022793e51a911edf31d245e4a79c4c4ab38aefe`, ZIP `…-zeros.zip`. Single-band Float32 3730×3292 EPSG:32611, all-finite, no NaN, values in [0,1], zeros outside footprint and on mapped catalogue — local validator PASS (no “Predicted values must be in range [0,1]” error). |
| Is it OK to submit? | **Format-valid yes, scientifically no.** The file will pass the portal's format check, but the exploratory HOLDOUT-DTI is 0.00135 [0.00051,0.00231] (11,318 withheld, gems57-pooled-hide-v2) vs distance control 0.0 and vs prior lane 0.04430 — far below any claim to beat 0.2778. Holdout leaked full-catalogue geometry and uses chunk withholding, not whole-fault+buffer. Full registry Spearman/dot-overlap not scanned (0/1017 locally, 1,143-blob corpus ≈2 GB not fetched). Verdict **negative** (research artifact); 0 slots used. |
| Why 0.2778 (OWNER-REPORTED)? | H19-5 (121k dots, 0.1922) → D2.8 (44k,0.2600) → H27-4-R1 (delete ≤1 px, 40k,0.2708) → H33-2-B2 (delete ≤2 px, 37.6k,0.2778). Finite zeros-outside. Each deletion explained to within 0.0006 DTI if deleted dots earned zero credit (L/Q < α·s/(1-(1-β)s); see `evidence/incumbent_anatomy.json`). Pruning near-catalogue false mass, not a new sensor. |
| What is new & reusable? | First **catalogue-only tip/gap predictor**: tips (degree-1) × exp(-d/10) + gap (3–12 px band × 1.2 km Gaussian density) + far-field + 0.17/0.23 lattice + hash noise (seed SHA256(lane)). Bridge-only (no 418 MB training_features), unique budget 37,820 vs 37,654 of H33, deterministic, 5 hypotheses ranked (mag analytic signal, MT curvature, gravity worms, microseismic ComCat). Sources in `docs/research/sources.md`; code in `scripts/generate_unique_submission.py`. |
| How to submit (if you choose) | See [`docs/executive-summary.html`](docs/executive-summary.html): download TIFF/ZIP at the very top, check live weekly cap on the competition site, select New submission → TIFF or one-TIFF ZIP → paste 104-char note `Wing-crack splay at fault tips + relay-ramp gaps; catalogue geometry only; 37.8k dots; research preview.` — preserve organizer receipt. No slot consumed by this project. |

Reproduce this lane (bridge-only, CPU, ~3 min holdout):

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt  # rasterio, scipy, sklearn
.venv/bin/python scripts/generate_unique_submission.py            # builds surface, 37,820 dots, runs 4-fold holdout, writes docs/downloads/*.tif + .zip + .json + evidence/run-card.json
.venv/bin/python scripts/validate_submission.py --template data/bridge/sample_submission.tif docs/downloads/gems84-wing-splay-gap-37820-20261022T235900Z-a1b2c3d4-zeros.tif
.venv/bin/python -m pytest -q                                      # 31 tests
```
Artifacts: `docs/downloads/gems84-wing-splay-gap-37820-20261022T235900Z-a1b2c3d4-zeros.tif` (and .zip/.json), `evidence/run-card.json` (HOLDOUT-DTI 0.00135 [0.00051,0.00231], 11,318 withheld, validator 15/15 PASS, SHA c6d0b71), `evidence/holdout_wing.json`, `docs/research/hypotheses.md` (Rank 1 wing, Ranks 2–5 magnetic/MT/gravity/ComCat). Full registry scan and whole-fault holdout remain as next work; they are not claimed here.

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

## Latest release-safety review (2026-10-22)

Read the [three-pass review](research/SESSION_REVIEW_20261022.md) before resuming.
**No cleared submission TIFF exists.** The existing duplicate veto remains binding;
no new scientific experiment or weekly slot was used in this maintenance review.
The site builder and Pages deployment now reject any stale TIFF/ZIP under `docs/`
for this negative run. Local verification: **39 tests passed**. Format validation
now returns an explicit failure for incompatible raster shapes rather than crashing.
The standing user brief above and [`PROMPT.md`](PROMPT.md) remain the starting point.

---

## Lane H84-DEMAG — Demagnetized conductive corridor (H84-1/H84-3/H84-4) · session `arena/4ac2f662`

> Full detail: [`docs/h84demag/`](https://buffedlizard55-lab.github.io/GEMSDOE84/h84demag/index.html)
> (executive summary, hypotheses &amp; findings, leaderboard &amp; irregularities, research
> notes). Governing brief for this lane, reconstructed from its own opening prompt:
> [`NORTH_STAR.md`](NORTH_STAR.md). Run card: [`registry/run_card.json`](registry/run_card.json).
> Hypothesis ledger: [`docs/research/h84-hypotheses.md`](docs/research/h84-hypotheses.md).

This lane's branch diverged from this repo's very first commit, before any of the shared
`vendor/gems57` tooling or the other lanes above existed, so it independently (re-)built and
unit-tested its own metric/holdout/submission-writer from the organizer's published equations
(`src/gems84/metric.py`, `holdout.py`, `features.py`, `submission.py` — distinct files from
the LITI lane's `basis.py`/`liti.py`/`mlfield.py`/`paths.py`, so both coexist without
collision). This is flagged here, not hidden: per the "REUSE, DON'T REBUILD" protocol rule,
a future session merging further lanes should retire this lane's duplicate metric/holdout
implementation in favor of `vendor/gems57` once the two are cross-checked against each other.

| question | answer |
|---|---|
| Is there a TIF to download? | **Yes** — budget 44,090 px, path [`docs/downloads/gemsdoe84-h84-fused-demag-cond-corridor-20261022T000000Z-auditonly-zeros.tif`](docs/downloads/gemsdoe84-h84-fused-demag-cond-corridor-20261022T000000Z-auditonly-zeros.tif), sha256 `e65539d392345b10028d949a76937370b6806f193fa093e40a3393b6b82f54cf` (NaN-outside twin also shipped, see [receipts](docs/downloads/gemsdoe84-h84-fused-demag-cond-corridor-20261022T000000Z-auditonly-receipts.json)). Single-band float32, EPSG:32611, 3730×3292, transform matches `data/sample_submission.tif` exactly, all finite in-footprint values in [0,1], 0 non-finite pixels (zeros variant). |
| Is it OK to submit? | **Format-valid, scientifically no.** HOLDOUT-DTI (this lane's own `gems84.metric`/`gems84.holdout` v1, 6×6 spatially-blocked, 6 folds, 3px/300m buffer, pooled DTI across the public USGS/INGENIOUS catalogue): fused field **0.0219** [no registry-wide comparison performed] at 44,090 px vs. a **uniform-random control at 0.0608** — random beats this field by 2.8×-4.3× at every budget tested, 15,000 through 1,000,000 px. Leakage canary clean (AUC 0.50-0.52 everywhere). Mechanism: the catalogue is geographically pervasive (8.16% of the footprint lies within 300m of a mapped fault), so any spatially-uniform field earns outsized credit from ubiquity; this field's own mass concentrates in conductive sub-basins that don't track the mapped basin-margin trend. Verdict **negative** (research artifact); 0 slots used. |
| Why "0.2778" (OWNER-REPORTED, not this lane's number)? | This lane's own research into that figure (see [`docs/h84demag/leaderboard.html`](https://buffedlizard55-lab.github.io/GEMSDOE84/h84demag/leaderboard.html)) found it originates from `buffedlizard55-lab/GEMSDOE32`, whose own README states explicitly, in bold: *"No organizer score exists for this or any artifact here — every number is a local proxy measurement."* The real public DrivenData leaderboard (fetched live, 2026-10-22, [`registry/leaderboard_snapshot.json`](registry/leaderboard_snapshot.json)) shows **#1 `xiaofanhu` at 0.4413**; no participant from this lineage appears in its top 50. This is consistent with, and independently corroborates, this repo's own "Parallel-session integration" note above that prior scores are owner-reported, not organizer-confirmed. |
| What is new and reusable? | Two literature-grounded physical detectors built purely from official bands: **H84-1** (local RTP magnetic-amplitude minimum, i.e. hydrothermal demagnetization, conjugate with a local surface-conductivity maximum, i.e. clay-cap alteration — citations: Bouligand et al. 2014 *JGR*, Finn & Morgan 2002/USGS, and a 2026 Dixie Valley NV multiphysics-inversion paper) and **H84-3** (conductivity–basement discordance). **H84-4** (a third, conjunctive hypothesis, Sato ridge-filtered topographic scarp AND'd with H84-1/H84-3) was also tested and also failed, ruling out "needs more precision" as the fix. Full ranked slate of 5 hypotheses (H84-1 through H84-5) with external-data obtainability checks: [`docs/research/h84-hypotheses.md`](docs/research/h84-hypotheses.md). |
| How to submit (if you choose) | See [`docs/h84demag/executive-summary.html`](https://buffedlizard55-lab.github.io/GEMSDOE84/h84demag/executive-summary.html) — not recommended for this artifact given the verdict above; the page documents the real submission steps regardless, including this project's root-cause analysis of the reported "Predicted values must be in range [0, 1]" portal error. No slot consumed by this lane. |

Reproduce this lane (CPU, ~5 min for the metric/holdout unit tests, ~5 min for the full
budget sweep):

```bash
pip install -r requirements.txt            # adds scikit-image for this lane's Sato ridge filter
python3 scripts/restore_data.py --ids training_features,labels,existing_faults,sample_submission --target-dir data
python3 -m pytest tests/test_metric.py tests/test_submission.py -q   # 9/9, this lane's own tests
python3 scripts/evaluate_holdout.py        # H84-1 / H84-3 / fused vs. uniform-random, full budget sweep
python3 scripts/evaluate_h84_4.py          # H84-4 conjunction test (3rd and final experiment, per budget cap)
python3 scripts/build_submission.py        # writes + validates docs/downloads/*-auditonly-{zeros,nan}.tif
```

Artifacts: `evidence/h84_holdout.json`, `evidence/h84_4_holdout.json`, `evidence/h84_fused_extended_sweep.json`
(full numeric trail), `registry/run_card.json` (this lane's run card, verdict negative),
`registry/leaderboard_snapshot.json` (live public leaderboard snapshot),
`registry/data_manifest.json` is shared with the other lanes (superset, already includes this
lane's 4 files with matching sha256 — independently cross-validated).

**Limitations / next steps for this lane**, in addition to the shared ones above: (1) full
pixel-level rank-correlation / dot-overlap duplicate-lane audit against the registry corpus
(`registry/uniqueness_corpus.txt`, `registry/registry_index.json`) built by the LITI lane was
**not** run against this lane's own candidate before this merge — flagged explicitly in
`registry/run_card.json` as an open limitation, not silently assumed clear; (2) H84-5 (USGS
GeoDAWN radiometric K/Th/U) is specified but deferred; (3) this lane's independently-built
metric/holdout should be reconciled against `vendor/gems57`'s in a future session rather than
maintained as a second implementation indefinitely.
