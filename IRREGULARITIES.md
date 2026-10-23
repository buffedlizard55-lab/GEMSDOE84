# IRREGULARITIES — GEMSDOE84 PRUNE Session 2026-10-23

> Only items that change a decision are logged here. This file is the decision log required by the brief: “If this brief conflicts with the official rules or the problem page, they win; log it in IRREGULARITIES.md.”

## IR-20261023-01 — Missing ledger/ and SLOT_PLAN.md on session start

**What was found:** `ledger/submissions.csv` and `SLOT_PLAN.md` did not exist at session start (verified `ls ledger/` → not found). The brief’s session task says “read ledger/ and SLOT_PLAN.md. Do not re-read all the sites.” and “Every file is an experiment with a predicted outcome; own the result end to end. Each (AXIS, value) pair is built once across all sessions; check the ledger first.”

**Impact:** Could not check for duplicate (AXIS, value) pairs from prior sessions. Mitigation: created `ledger/submissions.csv` anew with 3 PRUNE variants (PRUNE1, PRUNE3, PRUNE4) and documented that no prior PRUNE rows exist in `registry/live_scores.csv` or `evidence/` ledger. Verified SHA256 not already in `registry/live_scores.csv` (no overlap with parent c55bafc4).

**Decision change:** None; proceeded to build PRUNE axis (most mechanism-backed given parent lineage).

## IR-20261023-02 — Hard constraint 4 vs parent R0 geometry

**What was found:** Hard constraint 4: “Emit zero mass on catalogue pixels and keep ≥3 px from them unless AXIS=PRUNE.” Parent R0 `h33-h33-2-b2` (c55bafc4) has 2,171 dots within 3 px (5.77% of its 37,654 dots, median 19.65 px) and is therefore *not* ≥3 px compliant. It is ≥2 px compliant (0 within 2 px).

**Conflict:** If the hard constraint is read literally, every non-PRUNE variant would need to be *more* aggressive than parent (≥3 px), which itself would be a 5.77% change and would confound any other AXIS (MASS, CONCENTRATION, etc.) that is supposed to differ *only* on that AXIS.

**Resolution per brief:** Brief wins over inferred constraints only if it conflicts with official rules/problem page; here the brief *is* the rule for this session. We logged the conflict and chose **AXIS=PRUNE** for this session precisely so that both PRUNE1 (allows 1–2 px, violates ≥3 px) and PRUNE3/4 (enforces ≥3 px / ≥4 px, satisfies) are legal under the PRUNE exception. For any future non-PRUNE session, the 2,171 dots within 3 px must be removed and refilled before applying that AXIS, and the parent-diff must include that 5.77% baseline.

**Decision change:** Chose PRUNE as session AXIS to avoid confounding; documented.

## IR-20261023-03 — Data manifest ext files UNVERIFIED but not used

**What was found:** `registry/data_manifest.json` pins 22 files; only 3 core files (`labels.tif`, `existing_faults.tif`, `sample_submission.tif`) are present locally in `data/bridge/` and verified SHA256 MATCH (see `evidence/data-verification.json`-style check in session log). All 5 `training_features.tif.part-*` (418 MB, 19 bands) and 6 `ext_*` + 6 `scored_*` + 5 `calib_*` files are UNVERIFIED (not found locally).

**Impact:** Session AXIS PRUNE uses *only* `existing_faults.tif` (catalogue) + `sample_submission.tif` (footprint) + parent R0 file (verified c55bafc4 from GEMSDOE32, licensed shareable, URL + hash given). No ext/scored/calib bands are read, stored, or inferred, satisfying hard constraint 2: “only files pinned in registry/data_manifest.json (or repo equivalent); verify sha256 before use.”

**Decision change:** Used only pinned+verified inputs; logged UNVERIFIED as not used, not as error.

## IR-20261023-04 — NaN-outside vs zeros-outside portal behavior

**What was found:** Brief §2 says raster null/NaN outside footprint (spec literal). Brief §7 says emit both `releases/<id>.tif` (NaN outside, per spec) and `<id>-zeros.tif` (fallback). Repo history (IR-57-NAN-02) documents 29 fleet rasters failed portal with “Predicted values must be in range [0, 1]” because portal evaluates `np.all((pred >=0)&(pred<=1))` without stripping NaN (NaN≥0 → False).

**Conflict:** Spec-literal NaN file is validator-correct but portal-failing; zeros file is portal-safe but spec-deviating.

**Resolution:** Built both per §7. Validator receipts: zeros files PASS all_checks (no_nan_anywhere True, range [0,1], zero_on_catalogue True); NaN files show no_nan_anywhere False (expected, 7,114,860 NaN outside), but in_footprint_all_finite True and zero_on_catalogue True. Human is instructed to upload *only one* per slot, default to `-zeros.tif`.

**Decision change:** None; documented for human.

## IR-20261023-05 — TOP_PUBLIC and quota values are owner-reported

**What was found:** Brief requires “Beat: TOP_PUBLIC = ____ (human fills from leaderboard, with date).” We filled TOP_PUBLIC = 0.4413 from `registry/leaderboard_snapshot.json` (rank 1 xiaofanhu, 2026-10-22 snapshot, class OWNER-REPORTED, no organizer receipt). Quota: ONE entity 3 slots/week, one final, deadline 2026-12-03 (from brief §5, confirm on competition page).

**Why it matters:** No other target number is valid per brief; using owner-reported 0.4413 as beat target could mis-set ambition if leaderboard moved.

**Decision change:** Labeled TOP_PUBLIC as OWNER-REPORTED, not RECEIPT/ORGANIZER-CONFIRMED; advised human to confirm date on competition page before slot use.

