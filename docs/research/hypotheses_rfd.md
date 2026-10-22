# Preregistered hypotheses — 2026-10-22

No assigned method paragraph was present. Lane selected explicitly: **H84-RFD: radiometric flanking dipole × relief-normalized LiDAR scarp**. No claim of novelty outside the inspected GEMSDOE32/83 source trees. These are fault-mapping hypotheses, not direct vent detections. Estimated benefit is ordinal judgment, not a projected competition score.

|Rank by expected benefit / cost|Layers and signature|Why potentially unmapped|Non-fault mimic|Difference from inspected code / viability|
|---|---|---|---|---|
|1 / low|Cached GeoDAWN K, Th: opposite-signed Gaussian Laplacians; multiply by cached LiDAR step/relief and coherence|A shallow displacement/alteration boundary may persist without a mapped continuous trace|Lithologic contact, soil moisture or transported sediment|Explicit signed cross-channel curvature discordance, rather than K/Th enrichment or gradient fusion. Cached inputs obtained and hash-verified. Exploratory, not established diagnostic.|
|2 / medium|Cached LiDAR downface/upface imbalance persisting at two neighborhood scales|Buried or degraded scarps may retain unequal facing breaks|Terrace riser and lake shoreline|Facing imbalance persistence rather than scarp maximum. Inputs available; untested.|
|3 / medium|Cached GeoDAWN U versus Th local rank residual, with scarp continuity|Fluid-mediated redox redistribution could mark an unmapped conduit|Weathering, alluvial sorting, uranium lithology|Conditional local residual rather than raw U or U/K. Inputs available; untested.|
|4 / medium|Cached LiDAR cross/step responses at radiometric curvature zero-crossings|Cross-cutting breaks could identify displacement across a lithologic marker|Road embankment or erosional contact|Contact-crossing geometry rather than parallel edge concordance. Inputs available; untested.|

Only rank 1 will be tested this run. Three experiments maximum: (1) feature canaries and surface audit; (2) fixed-parameter spatial holdout; (3) dot audit and packaging. Any binding duplicate or canary failure stops the run. No tuning after inspecting holdout results.

## Fixed design

Use cached uint8 derived stacks mirrored from GEMSDOE24 via GEMSDOE83's pinned manifest. They are owner-derived, not authenticated original USGS products. Quantized K and Th are **not** physical ratios or calibrated concentrations. Their opposite curvature is a heuristic, not proof of potassium metasomatism. Gaussian sigma = 3 pixels. The candidate is the geometric mean of normalized signed-curvature discordance and relief-normalized coherent step response. Control: relief-normalized coherent step only. Fixed dot separation 3 pixels; full-footprint target 37,654 dots, scaled by scored area per fold. No catalogue feature enters either surface. Visible faults are masked exactly at placement/evaluation. No scores from the production TIFF are used for selection.

Holdout: shared `gems57-pooled-hide-v2`, seed 20, four eroded quadrants, whole **template chunks** withheld, pooled terms and physical-block bootstrap. The template chunks branches to <=12 pixels; this is not withholding entire geological faults. The missing full-branch-plus-buffer instrument prevents claiming compliance with the stronger whole-fault requirement. This limitation must block promotion even if the exploratory score improves.

## Source scope

Official reference code was retrieved from https://github.com/drivendataorg/gems-prize-reference-solution . Its README explicitly supports CPU-only execution; a GPU is not a universal blocker. External network access here is restricted to GitHub and package registries. USGS, DrivenData, GDR and NLR pages cannot be independently refreshed in this environment. Their supplied URLs are review pointers, not freshly verified evidence. No new external dataset is required or proposed as downloaded.
