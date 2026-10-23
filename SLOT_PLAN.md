# SLOT_PLAN — next 3 slots, then the weeks to the deadline

Updated 2026-10-23 by the agent session on branch `arena/1c8a6632-gemsdoe84`.
Parent **R0 = `h33-h33-2-b2`** (GEMSDOE32), rebuilt byte-identically this session
(`evidence/r0_rebuild_receipt.json`, SHA-256 `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`,
37,654 dots). Its `0.2778` is a **CLAIM** (no receipt in `ledger/`).

- **TOP_PUBLIC = 0.3195** — `OFFICIAL_SNAPSHOT`, manual read of the public leaderboard
  2026-10-03 (`docs/evidence/upstream-score-ledger.csv`, rank 1 "DARD"). **Human must refresh
  this with a date before any slot decision**; this session was not allowed to read
  drivendata.org.
- **Slots left this week: unknown — human must fill.** One entity, 3 scored submissions per
  rolling week, one final submission chosen blind. Deadline 2026-12-03 (confirm on the
  competition page).
- **AXIS this session: SNAP** (the human left the axis blank). SNAP was chosen because it is
  the only axis whose inputs are all pinned-and-verified and whose definition needs no
  judgement call the parent does not already record — see "Axes not built, and why" below.

## Next 3 slots, in order

| # | File (`releases/`) | Change vs R0 | Predicted live change (MODEL) | What the result changes |
|---|---|---|---|---|
| 1 | `h33-2-b2-snap1p4px-g0p02-20261023-0b6a2ab2` | 2,416 / 37,654 dots moved (**6.42 %**), mean 1.383 px, onto stronger `tmi_hg`/`iso_grav_anom_hg` crests inside 1.42 px | **+0.004 … +0.011** | `>= +0.01`: SNAP mechanism confirmed → run slot 2. Within `±0.01`: **no evidence** (public chunks only) → skip slot 2, spend it on the human-approved ranking arm. `<= -0.01`: SNAP falsified — the gradient crests are non-fault contacts; close the axis and record the crest prior as harmful. |
| 2 | `h33-2-b2-snap2p0px-g0p02-20261023-b2019f55` | 4,152 dots moved (**11.03 %**), mean 1.910 px, window 2.0 px | **+0.007 … +0.019** | Dose step at a fixed gate. If slot 2 > slot 1 by `>= 0.01`, positional uncertainty is the binding constraint → run slot 3. If slot 2 <= slot 1, the extra reach is picking up parallel non-fault gradients; stop the ladder and keep slot 1's file as the SNAP candidate. |
| 3 | `h33-2-b2-snap2p0px-g0p01-20261023-7bdaa58b` | 9,966 dots moved (**26.47 %**), mean 1.898 px, loosest gate | **+0.018 … +0.044** | Top of the ladder. Only worth a slot if slots 1 and 2 were both positive: a monotone rise with dose is the mechanism signature, a fall means the gate was doing the work and the surface is noise. |

Prediction basis (all **MODEL**, never scores): a pure position change leaves dot count and
mass untouched, so `dDTI ≈ dT / D` with `D = 18,262` from the live-anchor inversion recorded in
`evidence/incumbent_anatomy.json`; scenario band = 10–25 % of moved dots closing one full pixel
of gap to a truth pixel (kernel gain 1/3 each). Preregistered **before** the report-only
measurements were run.

Report-only, never gates (`evidence/snap_reports.json`): catalogue hide-and-recover PROXY
moved **−0.00002 … −0.00010** vs R0 (0.00438 pooled, 22,641 withheld positives, Wilson 95 %
coverage CI ±0.001) and the SGMC control moved **−0.0005 … −0.0027** — both mildly negative
and both monotone in dose. Neither instrument is validated (the brief records a −0.87…+0.54
correlation with live scores), but they are the reason slot 1 is the *smallest* dose. Leakage
canary passed: worst single-band `max(AUC, 1−AUC) = 0.5765 <= 0.90`.

## Weeks to the deadline (2026-10-23 → 2026-12-03, ~6 weeks)

- **wk 1–2** — SNAP ladder (above). If it dies at slot 1, substitute the human-approved
  ranking arm (`CREDIT-REALLOC`, below) and then PRUNE-with-refill at fixed count.
- **wk 3–4** — combine the two best surviving axes at fixed count; one slot for the
  combination, one for the single-axis control.
- **wk 5** — confirm on a re-run of the winner, and build the Phase-2 `TRACKB` pack
  (strike-consistent ≥1 km traces + one evidence paragraph each) without spending a slot.
- **wk 6** — choose the final file and a fallback, re-validate the format of **both**
  (`scripts/validate_submission.py` against `sample_submission.tif`), and hand the human the
  two file names plus their 140-char notes.

## Axes proposed, not built this session

1. **CREDIT-REALLOC** (fixed count). *Mechanism:* the recorded inversion says R0's kept dots
   average 0.135 kernel credit against a marginal bar of 0.0556, and the DTI denominator
   charges 0.2 per dot whatever it earns — so re-placing the lowest-credit decile where
   uncovered plausible trace is densest should raise `T` at constant `n`. *Confounder:* it is
   MASS and CONCENTRATION wearing a fixed count; and any credit estimate fitted on the
   catalogue regresses toward already-mapped faults. *Falsifier:* a 10 % reallocation at fixed
   count that moves live by < 0.01 says credit, not geometry, was never the binding constraint.
   **Blocked on a human decision:** the parent's own recipe stores no dot ranking (see
   `IRREGULARITIES.md`), so the ranking must be named and approved before this is a controlled
   edit of R0.
2. **ACQUISITION-GATED SNAP**. *Mechanism:* positional uncertainty is a property of the survey,
   not of the pixel — GeoDAWN Area 2 was flown at ~400 m line spacing, so snapping should be
   restricted to those acquisition blocks and switched off where the data are already precise.
   *Confounder:* acquisition blocks are geologically biased (basin vs range front), so the arm
   mixes SNAP with RELIEF. *Falsifier:* block-restricted arm scores the same as the
   unrestricted arm → positional uncertainty is not the mechanism behind any SNAP gain.
3. **TRACKB for Phase 2** (not a weekly-slot candidate). *Mechanism:* Phase-2 labels are
   expanded by experts reviewing submitted faults, so a strike-consistent ≥1 km trace is worth
   more than the same mass as dots. *Confounder:* unmeasurable on public chunks; it can only
   waste a Phase-1 slot. *Falsifier:* if the human confirms Phase-1 scoring is what the week
   buys, drop it.

## Axes not built, and why

- **MASS** — needs "the parent's own ranking". The recorded recipe has none: R0 descends from
  `dot_thin`, a deterministic BFS Poisson-disk walk over the H19-5 field with no score
  (`GEMSDOE24/src/gems/thinning.py`), and GEMSDOE19 (the H19-5 field's own recipe) returns 404
  on `api.github.com`. Re-ranking by a substitute would not be a controlled edit of R0.
- **CONCENTRATION / RELIEF** — feasible with the restored `training_features.tif`, but each
  needs a km-block prior or a relief tercile definition that the parent does not record; both
  would import a modelling choice the session was not given.
- **PRUNE** — R0 already *is* the `B=2` prune, and the upstream instrument ranks `B=3` below
  `B=2` (`evidence/h33_validation.json` `lm_validity_report`: H33-2-B3 0.26437 vs H33-2-B2 0.26792 LM-calibrated), so the arm's expected
  value is the lowest of the set.
