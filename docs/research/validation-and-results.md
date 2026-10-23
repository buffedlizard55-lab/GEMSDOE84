# Experimental Validation, Uniqueness Audit & Limitations (`H84-B` / `H84-TCDH`)

All numerical claims in this document carry explicit evidence labels per the Parallel-Run Protocol:
- **`HOLDOUT-DTI`**: Evaluated strictly via unmodified `vendor/gems57/evaluate_holdout.py` (`evaluator_version = "gems57-pooled-hide-v2"`), buffered whole-component hide-and-recover (`seeds = (20, 21)`, `hide_frac = 0.20`, `buffer_px = 3`, `n = 22,893` pooled withheld positive fault pixels), pixel-exact masking of visible catalogue faults (`alpha = 0.2, beta = 0.8`, 300 m / 3 px linear triangular kernel), and 1,000-draw 20 km (`200 px`) spatial block bootstrap 95% confidence intervals.
- **`ORGANIZER-CONFIRMED`**: Verified directly from [DrivenData Public Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [Problem Description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), and [Official DOE/NLR Prize Rules (`NREL/TP-5700-96647`)](https://docs.nlr.gov/docs/fy26osti/96647.pdf) on `2026-10-22`.
- **`OWNER-REPORTED`**: Private team submission scores from `registry/live_scores.csv` (`0.2778` for `H33-2-B2`, etc.). Never treated as organizer-verified public leaderboard entries, and **never used to fit `H84-TCDH`**.

---

## 1. Pre-Model Leakage Canary (`EXP-84B-1`, `evidence/exp84b1_ablation.json`)

Every one of the **52 features** (`36` blind geophysical/geomorphic/hydrothermal/deconfounding features + `16` visible-only fault-network anatomy features) was audited individually against buffered withheld fault components on Seeds 20 and 21 before model training:
- **Hard Stop Criterion**: Symmetric single-feature `AUC > 0.90` = leakage until proven otherwise.
- **Result**: **`PASSED`** across all 52 features (`max symmetric AUC = 0.7724` on `anat_log_d2`, Seed 20; `0.7483` Seed 21).
- **Top Blind Sensor Features (Zero Catalogue Input)**:
  1. `hydro_rad_k_bnorm` (GeoDAWN block-normalized potassium alteration): `max_sym_auc = 0.5970`
  2. `geom_lidar_scarp` (3DEP LiDAR scarp gradient): `max_sym_auc = 0.5855`
  3. `geom_scarp_clean` (Lake Lahontan `< 1,335 m` shoreline-deconfounded scarp): `max_sym_auc = 0.5837`
  4. `geom_topo10_scarp` (10 m DEM multi-scale scarp): `max_sym_auc = 0.5754`
  5. `mech_seismic_swarm` (relocated microseismic lineament density): `max_sym_auc = 0.5714`
  6. `mech_coulomb_transtens` (GPS shear/dilation aligned Coulomb reactivation): `max_sym_auc = 0.5704`

---

## 2. Three-Experiment Protocol Summary (`3 / 3` Budget Used)

### Experiment 1 — `EXP-84B-1`: Controlled Feature-Group Ablation (`evidence/exp84b1_ablation.json`)
Evaluated under identical template `emit.allocate_patient` emission (`gems57-pooled-hide-v2`, `n = 22,893` withheld positives):

| Arm | Description | Pooled `HOLDOUT-DTI` | 20 km Block-Bootstrap 95% CI | `> 25 px` Blind Kernel Recall |
|---|---|---:|---:|---:|
| `incumbent_h33_b2_recipe` | `GEMSDOE25` `d2-8` + `d_vis > 2 px` collar baseline | `0.1056` | `[0.0952, 0.1159]` | `20.8%` |
| `ctrl_phys_blind_only` | Stage A 36-feature pure physics (zero catalogue features) | `0.0673` | `[0.0563, 0.0786]` | `12.4%` |
| `ctrl_base19_anat` | Original 19-band GEMS stack + 16 visible-only anatomy features | `0.1209` | `[0.1100, 0.1328]` | `2.6%` |
| `h84b_tcdh_full` | Full 52-feature `H84-TCDH` 2-stage 4-quadrant LOQO stack | **`0.1251`** | **`[0.1140, 0.1362]`** | `4.1%` |

- Paired improvement `h84b_tcdh_full - incumbent_h33_b2_recipe`: **`+0.0195` (`HOLDOUT-DTI`, `95% CI [+0.0062, +0.0339]`)**.
- Paired improvement `h84b_tcdh_full - ctrl_base19_anat`: **`+0.0042` (`HOLDOUT-DTI`, `95% CI [+0.0018, +0.0067]`)** — proving statistically significant added value from the GeoDAWN multi-altitude tilt-worm, Coulomb transtensional, INGENIOUS hydrothermal, and Lake Lahontan deconfounding layers over the 19-band baseline.

### Experiment 2 — `EXP-84B-2`: Spatial Dot Allocation & Two-Stratum Architecture (`evidence/exp84b2_allocation.json`)
Evaluated on frozen `EXP-84B-1` out-of-fold probability arrays (`gems57-pooled-hide-v2`, `n = 22,893` withheld positives):

| Allocator Arm | Mean Dots / Seed | Pooled `HOLDOUT-DTI` | 95% Block CI | Paired `ΔDTI` vs `H33-2-B2` (`95% CI`) | Registry Gate 3B Status |
|---|---:|---:|---:|---:|---|
| `incumbent_h33_b2_recipe` | `38,899` | `0.1056` | `[0.0944, 0.1166]` | Baseline (`0.0000`) | Reference prior |
| `alloc_iso_patient` | `49,378` | `0.1251` | `[0.1143, 0.1367]` | `+0.0195` (`[+0.0062, +0.0339]`) | Dense halo packing (`1–2 px`) |
| `ctrl_b19_nms3_37k` | `37,654` | `0.1537` | `[0.1407, 0.1663]` | `+0.0480` (`[+0.0332, +0.0628]`) | Near-catalogue saturated |
| `alloc_fixed_nms3_37k` | `37,654` | `0.1612` | `[0.1486, 0.1735]` | `+0.0555` (`[+0.0420, +0.0697]`) | **REJECTED by Gate 3B (`0.8955 > 0.70`)** |
| **`alloc_twostrat_nms3_39k` (PROMOTED)** | **`39,000`** | **`0.1234`** | **`[0.1113, 0.1363]`** | **`+0.0178` (`[+0.0040, +0.0321]`)** | **`PASSED` (`0.6760 <= 0.70`, `|rho| = 0.2629`)** |

### Experiment 3 — `EXP-84B-3`: Full-Footprint LOQO Emission, 1,163-Raster Uniqueness Audit & Automated Packaging (`evidence/exp84b3_uniqueness_and_packaging.json`)
- **Unstratified Gate 3B Stop (`evidence/exp84b3_unstratified_gate3b_stop.json`)**: `alloc_fixed_nms3_37k` placed `76.6%` of dots within `d_cat <= 15 px`. While it cleared all `957` discrete `<= 100k`-dot submissions (`max overlap = 0.6958 <= 0.70`) and Gate 3A (`max |Spearman| = 0.6188 <= 0.90`), wide-collar/belief priors (`GEMSDOE3__coverage-v3-wide`, `13GEMSDOE__r6`, `GEMSDOE48`, `7GEMSDOE__halo15`) saturate `d_cat <= 15 px` with `halo_coverage = 0.402–0.676 < 0.70`, producing `0.8955 > 0.70` forward overlap. Per protocol, that unstratified candidate was halted and never packaged.
- **Two-Stratum Resolution (`alloc_twostrat_nms3_39k`)**: Splitting the `sep = 3 px` (`300 m`) discrete dot budget into **Stratum 1 (`24,500` LOQO `H84-TCDH` corridor/relay/tip-extension dots)** and **Stratum 2 (`14,500` concealed low-relief intra-basin basement/magnetic-gravity tilt/Coulomb/INGENIOUS hydrothermal dots at `d_cat > 36 px`)** — derived strictly from geophysical sensors without consulting any registry raster — passes every gate:
  - **Gate 3A (Continuous Surface across 1,163 rasters)**: `max |Spearman rho| = 0.2629 <= 0.90` (`PASSED`).
  - **Gate 3B (Post-Placement Dots across 1,163 rasters / 1,092 discriminating priors)**: `worst_forward_overlap = 0.6760 <= 0.70`, `worst |Spearman| = 0.0380 <= 0.90`, `binding_duplicate_decision = False`, `pixel_unique = True` (`PASSED`).
  - **Gate 3C (Packaging & Dual Automated Validation)**: `docs/downloads/gems84-h84b-tcdh-twostrat-39000d-20261022T235800Z-zeros.{tif,zip,json}` passes both `vendor/gems57/validate.py` and `scripts/validate_submission.py` (`EPSG:32611`, `3730 x 3292`, `float32`, `[0.0, 1.0]`, `nodata = None`, `n_nan = 0`, `n_inf = 0`, `0` catalogue pixels, `0` outside-footprint pixels).

---

## 3. Scientific Limitations & Risk Disclosures

1. **Catalogue-Incomplete Holdout vs Expert Concealed-Fault Test Labels**: Our buffered whole-component holdout (`gems57-pooled-hide-v2`) withholds mapped faults from `labels.tif`, which is naturally enriched in exposed range-front scarps relative to concealed basin-interior faults. Consequently, shifting `14,500` dots (`37.2%` of budget) into concealed low-relief basins (`d_cat > 3.6 km`) trades `0.0377` of exposed-catalogue `HOLDOUT-DTI` (`0.1612 -> 0.1234`) in exchange for genuine blind-basin discovery capacity and strict registry uniqueness (`0.6760 <= 0.70`). Whether this blind-basin allocation yields higher live DTI than corridor-only placement depends on the concealed-fault fraction in the USGS/NLR expert test labels (especially in Final Prize Round Phase 2).
2. **Non-Fault Geophysical Confounders**: Although `H84-TCDH` explicitly models and suppresses Pleistocene Lake Lahontan (`< 1,335 m`) wave-cut shorelines, road prisms (`tiger_road_distance_m.tif`), E–W GeoDAWN flight-line leveling ringing, and unbroken caldera/pluton margins (requiring multi-altitude tilt alignment + Coulomb/hydrothermal support), deeply buried Mesozoic thrust contacts or tabular Tertiary basalt dike swarms beneath quaternary valley fill can still mimic intrabasin basement fault steps.
3. **Coarse Regional Resolution of Crustal Auxiliaries**: Geodetic strain, heat flow, and regional Bouguer gravity bands inside `training_features.tif` are interpolated from sparse station spacings (`5–20 km`) onto the `100 m` evaluation grid; pinpoint localization (`<= 300 m` DTI kernel) within concealed basins relies primarily on `200–400 m` GeoDAWN aeromagnetic/radiometric gradients, `10 m` DEM drainage `χ` anomalies, relocated microseismicity, and localized INGENIOUS `2 m` temperature / sinter halos.
4. **Live Score Non-Equivalence**: `HOLDOUT-DTI` values (`0.1056` baseline, `0.1234` promoted) are measured on 20% withheld catalogue subsets per fold (`~2,860` truth pixels/fold vs `~39,000` full-grid dots) and therefore have a systematically lower numerical scale than full-grid DrivenData leaderboard scores (`0.2778` `OWNER-REPORTED`, `0.4413` `ORGANIZER-CONFIRMED`). Only paired `ΔDTI` (`+0.0178`, `95% CI [+0.0040, +0.0321]`) is scientifically interpretable; **no live leaderboard projection is made**.
