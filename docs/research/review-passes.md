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

## Lane H84-CSAT — Three-Pass Review (`arena/fcacc90c-gemsdoe84`, 2026-10-22)

### Pass 1 — Preregistration, Implementation, and 3-Experiment Execution
- Restored and SHA-256-verified all 10 core/external datasets (`training_features.tif`, `lidar_scarp_features_u8.tif`, `topo_10m_derived_100m_u8.tif`, `geodawn_rad_u8.tif`, `geodawn_extensions_u8.tif`, and GDR #1391 CSVs) plus all `1,166` git-SHA1-verified `.tif` blobs (`1,160` unique `3730x3292` `EPSG:32611` grid rasters, `0` errors) into `/tmp/gemsdata` outside `/home/user` snapshot storage.
- Preregistered 5 untried geological hypotheses (`H84-CSAT` + `H84-2`..`H84-5`) in `docs/research/hypotheses.md` and locked hyperparameters in `registry/preregistration.json` before running any experiment.
- Implemented `src/gems84/csat.py` (`38` catalogue-blind physical/geothermal/LiDAR/GeoDAWN channels + `20` visible-only strain-transfer & coupling channels, strict LOQO Dual-Habitat HGB + ExtraTrees ensemble, quadrant Bayes calibration) reusing unmodified `vendor/gems57/*`.
- Executed `EXP-84-1` (58-feature canary `max = 0.76042 <= 0.90` PASS; 1,160-raster pre-placement surface `|Spearman rho| = 0.73533 <= 0.90` PASS), `EXP-84-2` (paired `gems57-pooled-hide-v2` holdout across `22,893` withheld positives), and `EXP-84-3` (`38,453`-dot GeoTIFF packaged via `submission_writer.py`, validated by `gems57.validate` + `scripts/validate_submission.py`, and audited across all `1,160` registry rasters).

### Pass 2 — Defect Discovery, Memory & Permission Hardening, and Edge-Case Fixes
- **RAM edge case fixed**: Eliminated an eager `600 MB` full-footprint `X_eval_A` concatenation inside `src/gems84/csat.py` (predicting quadrant-by-quadrant instead) and explicitly freed fold buffers in `scripts/exp84_2_holdout_eval.py`, keeping peak `VmRSS <= 1.80 GB` inside the `3.8 GiB` container.
- **File-mode edge case fixed**: `tempfile.mkstemp` inside `submission_writer.py` leaves `0600` permissions after `os.replace`; added explicit `0o644` chmod in `scripts/exp84_3_emit_and_audit.py` so GitHub Pages can serve `docs/downloads/gemsdoe84-h84-csat-d28-20261022T234500Z-a5483424-zeros.{tif,zip,json}`.
- **Two scientific/protocol irregularities isolated (`IR-84-11`, `IR-84-12`)**:
  - `IR-84-11`: `vendor/gems57/emit.py` line 104 clamps `kself = np.minimum(ekc, 1.0)`, collapsing $c(1-k(x))$ to `0` on high-probability corridors and cutting `HOLDOUT-DTI` from `0.16850` (`csat_poisson`) to `0.08153` (`csat_submod`) at the identical `31,057`/`30,474` dot counts.
  - `IR-84-12`: Domain-restricted blanket priors (`7GEMSDOE:gems7-halo15` `1,828,699` px; `GEMSDOE3:coverage-v3-wide` `624,025` px) have global `halo_coverage < 0.70` yet saturate `77%–100%` of `d <= 15 px`, triggering `binding_duplicate_decision` despite `0` flags against all `1,006` `<= 55k`-dot submissions and max Jaccard `0.03912`.
- Enforced fail-closed honesty: did NOT run a 4th post-hoc parameter-tuned experiment to bypass the 3-experiment cap, and did NOT modify `vendor/gems57/*`.

### Pass 3 — Prompt Re-Check, Deterministic CI Site Build, and Test Verification
- Verified that `scripts/build_run_card.py` and `scripts/build_site.py` deterministically regenerate all JSON run cards and HTML pages (`git diff --exit-code -- docs` clean, matching `.github/workflows/ci.yml`).
- Verified all `pytest` suites pass (`vendor/gems57` SHA-256 pins, `research/source-receipts.json` SHA-256 pins, local HTML link integrity, `csat.py` unit tests, and on-disk GeoTIFF `[0, 1]` / `EPSG:32611` / zero-NaN / SHA-256 verification).
- Confirmed unmistakable top-of-page `DO NOT SUBMIT TO WEEKLY LIVE SLOT` automated status alongside prominent `.tif` download access, executive-summary submission guide, `H33-2-B2` causal/algebraic audit, 5-hypothesis comparison, and verified source register.

