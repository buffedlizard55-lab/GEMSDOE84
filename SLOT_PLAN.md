# SLOT PLAN — single entity, 3 scored slots/week, deadline 2026-12-03

- **Today** `2026-10-23` (UTC) · **Deadline** `2026-12-03` = `41` days = `5.86` weeks · max `18` slots at `3/week` for ONE entity (owner must confirm the live quota; `TopPublic` is still `UNVERIFIED`).
- **Parent R0** `h33-h33-2-b2` (`37,654` unit-mass dots, `d_cat > 2.0 px`, `0.2778` **CLAIM** — no organizer receipt in `ledger/`). Re-verified byte-identical this session (`c55bafc4…`).
- **Built, gated, unscored** (`ledger/submissions.csv`): MASS `-10pct` / `+10pct` / `-20pct` · SNAP `1p4px-g0p02` / `2p0px-g0p02` / `2p0px-g0p01` · **PRUNE `d2p5` / `d3p0` / `d4p0`** (this session, `scripts/build_prune_variants.py`, `evidence/prune_variants_receipt.json`).
- Treat any live change `< 0.010` as **no evidence** (public chunks only; the private score differs).

## 1. Next three slots

| # | File (`releases/<id>.tif`; upload the matching `-zeros.tif` only if the portal rejects NaN) | Change vs R0 | Predicted live change | What the receipt decides |
|---|---|---|---|---|
| **1** | `h33-h33-2-b2-mass-drop10pct-20261023-2cde51f3` | drop lowest-ranked `10.00%` (`37,654 → 33,889`) | `+0.0020..+0.0045` (MODEL) | The whole lineage wins by pruning. If `> 0.2778`: the tail is FP-dominated → make `33,889` the new parent and burn slot 2 on the steepest prune (`-20pct`). If `< 0.2778`: R0's tail carries real credit → stop pruning, spend the week on SNAP. |
| **2** | `h33-2-b2-pruned3p0-20261023-26e80847` | collar `2.0 → 3.0 px`, count held at `37,654` (`2,171` out / `2,171` in, `11.53%` changed) | `+0.0000..+0.0047`, central `+0.0024` (MODEL) | **The masking test.** Known catalogue pixels are masked out of the labels, so dots inside the 3 px kernel alive only on *new-fault* truth. If `≥ 0.2790`: masking dominates → move to `d4p0` next week. If `≤ 0.2768`: new-fault truth does lie within 300 m of the known traces → collar is productive, revert to `<= 2 px` and never widen it. |
| **3** | `h33-2-b2-snap2p0px-g0p01-20261023-7bdaa58b` | `26.47%` of dots moved ≤2 px onto the TMI/gravity-gradient edge, mean shift `1.90 px` | `+0.018..+0.044` (MODEL) | Largest built effect and it does not change mass or collar. If it lands, position error (not dot selection) is the real headroom → SNAP becomes the weekly lever and slot 3 next week is `snap` × winning collar. If it does not, the 400 m line spacing is already unresolved at the 3 px kernel and no geometry work will pay. |

Fallbacks already built: `mass-add10pct` (tests under-allocation), `snap2p0px-g0p02` (weaker variant of slot 3), `pruned2p5`/`pruned4p0` (either side of slot 2).

## 2. Weeks to the deadline

- **Wk 1** slots 1–3 above (one point each on MASS, PRUNE, SNAP — three mechanisms, not one curve).
- **Wk 2** (slots 4–6): escalate the winner and fill the mass curve — MASS `-20pct` and `+10pct` if slot 1 was ambiguous; otherwise `pruned4p0` or `snap1p4px-g0p02`.
- **Wk 3–4** (slots 7–12): one interaction at a time on the 2 best axes (collar × snap; collar × mass), matched count each time.
- **Wk 5–6** (slots 13–18): confirm the best file twice (shipped `.tif` and `-zeros.tif` twin), re-validate format on both, choose the **final blind submission** plus a fallback, re-run the format gate on the fallback.

## 3. Provenance caveat that must gate the *reading* of results

The catalogue hide-and-recover `PROXY` is structurally blind to collar geometry: the withheld truth is catalogue-derived, so any arm pushed `≥ 3 px` off the catalogue scores `0.0000` there while the same family scores `0.2778` live. Use the proxy for *ranking quality* only, never to rank PRUNE arms (`IR-DEC-08`).

## 4. Better axes for future sessions (proposed, not built)

1. **`AXIS = PRUNE-CONTINUOUS`**: replace the hard collar with a radial kernel-alignment weight — dots at `d_cat ∈ (3, 6) px` placed *along-strike* of the nearest mapped trace rather than across it. *Mechanism*: unmapped splays are strike-parallel; *confounder*: fan-head trenches parallel to range fronts; *falsifier*: no live change vs `d3p0` at matched count.
2. **`AXIS = CONCENTRATION` (1 km blocks)**: move `10–20%` of dots from the lowest-prior blocks to the highest, report block-density CV (best files reportedly `0.51–0.59`). *Mechanism*: fault systems cluster at step-overs; *confounder*: Quaternary basin fill suppresses detection, so high-prior blocks may just be well-imaged; *falsifier*: CV rises but live score falls.
3. **`AXIS = RELIEF`**: shift `10–15%` of mass between basin / piedmont / range-front terciles of detrended elevation, count fixed. *Mechanism*: range-front faults carry most new mapping; *confounder*: relief is also where lidar coverage and DEM texture are best.
