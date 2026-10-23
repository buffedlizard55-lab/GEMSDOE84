# AI use disclosure (competition rules require disclosure; brief v2 §4.6)

Session 2026-10-23, branch `arena/b6ffc791-gemsdoe84`, AXIS=PRUNE.

## What the AI (Arena agent) wrote/did

- Fetched sha-pinned inputs from the owner's GitHub mirrors only (no
  Drivendata contact, no credentials, no submission code): R0 twins, h27-4
  base, H19-5/d1.5/d2.8 lineage, SGMC control; verified every hash before use
  and appended the three parent pins to `registry/data_manifest.json`.
- Verified R0 by file sha256 and by rebuilding its dot set
  (base − ≤2 px = R0 exactly); measured all lineage distance/spacing/block
  statistics quoted in the cards (scripts + receipts, deterministic).
- Wrote `scripts/build_prune_variants.py`, `scripts/validate_release.py`,
  `scripts/build_ledger.py`, `scripts/proxy_report.py`,
  `tests/test_metric_algebra.py`; built the two `releases/` variant pairs;
  ran all MUST gates on re-read files; ran report-only PROXY/SGMC.
- Drafted `ledger/`, `SLOT_PLAN.md`, `IRREGULARITIES.md`, `docs/SUBMIT.md`,
  mechanism cards, predictions (MODEL) and this disclosure.
- Did not submit anything, did not read the leaderboard, did not spend a slot.

## What the human decided

- Supplied brief v2 and assigned AXIS=PRUNE.
- Confirmed brief v2 supersedes the repo's duplicate-protocol STOP for this
  work (see `IRREGULARITIES.md` #2).
- Left TOP_PUBLIC, slot counts, deadline confirmation, and receipts as TBD
  (to be filled from the human's own registered account).
- Retains all submission decisions: which twin to upload, when, and final-file
  selection. All live scores remain CLAIM until the human pastes receipts.
