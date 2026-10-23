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

## 3. Addendum — 2026-10-23 `AXIS = PRUNE` Session (branch `arena/5be6452b-gemsdoe84`)

### 3.1 What the AI Agent Wrote and Executed in This Session

- **Session-start verification**: restored all 23 manifest files + 4 parent-lineage pins from `codeload.github.com` only, SHA-256-verified (`evidence/prune_input_restore_receipt.json`); rebuilt Parent R0 byte-identically in both encodings (`evidence/r0_rebuild_receipt_20261023_prune.json`); measured the collar-ladder identities `solo == d2_8 & (d_cat>1)` (40,199 dots) and `R0 == d2_8 & (d_cat>2)` on hash-verified bytes. No drivendata.org or dropbox.com contact; no credentials read, stored, or printed; no submission automation written.
- **IR-DEC-07 diagnosis and shared-tool fix**: the new build's ranking-fidelity gate caught that the committed `ensure_unpacked_bands` (float32 nodata sentinel written through as data) silently zeroes the H33-A surface by float32 overflow, making the committed MASS masks irreproducible (602–2,246 px/arm). The agent isolated the cause by controlled probes (catalogue-mask variants, ingredient ablations, per-surface holdout AUCs), then fixed `ensure_unpacked_bands` once (sentinel→NaN at unpack + rewrite of sentinel-bearing bands). After the fix the MASS masks reproduce to ≤12 boundary dots per arm and the MASS session's recorded canary (max AUC 0.5949) and fold-clean R0 PROXY (0.10564) reproduce.
- **PRUNE variant construction (`scripts/build_prune_variants.py`, new)**: two fixed-count (37,654-dot) single-axis variants of R0 — `h33-h33-2-b2-prune-dcatgt3px-20261023-a7d86ed4` (remove 2,171 dots at `d_cat ∈ (2,3] px`, refill by the parent's exact-marginal-gain greedy at `d_cat>3 px`, 11.53% changed) and `h33-h33-2-b2-prune-dcatgt1px-20261023-f5c7e4fb` (re-admit the (1,2] px ring from the 0.2708 lineage set, rank-trim to count; 2,492 ring dots retained, 13.24% changed) — emitted as `releases/<id>.tif` (NaN outside) + `<id>-zeros.tif`, re-read from disk through all MUST gates, with REPORT-ONLY diagnostics (`evidence/r0_prune_variants_20261023.json`): fold-clean hide-and-recover PROXY with CIs, 27-feature leakage canary (passed, 0.5949), SGMC control with its structural-bias note (IR-DEC-09).
- **Bookkeeping and tests**: `ledger/_prune_rows.json` + `--prune-rows` in `scripts/build_ledger.py` (ledger now 121 rows, 8 BUILT, 0 receipts); `tests/test_prune_axis.py`; rewrote `SLOT_PLAN.md` to one page (PRUNE `>3px` queued as slot 5, `>1px` conditional); appended the PRUNE packet (files, form notes, gate receipts, mechanism cards) to `docs/SUBMIT.md`; added IR-DEC-07/08/09 to `IRREGULARITIES.md`; updated only the README CURRENT STATE block.

### 3.2 What the Human Decided (or Did Not) and Must Still Supply

- The session brief again left `AXIS`, `TOP_PUBLIC`, and slot quota blank, and the agent's clarification questions were skipped. `AXIS = PRUNE` is therefore recorded as **AGENT-SELECTED** (next unbuilt axis in the repo's `SLOT_PLAN.md` sequence after MASS/SNAP), not as a human assignment (IR-DEC-08). No live score was treated as a receipt.
- Still required from the human before/while spending slots: (1) current `TOP_PUBLIC` with date read, slots left this week / total, and confirmation of the 2026-12-03 deadline; (2) the organizer receipt (`receipt_score` + date in `ledger/submissions.csv`) for R0 (0.2778 CLAIM) and for each BUILT variant as manually uploaded — one file per slot from the human's own registered account; (3) confirmation of the data-use-terms question in IR-DEC-01.
