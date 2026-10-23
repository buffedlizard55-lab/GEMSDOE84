# Repository review — 2026-10-23 (UTC)

## Outcome

The repository contains an H84-THMS GeoTIFF and reproducible evidence artifacts, but global uniqueness is not established: its candidate-specific audit covers 359 rasters, not the full 1,143-raster registry index. The public-facing claim that it was approved to submit was too strong. The file is **OK TO DOWNLOAD FOR REVIEW** after local format preflight, but **NOT AUTHORIZED TO SUBMIT**. No competition slot was used and no organizer receipt was observed. The separate LITI full-corpus duplicate result is not evidence about this H84-THMS TIFF; see `registry/current_release_status.json`.

## Verified locally in this review

- `submissions/gems84-h84-thms-dink300-37654dots-20261022-2f4190b4-zeros.tif` reopens as a one-band `float32` GeoTIFF, shape `3730 × 3292`, CRS `EPSG:32611`, transform `(100, 0, 243350, 0, -100, 4508550)`, `nodata=None`.
- All raster values are finite and in `[0,1]`; there are `37,654` positive cells. SHA-256: `509fa4971a3cdf119a0ae7140b0fac31860d063af9bcc914266d98294f2ba7b5`.
- Compared with the locally restored `data/bridge/sample_submission.tif`, shape/CRS/transform match. `scripts/validate_submission.py` returns `format_valid: true` and `submission_authorized: false` (format only).
- Python test suite after PR #14 integration: `56 passed` (`python -m pytest -q`, after installing `requirements.txt` into ignored `.venv`). Rasterio emitted 36 `PendingDeprecationWarning`s from its transform helper; no test failures.
- Existing H84 experiment evidence records `HOLDOUT-DTI = 0.225508573` (evaluator `gems57-pooled-hide-v2`, pooled, 22,663 withheld positive pixels, 95% CI `[0.210089596, 0.240437642]`). This is a locally reported holdout metric, not a leaderboard score. Do not compare it as though it were organizer-confirmed.
- `evidence/h84_uniqueness.json` records a pass across 359 audited rasters: pre-placement surface maximum absolute Spearman `0.365582`, maximum 3-px dot overlap `0.649997`; final emitted dots maximum absolute Spearman `0.085702`, maximum 3-px overlap `0.649997`. This does not certify uniqueness against every repository, all live submissions, or any registry entries outside that audited snapshot.

## Problems found and corrected

1. `README.md`, `docs/index.html`, and `docs/executive-summary.html` said “OK TO DOWNLOAD & SUBMIT WITHOUT HUMAN INTERVENTION” and “Automated Portal Validator”. Available code/evidence supports local format/range checks only, not portal acceptance. These claims now distinguish download-for-review from submission authorization.
2. Several H84 JSON records said `ok_to_submit: true`, while the generated submission receipt already said `approved_for_weekly_slot: false` and `promoted: false`. Updated H84 status fields to `submission_authorized: false`; promotion is explicitly only to a separate selector review.
3. The H84 experiment records retain the branch on which those experiments were executed; it differs from the active review branch. This is preserved as historical provenance, not silently rewritten.
4. `docs/downloads/` previously offered non-promoted binaries, including an audit-only TIFF with NaNs. The non-promoted TIFF/ZIP files were removed by the 2026-10-23 fresh-audit changes (IR-84-08); the site download inventory now retains only the H84-THMS artifact and its archive. The local format gate still does not establish submission authorization.

## Important blockers / limitations

- The public leaderboard snapshot in `evidence/fresh_audit_20261023.json` records the top entry as xiaofanhu, `0.4413`, `ORGANIZER-CONFIRMED` (public leaderboard fetched 2026-10-23). This is not an H84-THMS submission receipt and does not confirm a score for this candidate. The weekly slot cap was not independently checked in this review. Holdout-DTI `0.225508573` and a public leaderboard score are different evidence types and must not be treated as directly comparable.
- No submission-page receipt is present; therefore no `ORGANIZER-CONFIRMED` score is recorded. Historical H84 run cards record branch `arena/010446b1-gemsdoe84`; this review is on `arena/aff3aeca-gemsdoe84`. I preserved the historical branch value rather than relabeling past evidence.
- Full organizer training feature stack and official template are not present in `data/`; only bridge rasters and a restore receipt are present. I did not rerun the scientific pipeline or regenerate the TIFF.
- The candidate's holdout score is below the user-reported current high score numerically, but these are different evidence types and cannot be directly compared. There is no evidence here that the TIFF beats the current best on an identical holdout protocol. It should not be sent to the selector as “proven to win” or uploaded as an approved submission.
- Even though the saved uniqueness receipt covers 359 rasters, full/fresh cross-fleet registry coverage remains uncertain. Verify source snapshot completeness before declaring globally unique.
- Official links are preserved for independent checking; they were not live-fetched in this review due network policy: [competition](https://www.drivendata.org/competitions/306/competition-doe-gems/), [problem/metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [about](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/), [competition data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), [DOE GDR #1391](https://gdr.openei.org/submissions/1391), and [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and).

## Next work (ordered)

1. Verify/retrieve the official submission template and current leaderboard/weekly cap from DrivenData in an authorized environment; save timestamped receipts, not screenshots alone.
2. Reconcile all lane-specific run cards, site status, and download directories under a single auditable selector. Only the selector can authorize a real slot.
3. Restore the exact organizer training stack and cache; rerun the shared hide-and-recover evaluator and each-feature canary from a clean state, with whole-segment buffered folds and archived source hashes.
4. Require a pre-placement and final-dot uniqueness audit against a complete dated registry snapshot; fail closed if missing entries prevent the lane thresholds from being checked.
5. Compare the candidate to the frozen current holdout best under the same evaluator/folds/placement budget. Do not spend a competition slot unless the candidate beats that incumbent under the preregistered rule; report paired CI.
6. For the separate selector, verify the submission cap, reviewer rules and exact portal format; upload only after explicit authorization. Record the organizer receipt and label its score `ORGANIZER-CONFIRMED`.

## Passes completed

- **Pass 1 — repository and artifact inventory:** read root mandate/readme, H84 experiment records, submission validator, tests, workflows, site files and data tree.
- **Pass 2 — implementation/evidence verification:** independently reopened and hashed the candidate TIFF; ran the local format validator against restored sample template; ran all 56 tests after integrating the fresh-audit changes. Found and corrected overclaimed submission authorization.
- **Pass 3 — consistency review:** checked landing and executive-summary text, H84 JSON receipt/build/run-card fields, and CI status. No new geological experiment was run; the existing three-experiment budget is treated as spent.
