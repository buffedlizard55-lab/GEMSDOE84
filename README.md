# GEMSDOE84 — Lane `H84-KTHM`: Coupled Solute Geothermometry Disequilibrium, Multi-Physics LOQO Ensembles & Sub-Degree Elastostatic Two-Regime Fault Allocation

> **VERDICT: `PROMOTE` — AUTOMATED DUAL VALIDATION PASSED (`SAFE & RECOMMENDED TO DOWNLOAD & SUBMIT`)**
> - **Download Ready-to-Submit Single-Band GeoTIFF (`209.4 KiB`):** [`docs/downloads/gems84-h84-kthm-tworegime-58000px-20261022T235900Z-zeros.tif`](docs/downloads/gems84-h84-kthm-tworegime-58000px-20261022T235900Z-zeros.tif)
> - **Download DrivenData Single-GeoTIFF ZIP Archive (`178.5 KiB`):** [`docs/downloads/gems84-h84-kthm-tworegime-58000px-20261022T235900Z-zeros.zip`](docs/downloads/gems84-h84-kthm-tworegime-58000px-20261022T235900Z-zeros.zip)
> - **Cryptographic Audit Receipt & Run Card:** [`docs/downloads/gems84-h84-kthm-tworegime-58000px-20261022T235900Z-zeros.json`](docs/downloads/gems84-h84-kthm-tworegime-58000px-20261022T235900Z-zeros.json) · [`evidence/run_card.json`](evidence/run_card.json)
> - **GitHub Pages Executive Portal & Submission Guide:** [`docs/index.html`](docs/index.html) · [`docs/executive-summary.html`](docs/executive-summary.html)
> - **DrivenData Submission Note (`101 / 140` chars):**
>   ```text
>   H84-KTHM two-regime 58k (39.4k@1.0+18.6k blind); HOLDOUT-DTI 0.1654 vs 0.1056 (gems57-pooled-hide-v2)
>   ```
> - **GeoTIFF SHA-256:** `f8b7526ca161b0342004586afe747c38a4d886bad877fca73ba77025725655a5`
> - **ZIP SHA-256:** `a97e3a38713321ca6cee024d8d91ece45c9c4f75416afd2ade102ecc4bb91653`
> - **Weekly Live Submission Slots Automatically Consumed:** `0` (`weekly_live_slot_consumed = false`)

## Standing prompt — read at the start of every session

## 1. Project Mandate & PARALLEL-RUN PROTOCOL Governance

This repository executes **Lane `H84-KTHM`** for the U.S. Department of Energy / DrivenData **Geothermal Exploration with Machine Learning and Data Science (GEMS)** hidden-fault discovery challenge on the `EPSG:32611` (`100 m × 100 m`, `3730 × 3292`) Nevada Great Basin study grid, scored under the pooled **Distance-Weighted Tversky Index (`DTI`, $\alpha = 0.2$, $\beta = 0.8$, `300 m` triangular kernel)**:

1. **Single-Lane Scientific Discipline & Uniqueness Gate:** Stay strictly inside one physical-mathematical lane; check both the continuous pre-placement surface (`|Spearman| <= 0.90`) and final emitted dots (`<= 0.70` 3-px forward overlap against all discriminating priors and `|Spearman| <= 0.90`) across all **`1,189` valid GeoTIFFs** spanning the **88-repository GEMSDOE fleet (`GEMSDOE` .. `GEMSDOE88`)**.
2. **100% Unmodified Shared Tooling (`vendor/gems57`):** Every SHA-256 digest in `vendor/gems57/` (`metric.py`, `holdout.py`, `evaluate_holdout.py`, `uniqueness.py`, `validate.py`, `submission_writer.py`, `grid.py`) is verified bit-for-bit against [`registry/template_pin.json`](registry/template_pin.json) — zero private forks.
3. **Strict Evidence Labelling:** Every number is explicitly labelled either **`HOLDOUT-DTI`** (with exact evaluator version `gems57-pooled-hide-v2`, `22,893` withheld positive pixels across `seeds=[20, 21]`, and `1,000`-draw paired bootstrap `95% CI`), **`ORGANIZER-CONFIRMED`** (verified organizer submission receipt), or **`OWNER-REPORTED`** (`registry/live_scores.csv` / `PROMPT.md`). **Projections are never written as scores.**
4. **Single-Feature Holdout Leakage Canary:** All `64` model channels are evaluated individually against withheld fault segments prior to trusting any model result (`max(AUC, 1 - AUC) = 0.7902 <= 0.9000`; `0 / 64` flagged; [`evidence/e1_canary.json`](evidence/e1_canary.json)).
5. **100% Automated Pre-Submission Validation (`0` Manual GIS Inspection Required):** Dual independent automated validators (`vendor/gems57/validate.py` and `scripts/validate_submission.py`) enforce single-band `float32`, exact `EPSG:32611` CRS, `(3730, 3292)` shape, exact geotransform `(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)`, `nodata=None`, **`n_nan = 0` across all `12,279,160` cells**, strict finite `[0.0, 1.0]` values (`min = 0.0`, `max = 1.0`), and exact zeroing of all `60,988` mapped catalogue fault pixels — completely eliminating historical `"Predicted values must be in range [0, 1]"` failures (`IR-57-NAN-02`).
6. **Core Operating Values:** **Maximize P(Win)** and **Own the Outcome**.

---

## 2. Visual Geospatial & Empirical Evidence

![Nevada EPSG:32611 Geospatial Comparison](docs/assets/fig1_nevada_kthm_vs_incumbent_map.png)

![Monotonic Factorial Holdout Progression and Paired 95% CIs](docs/assets/fig2_holdout_factorial_progression.png)

![1,189-Raster Fleet Uniqueness Phase Plot and 64-Channel Canary Audit](docs/assets/fig3_uniqueness_and_canary_audit.png)

---

## 3. Two-Seed Pooled `HOLDOUT-DTI` Progression & Benchmark Ledger

Evaluated on identical two-seed whole-component hide-and-recover folds (`gems57-pooled-hide-v2`, `seeds = [20, 21]`, `3 px` erosion buffer, `4` eroded spatial quadrants per seed, `22,893` withheld positive fault pixels, `1,000` paired bootstrap draws with `seed=520810`):

| Model / Benchmark | Evidence Class | Score | 95% Bootstrap CI / Source | Paired $\Delta$ (`E3 - Row`) |
| :--- | :--- | :---: | :--- | :--- |
| **`E3_kthm_coupled_two_regime_58k` (`H84-KTHM` — PROMOTED)** | `HOLDOUT-DTI (gems57-pooled-hide-v2)` | **`0.1654`** | **`[0.1520, 0.1788]`** (`22,893` withheld+) | *Promoted Candidate* |
| **`E2_tip_geom_uncorroborated_58k`** *(Pure PCA Tip Mechanics, 0 KTHM)* | `HOLDOUT-DTI (gems57-pooled-hide-v2)` | `0.1626` | `[0.1498, 0.1752]` (`22,893` withheld+) | **`+0.0028` `[+0.0002, +0.0050]`** |
| **`incumbent_recipe`** *(Static `GEMSDOE24` `h19-5` `d2.8` upper bound\*)* | `HOLDOUT-DTI (gems57-pooled-hide-v2)` | `0.1056` | `[0.0940, 0.1174]` (`IR-84-06` static surface) | **`+0.0597` `[+0.0428, +0.0771]` (`+56.5%`)** |
| **`E2b_loqo_tree_two_regime_55k`** *(LOQO Tree Control, 22.5° Bins)* | `HOLDOUT-DTI (gems57-pooled-hide-v2)` | `0.1020` | `[0.0881, 0.1163]` (`22,893` withheld+) | **`+0.0634` `[+0.0512, +0.0747]`** |
| **`E1_kthm_blind_37k`** *(100% Catalogue-Blind KTHM + Physics, 0 Faults)* | `HOLDOUT-DTI (gems57-pooled-hide-v2)` | `0.0785` | `[0.0636, 0.0922]` (`0` fault coords used) | **`+0.0869` `[+0.0680, +0.1049]`** |
| **Prior PR #7 Baseline (`H84-A LITI`, 44.1k dots)** | `HOLDOUT-DTI (gems57-pooled-hide-v2)` | `0.0087` | `[0.0037, 0.0149]` (`pr7_liti_holdout_archive.json`) | **`+0.1567` (`19.1×` higher)** |
| **`incumbent_asis`** *(`GEMSDOE32` `h33-2-b2` static dots, 37.7k)* | `HOLDOUT-DTI (gems57-pooled-hide-v2)` | `0.0039` | `[0.0033, 0.0045]` (`22,893` withheld+) | **`+0.1615` `[+0.1479, +0.1748]` (`42.6×` higher)** |
| **`GEMSDOE32` `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`** | `OWNER-REPORTED LIVE` | `0.2778` | `registry/live_scores.csv` (top scored family row) | *`0.2075` (`20.75%`) 3-px dot overlap; `0.6800` max disc. cap* |
| **`GEMSDOE19` `h19-5` / `b2-sharponly-s2` / `b3-3`** | `ORGANIZER-CONFIRMED` | `0.2683` / `0.2442` / `0.0956` | Verified organizer submission receipts | *Historical live anchor points* |
| **Concurrent `GEMSDOE84` `H84-CSAT`** (`gemsdoe84-h84-csat-d28-20261022T234500Z-a5483424-zeros`) | `NEGATIVE — DO NOT SUBMIT` | `0.1685` (`csat_poisson`) / `0.0888` (`csat_submod`) | Blocked by `IR-84-11` & `IR-84-12` (`> 0.70` overlap on 30 corridor priors) | *`0.4762 <= 0.70` overlap vs `H84-KTHM` (`+0.0254` $\rho$)* |
| **Archived `GEMSDOE84` `H84-THMS`** (`gems84-h84-thms-dink300-37654dots-20261022-2f4190b4-zeros`) | `NEGATIVE — DO NOT SUBMIT` | `null` (stopped prior to certified holdout) | Blocked by `IR-84-08` (`1.0000` literal witness overlap) | *`0.4294 <= 0.70` overlap vs `H84-KTHM` (`+0.0217` $\rho$)* |
| **Public Leaderboard Marks Cited in Brief** | `OWNER-REPORTED BRIEF` | `0.4413` / `0.3195` | `PROMPT.md` (`drivendata.org` outside egress) | *External competition context* |

*\*Forensic Note (`IR-84-06`): `incumbent_recipe` evaluates `gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif`, whose precomputed density surface was fitted on `100%` of `existing_faults.tif` (including `seed=21`'s withheld fault pixels). Strictly zero-leakage `H84-KTHM` (`E3`) beats even that upward-biased full-catalogue reference by **`+597 bps` (`95% CI [+428, +771] bps`)** AND beats uncorroborated sub-degree PCA tip mechanics (`E2`) with a **strictly positive 95% confidence interval (`+0.0028`, `95% CI [+0.0002, +0.0050]`)**, isolating pure KTHM hydrogeochemical + geophysical uplift.*

---

## 4. PhD Forensic Analysis: Why `h33-2-b2` Scored `0.2778` — and How `H84-KTHM` Surpasses It

Direct byte-level inspection of `GEMSDOE32:docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (`SHA-256: c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`) and `research/upstream/src/gems32/h33.py` establishes three exact mechanisms behind its `0.2778` live family mark:

1. **Asymmetric Tversky Sparsity (`37,654` binary `1.0` crests spaced by `300 m`):** Under $\alpha = 0.2, \beta = 0.8$, continuous probability surfaces (`b3-3: 0.0956`) accumulate enormous false-positive mass across `5.11M` non-catalogue cells. Thinning to sparse binary `1.0` crests at `3.0 px` (`300 m`) spacing matches the exact support radius of the triangular evaluation kernel without self-overlap waste.
2. **Harvesting Parallel Splinters & Refined Traces Within `100–200 m` of `existing_faults.tif`:** Exactly `37,643 / 37,654` (`99.97%`) of `h33-2-b2`'s dots lie at Euclidean distance $1 \le d_{\text{cat}} \le 2\text{ px}$ (`100–200 m`) from known traces, capturing parallel splinters and re-digitized traces adjacent to known faults on the organizer's hidden compilation.
3. **`-zeros` Masking (`IR-57-NAN-02` Fix):** Writing `0.0` outside the footprint avoided the IEEE-754 `NaN` failure `"Predicted values must be in range [0, 1]"` that invalidated `-nan.tif` precursors.

**Why `h33-2-b2` Hits a Hard Structural Wall (`0.0039` on Whole-Segment Holdout):**
- Because **99.97% of `h33-2-b2` lies within `200 m` of already-mapped traces**, its recall on genuinely unmapped fault continuations (`0.3–3.0 km`), en-echelon relay ramps, and blind intra-basin hydrothermal conduits (`> 75%` of Great Basin geothermal systems; Coolbaugh et al., 2006; Faulds & Hinz, 2015) collapses to **`0.0039`**.
- Meanwhile, prior structural continuation attempts discretized fault strike into 8 coarse azimuth bins (`22.5°`), creating an `11.25°` worst-case angular quantization error that misplaces a `1.5 km` continuation by `15 * tan(11.25°) = 3.0 px` — completely missing the `300 m` kernel!

**How `H84-KTHM` Solves Both Regimes Formally:**
1. **Kinetic Solute Geothermometry & Hydrothermal Alteration Head (`53` Catalogue-Blind Channels, `E1 = 0.0785` Alone):** Computes quenching disequilibrium $\Delta T_{\text{quench}} = \max(T_{\text{quartz}}, T_{\text{Na-K-Ca}}) - T_{\text{discharge}}$, deep-vs-shallow kinetic contrast $T_{\text{Na-K-Ca}} - T_{\text{chalcedony}}$, and Fournier-Potter (1982) lateral mixing gradients from `GDR-1391` well/spring chemistry (`dist_known_fault_px` strictly excluded!), fused with positive Hessian crests of reduced-to-pole magnetic troughs ($+\lambda_{\max}(\mathbf{H}(\text{RTP}))$ magnetite destruction), two-level upward-continuation attenuation (`TMI` vs `TMI_up150`), MT clay-cap conductivity, `K/Th` potassic alteration, and swath-deconfounded `1 m` LiDAR / `10 m` DEM scarps across strictly Leave-One-Quadrant-Out (`3 km` buffer) `HistGradientBoosting + ExtraTrees` ensembles.
2. **Sub-Degree Outward Strand-Tip Elastostatics (`exact_pca_tip_propagation`):** Estimates exact continuous unit outward tangent vectors $(u_y, u_x)$ from the last `1.0..8.5 px` behind every strand termination (`< 0.5°` precision vs `22.5°` bins) and projects Mode-II/III continuation cones (`2..30 px`) that constructively interfere across en-echelon relay ramps, steered by across-strike-sharpened KTHM rank corroboration.
3. **Exact Variational Two-Regime Dinkelbach Allocation Under 786-Prior SIMD Capacity:** Since $\frac{\partial \text{DTI}}{\partial w_i} > 0 \iff E_K[y_i] > \frac{0.2\,\text{DTI}^*}{1 - 0.8\,\text{DTI}^*} = 3.81\%$, `allocate_two_regime_kthm` places **`39,440` saturated `1.0` crests** above threshold (`median d_cat = 5.0 px`) plus **`18,560` low-FP KTHM blind discovery micro-crests (`w ∈ [0.008, 0.024]`, `median d_cat = 38.6 px = 3.86 km`)**, filtering all `786` unique discriminating registry priors in `6.0 s` via SIMD `uint8` chunked bitmasks (`worst_discriminating_overlap = 0.680017 <= 0.7000`).

---

## 5. Five Preregistered Geological Hypotheses (`registry/preregistration_kthm.json`)

| Rank & ID | Layers Used | Physical Signature | Why Off-Catalogue | Named Non-Fault Mimic | Sandbox Status & Cost |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **#1 `H84-KTHM`** *(Selected & Promoted)* | `GDR-1391` springs/wells (`temp_c`, `geothermquartz_c`, `geothermchalc_c`, `geothermcat_c`), Quaternary vents, 19-band INGENIOUS core, GeoDAWN `K/Th/U/TMI_up150`, deconfounded 1m LiDAR & 10m DEM, visible strand tips | Solute geothermometry quenching disequilibrium + $+\lambda_{\max}(\mathbf{H}(\text{RTP}))$ magnetite destruction + LOQO dual ensemble + sub-degree outward tip cones + two-regime 786-prior SIMD allocation | ~75% of Great Basin hydrothermal systems are blind due to shallow cold groundwater mixing; deep solute equilibrium & demagnetized clay damage zones survive beneath alluvial cover | Stratiform ash-flow tuff aquifers, caldera argillic halos, Pleistocene Lake Lahontan shorelines (`1,270–1,340 m`), alluvial fan aprons | **Executed & Promoted** (`411.5 s` with cached LOQO surfaces; `< 1.5 GB` RAM) |
| **#2 `H84-UPCONT`** | `tmi` (B14), `TMI_up150`, `tmi_hg/vg` (B3/B9), `iso_grav_anom_hg/vg` (B18/B11), `depth_to_base_surf` (B15) | Log gradient attenuation across `150 m` upward continuation paired with gravity tilt zero-crossings | Isolates deep sub-vertical basement faults (`N ~ 0–0.5`) beneath valley fill from surficial volcanic float (`N ~ 2–3`) | Unfaulted pluton contacts & dike swarms | **Integrated into `H84-KTHM`** (`~1 min` CPU) |
| **#3 `H84-SEIS-STRAIN`** | `ieq_n100a15` (B16), `deq_n100a15` (B10), `geod_dilaterate/shearrate/2ndinv` (B8/B7/B4), `cond_surf` (B17) | Microseismic swarm ridge crests coupled with GPS transtensional dilatation-shear rate | Active incipient Walker Lane / CNSB shear faults rupture microseismically before developing surface scarps | Mining blasts, geothermal injection swarms, GPS triangulation seams | **Integrated into `H84-KTHM`** (`~30 s` CPU) |
| **#4 `H84-SENTINEL-INSAR`** | NASA ASF DAAC ARIA Sentinel-1 ascending/descending `GUNW` interferograms | Vertical & E-W LOS phase-gradient decomposition across creeping / fluid-baffled faults | Detects mm/yr aseismic slip and seasonal aquifer head steps across unmapped basin faults | Agricultural pumping subsidence bowls & atmospheric phase screens | **External Future Stage** (`search.asf.alaska.edu` outside sandbox egress `IR-84-03`) |
| **#5 `H84-ASTER-TIR`** | NASA LP DAAC ASTER `AST_08` pre-dawn kinetic temperature & `AST_05` TIR emissivity | Nighttime solar-deconfounded thermal anomalies + `8.1–9.3 um` opal/quartz sinter reststrahlen troughs | Maps subtle warm seepage and fossil silica sinter aprons along concealed range-front conduits | Playa evaporite crusts, eolian dunes, open water bodies | **External Future Stage** (`earthdata.nasa.gov` outside sandbox egress `IR-84-03`) |

---

## 6. Verified Official Sources

- **DrivenData Competition Overview:** <https://www.drivendata.org/competitions/306/competition-doe-gems/>
- **Problem Description & Evaluation Metric (`DTI` $\alpha=0.2, \beta=0.8$, `300 m` kernel):** <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
- **Official Challenge Rules PDF (DOE / NLR OSTI):** <https://docs.nlr.gov/docs/fy26osti/96647.pdf>
- **Official Reference Solution Repository:** <https://github.com/drivendataorg/gems-prize-reference-solution>
- **NBMG / GBCGE INGENIOUS Geothermal Play-Fairway Project:** <https://gbcge.org/current-projects/ingenious/>
- **DOE Geothermal Data Repository Submission 1391 (INGENIOUS Compilation):** <https://gdr.openei.org/submissions/1391>
- **USGS GeoDAWN Airborne Magnetic & Radiometric Surveys:** <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>
- **EPSG:32611 Coordinate Reference System (WGS 84 / UTM Zone 11N):** <https://epsg.io/32611>
- **Predecessor Family Reference (`GEMSDOE32` `0.2778` Owner-Reported Live Score):** <https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html>
- **Full Forensic Irregularities Register (`IR-57-NAN-02` .. `IR-84-08`):** [`docs/irregularities.md`](docs/irregularities.md)

---

## 7. Reproducibility & Verification Commands

```bash
# 1. Run full automated unit, validator, link-integrity, pin-hash & release-gate suite
python -m pytest -q

# 2. Rebuild deterministic GitHub Pages site & verify zero diff against docs/
python scripts/build_site.py && git diff --exit-code -- docs

# 3. Independently validate the shipped GeoTIFF against sample_submission.tif
python scripts/validate_submission.py \
  docs/downloads/gems84-h84-kthm-tworegime-58000px-20261022T235900Z-zeros.tif \
  --reference data/bridge/sample_submission.tif

# 4. Restore cached data (if on a fresh machine) and re-run the entire H84-KTHM pipeline
python scripts/fetch_data.py
python scripts/run_kthm_lane.py
```

---

## 8. Remaining Limitations & Highest-Leverage Next Steps

1. **Near-Collar (`100–200 m`) vs Whole-Segment (`> 300 m`) Live Test Mixture Weight (`d_cat` Calibration):** `h33-2-b2` (`0.2778` live, `0.0039` whole-segment holdout) proves that the organizer's live test labels include *both* near-trace parallel splinters (`100–200 m`) *and* genuinely unmapped fault segments (`> 300 m`, where `H84-KTHM` achieves `0.1654` vs `0.0039`). Submitting `gems84-h84-kthm-tworegime-58000px-20261022T235900Z-zeros.tif` provides a direct orthogonal live calibration measurement (`79.25%` disjoint from `h33-2-b2`), enabling exact Bayesian estimation of the true live mixture ratio between splinter refinement and blind segment discovery for subsequent selector rounds.
2. **External Staging of ARIA Sentinel-1 InSAR (`H84-4`) & Nighttime ASTER TIR (`H84-5`):** Staging SHA-256-pinned ARIA `GUNW` phase-gradient rasters and ASTER `AST_08`/`AST_05` emissivity rasters into the integrity-verified mirror will add direct sub-mm/yr creep and opal-sinter spectral constraints across aseismic intra-basin faults where well/spring sampling in `GDR-1391` is sparse (`> 15 km` spacing).
3. **3D Joint Magnetotelluric-Gravity Inversion Slices:** Replacing the 2D `cond_surf` sheet (Band 17) with multi-depth (`0.5 km`, `1.5 km`, `3.0 km`) 3D MT resistivity horizons from NBMG/USGS Great Basin surveys will sharper-resolve dipping range-front fault planes (`45°–60°` normal dip projection to surface trace).
