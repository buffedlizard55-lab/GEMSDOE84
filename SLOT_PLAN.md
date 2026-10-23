# SLOT_PLAN — GEMSDOE84 Controlled PRUNE Axis

**Parent:** h33-h33-2-b2 (GEMSDOE32) — 37,654 dots, none within 2 px, claimed 0.2778 CLAIM, verified sha256 `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9` (2026-10-22).  
**Beat:** TOP_PUBLIC = 0.4413 (owner-reported snapshot 2026-10-22, leaderboard_snapshot.json) — not verified live.  
**Quota:** ONE entity = 3 slots/week + 1 final, deadline 2026-12-03 → ~6 weeks remain (as of 2026-10-23). Slots left this week: 3/3, total: ~18.  
**AXIS this session:** PRUNE (values 1, 3, 4). All variants keep 37,654 dots, zero on catalogue, 5.8–10.2% changed (1–50% gate passed).

## Next 3 slots in order

1. **Slot 1 — PRUNE3 (≤3 px) `h33-h33-2-b2-PRUNE3-20261023-10737d46`** — Most mechanism-backed: removes 2–3 px ring (2,171 dots) that lineage suggests are near-catalogue FP, refills far (median d_cat 19.65→21.54 px). Predicted +0.006 ±0.007. *If live Δ ≥+0.01:* hidden truth is dominantly blind → commit to aggressive prune + combine with CONCENTRATION. *If ≤−0.01:* hidden truth includes splinters within 300 m → revert to PRUNE1 direction.

2. **Slot 2 — PRUNE1 (≤1 px) `h33-h33-2-b2-PRUNE1-20261023-29e1ae46`** — Contrarian test: adds 2,545 dots in 1–2 px ring, removes far tails (median 19.65→15.81 px). Predicted −0.004 ±0.006 (more FP). *If live Δ ≥+0.01:* organizer’s new faults are parallel splinters → pivot to SNAP (local edge refinement) to better place near-catalogue dots. *If negative as predicted:* confirms pruning value.

3. **Slot 3 — PRUNE4 (≤4 px) `h33-h33-2-b2-PRUNE4-20261023-f1facecf`** — Stress test: removes 3–4 px ring (3,825 dots, 10.16% changed, median 23.19 px). Predicted +0.002 ±0.008 (diminishing returns). *If beats PRUNE3:* optimum ≥4 px → next week combine PRUNE3/4 with MASS −10% to test density. *If worse:* optimum ≈3 px.

## Weeks to deadline

- **Wk1-2 (2026-10-23 → 2026-11-06):** Execute PRUNE slots 1–3 (this plan). Evaluate live Δ with ≥0.01 threshold (public chunks only). Log in ledger/submissions.csv.
- **Wk3-4 (2026-11-07 → 2026-11-20):** Combine two best axes. Candidate A: PRUNE-best + CONCENTRATION 10% move (10 km blocks, CV 0.799→0.55 target). Candidate B: PRUNE-best + RELIEF 10% shift (basin→range-front). Each changes 1–50% from parent, same count.
- **Wk5 (2026-11-21 → 2026-11-27):** Confirm: re-validate format (CRS/shape/transform/dtype, NaN inside=0, NaN outside for -nan, 0 outside for -zeros, zero on catalogue), re-run holdout PROXY (n withheld, 95% CI reported only), canary AUC≤0.90. No rank-correlation/uniqueness gates.
- **Wk6 (2026-11-28 → 2026-12-03):** Choose final file blind (best live Δ) + fallback (second-best or R0). Re-validate both, produce releases/<id>.tif + -zeros.tif, 140-char note, push PR, human submits from own account.

## Proposals for better axes (not built this session)

- **RELIEF-TERCILE:** Shift 10% mass between basin/piedmont/range-front terciles from detrended elevation (training_features band 12). Mechanism: blind faults exposed at range fronts vs concealed in basins. Confounder: alluvial fan aprons mimic scarps. Falsifier: no live Δ ≥0.01 after shifting terciles.
- **SNAP-EDGE:** Move each dot ≤2 px to strongest TMI/gravity gradient (bands 2/13) or lidar scarp composite. Mechanism: corrects 150–200 m GeoDAWN line uncertainty. Mimic: anthropogenic lineaments (roads, field boundaries). Falsifier: mean displacement >1.5 px with no live gain.
- **CONCENTRATION-BLOCK:** Move 15% dots from lowest to highest 10-km prior blocks (prior = Quaternary vent density). Mechanism: geothermal systems cluster at step-overs. Mimic: volcanic vent alignment without fault. Falsifier: CV moves outside 0.51–0.59 with no live gain.

