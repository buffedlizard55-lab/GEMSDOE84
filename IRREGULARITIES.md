# Decision-changing irregularities

## IR-R0-CONC-01 — R0 conflicts with the literal non-PRUNE exclusion

R0 uses `d_catalogue > 2` and contains **1,611 dots at `2 < d < 3` Euclidean px**, while the v2 brief requires every non-PRUNE variant to keep dots at **≥3 px**. A pure R0→CONCENTRATION edit is therefore impossible under the literal rules.

**Decision:** all three arms share one fixed compliance repair before dosing: 1,611 same-count replacements, of which 1,608 stay in their original 1 km block and 3 use the nearest eligible vacancy elsewhere; 538 replacements are off H19-5 support. Six blocks have a count change of one. This is recorded in every receipt. R0 comparisons include this confound; only dose-to-dose comparisons isolate concentration. The inherited catalogue PROXY falls from 0.003885 (95% CI [0.003318, 0.004453]) to zero after the repair, which makes the confound material but remains REPORT ONLY.

## IR-R0-CONC-02 — Prior STOP protocol explicitly revised

`AGENTS.md` and the previous session required a stop under rank-correlation/dot-overlap rules. The owner's v2 brief explicitly replaces those with exact-hash and repeated `(parent, axis, value)` dedupe and assigns controlled R0 axes.

**Decision:** this session follows v2 as the explicit protocol revision. No rank-correlation or dot-overlap uniqueness threshold was applied; the obsolete H84 STOP was not used to block these R0 experiments.

## IR-R0-CONC-03 — Target, slots, and deadline are not independently available

The v2 brief leaves `TOP_PUBLIC` and slot counts for the human and asks for deadline confirmation. DrivenData access is prohibited by the brief and was not attempted.

**Decision:** `TOP_PUBLIC`, slots left/total, and deadline confirmation remain UNSUPPLIED/UNVERIFIED. No score target, submission authorization, or slot consumption is inferred. The human must supply them.

## IR-R0-CONC-04 — Competition rasters already have public-mirror exposure

This repository and pinned owner mirrors already contain competition-derived rasters; their data-use terms are unchecked. Adding six new public binary artifacts would increase that exposure.

**Decision:** the required `releases/*.tif` files exist in the Arena workspace but are Git-ignored and excluded from the PR. Code, CSV ledgers, JSON format receipts, and submission instructions are included. Existing public raster exposure is flagged rather than represented as cleared.
