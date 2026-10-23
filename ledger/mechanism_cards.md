# Mechanism Cards — PRUNE Axis (h33-h33-2-b2 variants)

**Parent:** h33-h33-2-b2 (GEMSDOE32) — 37,654 unit-mass dots, 0 within 2 px of catalogue, 2,171 within 3 px, median d_cat 19.65 px (1.965 km), claimed 0.2778 CLAIM. Verified sha256 `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`. Lineage: H19-5 121k px 0.1922 → D1.5 0.2477 → D2.8 0.2600 → H27-4 0.2708 → H33-2-B2 0.2778 (each step pruned near-catalogue dots). DTI = T/(0.2T+0.2(S-M)+0.8|G|), R=300 m triangular kernel, α=0.2 β=0.8. Isolated dot pays iff credit >0.2·DTI ≈0.056 at 0.28.

## Variant 1 — PRUNE1 (≤1 px exclusion)

- **ID:** h33-h33-2-b2-PRUNE1-20261023-29e1ae46
- **Change:** 6.76% of dots (2,545/37,654) moved: removed 2,545 far tails (dist >≈30 px), added 2,545 in 1–2 px ring (dist 1–2 px). Count fixed 37,654, zero on catalogue, now 2,545 within 2 px (was 0), 4,716 within 3 px, median 19.65→15.81 px. Block-density CV (10 km) 0.799→0.815 (more concentrated near catalogue).
- **Hypothesis:** Hidden new-fault truth includes significant parallel splinters / re-mapped traces within 100–200 m of known USGS/INGENIOUS traces (organizer forum confirms new-fault truth *can* lie within 300 m of known traces). Parent’s aggressive 2 px prune may have discarded valuable near-catalogue TP.
- **Mechanism:** Organizer masks known faults pixel-exactly; pixels beside them are scored normally against new-fault truth. A dot at 150 m from a known trace can earn full kernel credit (triangular weight 0.5 at 150 m) if a parallel splinter lies within 300 m. Pruning to 2 px forgoes that credit.
- **Non-fault mimic:** Colluvial aprons, lithologic contacts, vegetation lineaments, or scarp degradation halos subparallel to range fronts within 100–200 m of catalogue. Also DEM/LiDAR hillshade artifacts along known fault scarps.
- **Predicted sign/size:** **Negative** −0.004 ±0.006 (MODEL). Lineage shows each pruning step (D2.8→H27-4 Δ+0.0108, H27-4→H33-2-B2 Δ+0.0070) improved live score; reversing it should hurt. Expected FP mass increase 2,545·1.0 ≈2,545 weighted FP vs TP gain ≤0.5·2,545≈1,272 if only 50% of ring hits truth.
- **Falsifier:** Live Δ ≥+0.01 (public chunks, private may differ; treat <0.01 as no evidence) for PRUNE1 over R0. Would indicate near-catalogue hidden faults dominate and parent over-pruned; falsifies “blind far faults dominate” model.

## Variant 2 — PRUNE3 (≤3 px exclusion) — *Recommended Slot 1*

- **ID:** h33-h33-2-b2-PRUNE3-20261023-10737d46
- **Change:** 5.77% (2,171/37,654) moved: removed 2,171 dots in 2–3 px ring (the only near-catalogue dots parent retained), refilled 2,171 uniformly from allowed domain dist>3 px (median 19.65→21.54 px, within-3 px 2,171→0, CV 0.799→0.785). Same count, zero on catalogue, now ≥3 px from catalogue (satisfies hard constraint).
- **Hypothesis:** The 2–3 px ring dots are residual FP from the 100–200 m GeoDAWN line-spacing uncertainty (≈kernel radius). True hidden faults are dominantly blind intra-basin / range-front continuations >300 m from known traces (Faulds step-over systems on known faults are a *prior on interaction zones*, not fault pixels; target is fault pixels, not vents). Removing them increases precision without losing recall.
- **Mechanism:** DTI denominator penalizes S (sum p) and FP mass 0.2(S−M). Near-catalogue dots have low expected credit E_K[y_i] <0.038 (threshold at 0.28) because known traces are masked and hidden faults are not clustered there; they add denominator without numerator. Dinkelbach allocation says place dots where E_K[y_i] >0.038. Far blind dots have higher E_K.
- **Non-fault mimic:** Range-front alluvial fan toes or piedmont pediment breaks at 200–300 m from range-bounding faults could be mistaken for fault scarps if we prune them, we lose TP. Also relay ramps between en-echelon segments can sit 200–300 m from main trace.
- **Predicted sign/size:** **Positive** +0.006 ±0.007 (MODEL). Based on lineage Δ per % pruned: H27-4→H33-2-B2 removed 6.35% (2,545/40,199) for +0.0070 → 0.0011 per %; PRUNE3 removes 5.77% → +0.006. Small but directional.
- **Falsifier:** Live Δ ≤−0.01. Would indicate 2–3 px ring contains real parallel splinters or refined traces that contribute TP >0.056 credit; falsifies aggressive-prune model and would push next experiment to SNAP (local 2 px edge refinement) rather than more pruning.

## Variant 3 — PRUNE4 (≤4 px exclusion)

- **ID:** h33-h33-2-b2-PRUNE4-20261023-f1facecf
- **Change:** 10.16% (3,825/37,654) moved: removed 3,825 dots in 2–4 px (parent’s 2,171 in 2–3 px plus 1,654 in 3–4 px), refilled far (median 19.65→23.19 px, CV 0.799→0.772). Count fixed, ≥4 px from catalogue.
- **Hypothesis:** Pruning benefit is monotonic up to ~400 m (GeoDAWN 400 m line spacing → positional uncertainty ≈300 m kernel radius). Dots within 400 m of known traces are within the survey’s uncertainty envelope and are low-precision.
- **Mechanism:** Same DTI denominator logic as PRUNE3, extended to 400 m where GeoDAWN airborne magnetics/radiometrics have 150–200 m terrain clearance and 400 m line spacing; lineament positions are uncertain by ~kernel radius (USGS DDS 657e1d85d34e23d3533209f7). Farther refill samples unmapped basin interiors where 75% of geothermal systems are blind (Coolbaugh/Faulds).
- **Non-fault mimic:** Basin-center playa shorelines (Lahontan 1,270–1,340 m) and axial drainage terraces at >300 m from range fronts could be mistaken for blind faults; aggressive prune toward basin could increase FP there.
- **Predicted sign/size:** **Near-zero** +0.002 ±0.008 (MODEL). Diminishing returns: 3→4 px ring is sparser and less FP-dense; further pruning helps less and may start removing true relay-ramp TP. Predicted smaller than PRUNE3.
- **Falsifier:** If PRUNE4 beats PRUNE3 by ≥0.01, optimum is >3 px → next week test MASS −10% (sparser) + PRUNE4. If PRUNE4 < PRUNE3 by ≥0.01, optimum ≈3 px → stop pruning and combine PRUNE3 with CONCENTRATION.

**Shared notes:** All variants emit 0 mass on catalogue pixels (hard constraint 4) and keep footprint exactly (3730×3292, EPSG:32611, 100 m, transform 100,0,243350,0,-100,4508550). Values in [0,1], float32, single band, NaN outside (spec) + 0-outside fallback (portal). SHA256 not in ledger. Parent-diff 5.8–10.2% (1–50% gate). Re-read from disk after writing. PROXY hide-and-recover (n withheld, 95% CI) and leakage canary (AUC>0.90 stop) reported only, never gated. Live Δ<0.01 = no evidence (public chunks only).
