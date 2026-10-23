# Pre-Implementation Geological Hypotheses — `GEMSDOE84`

This document records the pre-implementation geological hypotheses formulated **before writing model code** for the active `GEMSDOE84` research lane (`H84-B: H84-TCDH`), together with the preserved historical record of the two earlier negative lanes in this repository (`H84-RFD` in PR #6 and `H84-A LITI` in PR #7).

Every hypothesis specifies:
1. **Exact data layers involved** (verified against SHA-256-pinned GeoDAWN, USGS 3DEP, and DOE GDR 1391 INGENIOUS stacks),
2. **Physical signature and mathematical feature transform**,
3. **Why these faults are unmapped in existing USGS Qfaults / INGENIOUS catalogues**,
4. **Primary non-fault geological confounder (false-positive mechanism)**, and
5. **Why this differs from what is already in `GEMSDOE84` and the 80+-repo GEMSDOE corpus**.

---

## Pre-Implementation Hypothesis Proposals (`H84-B` through `H84-F`)

### 1. `H84-B` (`H84-TCDH`, Selected Primary Lane): Transtensional Coulomb Slip-Dilation × Multi-Altitude Potential-Field Tilt-Worm Depth-Persistence × Hydrothermal Upflow-Conduit & Tip-Anisotropic Mechanics

- **Exact data layers involved:**
  - **19-band `training_features.tif` (GeoDAWN + INGENIOUS regional compilation):**
    - Geodetic & seismic tensor drivers: `geod_shearrate` (band 7), `geod_dilaterate` (band 8), `geod_2ndinv` (band 4), `deq_n100a15` (band 10), `ieq_n100a15` (band 16).
    - Potential-field & basement architecture: `mag_anom` (band 1), `rtp` (band 2), `tmi_hg` (band 3), `tc` (band 6), `tmi_vg` (band 9), `tmi` (band 14), `iso_grav_anom_slope` (band 5), `iso_grav_anom_vg` (band 11), `iso_grav_anom` (band 13), `iso_grav_anom_hg` (band 18), `depth_to_base_surf` (band 15), `cond_surf` (band 17), `det_elev` (band 12), `det_elev_slope` (band 19).
  - **Airborne GeoDAWN extensions & radiometrics (`DOI: 10.5066/P93LGLVQ`):**
    - `geodawn_extensions_u8.tif`: `ThK` (band 1), `UK` (band 2), `UTh` (band 3), `TMI_up150` (band 4, contractor TMI upward-continued to 150 m).
    - `geodawn_rad_u8.tif`: `K` (band 1), `Th` (band 2), `U` (band 3), `TC` (band 4), normalized per survey block via `acquisition_block_id_100m.tif` to suppress flight-block seam artifacts.
  - **Multi-resolution tectonic geomorphology & deconfounding:**
    - `lidar_scarp_features_u8.tif`: `ex_max`, `ex_mean`, `step_max`, `lapneg_max`, `lappos_max`, `downface_max`, `upface_max`, `cross_max`, `relief`, `coh100`, `strike`, `valid` (explicitly gated by `valid > 0` so partial 3DEP LiDAR coverage is separated from structural absence).
    - `topo_10m_derived_100m_u8.tif`: `slope_p90`, `slope_max`, `steep_frac`, `slope_std`, `relief_local`, `curv_prof_absmax`, `aspect_coherence`, `hs_lineament`, `dem_mean`.
    - `dem10_chi_100m_i16.tif`: `step_max_x1000`, `step_min_x1000`, `ksn_max_m0.9`, `log10_area_m2_x1000`, `zmean_m` (orthometric mean elevation for pluvial shoreline contour-tangency deconfounding).
    - `tiger_road_distance_m.tif`: road/rail/canal embankment proximity deconfounder.
  - **INGENIOUS blind hydrothermal upflow indicators (`DOI: 10.15121/1881483`):**
    - `2m_temperature_probe_INGENIOUS_regional_data.zip` (`3,800` stations: `T2m` and background-normalized `F2mDAB`, Coolbaugh et al., 2007).
    - `paleo_geothermal_regional.zip` (`709` travertine, sinter, and silicified deposits).
    - `gdr_wellspring_in_footprint.csv` (`temp_c`, `geothermquartz_c`, `geothermchalc_c`, `geothermcat_c`; **explicitly dropping `dist_known_fault_px`** to prevent label leakage).
    - `gdr_volcanic_vents_in_footprint.csv` (Quaternary volcanic dike/vent alignments; **explicitly dropping `dist_known_fault_px`**).
  - **Visible-only fault-zone structural anatomy (`vendor/gems57/`):**
    - `anatomy.py`, `relay_bend_anatomy.py`, and `damagezone_envelope.py` computed strictly from `visible_faults` on every holdout fold (`labels.tif` only at full-footprint inference).

- **Physical signature & mathematical feature transform:**
  1. **Spin-2 Structure-Tensor Strike & Optimal Transtensional Slip-Dilation Tendency:** Estimate local geophysical/geomorphic lineament strike $\theta(\mathbf{x}) \in [0, \pi)$ via the dominant eigenvector of the multi-scale spin-2 structure tensor combining `rtp`/`tmi_hg`, `iso_grav_anom_hg`, 10 m `hs_lineament`, and (where `valid > 0`) `lidar_scarp:strike`. In the Walker Lane–Northern Basin and Range transition, NW-striking dextral shear (`N35°W–N50°W`) transfers displacement into NNE–NE (`N10°E–N35°E`) normal/oblique faults (Faulds & Hinz, 2015). Compute orientation-resolved Walker Lane slip-dilation alignment ($\cos 2(\theta - \theta_{\text{opt,NNE}})$ and $\cos 2(\theta - \theta_{\text{opt,NW}})$) weighted by `geod_shearrate`, positive `geod_dilaterate`, and `geod_2ndinv` (Morris, Ferrill & Henderson, 1996).
  2. **Multi-Altitude Potential-Field "Tilt-Worm" Depth Persistence:** Shallow volcanic float, alluvial boulder fans, and E-W flight-line corrugations generate high-frequency magnetic tilt (`tc`, `tmi_vg`) at observation height that decays rapidly under upward continuation (`TMI_up150`) and lacks a coherent basement density step (`iso_grav_anom_hg`, `iso_grav_anom_vg`). Conversely, a basement-rooted fault juxtaposing Tertiary volcanics/sediments against Paleozoic/Mesozoic basement produces a phase-coherent tilt-angle zero-crossing ($\psi = \arctan(\text{VG}/(|\text{HG}|+\varepsilon))$) that persists across observation-level `rtp`/`tmi_vg`, 150 m upward-continued `TMI_up150` horizontal/Laplacian gradients, and `iso_grav_anom_hg` along the intrabasinal `depth_to_base_surf` inflection zone ($200\text{ m} < z_{\text{base}} < 2{,}200\text{ m}$).
  3. **Hydrothermal Fault-Valve Upflow & Geothermometer Disequilibrium Halo:** Blind geothermal faults maintain fracture permeability at step-overs, fault tips, and intersections (Sibson, 1990; Faulds et al., 2021). Compute multi-scale Gaussian kernel density and max-anomaly fields ($r \in \{500\text{ m}, 1.5\text{ km}, 4\text{ km}\}$) for `F2mDAB > 0` shallow temperature anomalies, paleo-geothermal sinter/travertine deposits, thermal springs, and **blind chemical geothermometer disequilibrium** ($\Delta T_{\text{geotherm}} = \max(T_{\text{quartz}}, T_{\text{chalc}}, T_{\text{cat}}) - T_{\text{surf}}$), interacted with shallow MT clay-cap conductivity gradients (`|\nabla cond_surf|`) and survey-block-normalized radiometric `K` and `UK` alteration ratios.
  4. **Deconfounded Scarp-Step × Subsurface Concordance & Anisotropic Collar Mechanics:** Separate surface scarp sharpness (`lidar_scarp` gated by `valid`, plus 10 m `slope_p90`, `curv_prof_absmax`, `step_max_x1000`) from anthropogenic embankments (`tiger_road_distance_m < 150 m`), E-W 200 m/400 m flight-line ringing ($\theta \approx 90^\circ$ magnetic-only edges), and pluvial Lake Lahontan wave-cut shorelines (`zmean_m` near highstand bands with contour-parallel gradient tangency and weak subsurface gravity/magnetic step). Couple with visible-only fault-tip relay/breach/horsetail splay potentials while distinguishing **along-strike tip extensions** (`tip_ahead > 0`, high true-positive continuation probability) from **cross-strike lateral digitizer collars** ($d_{\text{vis}} \le 2\text{ px}$ with `tip_ahead <= 0`, pure halo-redundancy trap).

- **Why unmapped in USGS Qfaults / INGENIOUS catalogues:**
  40–65% of NW Great Basin basins are blanketed by Holocene playa evaporites, eolian sand sheets, and latest Pleistocene Lake Lahontan lacustrine silts (Sehoo Highstand ~15.5 ka at ~1,338 m) that bury pre-15 ka fault scarps within intra-basin step-overs, accommodation zones, and axial grabens, while reconnaissance 1:250,000 mapping systematically truncated fault traces short of distributed horsetail tips and concealed relay ramps.

- **Primary non-fault geological confounders:**
  1. Pluvial Lake Lahontan wave-cut shorelines and barrier bars (`~1,330–1,340 m` Sehoo and `~1,390–1,405 m` Eetza highstands) mimicking linear scarps in LiDAR/10 m DEM;
  2. Shallow basaltic talus, lava-flow margins, and E-W GeoDAWN flight-line leveling corrugation creating shallow `tmi_vg` anomalies without 150 m upward-continued or gravity persistence;
  3. Playas/evaporite flats producing broad flat `cond_surf` highs and evaporite `U` enrichment without structurally aligned tilt-worm edges;
  4. Highway/railroad/canal grades (`tiger_road_distance_m`) producing sharp 2 m slope breaks.

- **Why this differs from what is already in the repo & GEMSDOE corpus:**
  - Prior `GEMSDOE84` `H84-RFD` (PR #6) used only the 19 base bands with radial isotropic log-ring deltas on a legacy chunked holdout (`0.04430`, negative) and collided with continuous registry rasters.
  - Prior `GEMSDOE84` `H84-A LITI` (PR #7) inverted 91 historical live scores into a 6-basis linear ridge without external geophysics (`0.00867`, negative, plus 56 discriminating-prior 3-px dot overlaps).
  - Across the 80+-repo corpus, `57GEMSDOE` modeled catalogue geometry + base 19 bands without INGENIOUS 2 m temperature probes, paleo-sinter/travertine, chemical geothermometer disequilibrium, `TMI_up150` multi-altitude tilt-worm persistence, or Lahontan contour-tangency deconfounding; `60GEMSDOE` tested standalone fluvial `chi` (`0.0351`); `GEMSDOE78` tested standalone 4-band GeoDAWN gravity-magnetic fusion (`0.0033`); and `GEMSDOE32` (`0.2778`) used isotropic `B=2` collar pruning on heuristic `H19-5` topographic scarps. None combined spatially cross-fitted multi-altitude potential-field persistence + transtensional Coulomb alignment + INGENIOUS hydrothermal upflow disequilibrium + anisotropic tip-vs-collar DTI kernel allocation.

---

### 2. `H84-C`: Pluvial Lake Lahontan Highstand Shoreline Contour-Tangency Deconfounder

- **Exact data layers involved:** `dem10_chi_100m_i16.tif` (`zmean_m`), `topo_10m_derived_100m_u8.tif` (`slope_p90`, `curv_prof_absmax`, `aspect_coherence`), `lidar_scarp_features_u8.tif` (`step_max`, `coh100`, `strike`, `valid`), `training_features.tif` (`iso_grav_anom_hg`, `tmi_vg`).
- **Physical signature & transform:** Wave-cut lacustrine shorelines strictly follow equipotential orthometric elevation contours ($\nabla z_{\text{mean}} \perp \hat{\mathbf{s}}_{\text{scarp}}$, zero along-scarp elevation variance $\sigma_z$ over 1–3 km windows, concentrated near Sehoo `~1,330–1,342 m` and Eetza `~1,390–1,405 m` elevations) and lack basement `iso_grav_anom_hg` steps, whereas range-front and piedmont normal faults cross-cut alluvial-fan elevation contours as fan apices rise 40–150 m between drainages.
- **Why unmapped:** Legitimate piedmont scarps below 1,400 m were reworked by wave action or misclassified as shorelines during photo-interpretation, while actual shorelines create massive false-positive clusters in pure DEM/LiDAR scarp detectors (`H19-5`).
- **Non-fault confounder:** Sub-horizontal Tertiary basalt mesa rims that also follow near-constant elevation contours.
- **Repo novelty:** No prior lane in `GEMSDOE84` or the registry computed orthometric contour-tangency × Lahontan highstand elevation gating. *Folded directly into `H84-B` as a dedicated deconfounder feature family rather than run standalone, because a pure suppressor cannot discover blind basin faults on its own.*

---

### 3. `H84-D`: Magnetotelluric Smectite Clay-Cap Lateral Edge × Survey-Normalized Radiometric `K` / `U/K` Alteration Halo

- **Exact data layers involved:** `training_features.tif` (`cond_surf`, `iso_grav_anom_hg`, `depth_to_base_surf`), `geodawn_rad_u8.tif` (`K`, `Th`, `U`), `geodawn_extensions_u8.tif` (`UK`, `ThK`), `acquisition_block_id_100m.tif`.
- **Physical signature & transform:** Hydrothermal illite-smectite clay caps form electrically conductive domes (`cond_surf`) whose **lateral gradient margins** (`|\nabla cond_surf|`), paired with block-normalized potassium metasomatism (`K`, `ThK` depletion) or travertine/silica `UK` anomalies over `iso_grav_anom_hg` steps, bound permeable feeder faults.
- **Why unmapped:** Hydrothermal clay alteration mechanically weakens host rock and obliterates brittle surface scarps, leaving feeder faults unmapped beneath altered alluvium/tuff.
- **Non-fault confounder:** Closed-basin saline playas and lithium/borate brines (high `cond_surf` + evaporitic `U` accumulation).
- **Repo novelty:** Untried in `GEMSDOE84`; prior radiometric lanes suffered flight-block leveling offsets because they omitted per-block normalization via `acquisition_block_id_100m.tif`. *Standalone DTI gain is limited by the 5–15 km smoothness of regional MT `cond_surf`, so its block-normalized edge features are integrated into `H84-B`.*

---

### 4. `H84-E`: Footwall Drainage `chi`-Discontinuity & Normalized Steepness (`ksn`) Step Across Range-Front & Relay Faults

- **Exact data layers involved:** `dem10_chi_100m_i16.tif` (`step_max_x1000`, `step_min_x1000`, `ksn_max_m0.9`, `log10_area_m2_x1000`), `topo_10m_derived_100m_u8.tif` (`relief_local`, `slope_p90`), `training_features.tif` (`iso_grav_anom_hg`).
- **Physical signature & transform:** Active normal dip-slip uplift creates transient upstream-migrating knickzones and abrupt steps in integral drainage coordinate $\chi$ (`step_max_x1000`) and channel steepness `ksn_max_m0.9` aligned across adjacent footwall catchments along a common strike.
- **Why unmapped:** Intrabasinal bedrock horsts and dissected relay ramps lack classic alluvial fault scarps when erosion paces slow (<0.2 mm/yr) slip.
- **Non-fault confounder:** Resistant welded ash-flow tuff / siliceous caprock ledges creating non-tectonic lithologic knickpoints across drainage networks.
- **Repo novelty:** `60GEMSDOE` tested standalone `chi` and obtained `HOLDOUT-DTI = 0.0351` (negative standalone due to lithologic caprock false positives and zero signal on flat playas). *Used inside `H84-B` strictly as an interaction with subsurface gravity/magnetic step persistence.*

---

### 5. `H84-F`: Microseismic Swarm Distance-Intensity Differential (`deq_n100a15` × `ieq_n100a15`) Along Geodetic Shear Gradients

- **Exact data layers involved:** `training_features.tif` (`deq_n100a15`, `ieq_n100a15`, `geod_shearrate`, `geod_2ndinv`, `rtp`, `tmi_vg`).
- **Physical signature & transform:** Unmapped Walker Lane accommodation zones and nascent dextral Riedel shears host diffuse microseismic swarms (`low deq_n100a15`, `high ieq_n100a15`) where geodetic shear rate is high, pinpointing active brittle structures only when sharpened onto 100 m `tmi_vg`/`rtp` lineaments.
- **Why unmapped:** Accommodation-zone strike-slip/oblique faults partition slip across tens of short (<3 km) discontinuous Riedel shears with <0.3 m vertical throw per event, below reconnaissance mapping thresholds.
- **Non-fault confounder:** Mining blasts, geothermal injection clusters, and off-fault aftershock clouds smeared by the regional `n=100` kernel.
- **Repo novelty:** Untried in `GEMSDOE84`, but too coarse (`100 m` evaluation requires `300 m` localization) to stand alone. *Included as a regional tectonic activity prior inside `H84-B`.*

---

## Pre-Implementation Ranking by Expected DTI Gain & Implementation Cost

| Rank | ID | Hypothesis Summary | Expected `HOLDOUT-DTI` Gain vs Incumbent Recipe (`0.1056`) | Implementation & Compute Cost | Pre-Code Decision |
|---:|---|---|---|---|---|
| **1** | **`H84-B` (`H84-TCDH`)** | Transtensional Coulomb slip-dilation × multi-altitude `TMI_up150`/`rtp`/`iso_grav` tilt-worm persistence × INGENIOUS 2 m probe / sinter / geothermometer upflow + Lahontan/road deconfounders + visible-only anisotropic tip-vs-collar anatomy | **High (`+0.03` to `+0.09` HOLDOUT-DTI over `0.1056` incumbent recipe)** — combines genuine off-collar blind-fault discovery (`>10–35 px` in basins) with high-precision tip/relay continuation while avoiding `B=2` lateral collar waste and prior-submission dot overlap | **Moderate (~25–35 min CPU total across 3 experiments)** using spatially cross-fitted HistGradientBoosting + DTI-aware expected-kernel allocation (`vendor/gems57/emit.py`) | **SELECTED (Active Lane)** |
| **2** | `H84-C` | Pluvial Lake Lahontan shoreline contour-tangency deconfounder (`zmean_m` × scarp-contour tangency) | Moderate as precision booster (`+0.005` to `+0.015`), low standalone recall | Low (~5 min) | **Folded into `H84-B` feature stack** |
| **3** | `H84-D` | MT `cond_surf` clay-cap edge × survey-block-normalized radiometric `K`, `UK`, `ThK` | Low–Moderate standalone (`cond_surf` 5–15 km resolution), strong Blind Geothermal interaction | Low (~5 min) | **Folded into `H84-B` feature stack** |
| **4** | `H84-E` | Footwall 10 m fluvial `chi` step & `ksn_max` across drainages | Negative standalone (`0.0351` in `60GEMSDOE`), positive only with potential-field filter | Low (~5 min) | **Folded into `H84-B` feature stack** |
| **5** | `H84-F` | Microseismic `deq`/`ieq` swarm differential × geodetic shear rate | Very low standalone (kilometric kernel), useful regional activity weight | Trivial (~2 min) | **Folded into `H84-B` feature stack** |

---

## Pre-Registered 3-Experiment Budget for Active Lane `H84-B` (`H84-TCDH`)

In strict compliance with the Parallel-Run Protocol (`<= 3` experiments, `< 2` hours wall-clock, shared unmodified `vendor/gems57/` evaluator/emitter/writer/uniqueness gate):

1. **`EXP-84B-1` — Single-Feature Leakage Canary Audit & Spatial-Block Cross-Fitted Ablation (`gems57-pooled-hide-v2`, `seeds=(20, 21)`, `22,893` withheld positives):**
   - Run single-feature symmetric holdout AUC on every `H84-B` feature (`hard gate: all single-feature symmetric AUCs <= 0.90`; explicitly verify zero label-derived columns from external CSVs).
   - Compare 4-quadrant spatially cross-fitted (LOQO) models under identical pooled DTI evaluation with 1,000-draw 20 km block-bootstrap 95% CIs:
     - `incumbent_h33_b2_recipe` (`0.1056` baseline),
     - `prev_h84a_liti` (`0.0087` prior lane baseline),
     - `ctrl_phys_blind_only` (pure geological/geophysical/hydrothermal stack with **zero** fault-catalogue features — directly testing genuine blind/unmapped fault recovery),
     - `ctrl_base19_plus_anatomy` (base 19 GeoDAWN bands + visible-only structural anatomy), and
     - `h84b_tcdh_full` (full `H84-TCDH` physics + hydrothermal + deconfounded scarp + anisotropic anatomy stack).
2. **`EXP-84B-2` — Post-Surface DTI Kernel-Aware Allocation vs Fixed-Separation Greedy Thinning (`vendor/gems57/emit.py`):**
   - Holding the `EXP-84B-1` out-of-fold probability surfaces fixed on `seeds=(20, 21)`, compare fixed-separation greedy dot thinning (`sep=3 px`, `37,654` dots, H33-style) against calibrated DTI-aware expected-kernel-credit marginal-bar allocation (`emit_calibrated`, accounting for the 300 m triangular kernel $k(d)=\max(1-d/300,0)$, $\alpha=0.2, \beta=0.8$, and cross-strike vs along-strike collar geometry) with paired 20 km block-bootstrap ΔDTI CIs.
3. **`EXP-84B-3` — Full-Footprint LOQO Inference, Dual-Stage 1,163-Raster Uniqueness Gate, & Automated GeoTIFF Packaging:**
   - Generate the full-footprint 4-quadrant out-of-fold surface (`visible_faults = labels.tif`).
   - **Gate 3A (Pre-Placement Surface Uniqueness):** Check `|Spearman rho| <= 0.90` on full continuous surface against all **1,163** registry rasters (`vendor/gems57/uniqueness.py`); stop immediately if exceeded.
   - Emit discrete dots via the winning `EXP-84B-2` allocator (`0` outside footprint, `0` on `existing_faults.tif`).
   - **Gate 3B (Post-Placement Dot Uniqueness):** Check `|Spearman rho| <= 0.90` across all **1,163** registry rasters AND `3-px forward dot overlap <= 0.70` across all discriminating priors (`halo_coverage < 0.70`); stop immediately if exceeded.
   - **Gate 3C (Automated Packaging & Triple Validation):** Write via `vendor/gems57/submission_writer.py`, validate via `vendor/gems57/validate.py` and `scripts/validate_submission.py` (`3730x3292`, `EPSG:32611`, `float32`, `0` NaN, `0` Inf, values strictly in `[0.0, 1.0]`, exact transform match), and record the machine-readable Run Card.

---

## Historical Archive of Earlier `GEMSDOE84` Lanes (Preserved for Audit Continuity)

- **`H84-RFD` (PR #6 — Radial Multi-Scale Potential-Field & Geomorphic Contrast, Negative):** Evaluated isotropic radial log-ring deltas on the 19 base bands using an older chunked holdout (`0.04430` vs step control `0.04436`, $\Delta = -0.00006$); halted cleanly with no submission promoted.
- **`H84-A LITI` (PR #7 — Leaderboard Information-Theoretic Inversion, Negative + Duplicate-Halted):** Fitted a 6-basis ridge regression to 91 historical live scores without physical external layers; scored `HOLDOUT-DTI = 0.00867` (`95% CI [0.00568, 0.01211]`) vs incumbent recipe `0.10564` ($\Delta = -0.09697$) and tripped 56 discriminating-prior 3-px dot overlaps (`max = 0.8586` vs `GEMSDOE48`). Halted cleanly per protocol.
