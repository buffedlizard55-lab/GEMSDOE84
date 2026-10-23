# AI_USE — what the AI wrote, what the human decided

Required by the challenge rules (generative-AI disclosure,
<https://docs.nlr.gov/docs/fy26osti/96647.pdf>). Session: 2026-10-23, branch
`arena/1c8a6632-gemsdoe84`.

## Written by the AI agent this session

- `scripts/restore_pinned_inputs.py` — single-pass, fail-closed restore of the pinned inputs
  from `codeload.github.com`, SHA-256 verified against `registry/data_manifest.json`.
- `src/gems84/parent.py`, `scripts/rebuild_r0.py` — the parent's recorded recipe, re-implemented
  and asserted byte-identical to the pinned R0 (`c55bafc4…`).
- `src/gems84/snap.py`, `scripts/build_snap_variants.py` — the AXIS=SNAP operator, the three
  variants, the format/hash/parent-diff gates and the release receipts.
- `scripts/build_ledger.py` — `ledger/submissions.csv` from this repo's committed score records.
- `scripts/measure_snap_reports.py` — the report-only proxy / canary / SGMC instruments.
- `tests/test_snap_axis.py` — metric-algebra, snap-operator and parent-rebuild tests.
- `SLOT_PLAN.md`, `IRREGULARITIES.md`, `docs/SUBMIT.md`, this file, and the README CURRENT STATE
  block.

AI assistance was used for code, for reading the restored upstream recipe
(`buffedlizard55-lab/GEMSDOE24`, `/GEMSDOE28`, `/GEMSDOE32`), and for the mechanism cards. No
external site was contacted except `codeload.github.com` and `api.github.com` (repo metadata) —
never drivendata.org, never dropbox.com. No credential was read, requested, stored or printed.
No submission was made and no leaderboard was scraped.

## Decided by the human (still outstanding)

- **AXIS for the session.** The brief left it blank; the agent chose SNAP and said why
  (`SLOT_PLAN.md`). The human may reassign.
- **TOP_PUBLIC** and **slots left this week** — human fills from the leaderboard, with a date.
- **Which file, if any, occupies a slot** — the agent never submits.
- **IR-84-S1**: whether the old rank-correlation / dot-overlap uniqueness protocol is still in
  force. If it is, these three files are research-only.
- **IR-84-S2**: whether hard constraint 4's "≥ 3 px from catalogue" is literal. If it is, these
  files are non-compliant and a PRUNE-axis build is required.
- **The ranking for any future MASS arm** — the parent's recipe stores none, so the ranking must
  be named by the human before a MASS variant is a controlled edit.
