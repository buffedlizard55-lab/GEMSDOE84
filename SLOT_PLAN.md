# SLOT PLAN — Single-Entity 3-Slots/Week Schedule to 2026-12-03

- **Current date**: `2026-10-23` (UTC) | **Competition deadline**: `2026-12-03` (`41 days` = `5.86 weeks`, max `18 slots` at `3 slots/week` for ONE entity; human to confirm exact remaining weekly/total quota).
- **Parent R0**: `h33-h33-2-b2` (`GEMSDOE32`, `37,654` unit-mass dots, `d_cat > 2.0 px`, `0.2778` `CLAIM` — owner-reported in `registry/live_scores.csv`; `0` organizer receipts in repo).
- **Active session axis**: `AXIS = MASS` (`3` variants built in `releases/` and logged as `status = BUILT` in `ledger/submissions.csv`).

## 1. Next 3 Slots in Order (Week 1 — `AXIS = MASS`)

| Slot | Variant ID (`releases/<id>.tif` & `<id>-zeros.tif`) | Change vs R0 (`37,654` dots) | Predicted Live Change (`MODEL`) | Fold-Clean Hide & Recover (`PROXY`, $n=22,893$) | SGMC Off-Cat Control (`PROXY`, $n=62,703$) | Decision Rule: What the Live Receipt Changes |
|---:|---|---|---|---|---|---|
| **1** | `h33-h33-2-b2-mass-drop10pct-20261023-2cde51f3` | Drop lowest-ranked `10.00%` (`-3,765` dots $\to$ `33,889`) | `+0.0020` to `+0.0045` DTI | `0.10439` (`95% CI [0.09228, 0.11565]`, $\Delta = -0.00126$) | `0.09156` raw / `0.06298` cal | **If $> 0.2778$**: R0 is over-budgeted; adopt `33,889`-dot parent as $R_1$ and testSlot 3 (`-20%`). **If $< 0.2778$**: R0 tail decile carries net-positive truth credit; prioritize Slot 2 (`+10%`). |
| **2** | `h33-h33-2-b2-mass-add10pct-20261023-ad925bd2` | Add next-ranked `10.00%` (`+3,765` dots at $r \ge 2.8\text{ px}, d_{\text{cat}} \ge 3.0\text{ px} \to$ `41,419`) | `-0.0030` to `+0.0025` DTI | `0.10737` (`95% CI [0.09503, 0.11862]`, $\Delta = +0.00172$) | `0.10719` raw / `0.06962` cal | **If $> 0.2778$**: unseen test fault prevalence $|G_{\text{test}}|$ supports $>37.6\text{k}$ dots; promote `41,419`-dot map to $R_1$. **If $< 0.2778$**: secondary ridges ($d_{\text{cat}} \ge 3\text{ px}$) dilute precision below the `7.19%` break-even bar. |
| **3** | `h33-h33-2-b2-mass-drop20pct-20261023-62bfc392` | Drop lowest-ranked `20.00%` (`-7,531` dots $\to$ `30,123`) | `+0.0010` to `+0.0065` DTI | `0.10149` (`95% CI [0.08969, 0.11274]`, $\Delta = -0.00416$) | `0.08368` raw / `0.05940` cal | Together with Slots 1–2, fits the 3-point quadratic $\text{DTI}(S)$ across $S \in \{30123, 33889, 37654, 41419\}$ to lock optimal mass $S^*$ before Week 2. |

## 2. Multi-Week Schedule (6 Weeks / 18 Slots to `2026-12-03`)

- **Weeks 1–2 (Slots 1–6)**: Single-axis isolation on `MASS` (Week 1: Slots 1–3 above) followed by `PRUNE` (`d_cat > 3.0 px` refilled at $S^*$ vs `d_cat > 2.0 px`), `CONCENTRATION` (reallocating 10–15% of dots from lowest-prior to highest-prior 10 km structural blocks at fixed $S^*$), or `SNAP` ($\le 2\text{ px}$ move onto local TMI/gravity-HGM/LiDAR scarp maximum).
- **Weeks 3–4 (Slots 7–12)**: Orthogonal combination of the 2–3 single axes that beat R0's live receipt (`MASS` $S^*$ + winning `PRUNE`/`CONCENTRATION`/`SNAP`/`RELIEF` setting), testing one interaction at a time.
- **Weeks 5–6 (Slots 13–18)**: Reserve slots for final variance-reduced ensemble verification and `TRACKB` geologist-vetted $\ge 1\text{ km}$ strike-consistent fault traces (GeoJSON + raster).

## 3. Proposed Better Single-Axis Experiments for Future Sessions (Not Built This Session)

1. **`AXIS = COLLAR_REFILL` (Euclidean $d_{\text{cat}} \ge 3.0\text{ px}$ Prune + Ranked Ridge Refill at Fixed $S = 37,654$)**:
   - *Mechanism*: R0 (`d_cat > 2.0 px`) retains `1,611` dots at diagonal distances $d_{\text{cat}} \in \{\sqrt{5}, \sqrt{8}\} \subset (2.0, 3.0)\text{ px}$ (`224–283 m`) from mapped catalogue faults. Under the $R = 300\text{ m}$ ($3.0\text{ px}$) triangular kernel, a dot at $2.24\text{ px}$ from a catalogue trace still has $38\%$ of its kernel disk overlapping the mapped trace's immediate halo where unmapped parallel splays are rare, incurring false-positive weight $0.2(1 - m_q)$. Replacing those `1,611` diagonal-collar dots (`4.28%` of R0) with the top `1,611` corroborated off-catalogue ridge dots ($d_{\text{cat}} \ge 3.0\text{ px}$) isolates pure collar geometry at fixed dot count.
   - *Confounder*: True en-echelon fault relay steps or sub-parallel hanging-wall splays lying `220–290 m` off a mapped master fault.
   - *Falsifier*: Live score drops by $> 0.0010$ relative to R0 at matched count `37,654`, proving that the $(2.0, 3.0)\text{ px}$ per-fault zone contains real unmapped test splays in `labels.tif`.
2. **`AXIS = TIP_CONE` (Along-Strike Catalogue Tip Continuation vs Intrabasinal Ridge Allocation at Fixed $S$)**:
   - *Mechanism*: Normal faults in the Basin and Range grow by along-strike tip propagation and relay-ramp linkage; unmapped fault segments preferentially extend within a $\pm 22^\circ$, `0.3–2.5 km` (`3–25 px`) cone ahead of mapped catalogue fault terminations when corroborated by horizontal gravity gradient (`18_iso_grav_anom_hg`) or 1 m LiDAR scarplets (`H33-C`). Shifting `10%` (`3,765` dots) of R0 from isolated intrabasinal ridges ($d_{\text{cat}} > 40\text{ px}$) into corroborated tip-continuation cones tests tip-growth localization at fixed count.
   - *Confounder*: Alluvial fan-head trenches and range-front stream mouths emerging at fault tips that mimic short scarp continuations.
   - *Falsifier*: Live score decreases relative to R0 while `SGMC` off-catalogue control increases, proving hidden public-test faults are whole unmapped range/basin structures rather than unmapped tip extensions of existing catalogue traces.
3. **`AXIS = SUBSURFACE_ANCHOR` (Basement-Depth / MT-Conductivity Step Re-Weighting Under Quaternary Cover at Fixed $S$)**:
   - *Mechanism*: Across `24.60%` of the active footprint where 1 m 3DEP LiDAR coverage is zero and across thick Quaternary playas where surface scarps are obliterated, active hydrothermal faults are imaged primarily by step gradients in basement depth (`15_depth_to_base_surf`), magnetotelluric conductivity (`17_cond_surf`, `H33-D`), and horizontal gravity gradient (`18_iso_grav_anom_hg`). Reallocating `10%` of R0 dots from DEM-only ridges (`corrob_count == 1`) onto basement/MT-anchored ridges ($r_{\min} = 2.8\text{ px}, d_{\text{cat}} \ge 3.0\text{ px}$) tests blind-fault recovery.
   - *Confounder*: Non-tectonic conductive playa evaporite brines and buried caldera ring-fracture lithologic contacts.
   - *Falsifier*: Live score drops below `h33-h33-2-b2-mass-drop10pct` (`33,889` dots), proving that adding subsurface-anchored dots performs worse than simply omitting the bottom 10% of DEM-only dots.
