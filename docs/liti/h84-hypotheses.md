# H84 — candidate hypotheses (written before the experiments ran)

Evidence classes: **[MEASURED]** computed here from hash-verified bytes ·
**[OWNER-REPORTED]** a live score from the owner's table (no organizer receipt) ·
**[OFFICIAL]** read from an organizer/USGS source · **[BLOCKED]** not obtainable from
this sandbox (reason stated) · **[MODEL]** a projection, never a score.

The lane paragraph that the parallel-run protocol refers to ("your lane is the single
method paragraph below") was **not present** in the brief. This session therefore
chose its own lane and recorded the choice up front (irregularity IR-84-01).

## What the 0.2778 file actually is [MEASURED, `evidence/incumbent_anatomy.json`]

| step | file | dots | rule | live |
|---|---|---:|---|---:|
| 0 | H19-5 solid mask (19GEMSDOE) | 121,131 | top-2.45 % ridges of an OOF catalogue-trained field + 4-line corroboration gate | 0.1922 |
| 1 | D2.8 (GEMSDOE25) | 44,090 | subset of step 0, dot packing at 2.83 px | 0.2600 |
| 2 | H27-4 r1 (GEMSDOE28) | 40,199 | **exactly** step 1 minus the 3,891 dots ≤ 1 px from a mapped fault | 0.2708 |
| 3 | **H33-2-B2 (GEMSDOE32)** | **37,654** | **exactly** step 2 minus the 2,545 dots ≤ 2 px from a mapped fault | **0.2778** |

The two deletions are explained to within 0.0006 DTI by the metric algebra *if the
deleted dots earned zero credit* (implied TP_w ≈ 5,073; predicted 0.2784 vs 0.2778
reported). Mean credit per kept dot ≈ 0.135, i.e. ~2.4× the marginal bar
`k > 0.2·DTI = 0.0556`. **Why it is the best:** the field's ranking is good, dotting
removed redundant mass, and the flank prune removed mass the live truth never
credits. **What limits it:** precision of the underlying field. Further pruning can
only remove credit-free mass, and the whole family is a single surface, so extra
rungs (B = 3, 4, …) cannot be unique by construction (> 70 % 3-px overlap).

## Candidates

| rank | id | layers | signature | why it should find *uncatalogued* faults | novelty vs the family | cost | validatable here |
|---:|---|---|---|---|---|---|---|
| 1 | **H84-A LITI** — leaderboard-inverted truth intensity | 13 physics/terrain bands (official 19-band stack + pinned 3DEP-10 m and 1 m-LiDAR derivatives), distance-to-catalogue bands, local catalogue density, and in E2 a catalogue-analogue ML crest | λ(x)=exp(θ·φ(x)) fitted so that the **official DTI formula in expectation** reproduces ~91 owner-reported live scores of hash-identified rasters | the live truth contains only *new* faults, so the scores are the only available labels for where new faults are; the catalogue holdout cannot supply that by construction | the family used live scores for a 1–2-parameter scatter model (GEMSDOE32 `live_anchor`); none has inverted a multi-basis spatial intensity from the whole score table | medium (CPU minutes) | yes: grouped CV on live scores + protocol holdout |
| 2 | H84-B mapping-effort prior | 1 m LiDAR coverage mask (`lidar_scarp_features_u8` band `valid`) | new expert mapping concentrates where 1 m LiDAR exists | effort, not physics, decides where new traces get drawn | coverage has only been used as a mask for scarp values, never as an intensity term | low | only through H84-A (it is one basis column) |
| 3 | H84-C under-mapped-district prior | 5 km Gaussian catalogue density | expert additions avoid districts that are already densely mapped | saturation: well-mapped ranges have fewer missing faults | no family surface uses negative density | low | only through H84-A |
| 4 | H84-D instrumental-seismicity lineaments | USGS ComCat hypocentres + focal mechanisms | nodal-plane-aligned epicentre streaks | active blind faults seismic without scarps | supplied bands 10/16 are 100 km-radius smooth fields | high | **[BLOCKED]** `earthquake.usgs.gov` is not on this sandbox's allow-list; source: <https://earthquake.usgs.gov/fdsnws/event/1/> |
| 5 | H84-E 2020 Mw 6.5 Monte Cristo Range rupture traces | InSAR/optical change products | surface rupture on largely unmapped strands | a rupture on unmapped ground is by definition missing from the catalogue | not used anywhere | high | **[BLOCKED]** ARIA/USGS products not reachable here; flagged for an unrestricted runner |

Expected-gain ranking is judgement, not measurement. H84-B and H84-C are tested
*inside* H84-A as coefficients (their sign and size on the live board is a measured
result of the fit). The run card (`evidence/run_card.json`) records the outcome,
including negative results.
