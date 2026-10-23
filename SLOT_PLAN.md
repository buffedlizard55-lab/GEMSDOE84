# Slot plan — one entity, 3 scored slots / rolling week (2026-10-23)

Parent R0 `h33-h33-2-b2` 0.2778 **CLAIM** (no receipt on file). TOP_PUBLIC:
**not supplied** — no numeric target is valid until the human fills it with a
date. Slots left / total: **not supplied**. Deadline 2026-12-03 **unconfirmed**
(human to confirm on the competition page) ⇒ ≤6 weeks nominal. Evidence bar:
a live change < 0.01 is no evidence (public chunks only; Phase 1 is private).

## Next 3 slots, in order

1. **`h33-h33-2-b2-prune3r-20261023-8316df41`** (BUILT, gates pass). PRUNE B=3,
   5.77% replaced. Predicted +0.004 [−0.003,+0.011] MODEL.
2. **`h33-h33-2-b2-prune4r-20261023-2459d700`** (BUILT, gates pass). PRUNE B=4,
   10.16% replaced. Predicted +0.005 [−0.008,+0.018] MODEL. Submit in the same
   week as slot 1 only if slot 1 returns ≥ R0 − 0.01; the pair is a dose curve.
3. **HOLD.** Do not spend slot 3 until slots 1–2 are read. Decision tree:
   - B3 ≥ R0+0.01 and B4 ≥ B3 → collar mass is dead even at 4 px; next session
     tests B=5 or MASS−10% from the B4 parent. Slot 3 = that file.
   - B3 ≥ R0+0.01, B4 ≤ B3−0.01 → optimum collar ≈3 px; slot 3 = MASS−10% or
     CONCENTRATION built from the B3 parent (new parent, same discipline).
   - |Δ| < 0.01 for both → collar is credit-neutral on public chunks; keep R0
     as final-file candidate, spend slot 3 on SNAP (positional uncertainty is
     then the largest untested term) once built.
   - Either ≤ R0−0.01 → falsified: annulus earns (refined-geometry mimic).
     Stop pruning; slot 3 held for an add-back/collar-swap design review.

## Weeks to deadline (nominal; adjust to the confirmed date/slot count)

- Wk 1 (now): slots 1–2 above; human pastes receipts into
  `ledger/submissions.csv`, fills TOP_PUBLIC + slot counts. No third spend.
- Wk 2: one new axis from the winning parent (MASS needs ranking
  reconstruction first — see proposals; else CONCENTRATION with a stated
  prior/block definition, or SNAP on TMI/gravity gradients).
- Wk 3–4: combine the two best *evidenced* (≥0.01) axes, one file per slot,
  never two changes per file. Bank slots if nothing clears the bar.
- Wk 5: confirm the leader with its exact file (no re-encode); choose final
  file + fallback; start TRACKB trace write-ups for the finalist (Phase 2).
- Wk 6: re-validate both finalists byte-for-byte (`validate_release.py`),
  freeze code + AI_USE.md for reproducibility/disclosure, submit final blind.

## Proposed better axes (not built this session)

- **RANK reconstruction (enabler for honest MASS).** Mechanism: recover the
  H19-5→d2.8 thinning order from field-support geometry (e.g. local support
  density is a monotone proxy for the lost continuous field). Confounder:
  proxy rank ≠ true rank where the field was flat; validate by re-thinning
  and checking dot-set recovery vs the real d2.8. Falsifier: recovered
  top-37.7k ≠ R0 lineage beyond spacing ambiguity ⇒ MASS stays undefined.
- **Collar-swap control.** Mechanism: move each (2,3] annulus dot radially
  outward to (3,4] on the same field support (same azimuth sector), isolating
  distance from field quality better than nearest-eligible refill.
  Confounder: outward pixels may leave the lineament crest. Falsifier:
  swap ≈ refill result ⇒ distance, not placement, drove Slots 1–2.
