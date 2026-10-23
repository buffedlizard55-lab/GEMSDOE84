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

## Inherited concurrent PRUNE sessions (historical disclosure)

- **AXIS=PRUNE session (2026-10-23, branch `arena/8db38540-gemsdoe84`)**:
  - The human supplied Brief v2 without an `AXIS` assignment, `TOP_PUBLIC`, or slot quota and skipped the agent's clarifying questions; the agent recorded defaults (`IR-DEC-07`) and chose `AXIS = PRUNE` (next unbuilt axis; MASS and SNAP already built once).
  - Restored all pinned inputs (`scripts/restore_pinned_inputs.py --ids all`, SHA-256 fail-closed), re-verified all `23` manifest hashes, rebuilt R0 bit-for-bit a second time, and verified the lineage identity solo `0.2708` base `= d2_8 & d_cat>1` (`40,199` dots).
  - Wrote `src/gems84/prune.py` (fixed-count collar operators) and `scripts/build_prune_variants.py`; built/gated `h33-h33-2-b2-prune-dgt1in-20261023-02ad0d5c`, `h33-h33-2-b2-prune-dge3refill-20261023-3745ebf6`, `h33-h33-2-b2-prune-dgt3refill-20261023-10ce9ad1` (all `37,654` dots; `13.52%` / `8.56%` / `11.53%` changed), ran REPORT-ONLY diagnostics (`evidence/r0_prune_variants_20261023.json`), extended `scripts/build_ledger.py` (`--prune-rows`), added `tests/test_prune_axis.py`, and updated `SLOT_PLAN.md`, `docs/SUBMIT.md`, `README.md` CURRENT STATE, `IRREGULARITIES.md`.
  - The agent submitted nothing and contacted only `codeload.github.com` (pinned mirrors) and PyPI (numpy/scipy/rasterio/pytest in a git-ignored `.venv`).


## 3. Session 2026-10-23 (`arena/f95a2890-gemsdoe84`, `AXIS = PRUNE`, second independent implementation)

- **AI wrote**: the collar-sweep builder `scripts/build_prune_collar_sweep.py` (reuses the recorded `scripts/build_r0_variants.py` ranking, the shared `gems57` holdout evaluator and the shared `gems84.parent` emitter rather than any private metric or writer), `tests/test_prune_collar_sweep.py` (10 tests: format gates, refill floor, distinctness, ledger/receipt consistency), the `README.md` CURRENT STATE block, `SLOT_PLAN.md`, the collar-sweep section of `docs/SUBMIT.md`, and `IR-DEC-08..12`. Its original filenames (`scripts/build_prune_variants.py`, `tests/test_prune_axis.py`) collided with the parallel `arena/8db38540-gemsdoe84` PRUNE session that merged first, so they were renamed on merge; both implementations are kept because their variants are not exact repeats (`IR-DEC-12`).
- **AI executed**: restored the pinned inputs from `codeload.github.com` (`scripts/restore_pinned_inputs.py`; 23/23 manifest hashes verified, receipt committed as `evidence/input_restore_receipt.json`), re-ran the parent gate (`scripts/rebuild_r0.py`: 6/6 checks PASS, `c55bafc4…`), built/gated/re-read the three collar variants, and ran the report-only diagnostics.
- **Human decided / must still supply**: the axis for this session (blank in both 2026-10-23 briefs — `PRUNE` chosen independently twice and logged as `IR-DEC-07`/`IR-DEC-08`); `TOP_PUBLIC` with a date; remaining weekly/total slot quota; and every `receipt_score` + `date` after uploading from the human's own account. The AI has never logged in, scraped the leaderboard, or submitted anything.

## Current continuation — owner-delegated PRUNE1.5 (2026-10-23)

**This section supersedes the earlier current-session HOLD for an unassigned
axis.** The owner explicitly said not to ask for an axis and to pick a session.
The human did **not** pick PRUNE1.5, its compensation ranking, prediction, slot
allocation or final file; those are agent decisions, not human endorsements.

### What the AI chose, wrote and executed

- Reverified all **23 manifest + four parent-lineage hashes**, then reconstructed
  R0 byte-for-byte in both encodings. Selected **AXIS=PRUNE**, value **1.5**: the
  1/3 px endpoints and 2.5/3/4 px sweeps were already built/reserved. One unused
  intermediate lattice state was built; no three-file quota-filling exercise.
- Proved that 30 R0 dots have **no** >=3 px allowed target within 2 px. A pure
  count-preserving SNAP cannot resolve this; no collar rule was silently waived.
  The new candidate uses only the brief's explicit **PRUNE exception**.
- Wrote `prune_intermediate.py`, `build_prune_intermediate.py`, preregistration and
  tests. Kept the physical field and original pre-prune dot pool: all **1,344**
  d_cat=2 px dots in, equal count of R0 dots out. Ranking is greedy exact shared
  kernel deletion loss against the **fixed H19-5 MODEL lineament reference**,
  updated after each removal, with row-major ties. This is not hidden truth,
  a calibrated posterior, or a claim that the discarded dots are non-faults.
- Preregistered **MODEL central +0.002 DTI**, plausible **−0.010..+0.015**, before
  diagnostics. It is an uncalibrated scenario, not a confidence interval. Did not
  use the catalogue PROXY to fit or upgrade that prediction.
- Built **one** 37,654-unit-dot mask, exactly **7.138683805173421%** symmetric
  difference from R0; wrote primary NaN-exterior and fallback zero-exterior TIFFs.
  Both were independently re-read and validated; the fallback used the unchanged
  shared writer. No original competition raster was added to Git/releases.
- Executed the unchanged shared catalogue evaluator: 22,893 withheld instances /
  21,032 unique pixels, conditional paired 20 km-block CIs, seeds 20/21 and
  bootstrap seed 520810. Clearly labelled **PROXY / shipped-mask / NOT fold-clean**:
  restoring catalogue-adjacent dots mechanically favors this instrument. The
  passing one-feature binary canary is not a leakage-freedom certificate.
- **Did not run SGMC**: the owner-derived mirror's license/shareability has no
  explicit verified receipt here. Reported that omission, not a gate. No new
  external data, lidar, feature fitting or physical detector was introduced.
- Merged concurrent main history on the fixed branch, preserving all 125 prior
  CSV rows and receipt bytes before appending one BUILT row. Protected the ledger
  initialiser against replacing existing history. Updated only README's CURRENT
  STATE, current packet/plan and decision records; did not redesign the site.
- Build source commit `23f5dbcacc3568e6469843693f67758611aa3442`, exact source hashes
  and input pins are in `evidence/prune_1p5_796cb891.json`. No forbidden host,
  login/submission code or credential access. The shared metric was not modified.

### What remains the human's decision/input

Only the human chooses whether/when to submit one encoding, manages the one-entity
rolling-week quota, selects the blind final, supplies TOP_PUBLIC with a read date,
the R0 submission-page receipt, remaining weekly/total quota and actual submission
dates, exact deadline/cutoff confirmation, and competition-data-use/public-mirror
permission. An explicit SGMC license is needed only to add that optional control.
The agent spent **zero** scored slots and requests **no further axis decision**.

## Inherited later concurrent audit additions (historical; current packet takes precedence)


## 4. Session 2026-10-23 (`arena/60b5c7f6-gemsdoe84`, `AXIS = CONCENTRATION`)

- **AI executed**: verified all 23 manifest hashes + parent pins in a fresh sandbox (`.venv` from PyPI; mirrors only from `codeload.github.com`), rebuilt R0 byte-identically, re-validated all 12 previously BUILT releases from disk, then discovered via `git fetch` that two parallel PRUNE sessions had merged to `main` (PRs #24/#25) after this branch forked — discarded its own duplicate PRUNE builder unbuilt, merged `origin/main`, and pivoted to the next unbuilt axis. Proved the canonical-ranking identity (PRUNE `dgt1in` removals bit-identical; MASS tails only 80.9%/85.1% concordant, `IR-DEC-13`) and measured CONCENTRATION greedy capacities before fixing doses (`IR-DEC-15`).
- **AI wrote**: `src/gems84/concentration.py`, `scripts/build_concentration_variants.py` (built/gated `conc5km-t50-m3765-6310efe0`, `conc5km-t25-m2400-caadfcce`, `spread5km-b50-m2400-ceb1073d`, all 37,654 dots; `evidence/r0_concentration_variants_20261023.json`), `ledger/_concentration_rows.json` + `ledger/_prune_sweep_rows.json` (restores sweep rows dropped by ledger rebuilds, `IR-DEC-14`), `tests/test_concentration_axis.py`, and the CONCENTRATION sections of `docs/SUBMIT.md`, `SLOT_PLAN.md`, `README.md` CURRENT STATE, `IRREGULARITIES.md` (`IR-DEC-13..16`).
- **Human decided / must still supply**: AXIS was again blank and the clarifying questions were skipped (third session; default logged in receipt + `IR-DEC-07/08` lineage). Still required: `TOP_PUBLIC` + date, slots left this week/total, a receipt for every uploaded file, resolution of the retained-dot collar reading (`IR-DEC-16`), and the data-use confirmation (`IR-DEC-01`). The AI has never logged in, scraped, or submitted.

## 5. Session 2026-10-23 (`arena/5be6452b-gemsdoe84`, `AXIS = PRUNE`, third parallel implementation — landed as reproduction audit, PR #28)

- The AI agent in this session independently selected `AXIS = PRUNE` (brief blank, clarification skipped — cf. `IR-DEC-07`/`IR-DEC-08`), restored all pinned inputs hash-verified from `codeload.github.com` only (`evidence/prune_input_restore_receipt.json`), rebuilt R0 byte-identically (`evidence/r0_rebuild_receipt_20261023_prune.json`), and built two fixed-count collar variants. Discovering on PR submission that two sibling sessions had already merged six PRUNE variants (PRs #24/#25) — and, during reconciliation, that a third sibling had merged CONCENTRATION ×3 (PR #29) — the agent **withdrew its two duplicates** rather than merge a third implementation (built-once rule).
- The session's durable contribution is `IR-DEC-17`: a MASS-mask fidelity gate root-caused `IR-DEC-13` to the float32 nodata sentinel silently killing the H33-A surface via the committed band unpacker; `scripts/build_r0_variants.py:ensure_unpacked_bands` now cleans sentinel→NaN. `scripts/audit_prune_reproduction.py` + `evidence/prune_reproduction_audit_20261023.json` record the measurements (MASS masks reproduce to ≤14 boundary dots/arm post-fix; all six merged PRUNE files carry the pre-fix canary fingerprint `0.5944` vs MASS-effective `0.5949`; clean-ranking rebuilds would change ≤273 dots per `>3 px`-class file, so no merged file was rebuilt). `IR-DEC-18` records the SGMC control's structural bias on this axis. CONCENTRATION ×3 share the pre-fix ranking provenance; their clean-ranking deltas are unmeasured.
- No drivendata.org or dropbox.com contact, no credentials touched, no submission automation, no slot spent. Human decisions still outstanding are exactly those in `IR-DEC-07` and §4/`IR-DEC-16`: `TOP_PUBLIC` + date, slots left, deadline confirmation, the retained-dot collar ruling, and a portal receipt per manual upload.

### Final concurrent-main integration (no extra raster build)

Main gained PR #29's CONCENTRATION records and PR #28's raw-band sentinel audit
after the first full self-check. The agent retained all records, audit files,
withdrawal warnings and sentinel fix, preserving the entire 126-row local CSV
prefix while adding three incoming rows (**129 rows / 16 BUILT**). Their TIFFs
were hash-checked against their ledger pins before collar inspection; all three
violate the strict non-PRUNE >=3 px rule and remain HOLD, not grandfathered.
PRUNE1.5's source/mask/file hashes and preregistered prediction did not change.

The agent scoped the sentinel regression tests to the six historical audited
files rather than banning later unused collar values, preserved every historical
file-hash/withdrawal check, made summary-count checks dynamic, and allowed human
receipt fields to be filled later. A recovery sidecar contains the one new row;
the initializer refuses any existing ledger. No live-change bound is inferred
from dot overlap. PRUNE1.5's fixed H19-reference operator never unpacks the raw
feature bands affected by IR-DEC-17; this is not a claim that the upstream H19
field is leakage-free. No further candidate or scored slot was created/used.
