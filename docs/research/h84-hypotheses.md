# H84 hypotheses — ranked before implementation, validated on holdout, reported honestly

Session: `arena/4ac2f662-gemsdoe84`, 2026-10-22. Every claim below carries one of:
`OFFICIAL` (organizer page / peer-reviewed source, link given), `HOLDOUT-DTI` (computed here
on our own spatially-blocked holdout against the public catalogue), `LITERATURE`
(peer-reviewed, general mechanism — not a DOI for this specific site), or `MODEL/ESTIMATE`
(never written as a result).

## Candidates, ranked by expected DTI improvement / implementation cost, before testing

| # | hypothesis | layer(s) | physical signature | why off-catalogue | distinct from prior art? | external data | rank |
|---|---|---|---|---|---|---|---|
| H84-1 | Demagnetized conductive corridor | `rtp`, `cond_surf`, `tmi_hg` (gate only) | Local **minimum** of RTP magnetic amplitude (not a gradient/edge) conjugate with a local **maximum** of surface conductivity | Hydrothermal demagnetization + clay-cap alteration can occur over a blind fault with no mapped surface rupture | As far as verifiable from the public record: yes. The one closely-related prior-art item we found, `conj_alteration_mag` in sibling repo `15GEMSDOE` (`src/gems/fields_ext.py`), conjoins *radiometric K/Th/U ratios* with a magnetic **edge** (gradient maximum) — a different data source (radiometrics, not in our 19-band stack) and a different transform class (edge, not amplitude minimum) | none | **1** (highest expected gain / lowest cost: 3 official bands, no new data) |
| H84-3 | Conductivity–basement discordance | `cond_surf`, `depth_to_base_surf` | Local conductivity high co-located with a local basement high (shallow cover) — thin cover is not normally conductive unless a near-vertical conduit cross-cuts the horst | A fault-controlled upflow conduit through a horst need not reach the surface in a mapped way | Not found combined this way anywhere in the accessible record | none | **2** |
| H84-4 | Scarp–alteration concordance | `det_elev` (Sato ridge filter) **AND** H84-1/H84-3 | Requires BOTH a topographic break-in-slope AND the alteration-corridor signature | Raises precision (fewer, higher-confidence detections) under the metric's harsh α=0.2 FP tax, which rewards precision heavily (see metric reduction below) | The organiser's own `tc`-band zero-crossing curvature transform was tried and **falsified** in a sibling repo (GEMSDOE32, `docs/research/hypotheses-round3.md`); that used a Laplacian-style zero-crossing on `tc`/`det_elev`. We use a Sato ridge/vesselness filter on `det_elev` specifically, a different operator, and require it jointly with an independent geophysical signal rather than alone | none | **3** |
| H84-2 | Gravity-curvature saddle × seismic quiescence | `iso_grav_anom`, `iso_grav_anom_hg/vg`, `ieq_n100a15` | Saddle point in gravity curvature at the flank of a basement step, gated by low local earthquake density (interpreted as a currently-locked/aseismic-creeping segment) | — | **Low** — closely resembles "H62-2 buried-basement step × gravity, quiescence-gated" already measured in sibling repo GEMSDOE32 (`docs/research/hypotheses-round3.md`) | none | 4 — **not implemented** (insufficient novelty margin to justify a slot) |
| H84-5 | GeoDAWN radiometric K/Th/U alteration ratio, differenced from the catalogue | **not present** in `training_features.tif`'s 19 official bands at all (verified: band list read from the file's own metadata, see `registry/data_dictionary.json`) | K-enrichment (illite/sericite) + U-mobilization, a classical epithermal/geothermal alteration signature, independent of H84-1's magnetic/conductivity signal | Complementary off-catalogue alteration evidence | Would reuse a known, well-precedented radiometric-ratio technique, but on data no prior accessible session is confirmed to have combined with our specific magnetic-minimum detector | **Yes.** Official source: USGS GeoDAWN data release, DOI [10.5066/P93LGLVQ](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7) (public domain, free). Obtainability check: a byte-identical uint8-quantized mirror already exists, hash-pinned, at `buffedlizard55-lab/GEMSDOE24:data/external/geodawn_rad_u8.tif` (sha256 `c22420f75999030d…`, per that repo's own `registry/data_manifest.json`, which we did **not** independently re-verify this session — flagged here as unverified-by-us). **Deferred**, not used in this session's shipped field, to keep the submission's provenance 100% primary/official-band. | 5 — **not run this session** |

## The metric reduction that motivated H84-4's "require both" design

From the organizer's own equations (page 967), with `T = TP_w`, `F = FP_w`, `K = |G|`:

```
1/DTI = alpha + alpha*(F/T) + beta*(K/T)        alpha=0.2, beta=0.8
```

Cutting false-positive mass `F` at fixed true-positive mass `T` is the cheapest lever the
metric offers (coefficient `alpha=0.2` vs. `beta=0.8` on the recall term) — this motivated
testing a conjunctive (AND) hypothesis that trades recall for precision. **Result: still
negative** (§ below) — the conjunction scored *worse* than the disjunctive fusion, not better,
because both inputs individually carry almost no signal (leakage-canary AUC ≈0.51), so ANDing
two near-noise fields compounds, rather than cancels, their shared weakness (the basin-fill
false-positive region).

## Leakage canary (every field tested alone before trusting any holdout number)

| field | AUC vs. full visible catalogue (300k sampled negatives) | flag (>0.90)? |
|---|---|---|
| H84-1 alone | 0.5139 | No |
| H84-3 alone | 0.5107 | No |
| H84 fused (max) | 0.5167 | No |
| H84-4 (conjunction) | 0.5068 | No |
| uniform-random control | 0.5007 | No |

No leakage detected in any field. The weakness is a genuine (lack of) signal problem, not a
label-leak artifact — confirmed by the independent mechanistic diagnosis below.

## Holdout results <span>(HOLDOUT-DTI, evaluator `gems84.metric`/`gems84.holdout` v1, 6×6
spatially-checkerboarded blocks, 6 folds, 3px/300m buffer, pooled DTI with 95% CI across
folds)</span>

Full numeric trail: `evidence/h84_holdout.json`, `evidence/h84_4_holdout.json`,
`evidence/h84_fused_extended_sweep.json`.

| budget (px) | H84-1 | H84-3 | H84 fused (max) | H84-4 | uniform random |
|---|---|---|---|---|---|
| 44,090 | 0.0164 [0.0058, 0.0125]* | 0.0166 [0.0055, 0.0183]* | 0.0219 [0.0094, 0.0210]* | 0.0134 | **0.0608** [0.0355, 0.0412]* |
| 120,000 | — | — | 0.0314 | — | — |
| 150,000 | — | — | 0.0349 | — | **0.1382** |
| 1,000,000 | — | — | 0.0601 | — | **0.1536** |

*95% CI is across the 6 fold-level DTI values (not a bootstrap over pixels); n folds = 6 in
every row. CI width reflects genuine spatial block-to-block variance, which is larger than
pixel-count alone would suggest — consistent with the fault network's own spatial clustering.

**At every tested budget the uniform-random control outperforms every H84 field by 2.8×–4.3×.**

## Why — the mechanism, not just the number

1. **Not leakage.** All AUCs are 0.50–0.52.
2. **Measured directly:** `scipy.ndimage.binary_dilation(fault_mask, iterations=3) & valid`
   covers **8.16%** of the 5,164,300-px footprint. The mapped fault network is geographically
   pervasive across this part of the Basin and Range, so *any* spatially-uniform mass placement
   earns real credit purely from ubiquity.
3. **The named non-fault mimic dominated.** H84-1/H84-3's design explicitly tried to guard
   against broad, equant, undeformed basin-fill sediment producing the same joint
   low-magnetization/high-conductivity signature with zero fault control, via a Sato
   ridge/vesselness filter meant to prefer elongated corridors. The diagnostic evidence (top-K
   pixel spatial spread, percentile structure of the composite field) shows this guard was
   **insufficient**: the field's extreme tail still concentrates in specific conductive
   sub-basins rather than along the basin-margin trend the mapped fault network actually
   follows.

## Verdict

**NEGATIVE.** Per the run-card protocol, this is a deliverable, not a failure to hide. None of
H84-1/H84-3/H84-4 is promoted to a submission slot. The shipped GeoTIFF on this site is
published for audit/reproducibility/continuity only, and is clearly labelled as such
everywhere it appears (filename, README, site banner, `registry/run_card.json`).

## What would need to change to test H84-2 or H84-5 properly

- H84-2 needs a stronger novelty argument or an explicit side-by-side re-measurement against
  the sibling repo's H62-2 result using OUR holdout (not assumed from their numbers) before it
  is worth a slot.
- H84-5 needs either (a) a session with access to `sciencebase.gov` / the USGS GeoDAWN release
  directly (not available from this sandbox's allow-listed hosts), or (b) pulling the
  owner-mirrored, hash-pinned copy from `buffedlizard55-lab/GEMSDOE24` the way `training_features.tif`
  was pulled in this session (§1 of the README) — technically straightforward, deferred this
  session for provenance-cleanliness reasons stated above.
