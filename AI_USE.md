# AI USE DISCLOSURE — DrivenData GEMS Prize (#306)

Per the competition rules for the U.S. Department of Energy Geothermal Earthshot Machine Learning & Fault-Detection Prize (`https://www.drivendata.org/competitions/306/competition-doe-gems/`) and Brief v2 Hard Constraint #5, this document records the boundary between AI-generated artifacts and human decisions.

## 1. What the AI Agent Wrote and Executed

- **Manifest & Parent R0 Verification (`scripts/build_r0_variants.py`, `scripts/rebuild_r0.py`)**:
  - Verified all `23` SHA-256 hashes in `registry/data_manifest.json` against `.cache/gems_data/` and unpacked the `19` float32 bands of `training_features.tif` into `.cache/gems_data/bands/01_mag_anom.npy`..`19_det_elev_slope.npy`.
  - Rebuilt Parent R0 (`h33-h33-2-b2`, `GEMSDOE32`, `37,654` unit-mass dots) deterministically from `scored_h19_5` (`e27054cf`) via `dot_thin(r_min=2.8)` $\to$ `d2_8` (`44,090` dots, bit-identical) $\to$ `d_cat > 2.0 px` (`37,654` dots, `digest8 = e5eb6e7e`), matching the exact SHA-256 of both `-zeros.tif` (`c55bafc470054e82...`) and `-nan.tif` (`baeae3219bba6a19...`).
- **Ledger Construction (`ledger/raw_paste.txt`, `ledger/submissions.csv`, `scripts/build_ledger.py`)**:
  - Built `ledger/raw_paste.txt` and `ledger/submissions.csv` from `registry/live_scores.csv` (`103` owner-reported rows, labeled `CLAIM`) and `docs/evidence/upstream-score-ledger.csv` (`OFFICIAL_SNAPSHOT`), collapsing exact repeats and appending the `BUILT` single-axis variants (`AXIS = MASS` and `AXIS = SNAP`).
- **Parent Ranking & Single-Axis Variant Generation (`scripts/build_r0_variants.py`, `scripts/build_snap_variants.py`, `releases/`)**:
  - Reconstructed the `GEMSDOE32` ridge-corroboration posterior combining `corrob_count` (`h19_5`, `h19_4`, `h16_1`, `tgc_v2_d15`, `d15`, `ens12`), `H33-A..D` multi-physics oriented-lineament consensus (`research/upstream/src/gems32/h33.py`), and `lidar_scarp_composite`, and implemented exact vectorized 25-offset ($R = 3.0\text{ px}$) top-2 kernel marginal DTI gain $\Delta J(x) = (1 - \alpha s_0)\Delta T(x) - \alpha s_0(1 - m_q(x))$.
  - Built and verified the `3` `AXIS = MASS` variants (`h33-h33-2-b2-mass-drop10pct-20261023-2cde51f3` with `33,889` dots, `h33-h33-2-b2-mass-add10pct-20261023-ad925bd2` with `41,419` dots, and `h33-h33-2-b2-mass-drop20pct-20261023-62bfc392` with `30,123` dots) and `3` `AXIS = SNAP` variants in both `.tif` (`NaN` outside footprint) and `-zeros.tif` (`0.0` outside footprint) formats.
- **Validation, Diagnostics, Tests, and Documentation**:
  - Executed disk re-read format/gate validation (`verify_written_pair_from_disk`, `scripts/validate_submission.py`) and REPORT-ONLY diagnostics (`catalogue_hide_and_recover_proxy`, `leakage_canary`, `sgmc_off_catalogue_control`), saving structured receipts to `evidence/r0_mass_variants_20261023.json`.
  - Authored `SLOT_PLAN.md`, `docs/SUBMIT.md`, `IRREGULARITIES.md`, `AI_USE.md`, the `CURRENT STATE` block update in `README.md`, and unit tests in `tests/test_r0_variants.py` and `tests/test_snap_axis.py`.

- **AXIS=PRUNE session (2026-10-23, branch `arena/8db38540-gemsdoe84`)**:
  - The human supplied Brief v2 without an `AXIS` assignment, `TOP_PUBLIC`, or slot quota and skipped the agent's clarifying questions; the agent recorded defaults (`IR-DEC-07`) and chose `AXIS = PRUNE` (next unbuilt axis; MASS and SNAP already built once).
  - Restored all pinned inputs (`scripts/restore_pinned_inputs.py --ids all`, SHA-256 fail-closed), re-verified all `23` manifest hashes, rebuilt R0 bit-for-bit a second time, and verified the lineage identity solo `0.2708` base `= d2_8 & d_cat>1` (`40,199` dots).
  - Wrote `src/gems84/prune.py` (fixed-count collar operators) and `scripts/build_prune_variants.py`; built/gated `h33-h33-2-b2-prune-dgt1in-20261023-02ad0d5c`, `h33-h33-2-b2-prune-dge3refill-20261023-3745ebf6`, `h33-h33-2-b2-prune-dgt3refill-20261023-10ce9ad1` (all `37,654` dots; `13.52%` / `8.56%` / `11.53%` changed), ran REPORT-ONLY diagnostics (`evidence/r0_prune_variants_20261023.json`), extended `scripts/build_ledger.py` (`--prune-rows`), added `tests/test_prune_axis.py`, and updated `SLOT_PLAN.md`, `docs/SUBMIT.md`, `README.md` CURRENT STATE, `IRREGULARITIES.md`.
  - The agent submitted nothing and contacted only `codeload.github.com` (pinned mirrors) and PyPI (numpy/scipy/rasterio/pytest in a git-ignored `.venv`).

## 2. What the Human Decided and Must Supply

- **Experimental Framework & Constraints (`PROMPT.md`)**:
  - The human defined the experimental protocol (Brief v2), hard constraints (no `dropbox.com` or `drivendata.org` access, zero catalogue mass, $\ge 3\text{ px}$ collar on newly added non-`PRUNE` dots, no label probing, single-entity `3 slots/week` budget, and no rank-correlation or dot-overlap "uniqueness" gates), and the baseline choice of Parent R0 (`h33-h33-2-b2`, `0.2778` `CLAIM`).
- **Human Decisions & Inputs Required Before Portal Upload**:
  1. Supply current `TOP_PUBLIC` leaderboard score and exact `Slots left this week / total` for the single competing entity.
  2. Supply organizer receipt(s) (`receipt_score` and `date` in `ledger/submissions.csv`) for `h33-h33-2-b2` (`0.2778` `CLAIM`) and for each of the `AXIS = MASS` / `AXIS = SNAP` variants as they are manually uploaded to DrivenData by the human.
  3. Confirm data-use terms regarding competition rasters mirrored in upstream public repositories (`IR-DEC-01` in `IRREGULARITIES.md`).

## 3. Session 2026-10-23 (`arena/f95a2890-gemsdoe84`, `AXIS = PRUNE`, second independent implementation)

- **AI wrote**: the collar-sweep builder `scripts/build_prune_collar_sweep.py` (reuses the recorded `scripts/build_r0_variants.py` ranking, the shared `gems57` holdout evaluator and the shared `gems84.parent` emitter rather than any private metric or writer), `tests/test_prune_collar_sweep.py` (10 tests: format gates, refill floor, distinctness, ledger/receipt consistency), the `README.md` CURRENT STATE block, `SLOT_PLAN.md`, the collar-sweep section of `docs/SUBMIT.md`, and `IR-DEC-08..12`. Its original filenames (`scripts/build_prune_variants.py`, `tests/test_prune_axis.py`) collided with the parallel `arena/8db38540-gemsdoe84` PRUNE session that merged first, so they were renamed on merge; both implementations are kept because their variants are not exact repeats (`IR-DEC-12`).
- **AI executed**: restored the pinned inputs from `codeload.github.com` (`scripts/restore_pinned_inputs.py`; 23/23 manifest hashes verified, receipt committed as `evidence/input_restore_receipt.json`), re-ran the parent gate (`scripts/rebuild_r0.py`: 6/6 checks PASS, `c55bafc4…`), built/gated/re-read the three collar variants, and ran the report-only diagnostics.
- **Human decided / must still supply**: the axis for this session (blank in both 2026-10-23 briefs — `PRUNE` chosen independently twice and logged as `IR-DEC-07`/`IR-DEC-08`); `TOP_PUBLIC` with a date; remaining weekly/total slot quota; and every `receipt_score` + `date` after uploading from the human's own account. The AI has never logged in, scraped the leaderboard, or submitted anything.
