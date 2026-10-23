# Lane H84B-UAS — Preregistered hypotheses (written BEFORE any experiment this session)

Session date: 2026-10-23. Branch: `arena/202ee691-gemsdoe84`.
Prior lane in this repo: H84-THMS (shipped, HOLDOUT-DTI 0.2255 dual-seed pooled, 22,663 withheld px,
evaluator `gems57-pooled-hide-v2`; no ORGANIZER-CONFIRMED score recorded in repo).

**IR-84B-01 (flagged irregularity):** the session prompt says "Your lane is the single method
paragraph below", but no method paragraph was present in the prompt as received. This session
therefore self-defines ONE lane (below), preregisters it here before running anything, and stays
inside it. The lane must still pass the duplicate gates (Spearman |ρ| ≤ 0.90 and 3-px dot
overlap ≤ 0.70 vs registry rasters, checked on surface and final dots).

## Why H33 scored 0.2778 (ORGANIZER-CONFIRMED) — short form
Full forensic proof: `research/why-h33-scored-02778.md`. Verified facts used here:
H33 = 37,654 binary dots = D2.8 Poisson-disk (r≈2.828 px) decimation of the H19-5 continuous
ridge field, pruned to d_cat > 2 px. Under DTI (α=0.2, β=0.8, R=3 px triangular, max-kernel),
dots closer than ~2.8 px cannibalise each other's kernel disk (ΔTP_w≈0, full extra FP_w), and
dots within 2 px of the mapped catalogue sit in the digitisation collar of already-known faults
(near-zero withheld-truth recovery, full FP cost). Removing both waste classes took
0.1922 → 0.2477 → 0.2600 → 0.2708 → 0.2778 (all ORGANIZER-CONFIRMED, owner-supplied receipts
in `registry/live_scores.csv`).

## What caps H33 — the exploitable gaps (measured, repo evidence)
1. **Fixed isotropic spacing.** r=2.8 px everywhere. On a correctly located fault trace, extra
   dots cost ~0 FP (k_self≈1) and raise TP_w (truth px midway between 2.8-px-spaced dots gets
   only k≈0.53). Under high positional uncertainty the opposite holds. Optimal spacing is
   therefore a function of local trace-location uncertainty — no prior family lane varies it.
2. **1.2 km truncation.** 100% of H33 dots at d_cat ≤ 12 px; repo holdout forensics put 53.2%
   of withheld fault px beyond 1.2 km. Cause: catalogue-distance features (ns_logdist AUC 0.80)
   dominate the parent ridge field.
3. **Binary-only emission.** The metric is soft (TP_w uses p(x)·k). Theory check (this doc):
   for independent locations DTI is linear-fractional in p ⇒ bang-bang (0/1) is optimal; soft
   gains can only come from max-kernel interactions and ratio-variance reduction. Expected
   small — worth one holdout arm as a falsification test, not a lane.

## Candidate hypotheses, ranked

### H-UAS-1 (RANK 1 — THE LANE): Uncertainty-Adaptive Anisotropic Spacing
- **Layers:** 19 official `training_features.tif` bands + `external/lidar_scarp_features_u8.tif`
  + `external/topo_10m_derived_100m_u8.tif` (all already SHA-pinned in
  `registry/data_manifest_liti.json`; no new external data).
- **Signature:** bagged HistGradientBoosting ensemble → mean surface μ(x) and inter-seed
  disagreement σ(x). Dot spacing s(x) = clip(s0 + a·σ̂(x), 1.5, 3.4) px (dense where the trace
  is confidently located, sparse where not), admitted greedily by expected marginal DTI
  (Dinkelbach test vs μ interpreted as calibrated hit-probability field), collar d_cat > 2 px.
- **Why unmapped faults:** catalogue faults are the confidently-mappable subset by construction.
  Withheld/undiscovered faults concentrate where μ is moderate and σ high (buried piedmont
  splays, playa-masked traces) — exactly where fixed 2.8 px spacing either over-spends FP (if
  the trace is mislocated) or under-covers TP (if located). Spacing matched to σ spends the
  same dot budget at higher expected TP_w/FP_w.
- **Differs from all prior lanes:** every scored family submission used fixed spacing
  (Poisson r=1.5/2.8, lattice s=5, fixed-min-dist Dinkelbach in H82/H83/H84-THMS).
  σ-adaptive spacing + distance-blind training (H-UAS-2, folded in as an ablation arm) is new.
- **Named non-fault mimic:** ensemble disagreement is also maximal at lithologic contacts,
  caldera margins and road/rail corridors — σ may track mapping ambiguity, not faulting.
- **Expected gain / cost:** +0.01…+0.03 HOLDOUT-DTI over fixed-spacing same-surface control /
  medium (one ensemble fit + greedy emitter).

### H-UAS-2 (RANK 2 — ablation arm inside the lane): Distance-Blind Far-Field Recovery
- **Layers:** physical bands only; NO catalogue-distance or catalogue-derived feature anywhere.
- **Signature:** same μ(x) with distance features deleted; dot budget allocated across
  d_cat bands (2–12 px, 12–30 px, >30 px) by holdout-measured marginal DTI per band.
- **Why unmapped:** removes the mechanism that truncated H33 at 1.2 km.
- **Mimic:** far-field base rate is low; band quota may just spend FP in empty basins.
- **Expected gain / cost:** +0.005…+0.02 / low.

### H-UAS-3 (RANK 3 — falsification arm): Soft Fractional Hedging
- **Layers:** μ(x) from H-UAS-1. **Signature:** emit p = clip(μ_cal, 0, 1) at admitted
  locations instead of 1.0. **Why:** max-kernel soft TP_w. **Theory predicts ≈0 or negative**
  (bang-bang optimality); a clean negative closes this question for the whole programme.
- **Mimic:** miscalibration of μ masquerades as hedging gain. **Cost:** trivial.

### H-UAS-4 (RANK 4 — not run unless budget remains): Across-Strike Staggered Double-Row
- **Layers:** μ(x) Hessian ridge width. **Signature:** where ridge width > 2 px (across-strike
  uncertainty), two staggered rows at ±1.5 px, along-spacing 4 px. **Mimic:** broad gradients
  from lithology, not wide fault zones. **Cost:** medium.

### H-UAS-5 (RANK 5 — diagnostic only): Seismogenic Blind-Fault Coincidence
- **Layers:** bands `earthquake_density`, `distance_to_earthquake`, `geodetic_dilatation_rate`,
  `depth_to_basement` (in-stack; underlying official source USGS Earthquake Catalog,
  https://earthquake.usgs.gov/earthquakes/search/ — free, no new fetch needed).
- **Signature:** high eq-density × dilatation × deep-basement coincidence far from catalogue.
- **Why unmapped:** buried intrabasin faults are seismogenic but have no surface trace.
- **Mimic:** geothermal-field induced seismicity; aftershock clouds. **Cost:** low.
  Tested only as a canary/AUC diagnostic in EXP-1.

## Experiment budget (protocol: ≤3)
- EXP-84B-1: leakage canary — single-feature AUC of every candidate channel (incl. σ, eq
  coincidence) on spatially-blocked holdout. Any AUC > 0.90 ⇒ leakage, stop & investigate.
- EXP-84B-2: holdout arms on identical folds: (A0) fixed 2.8 px spacing control on μ;
  (A1) σ-adaptive spacing; (A2) A1 + distance-blind band quota; (A3) soft-fractional A1.
  Pooled HOLDOUT-DTI + block-bootstrap 95% CI, evaluator `gems57`/`gems84` dti_fast (α0.2 β0.8 R3px).
- EXP-84B-3: build winning arm on full catalogue-visible training, uniqueness gates vs registry
  (surface ρ and final-dot 3-px overlap), fail-closed writer + 15-pt validator, run card.
  Verdict promote ONLY if EXP-2 winner beats A0 control with CI excluding 0 AND gates pass.
  A negative result is shipped as a negative run card with NO new submission file promoted.

## AMENDMENT 2026-10-23 (recorded BEFORE running EXP-84B-3)
EXP-84B-2 result: A1 (σ-adaptive) 0.1570 < A0 (fixed) 0.1703; A3 soft 0.1356 (theory-confirmed
negative). Diagnosis: bagged-HGB σ has raw AUC 0.61–0.64 FOR withheld faults — σ tracks
decision-boundary ambiguity μ(1−μ), not trace positional error, so "sparse where σ high"
thinned dots on faults (TP −8%). H-UAS-1 as specified is FALSIFIED.
EXP-84B-3 is redefined (build becomes a production step after EXP-3, disclosed here):
test preregistered H-UAS-4's variable — POSITIONAL sharpness h(x)=μ−blur₂(μ) — as the spacing
driver (dense 1.5px on sharp ridges → sparse 3.4px on diffuse), identical folds/seeds/models,
A0 re-emitted as determinism control (must reproduce 0.1703). Promote ONLY if A4 > A0.
If A4 also fails: lane verdict = negative; a unique candidate TIF from the A0 control surface
may still be shipped CLEARLY LABELLED unpromoted (selector step is separate, per protocol §6).
