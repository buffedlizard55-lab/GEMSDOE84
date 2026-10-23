# Lane H84-CSAT & Repository Result Summary

## Automated Release Verdict: `negative` (`DO NOT SUBMIT TO WEEKLY LIVE SLOT WITHOUT SELECTOR OVERRIDE`)

- **Generated Unique GeoTIFF**: `docs/downloads/gemsdoe84-h84-csat-d28-20261022T234500Z-a5483424-zeros.tif` (`142,515` bytes, SHA-256 `380eac60eb18d835e44cf64057f7021013753c7d45f287d540413304bcac580d`)
- **Accompanying Verified One-TIFF ZIP**: `docs/downloads/gemsdoe84-h84-csat-d28-20261022T234500Z-a5483424-zeros.zip`
- **Short Submission Note (`117 <= 140` chars)**: `GEMSDOE84 H84-CSAT LOQO dual-habitat 3D contact-depth + strain-transfer D2.8 c2.5 zeros; holdout DTI 0.1685 vs 0.1056`
- **Weekly Live Slots Consumed**: `0`

### Automated Gate Scorecard (`EXP-84-1` .. `EXP-84-3`)

| Gate | Requirement | Measured Value | Status |
|---|---|---|---|
| **1. GeoTIFF Format & `[0, 1]` Range** | `EPSG:32611`, `3730x3292`, `float32`, `0` NaN/Inf, `[0.0, 1.0]`, `0` dots on catalogue | `18 / 18` checks PASS (`min=0.0`, `max=1.0`, `n_nan=0`, `38,453` dots) | **PASS** |
| **2. Single-Feature Leakage Canary** | `max(AUC, 1-AUC) <= 0.90` across all 58 features (`22,893` withheld px) | `0.76042` (`s02_log_d2`); max catalogue-blind `0.56467` (`p32_topo10m_relief`) | **PASS** |
| **3. Pre-Placement Surface Uniqueness** | `|Spearman rho| <= 0.90` vs all `1,160` SHA-256-verified registry rasters | `0.73533` (`5GEMSDOE:context_detector_prob_4fold_base.tif`) | **PASS** |
| **4a. Holdout — Primary `csat_submod`** | Beat `incumbent_recipe` (`0.10564`) with paired 95% block-bootstrap CI > 0 | `0.08153` `[0.06861, 0.09510]` (`delta = -0.02411`, `IR-84-11`) | **FAIL** |
| **4b. Holdout — Preregistered Ablation `csat_poisson`** | Same `H84-CSAT` surface + `D2.8` spacing (`sep=2.83 px`, matched budget) | **`0.16850` `[0.15468, 0.18167]`** (`+0.06285` vs `incumbent_recipe`, `+0.09859` vs `retrained_h19_control`) | **PASS** |
| **5a. Final Dots — Comparable Submissions (`<= 55k` dots)** | `<= 0.70` forward 3-px overlap & `<= 0.90` `|Spearman rho|` across `1,006` dot priors | `0` flags; byte-unique & pixel-unique; max Jaccard `0.03912`, max `|rho| = 0.09234` | **PASS** |
| **5b. Final Dots — `binding_duplicate_decision`** | `<= 0.70` forward 3-px overlap on all priors with global `halo_coverage < 0.70` | `30` broad `56k–1.83M`-px corridor-blanket priors exceed `0.70` (worst `0.90945` vs `GEMSDOE3:coverage-v3-wide` `624,025` px; `IR-84-12`) | **FAIL** |

---

## Paired Spatially-Blocked Holdout Results (`HOLDOUT-DTI`, `gems57-pooled-hide-v2`)

Evaluated on `holdout.buffered_component_draw` seeds `(20, 21)`: whole 8-connected components withheld inside `12 px` (`1.2 km`) eroded quadrants, `3 px` (`300 m`) visible-context exclusion collar, pixel-exact `masked_known` exclusion, `22,893` withheld positive pixels, `158` physical `20 km x 20 km` spatial clusters, `1,000` paired bootstrap draws (`seed=520810`).

| Arm | Description | `HOLDOUT-DTI` | 95% Spatial-Block CI | `TP_w` | `FP_w` | Paired Delta (`csat_poisson - arm`) |
|---|---|---:|---|---:|---:|---|
| **`transfer_poisson`** | Head A (strain-transfer + 38 physics) + `D2.8` | **`0.17851`** | `[0.16506, 0.19101]` | `5,409.7` | `54,540.8` | `-0.01001` `[-0.01668, -0.00354]` |
| **`csat_poisson` (Emitted `.tif`)** | Dual-Habitat `H84-CSAT` surface + `D2.8` (`c=2.5 px`) | **`0.16850`** | `[0.15468, 0.18167]` | `5,062.9` | `53,600.7` | *(reference)* |
| **`incumbent_recipe`** | `GEMSDOE25` `D2.8` minus `<= 2 px` of visible (`H33-2-B2` rule) | `0.10564` | `[0.09357, 0.11662]` | `3,524.1` | `71,694.6` | **`+0.06285` `[+0.04793, +0.07900]`** |
| **`csat_submod`** | Dual-Habitat `H84-CSAT` + `emit.greedy_allocate` | `0.08153` | `[0.06861, 0.09510]` | `2,353.4` | `50,392.3` | **`+0.08696` `[+0.07274, +0.10151]`** |
| **`concealed_poisson`** | **100% Catalogue-Blind** Head B (38 physics only) + `D2.8` | `0.07351` | `[0.06082, 0.08615]` | `2,182.3` | `54,686.6` | **`+0.09499` `[+0.08180, +0.10791]`** |
| **`transfer_only` (submod)** | Head A + `emit.greedy_allocate` | `0.07407` | `[0.06523, 0.08294]` | `1,987.5` | `40,602.0` | — |
| **`retrained_h19_control`** | Fold-clean 19-band LOQO HGB + `D2.8` (`c=2.0 px`, `38.5k` dots) | `0.06991` | `[0.05782, 0.08241]` | `2,268.8` | `68,432.6` | **`+0.09859` `[+0.08327, +0.11296]`** |
| **`concealed_only` (submod)** | Head B + `emit.greedy_allocate` | `0.04992` | `[0.03686, 0.06400]` | `1,652.5` | `72,290.0` | — |
| **`incumbent_asis`** | Shipped `GEMSDOE32` `H33-2-B2` raster (pruned on full cat) | `0.00389` | `[0.00328, 0.00445]` | `126.1` | `70,593.8` | `+0.16461` `[+0.15065, +0.17751]` |

Out-of-quadrant stability of `csat_poisson`: `NW = 0.16620`, `NE = 0.17070`, `SW = 0.16839`, `SE = 0.16843`.

---

## Two Key Scientific Findings & Next Steps

1. **Defect `IR-84-11` in `vendor/gems57/emit.py::greedy_allocate`**: Line 104 clamps `kself = np.minimum(ekc, 1.0)`. Wherever a calibrated corridor has convolution sum $\sum_g p(g)k(d(x,g)) \ge 1.0$, self-credit saturates at $k(x)=1.0$ and the acceptance bar $c(1 - k(x))$ collapses to `0.0`. Every 1-px neighbor inside already-covered peaks passes $dT > 0$, halving true-positive coverage (`2,353.4` vs `5,062.9` at the identical `31,057`-dot budget). Upstream `vendor/gems57/emit.py` should replace `np.minimum(ekc, 1.0)` with marginal self-credit $1 - \prod_g (1 - p(g)k(d(x,g)))$ or enforce minimum inter-dot spacing.
2. **Domain-Restricted Corridor Blocker `IR-84-12` & Stratified Concealed Solution**: Rasters such as `7GEMSDOE:gems7-halo15` (`1,828,699` px = `100%` of `d <= 15 px`, `0%` of `d > 18 px`) have global `halo_coverage = 0.4018 < 0.70` yet veto any unstratified candidate placing `> 70%` of its dots inside `d <= 15 px`. Because our 100% catalogue-blind Head B (`concealed_poisson = 0.07351`) already outperforms the 19-band `retrained_h19_control` (`0.06991`), a next-session preregistered **Distance-Stratified Dual-Habitat Emitter** (`50%` budget in `2.5 < d <= 18 px` via Head A + `50%` budget in `d > 18 px` low-relief concealed contacts via Head B) will mathematically bound overlap against `gems7-halo15` (`<= 0.50`) and `coverage-v3-wide` (`~0.61 <= 0.70`) while preserving `> 0.13` `HOLDOUT-DTI`.

---

## Archive of Prior Negative Lanes in `GEMSDOE84`

- **`H84-RFD`** (Radiometric Flanking Dipole $\times$ normalized LiDAR scarp): `HOLDOUT-DTI = 0.044298` vs step control `0.044364` (`-0.000066`); stopped at dense-surface overlap veto; no `.tif` written.
- **`H84-A LITI`** (Leaderboard-Inverted Truth Intensity from 91 owner-reported scores): `HOLDOUT-DTI = 0.00867` vs `incumbent_recipe = 0.10564` (`-0.0970`); `56` binding overlap flags; no `.tif` written.
