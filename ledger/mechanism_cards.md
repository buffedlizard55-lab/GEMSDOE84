# Mechanism cards — AXIS=PRUNE, parent R0 `h33-h33-2-b2` (2026-10-23)

Parent, verified this session: R0 (file sha256 `c55bafc4…`, 37,654 unit dots)
is exactly `h27-4-r1` (40,199 dots) minus dots ≤2 px from the catalogue, and
`h27-4-r1` is `d2.8` (44,090) minus dots ≤1 px. R0 has **0 dots within 2 px**,
2,171 within 3 px, 3,825 within 4 px; median catalogue distance 19.6 px.
Live anchors are CLAIM (owner-reported, no receipts): d2.8 0.2600 → h27-4
0.2708 → R0 0.2778. Both pruning steps are fit to within 0.0006 DTI by
assuming the deleted dots earned ~zero kernel credit (MODEL inversion in
`evidence/incumbent_anatomy.json`; re-measured distances match it exactly).

## Card 1 — `…-prune3r-20261023-8316df41` (B=3 px + refill, 5.77% replaced)

- **Hypothesis.** The 2,171 R0 dots in the (2,3] px annulus earn below the
  marginal bar (≈0.2·DTI ≈ 0.056 at 0.28): at 200–300 m from a mapped trace,
  the ancestral field's support is mostly halo — mapping generalisation at
  100 m, damage-zone width of the *catalogued* fault, and GeoDAWN-scale
  positional smear — not distinct unmapped strands. Moving that mass to
  same-field pixels beyond 3 px (parallel splays, step-over relays, tip
  continuations of the kind the field actually nominated) raises mean credit
  per dot at fixed count.
- **Mechanism.** Organisers mask catalogue pixels pixel-exactly and score
  neighbours against new-fault truth only. If annulus dots sit on the
  already-mapped structure's halo, they pay full FP mass (≈0.2 each in the
  denominator) for ~no TP credit, exactly as the ≤1 and ≤2 px deletions
  measured live (+0.0108, +0.0070 CLAIM). Refill spends the same budget on
  field support whose nearest catalogue distance exceeds the kernel radius.
- **Non-fault mimic that would make this lose.** Refined geometry: the
  hidden compilation re-digitises existing systems offset by 200–300 m, so
  annulus dots sit on scored "new geometry" pixels and earn real credit
  (brief: "new fault" includes newly mapped geometry of existing systems).
  Genuine 200–400 m subsidiary shears inside wide damage zones act the same.
  The SGMC control falling with collar size (0.0929 → 0.0851 → 0.0780,
  PROXY) is consistent with this mimic, which is why the predicted range
  includes negative values.
- **Predicted live change (MODEL).** +0.004, range [−0.003, +0.011]
  (anchor algebra: Δ ≈ 2,171·(credit_refill − credit_annulus)/19,340 with
  credit_annulus 0–0.056, credit_refill 0.03–0.10 vs kept-dot mean 0.135).
  Below the 0.01 evidence bar centrally — read together with Card 2 as a
  dose pair. PROXY cannot rank this (mechanically 0.0000, see report note).
- **Falsifier.** Live ≤ R0 − 0.01 ⇒ the (2,3] annulus earns above-bar
  credit on public chunks; prune direction is wrong, stop and test add-back.
- **Measured confounds.** Refill spacing floor 2.0 px vs parent 2.83 px
  (only 611 pool pixels satisfy 2.8 px — ancestral thinning is near-maximal);
  median refill displacement 11.4 px; 5 km block-density CV 0.899 → 0.908;
  refill tiers 1,326 d1.5 / 845 H19-5-only. All bias the gain downward.

## Card 2 — `…-prune4r-20261023-2459d700` (B=4 px + refill, 10.16% replaced)

- **Hypothesis / mechanism.** Same as Card 1, extended one kernel-width:
  the (3,4] annulus (1,654 further dots) is still halo-dominated. This is
  the dose step that can clear the 0.01 evidence bar if the hypothesis
  holds, and it localises the optimum collar when read against Card 1.
- **Mimic.** As Card 1, stronger: at 300–400 m, offset re-digitisation and
  true subsidiary strands are *more* plausible than at 200–300 m; these dots
  can also earn partial kernel credit from new-fault pixels within 300 m of
  known traces even when they are not on one.
- **Predicted live change (MODEL).** +0.005, range [−0.008, +0.018].
  Wider and less certain than Card 1 by design; it is an experiment, not a
  favourite.
- **Falsifier.** Card 1 ≥ R0 but Card 2 ≤ Card 1 − 0.01 ⇒ credit lives in
  (3,4]; optimum collar is 3 px. Both ≤ R0 − 0.01 ⇒ Card 1 falsifier.
- **Measured confounds.** Median refill displacement 32.3 px (refills travel
  to spacing gaps in the field — locality is weaker than Card 1); 5 km CV
  0.899 → 0.933; tiers 2,507 / 1,318. Interpret a Card-2 loss jointly with
  displacement, not as pure collar evidence.

## Deliberately not built (dedupe / undefined ranking)

- PRUNE B=3 **without** refill (35,483 dots) is dot-identical to GEMSDOE32
  `H33-2-B3`, already built 2026-10-04 (no live score in the ledger). Not
  rebuilt; if ever wanted it also confounds MASS (−5.8% dots).
- PRUNE B=1 **without** count-hold is the already-scored base (0.2708 CLAIM).
  B=1 *with* count-hold needs a within-tier ranking of R0's dots to trim;
  the lineage rasters are all binary, so that ranking is not stored and any
  invented trim rule would smuggle in a second axis. Not built.
