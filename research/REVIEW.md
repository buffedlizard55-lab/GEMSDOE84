# Research review and experiment preregistration

## Evidence boundary

Reviewed the entire starting checkout: README only. Inspected the recursive tree of GEMSDOE32 and the organizer reference through GitHub API; fetched the evidence listed below. This is not an exhaustive review of every linked GEMSDOE repository, nor line-by-line verification of all upstream claims. Raw upstream files retain their original, sometimes unsupported numbers; **they are archival evidence, not endorsed scores**.

| Source | Pin / status | Supports |
|---|---|---|
| [Organizer reference README](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md) | Retrieved via GitHub API | Data placement, notebook baseline, CPU/GPU options; not this checkout's readiness |
| [H33 audit](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/780a5a534269c79adfe6d1d7d5aadead161332aa/evidence/h33_validation.json) | Retrieved; third-party team evidence | Inherited-base removal mechanism; explicitly contaminated catalogue holdout; calibrated surrogate |
| [Data manifest](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/780a5a534269c79adfe6d1d7d5aadead161332aa/registry/data_manifest.json) | Retrieved; mirror provenance only | Hash-pinned public mirror pointers exist; organizer authentication does not follow |
| [Upstream irregularities](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/780a5a534269c79adfe6d1d7d5aadead161332aa/registry/irregularities.json) | Retrieved; third-party statements | Known footprint/provenance problems need independent resolution |
| [Competition problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Supplied official URL; blocked by network policy | Manual-review pointer only; no fresh verification |
| [Submission page/data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Not retrieved | Template, rules and submission cap must be checked on organizer service |
| [GDR INGENIOUS resource](https://gdr.openei.org/submissions/1391) | Not retrieved | Potential official thermal/geology data; availability/license not verified here |
| [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) | Not retrieved | Official-source pointer, not a verified available download |
| [Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | Not retrieved | Rules must be reviewed before slot selection |

The downloaded files came from `main`; the tip SHAs above were recorded during this session. Their per-file Git blob SHAs are recorded separately. No claim that these are organizer-verified competition assets is made.

## Why H33-2-B2 could help (not a causal proof)

The audit's `candidates` record says it starts with the group's inherited base and deletes predictions within two raster pixels of catalogue faults. Those nearby pixels may be redundant or low-credit relative to the undisclosed evaluation positives. Removing them can reduce false-positive penalty faster than it reduces recovered fault credit. This is a plausible precision-budget explanation, not evidence of a newly discovered physical mechanism. Zero-filling exterior pixels concerns file compatibility, not proof of improved science.

A distance-aware Tversky objective rewards spatial coverage and penalizes unnecessary prediction mass. The exact effect depends on the evaluator's pooled soft counts and true hidden geometry. Neither the reported organizer result nor causal attribution can be established from this audit alone. Its `instruments.catalogue_hidden_mean` is explicitly labelled leak-contaminated; its other instrument is prevalence/leaderboard calibrated. We therefore do not present those numbers as HOLDOUT-DTI or ORGANIZER-CONFIRMED.

The requested target score and listed leaderboard figures are **UNVERIFIED USER-REPORTED**, not reproduced here as measured results. Exceeding a previous result is possible in principle, but no evidence in this checkout establishes that we can do so. Repeated leaderboard adaptation is itself an overfitting risk.

## Ranked candidate hypotheses — proposals only, no method lane selected

Ranking is qualitative expected utility under scientific uncertainty, not predicted DTI. The checkout had no implemented models, so all differ from its initial state. No claim of novelty across the full parallel registry is possible. No candidate is currently viable for execution: cached bands, band metadata, shared evaluator, segment split and registry must first be restored. No new external dataset is treated as obtainable without a successful source check.

| Rank / cost | Layers and exact physical signature | Why potentially missed by catalogue | Named non-fault mimic | Difference / scope limitation |
|---|---|---|---|---|
| A / medium | GeoDAWN total-field magnetics + DEM: ridge of local phase-symmetry of the magnetic horizontal derivative, persistent across upward-continuation scales, conditioned on low DEM relief | A buried structural break beneath basin fill may lack a surface scarp | Buried volcanic dike | Tests phase/scaling under cover, not inherited catalogue-flank pruning. Broader worm/tensor lanes already exist in the supplied project list; must check full registry before adoption |
| B / medium-high | GeoDAWN K, Th and U + DEM: opposing along-slope residual gradients in log(K/Th) and log(U/Th), using valid positive measurements only | Alteration along a permeable buried conduit may persist without mapped displacement | Sediment provenance boundary | Residual transport-conditioned radiometric chemistry, not raw edge fusion. Related alteration lanes exist; distinction remains unproven |
| C / high | Gravity + magnetics: spatially coherent break in cross-spectrum phase along basin-margin transects, stable under removal of regional trend | A covered basement offset may be subtle in either field alone | Unfaulted intrusive contact | Cross-field phase discontinuity rather than amplitude conjunction; requires verified cached gravity and magnetic bands and sampling resolution |
| D / high | DEM + GeoDAWN radiometrics: repeated channel-profile convexities across adjacent catchments with consistent cross-channel radiometric residual step | Distributed young deformation may evade isolated scarp mapping | Lithologic knickpoint or lake-level terrace | Replicated cross-catchment change-point test, not isolated DEM ridges. Hydrology lanes exist; novelty needs registry inspection |

These are falsifiable physical proposals, not established geological findings or confirmed unused lanes. They require literature validation before promotion. For all four, first look for matching layers in the shared official feature cache; absent those, the official GeoDAWN data landing page above is the specific source to investigate. A new DEM would require USGS 3DEP via [The National Map](https://apps.nationalmap.gov/downloader/), also inaccessible under current network policy. No new external-data idea is declared viable.

## Preregistered test for A (blocked, not executed)

1. Confirm lane and cached physical-band identities. Exclude catalogue-distance priors from the physical surface.
2. Freeze segment-level spatial splits with buffer specified by shared evaluator. Recompute any catalogue-derived gates from visible segments only.
3. Canary every feature separately; investigate AUC above 0.90 before fusion. Record positive counts and evaluator version.
4. Full registry check on the surface before placing dots. Stop on duplicate or unavailable registry.
5. Fix one physical fusion/placement configuration before evaluation; compare pooled HOLDOUT-DTI and paired segment-bootstrap 95% CI against the frozen incumbent. Do not average fold DTI as pooled DTI.
6. Check final dots against every registry entry and serialize via shared writer; inspect the reopened TIFF. No weekly slot until separate selector approval.

Experiments executed: none. No withheld positives, CI, rank correlations, overlaps or raster checksum exist for a new candidate. Those fields are null, not zero.

## Three review passes

- **Pass 1:** inspected empty checkout, fetched upstream evidence, created truthful blocked site, format inspector and tests. No copied competition raster was published.
- **Pass 2:** tested NaN, infinity, both range violations, CRS, transform, shape, multiband and nodata rejection. Fixed dependency pins to actual installed versions. Missing evidence remains a blocker rather than a successful validation.
- **Pass 3:** checked mandate coverage; separated format validity, research promotion and slot authorization; documented missing lane/cache/evaluator, source restrictions, unverified scores, incomplete full-prompt archival and incomplete broader-repo review. New-TIFF generation remains unsatisfied and is explicitly disclosed.
