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

## 2. What the Human Decided and Must Supply

- **Experimental Framework & Constraints (`PROMPT.md`)**:
  - The human defined the experimental protocol (Brief v2), hard constraints (no `dropbox.com` or `drivendata.org` access, zero catalogue mass, $\ge 3\text{ px}$ collar on newly added non-`PRUNE` dots, no label probing, single-entity `3 slots/week` budget, and no rank-correlation or dot-overlap "uniqueness" gates), and the baseline choice of Parent R0 (`h33-h33-2-b2`, `0.2778` `CLAIM`).
- **Human Decisions & Inputs Required Before Portal Upload**:
  1. Supply current `TOP_PUBLIC` leaderboard score and exact `Slots left this week / total` for the single competing entity.
  2. Supply organizer receipt(s) (`receipt_score` and `date` in `ledger/submissions.csv`) for `h33-h33-2-b2` (`0.2778` `CLAIM`) and for each of the `AXIS = MASS` / `AXIS = SNAP` variants as they are manually uploaded to DrivenData by the human.
  3. Confirm data-use terms regarding competition rasters mirrored in upstream public repositories (`IR-DEC-01` in `IRREGULARITIES.md`).

## 3. Current session — 2026-10-23 / `arena/796cb891-gemsdoe84`

This section supersedes any earlier implication that the human authorized MASS,
SNAP, a grandfathered >2 px collar, or an upload in **this** session.

### AI work performed

- Read the manifest, recorded R0 recipe, ledger, slot plan and required repository
  entry documents. Used only GitHub metadata/archives and PyPI; no contact with
  dropbox.com or drivendata.org, no credentials accessed, no login/submission code.
- Restored into ignored `.cache/gems_data/`; verified **23 manifest files + four
  pinned parent-lineage files**, then rebuilt R0 from the exact recorded base.
  Both GeoTIFF SHA-256 hashes match; no parent approximation. Parent rebuilds remain
  ignored and are not shipped as candidates.
- Wrote `src/gems84/brief_v2.py`, `scripts/preflight_brief_v2.py`, and regression
  tests. Added explicit-axis / repeated-pair guards to the historical builders,
  before their side effects. Added explicit primary-NaN / fallback-zero format
  validation and float32 enforcement without changing shared metric/writer code.
- Re-read all six **inherited** variant pairs, checked exact hashes and template
  format, and measured their strict catalogue clearance. All have <3 px dots;
  none is currently submission-cleared. Did not modify, rename or rebuild them.
- Read the [pinned PR #21 ledger](https://github.com/buffedlizard55-lab/GEMSDOE84/blob/c2802971924cc0928145f48fb4ddb6ad6bd6c508/ledger/submissions.csv) through GitHub and preserved its PRUNE 1/3/4
  settings in `ledger/experiment_reservations.json`, with immutable URL and ledger
  SHA-256. Its rasters and reproducibility were **not** validated. Left the primary
  119-row CSV and all human receipt fields byte-for-byte unchanged.
- Recorded the local validation report in
  `evidence/brief_v2_preflight_796cb891.json`; updated only README's CURRENT STATE
  block, the slot/submission instructions and decision-changing irregularities.
  No site redesign or new competition-data binaries. No new external scientific
  data, fitted features, catalogue PROXY, leakage canary or SGMC evaluation.
- Ran tests, format validators and generated-file reproducibility checks; final
  test/CI results belong to the PR, not to a live competition score receipt.

### Human decisions and missing inputs

The human supplied Brief v2, named R0 and its claimed 0.2778, limited the work to
one entity and reserved final selection/upload to the human. The human **did not**
assign an AXIS/unused value, authorize a collar waiver, or provide current
TOP_PUBLIC/date, remaining rolling-week/total slots and submission dates, a parent
submission-page receipt, exact deadline/cutoff confirmation, or permission for the
existing public competition-data mirrors. Those remain required. No live change
is predicted for this audit-only session; zero candidates built and zero slots used.
