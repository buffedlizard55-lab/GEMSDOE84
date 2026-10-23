# SLOT PLAN — Single-Entity 3-Slots/Week Schedule to 2026-12-03

- **Current date**: `2026-10-23` | **Deadline**: `2026-12-03` (`41 days` ≈ `5.9 weeks`, max `18 slots` at `3/week`, ONE entity; human to confirm remaining quota — still unfilled).
- **Parent R0**: `h33-h33-2-b2` (`37,654` dots, `d_cat > 2.0 px`, `0.2778` CLAIM — `0` receipts in repo). **TOP_PUBLIC**: `UNVERIFIED` (stale snapshot `0.3195`, 2026-10-03).
- **Built, gated, unscored** (`ledger/submissions.csv`, `releases/`): MASS ×3, SNAP ×3 (2026-10-23 session 1), PRUNE ×3 (this session, count fixed `37,654`). Assumption recorded in `IRREGULARITIES.md` (IR-DEC-07): nothing submitted yet; if any file below already has a receipt, tell the next session and re-plan around the winner.
- Reading rule (Brief v2): a single live change `< 0.01` is no evidence; ordered patterns across an axis's receipts are.

## 1. Next 3 slots in order — Week 1 (AXIS = MASS, unchanged)

| Slot | Variant | Change vs R0 | Pred. (MODEL) | What the receipt changes |
|---:|---|---|---|---|
| 1 | `h33-h33-2-b2-mass-drop10pct-20261023-2cde51f3` | `33,889` dots (−10%) | `+0.0020..+0.0045` | `>R0`: R0 over-budgeted → parent mass drops. `<R0`: tail decile pays → Slot 2 is the candidate. |
| 2 | `h33-h33-2-b2-mass-add10pct-20261023-ad925bd2` | `41,419` dots (+10%, added at `d_cat>=3`) | `−0.0030..+0.0025` | `>R0`: test prevalence supports >37.6k. `<R0`: secondary ridges dilute. |
| 3 | `h33-h33-2-b2-mass-drop20pct-20261023-62bfc392` | `30,123` dots (−20%) | `+0.0010..+0.0065` | With 1–2, fits DTI(S) curvature → lock `S*` before combining axes. |

## 2. Week 2 queue — SNAP then PRUNE (all built; order within week as listed)

| Slot | Variant | Change vs R0 (`37,654` dots) | Pred. (MODEL) | What the receipt changes |
|---:|---|---|---|---|
| 4 | `h33-2-b2-snap2p0px-g0p02-20261023-b2019f55` | 11.03% dots moved ≤2 px to stronger TMI/grav HG | `+0.007..+0.018` | Tests positional error ~ kernel radius (GeoDAWN 400 m lines). `>R0`: snap the combined file. |
| 5 | `h33-h33-2-b2-prune-dge3refill-20261023-3745ebf6` | collar `>=3 px`: −1,611 diag dots, ranked refill (8.56%) | `0.000..+0.003` | `>R0`: adopt `>=3 px` collar everywhere. `<R0` by >0.001: (2,3) px ring holds splays. |
| 6 | `h33-h33-2-b2-prune-dgt1in-20261023-02ad0d5c` | collar `>1 px`: +2,545 ring / −2,545 lowest-gain (13.52%) | `−0.002..−0.006` | Falsification arm. `>=R0`: the 0.2708→0.2778 step was mass, not collar → reallocate budget near traces. |

Reserve built files if a week-2 slot must be swapped: `h33-h33-2-b2-prune-dgt3refill-20261023-10ce9ad1` (collar `>3 px`, 11.53%; submit only if Slot 5 ≥ R0, to price the exact-3.0 px ring), SNAP `1p4px-g0p02` / `2p0px-g0p01` (submit only if Slot 4 > R0, to price window/gate strength).

## 3. Weeks to deadline

- **Weeks 3–4 (slots 7–12)**: combine winners ONE interaction at a time on the best receipt parent (e.g. `S*` × winning collar; `S*` × SNAP; collar × SNAP). Then the still-unbuilt axes on that parent: CONCENTRATION (10–20% block reallocation, report density CV), RELIEF (basin/piedmont/range-front tercile shift).
- **Weeks 5–6 (slots 13–18)**: confirm the combined file, choose final + fallback, re-validate both formats from disk; TRACKB ≥1 km strike-consistent traces (GeoJSON + raster + per-trace evidence) prepared for Phase 2 expert review — not a weekly slot unless the human decides.

## 4. Proposed better axes (not built; for a future session)

1. **COLLAR_REFILL — BUILT this session** as PRUNE `dge3refill`/`dgt3refill` (see §2). Do not rebuild.
2. **`AXIS = TIP_CONE`** (unchanged from prior plan): shift 10% of dots from isolated intrabasinal ridges (`d_cat > 40 px`) into corroborated ±22°, 0.3–2.5 km along-strike cones ahead of catalogue terminations. *Confounder*: fan-head trenches at range-front stream mouths. *Falsifier*: live < R0 while SGMC control rises → hidden faults are whole unmapped structures, not tip extensions.
3. **`AXIS = SUBSURFACE_ANCHOR`** (unchanged): reallocate 10% from DEM-only ridges (`corrob_count == 1`) to basement-depth/MT/gravity-step-anchored ridges under Quaternary cover. *Confounder*: playa-brine conductors, caldera ring contacts. *Falsifier*: live < MASS −10% receipt → subsurface-anchored dots are worse than omitting the tail.
4. **`AXIS = VALUE`** (new): R0 is unit-mass; the format allows [0,1]. Halve the mass (0.5) of the lowest-gain decile instead of deleting it (same pixels, S −5%). *Mechanism*: under DTI algebra a 0.5-dot pays half the FP penalty while keeping partial max-cover credit where dots overlap a truth line. *Confounder*: organizer-side thresholding (none documented). *Falsifier*: live ≤ MASS −10% receipt at matched pixels → fractional mass never beats deletion.
