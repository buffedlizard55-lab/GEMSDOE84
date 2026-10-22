# Three-pass implementation review

## Pass 1 — build and execute

- Inspected the empty starting checkout, predecessor repositories and official reference README/tree.
- Reused pinned shared evaluator, holdout, writer and validators; reused cached derived physical rasters instead of copying prediction TIFFs as features.
- Preregistered four hypotheses and one selected lane before implementation; restored and hash-verified all required data without requesting credentials.
- Indexed linked public repositories at resolved commits and downloaded their distinct TIFF blobs to an ignored cache.
- Implemented canaries, full-footprint pre-placement rank comparisons, fixed-parameter spatial holdout, strict final-dot duplicate stop and guarded packaging.

## Pass 2 — inspect failures and repair

- Found historical H33 ZIP contains no TIFF; recorded byte-level evidence and added warning to the guide.
- Found geometry-mismatched registry rasters. Added explicitly recorded nearest-neighbor comparison alignment; did not treat their native grids as valid submissions.
- Found malformed registry TIFF. Added explicit unreadable-row evidence and blocked complete uniqueness clearance. Did not silently count the error as a passing comparison.
- Added deterministic candidate-bound rank-audit checkpoints so tool repairs do not repeat every expensive comparison or change hypothesis parameters.
- Verified the shared vendor files against their pinned hashes. No metric, holdout or writer implementation was modified.
- Added input hash verification to the pipeline, empty-mask/invalid-budget fail-closed guards and output directory creation before packaging.

## Pass 3 — acceptance and edge cases

- Exercised real shared-writer GeoTIFF and ZIP roundtrip in a temporary fixture, rejection of NaN/infinity/out-of-range values, overwrite refusal, exact visible masking, pooled count/CI reporting and dot separation.
- Kept the scientific verdict distinct from format validity. Missing whole-geological-fault-plus-buffer validation and unreproduced current best block promotion unconditionally.
- Added a site generated from the negative run card, with no substituting historical TIFF or test fixture. The guide explains future submission steps without asserting the current run is eligible.
- Preserved bounded experiment scope. Technical retries repair the same fixed experiments; they are not parameter searches or additional hypotheses.
- Repository checks and deployment status are reported in the PR, not inferred from local success. No organizer submission or weekly slot is used.

## Unmet requirements, explicitly not waived

A guaranteed higher-scoring, globally unique, submission-approved TIFF has **not** been established. Official non-GitHub pages could not be freshly verified under the network policy. The README contains an operational transcription, not the full verbatim original user message. A whole-fault shared-template correction and a coordinated solution to any literal dense-registry overlap veto must happen before a production candidate can be promoted. No claim of complete line-by-line verification of inaccessible sources is made.

Pages configuration was inspected: an existing public legacy Pages site serves `main:/`. Switching it to workflow mode returned HTTP 403 (integration lacks Pages settings permission). The implementation therefore preserves legacy deployment, adds a root redirect to `docs/`, and does not install a conflicting deployment workflow. This permission failure is not evidence of a bad GitHub login.

### Concurrent-main reconciliation

The first merge attempt found conflicts from three parallel-session PRs already merged into main. Their validators, tests, source archives, hypothesis pages and historical JSON cards were retained. Conflicting original landing pages/README were archived under `research/concurrent-readiness/` as source text. Older cards are explicitly marked superseded; the measured H84-RFD card remains canonical. The presence-only readiness helper now reflects actual H84-RFD cache/vendor paths and still does not authorize submission. All 27 combined tests pass locally. The already-merged Pages workflow is preserved rather than silently removed; its eventual deployment result is checked separately.


---

# Three-pass review — H84-WING (2026-10-22, bridge-only, 37,820 dots)

## Pass 1 — build and execute (wing)

- Inspected current checkout: bridge files present (existing_faults 7ba308cc…, sample_submission 2176d08e…), LITI and RFD lanes negative with no TIFF, 31 prior tests. Read PROMPT.md (verbatim) and README brief each session.
- Generated 5 hypotheses distinct from H84-RFD/H33 A–E (tip wing-crack, magnetic analytic signal, MT conductivity curvature, gravity worm persistence, ComCat microseismic), ranked by expected DTI/cost; selected Rank 1 (tip/gap) for bridge-only cost.
- Implemented `scripts/generate_unique_submission.py`: catalogue tip map (degree-1) → exp(-d/10) tip proximity, 3–12 px gap band × 1.2 km Gaussian density, quantile-normalized far-field, 0.17/0.23 lattice, deterministic hash noise seed 289926028; combine 0.45·dist+0.25·tip+0.20·gap+0.10·lattice with 0.88+0.24·noise, clip [0,1], zero outside/on catalogue.
- Greedy dot placement 37,820 budget, 3-px separation, pixel-exact catalogue mask; validated in-memory (finite [0,1], outside zero) and on-disk via shared `submission_writer` (15/15 checks, .tif + one-TIFF .zip + .json receipt).
- Ran pooled holdout `gems57-pooled-hide-v2` seed 20, 4 folds, 11,318 withheld (same as RFD), 1000-draw spatial-cluster bootstrap; recorded HOLDOUT-DTI wing 0.00135 [0.00051,0.00231] vs control 0.0.

## Pass 2 — inspect failures and repair (wing)

- Found holdout leaked full-catalogue geometry (surface built once from full catalogue, not per-fold visible-only) → flagged as blocker, set verdict negative even though delta >0.
- Found holdout absolute 0.00135 far below prior best 0.04430 on same folds → not a promotion, documented as negative deliverable (format-valid research artifact).
- Found registry corpus not downloaded (0/1017 locally, 1,143-blob ≈2 GB not fetched) → marked uniqueness pending, not assumed. No silent dense-raster exemption; deterministic seed/budget are the uniqueness construction.
- Found site links to `registry/inventory.json` broke local-link test (file at `evidence/inventory.json`) → fixed to `evidence/inventory.json`.
- Found `research/hypotheses_wing.html` links broke (file is `.md`) → fixed to `.md`; added missing `numpy` import in test, handled both run-card schemas (hyphen/underscore, submission vs submission_file).
- Found `evidence/run-card.json` vs `evidence/run_card.json` dual files → updated tests to handle both, added missing `submission_slots_used` alias, added `registry_correlation_overlap` alias, and synced `docs/data/run-card.json` (download_allowed true, submission_authorized false for negative).
- Verified TIF with independent `scripts/validate_submission.py` (format_valid true) and `rasterio` (3730×3292 Float32 EPSG:32611, min 0 max 1, 0 NaN, 37,820 positives, outside zero, on-catalogue 0) and ZIP roundtrip.
- Copied evidence to `docs/evidence`, updated `docs/index.html` (prominent top download, FORMAT-VALID ONLY banner), `executive-summary.html` (exact portal steps), `research.html` (new hypotheses/sources/result), and `README.md` (wing lane table).

## Pass 3 — acceptance and edge cases (wing)

- Re-ran full pytest 31/31 pass (was 27, now 31 after fixes); checked validator on final bytes (SHA c6d0b710…).
- Checked edge cases: empty mask and zero budget raise ValueError (fail-closed); overwrite refused by writer; NaN/inf/out-of-range rejected before write; non-finite outside handled; catalogue masking pixel-exact; budget 37,820 vs 37,654 unique; note 104/140 chars; transform exact.
- Kept scientific verdict distinct from format validity: file is downloadable at the very top (obvious) but banner says “FORMAT-VALID ONLY — portal will accept, scientific promotion BLOCKED”, with validator and holdout displayed and `ok_to_submit` field. No weekly slot used; no organizer receipt claimed.
- Did not copy any prior TIFF; wing surface is deterministic geometry, not a pruned H19-5. Rank correlation not measured locally, so no claim of beating 0.2778; only algebra explains why pruning helped H33.
- Unmet requirements preserved: whole-fault+buffer holdout, per-fold visible-only recomputation, full registry scan, organizer-authenticated hashes, live leaderboard/cap verification, and line-by-line verification of blocked hosts remain pending and are not waived.
