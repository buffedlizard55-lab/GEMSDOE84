# Next candidate hypotheses (2026-10-23) — NOT implemented, NOT validated

Status for every row below: **proposal only**. None has beaten the current holdout
best (`HOLDOUT-DTI 0.2255`, evaluator `gems57-pooled-hide-v2`, 22,663 withheld px,
95% CI [0.2101, 0.2404], 2026-10-22 evidence in `evidence/h84_exp2_dualseed_holdout.json`).
Per protocol, **no new TIF may be emitted and no weekly slot may be spent** from any
row until it beats that number on the same hide-and-recover holdout, with the
leakage canary (single-feature AUC ≤ 0.90) and both uniqueness gates
(rank-corr ≤ 0.90, 3-px dot overlap ≤ 0.70, surface AND final dots).
They were checked against the implemented 96-channel stack in `src/gems84/features.py`
(72 physical + 24 structural/coupling names listed there) — none is a rename of an
existing channel. Novelty across all 88 sibling repos is **not** claimed; a registry
scan is still required before adoption.

| Rank | ID | Layers (exact) | Physical signature targeted | Why it should catch a catalogue-missing fault | Differs from implemented H84-A…E | Named non-fault mimic | Cost / data |
|---|---|---|---|---|---|---|---|
| 1 | NX-5 divide-asymmetry | USGS 3DEP 10 m DEM derivatives already referenced by H84-B (`topo_10m_derived_100m_u8.tif`, `dem10_chi_*`), reprojected to the 100 m grid | **Across-divide χ / Gilbert-metric asymmetry**: systematic difference in channel-head χ and hillslope relief across a drainage divide, indicating divide migration driven by differential uplift across an active range-front fault | A fault with no preserved scarp (buried under piedmont) still perturbs base level on one side, so the divide migrates; the signal survives where scarp height = 0 | H84-B used χ-knickpoints/profile curvature *along* channels; it never computed *across-divide* asymmetry or divide-migration direction | Lithologic erodibility contrast across a contact (welded tuff vs. sediment) also migrates divides | **Low** (~1 day CPU on cached DEM derivatives). No new data. **Validate first.** Blocked today only by the absent feature cache in a clean checkout — restore via `scripts/download_competition_data.sh` + `scripts/prepare_data.py`, then run canary → holdout |
| 2 | NX-3 seismicity-alignment tensor | USGS ComCat event catalogue (free FDSN API, no key: https://earthquake.usgs.gov/fdsnws/event/1/ — ComCat docs https://earthquake.usgs.gov/data/comcat/) | **Epicentre lineament tensor + focal-mechanism T-axis consistency**: local principal axis of epicentre scatter aligned with regional extension (T-axis), depth-sliced 5–15 km | Blind faults at seismogenic depth produce aligned microseismicity before any surface rupture exists (cf. Monte Cristo 2020 unmapped-fault rupture, cited in `registry/sources.json`) | Implemented stack uses only `earthquake_density` and `distance_to_earthquake` (Bands 16/10) — scalar density, never alignment, depth-slicing, or mechanism axes | Magmatic swarm beneath a volcanic centre (alignment = dike, not range-front fault); catalogue location error in sparse-network areas | Medium (API pull is free and was verified obtainable 2026-10-23 via the official USGS pages above; moment-tensor coverage in Nevada is sparse — degrade gracefully to alignment-only) |
| 3 | NX-1 InSAR coherence/LOS break | Sentinel-1 SLC pairs via NASA ASF DAAC (free, Earthdata login: https://www.earthdata.nasa.gov/data/platforms/space-based-platforms/sentinel-1 ; on-demand InSAR https://www.earthdata.nasa.gov/learn/tutorials/explore-sentinel-1-insar-products) | **LOS velocity step / coherence-loss lineament** across a range front: interseismic creep or differential subsidence (geothermal production/injection or tectonic) localised on a structure | A creeping or fluid-driven blind fault can deform the surface without a scarp and without a thermal anomaly at 2 m depth | No SAR layer exists anywhere in the 96 channels; H84 used only passive potential fields + DEM + thermal points | Agricultural groundwater pumping subsidence bowl edge; playa desiccation cracks | **High** (SLC download + interferogram processing, GPU/time heavy; Earthdata account required — free but a credential this sandbox does not hold, so **not obtainable autonomously here today**; flagged, not proposed as immediately viable) |
| 4 | NX-2 TIR silica/thermal-inertia | ASTER / ECOSTRESS via NASA LP DAAC (free, Earthdata login: https://www.earthdata.nasa.gov/data/instruments/aster , https://www.earthdata.nasa.gov/data/instruments/ecostress/resources) | **Night-time thermal-inertia + silica emissivity index** anomaly linearised along a range front (silicified fault rock / sinter apron outcrop) | Exposed silicified fault rock has distinct emissivity/thermal inertia even where the fault is absent from USGS/INGENIOUS mapping | H84-D used airborne gamma-ray K/Th/U and magnetics; no thermal-infrared emissivity band exists in the stack | Lithologic silica signal from rhyolite flows unrelated to faulting; ECOSTRESS ISS orbit gives irregular revisit | Medium-high (free data, verified 2026-10-23; cloud/snow screening + 70–90 m native resampling needed; Earthdata login as NX-1) |
| 5 | NX-4 hydrochemistry mixing | DOE GDR #1391 well/spring chemistry beyond the geothermometer columns already used (https://gdr.openei.org/submissions/1391) | **Cl–B–Li / Na-K-Mg mixing systematics**: deep-reservoir fluid fraction mapped as a point process, interpolated only along structural grain | A blind upflow can leak a chemical signature into shallow wells with zero scarp, zero 2 m-probe anomaly (deep circulation) | H84-A used temperature + quartz/chalcedony/Na-K-Ca geothermometers + 2 m probes + sinter; it never used solute-ratio mixing fractions | Evaporative playa brine contamination mimics deep Cl/B signatures | Medium. **Obtainability unverified**: whether GDR #1391 exposes the needed solute columns in the footprint extract must be checked column-by-column (the IR-84-02 lesson: assumed column names silently produced all-zero channels in GEMSDOE83). Do not propose as viable until that check passes |

## Why H33 scored 0.2778 (owner-reported) and what would have to be true to beat it

Byte-level anatomy is in `docs/research/why-h33-scored-02778.md`: H33 is a
37,654-dot Poisson-disk (r≈2.8 px) subset pruned to `d_cat > 2 px`. Under the
official DTI (α=0.2, β=0.8, R=300 m triangular kernel — re-verified on the official
problem page https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
on 2026-10-23), dots within ~200 m of a mapped fault mostly duplicate kernel
coverage of already-known faults and pay FP penalty, so pruning them raised the
score (0.2600 → 0.2708 → 0.2778 chain, **OWNER-REPORTED** in `PROMPT.md`;
no DrivenData submission-page receipt for 0.2778 exists in this repo, see IR-84-10).
Beating it requires recovering *genuinely unmapped* fault pixels at
`d_cat > 3 px` faster than the FP cost — exactly what H84-THMS tested
(HOLDOUT-DTI 0.2255 vs fold-fair H33 rule 0.0975 on identical folds, 2026-10-22
evidence). Whether that holdout gain transfers to the private test set is
**unknown until an organizer receipt exists**; it is never written here as a score.

## Official sources used for this page (manual review)

- Competition / metric / submission format (competition **306**, fetched 2026-10-23): https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Public leaderboard (fetched 2026-10-23; #1 xiaofanhu **0.4413 ORGANIZER-CONFIRMED**): https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- GDR #1391 (INGENIOUS): https://gdr.openei.org/submissions/1391
- USGS GeoDAWN: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- Sentinel-1 / ASF DAAC, ECOSTRESS / ASTER (LP DAAC), ComCat: links in the table above.
