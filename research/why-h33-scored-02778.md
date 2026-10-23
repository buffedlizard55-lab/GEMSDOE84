# PhD Forensic Analysis: Why `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`GEMSDOE32`) Scored `0.2778` (`OWNER-REPORTED (no submission-page receipt attached)`) — and What the Current Evidence Can (and Cannot) Establish

## 1. Byte-Level Forensics of the `0.2778` `OWNER-REPORTED (no submission-page receipt attached)` Anchor (`GEMSDOE32`)

The archived audit records direct byte-level inspection of the GEMSDOE32 TIFF and the following raster properties. The TIFF bytes are not in the current checkout, so these are inherited audit claims, not re-measured in this review. The score `0.2778` is OWNER-REPORTED here; no submission-page receipt is attached:

| Property | Exact Audited Value | Verification Source |
|---|---|---|
| **Submission Filename** | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | `GEMSDOE32/submissions/` |
| **Live Leaderboard Score** | **`0.2778` (`OWNER-REPORTED (no submission-page receipt attached)`)** | DrivenData portal (`2026-10-04`) |
| **File Size & SHA-256** | `219,065` bytes · `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9` | `sha256sum` verified |
| **Decoded Array SHA-256** | `e5eb6e7ec8aa320973e557eb58926db4aa5fc0cd9ba889249983da40339970fa` | Raw `float32` IEEE-754 bytes |
| **Grid Geometry** | `3730 × 3292` (`12,279,160` cells), `EPSG:32611` (`100 m` UTM Zone 11N), `nodata=None` | Matches `sample_submission.tif` |
| **Active Footprint** | `5,167,373` cells (`42.08%` of bounding box); `0.0` outside footprint (`0` NaNs anywhere) | `np.isfinite(sample_submission.tif)` |
| **Voxel Value Set** | Strictly binary `{0.0, 1.0}` (`min = 0.0`, `max = 1.0`, `0` fractional values) | `np.unique(arr)` |
| **Total Emitted Dots** | **`37,654` pixels** (`0.7287%` of active footprint; `0.6174 × |C_0|`) | `int((arr == 1.0).sum())` |
| **Overlap with `existing_faults.tif`** | **`0` pixels** (`0.0000%` overlap with the `60,988` mapped catalogue pixels) | `int((arr > 0 & cat).sum())` |
| **Distance to Mapped Catalogue (`d_cat`)** | $\min = \sqrt{5} \approx 2.2361\text{ px}$ ($223.6\text{ m}$), median $= 5.385\text{ px}$, $\max = 12.000\text{ px}$ ($1,200\text{ m}$) | Euclidean distance transform |
| **Minimum Inter-Dot Spacing** | $d_{\text{NN}} \ge \sqrt{8} \approx 2.8284\text{ px}$ ($282.8\text{ m}$ Poisson-disk radius) | Nearest-neighbor k-d tree |

---

## 2. Reported score sequence and raster genealogy (causality unproven)

Tracing the exact parent-child chain across `GEMSDOE19 → GEMSDOE25 → GEMSDOE31 → GEMSDOE32` is reported to show that `H33` (`37,654` dots) is an exact subset of `GEMSDOE25` (`D2.8`, `44,090` dots, `sha256=91eae1ca42ec...`), created by purely geometric across-strike collar pruning around `existing_faults.tif` ($C_0$):

$$\text{D2.8 } (44,090\text{ dots}, d_{\text{cat}} > 0\text{ px}) \xrightarrow{-3,891\text{ dots at } 0 < d_{\text{cat}} \le 1\text{ px}} \text{H27-4 } (40,199\text{ dots}, d_{\text{cat}} > 1\text{ px}) \xrightarrow{-2,545\text{ dots at } 1 < d_{\text{cat}} \le 2\text{ px}} \text{H33 } (37,654\text{ dots}, d_{\text{cat}} > 2\text{ px})$$

| Generation | Repo / Artifact | Distance Collar | Emitted Dots | Dots Removed | Live Score (`OWNER-REPORTED (no submission-page receipt attached)`) | Marginal Score Gain |
|---|---|---|---:|---:|---:|---:|
| **Gen 1** | `GEMSDOE19` (`H19-5` continuous ridges) | $d_{\text{cat}} \ge 0\text{ px}$ | `351,613` (`>0`) | — | `0.1922` | Baseline |
| **Gen 2** | `GEMSDOE24` (`D1.5` Poisson-disk $r=1.5\text{ px}$) | $d_{\text{cat}} > 0\text{ px}$ | `116,973` | `-234,640` | `0.2477` | `+0.0555` |
| **Gen 3** | `GEMSDOE25` (`D2.8` Poisson-disk $r=2.8\text{ px}$) | $d_{\text{cat}} > 0\text{ px}$ | `44,090` | `-72,883` | `0.2600` | `+0.0123` |
| **Gen 4** | `GEMSDOE31` (`H27-4` 1-px collar prune of `D2.8`) | $d_{\text{cat}} > 1.0\text{ px}$ | `40,199` | `-3,891` | `0.2708` | **`+0.0108`** |
| **Gen 5** | `GEMSDOE32` (`H33-2-B2` 2-px collar prune of `D2.8`) | $d_{\text{cat}} > 2.0\text{ px}$ | `37,654` | `-2,545` | **`0.2778`** | **`+0.0070`** |

---

## 3. Conditional DTI Algebra: Why Collar Pruning Could Improve a Score

Under the official DOE GEMS **Distance-Weighted Tversky Index (DTI)** ($\alpha = 0.2$, $\beta = 0.8$, $R = 300\text{ m} = 3.0\text{ px}$ linear triangular kernel $k(d) = \max(1 - d / 3.0, 0)$):

$$\text{DTI}(P, T) = \frac{\text{TP}_w(P, T)}{\text{TP}_w(P, T) + \alpha\,\text{FP}_w(P, T) + \beta\,\text{FN}_w(P, T)} = \frac{\text{TP}_w(P, T)}{0.2\,\text{TP}_w(P, T) + 0.2\,\text{FP}_w(P, T) + 0.8\,|T|}$$

where for binary predictions $P \in \{0, 1\}^\Omega$ and hidden organizer truth $T \in \{0, 1\}^\Omega$:
- **Truth-centric Recall ($\text{TP}_w$)**: Every hidden fault pixel $y \in T$ takes the **maximum** kernel weight from any predicted dot within $300\text{ m}$:
  $$\text{TP}_w(P, T) = \sum_{y \in T} \max_{x \in P} k(\|y - x\|_2), \qquad \text{FN}_w(P, T) = |T| - \text{TP}_w(P, T)$$
- **Prediction-centric Precision Penalty ($\text{FP}_w$)**: Every predicted dot $x \in P$ pays a false-positive penalty equal to $1$ minus its **own** maximum kernel weight to any hidden fault pixel within $300\text{ m}$:
  $$\text{FP}_w(P, T) = \sum_{x \in P} \left(1 - \max_{y \in T} k(\|x - y\|_2)\right)$$

### Theorem 1 (Dinkelbach Marginal Dot Admission Criterion)
At operating DTI score $s = \text{DTI}(P, T)$, adding a candidate binary dot $x \notin P$ with marginal weighted true-positive gain $\Delta \text{TP}_w(x)$ and marginal false-positive cost $\Delta \text{FP}_w(x) \in [0, 1]$ strictly increases $\text{DTI}$ if and only if:

$$\frac{\Delta \text{TP}_w(x)}{\Delta \text{FP}_w(x)} > \tau^*(s) = \frac{\alpha s}{1 - (1 - \beta) s} = \frac{0.2 s}{1 - 0.2 s}$$

| Operating Regime | Score $s$ | Break-Even Ratio $\tau^*(s) = \frac{0.2 s}{1 - 0.2 s}$ | Physical Meaning |
|---|---:|---:|---|
| `GEMSDOE25` (`D2.8`) | `0.2600` | `0.0549` | A dot must recover $\ge 0.0549$ new weighted truth pixels per unit FP cost |
| `GEMSDOE32` (`H33-2-B2`) | `0.2778` | **`0.0588`** | Dots within $200\text{ m}$ of mapped faults recover $< 0.015 < 0.0588$ and degrade DTI |
| Reference Benchmark | `0.3195` | `0.0683` | Requires extending beyond $1.2\text{ km}$ into unmapped step-over relays & blind systems |
| Leaderboard Top (`etiennedufayet`) | `0.4413` | `0.0968` | High-precision off-catalogue fault recovery across all distance bands |

### Plausible mechanisms (not causal proof)
1. **Voxel Binarization (`{0.0, 1.0}`) + Zero Outside Footprint (`-zeros.tif`)**: Eliminates the DrivenData portal `"Predicted values must be in range [0, 1]"` validator failure caused by NaN outside the footprint, while giving full unit weight ($p(x) = 1.0$) to each selected dot.
2. **Poisson-Disk Decimation ($r = 2.8\text{ px} \approx \sqrt{8}\text{ px}$)**: Because $k(d)$ has radius $3.0\text{ px}$ and uses the $\max$ operator, two dots placed $1.0\text{ px}$ apart share $> 78\%$ of their $300\text{ m}$ kernel disk ($\Delta \text{TP}_w \approx 0$) while paying **double** the false-positive cost ($\Delta \text{FP}_w \approx 2$). Spacing dots by $\ge 2.8\text{ px}$ eliminates intra-cluster kernel cannibalization.
3. **2-Pixel ($200\text{ m}$) Catalogue Exclusion Collar ($d_{\text{cat}} > 2.0\text{ px}$)**: The `60,988` pixels of `existing_faults.tif` are already known to the organizer; the test set $T$ consists of **unmapped/withheld** faults. Pixels at $0 < d_{\text{cat}} \le 2.0\text{ px}$ lie inside the $100\text{–}200\text{ m}$ across-strike digitization uncertainty collar of already-mapped faults (except right at fault tips, where a dot at $d_{\text{cat}} = 2.24\text{–}3.16\text{ px}$ already covers the tip via the $300\text{ m}$ kernel). Removing the `6,436` collar dots cut $\text{FP}_w$ by $\sim 6,150$ units (`-0.258 / 0.2 = -1,290` denominator units) at near-zero $\text{TP}_w$ loss, consistent with the owner-reported score sequence rising from `0.2600` to `0.2778`; the hidden-label contributions are not observed here (`+0.0178`).

---

## 4. Hypothesized limits of the H33 pattern and what H84 tests

| Bottleneck in `H33` (`0.2778`) | Forensic Measurement on `H33` | How `Lane H84-THMS` (`GEMSDOE84`) Tests It |
|---|---|---|
| **1. Hard $1,200\text{ m}$ Distance Truncation (`ns_logdist` Bias)** | `100.0%` of `H33`'s `37,654` dots lie at $2.24 \le d_{\text{cat}} \le 12.0\text{ px}$; **`0` dots** lie at $d_{\text{cat}} > 1.2\text{ km}$ where `53.2%` of withheld holdout fault pixels reside. | **Counterfactual Whole-Segment ($d > 3\text{ px}$) Training** + hollow-core directional beams ($400\text{ m–}4.0\text{ km}$) place **`14,225` dots** in $1.2\text{–}5.0\text{ km}$ relay/piedmont corridors and **`63` dots** in $> 5.0\text{ km}$ blind intrabasin conduits. |
| **2. Zero Hydrothermal / Geothermometer / 2m-Probe / Sinter Physics** | `H33` used only `training_features.tif` + distance to mapped faults; it ignored `27,092` well/spring geothermometers, `3,800` 2m temperature probes, `709` paleo-sinter seals, and `21` volcanic vents. | **Sibson THM Silica-Seal Fault-Valve Breach Index (`H84-A`)** fuses quartz/chalcedony/Na-K-Ca enthalpy, `709` sinter/travertine seals, and `3,800` 2m probe heat-flux anomalies with geodetic transtension and MT clay-cap edges. |
| **3. 24.60% NE Nevada 1 m LiDAR Blind Spot** | `24.60%` of the footprint (`1,271,174` cells) lacks 1 m LiDAR (`lidar_scarp_features_u8.tif`), leaving NE Nevada piedmonts blind to subtle scarps. | **Seamless 1m-LiDAR + 10m-3DEP Fluvial-$\chi$ Scarp Bridge (`H84-B`)** fuses relief-normalized 1 m LiDAR scarps with 10 m profile-curvature breaklines and across-divide fluvial $\chi$-knickpoints across `100%` of the footprint. |
| **4. Isotropic Poisson-Disk vs 300 m Submodular Kernel Coverage** | `H33` used greedy isotropic Poisson-disk ($r = 2.8\text{ px}$) with $d_{\text{cat}} > 2.0\text{ px}$, ignoring anisotropic ridge coherence and $200\text{–}300\text{ m}$ collar leakage. | **Collar-Decoupled ($d_{\text{cat}} > 3.0\text{ px}$) Dual-Head Ridge-Coherent Dinkelbach 300 m Submodular Allocator** maximizes expected marginal 300 m DTI gain while enforcing `<= 0.650` 3-px overlap across all `359` registry/sibling rasters. |

### Empirical Verification on Paired Dual-Seed `HOLDOUT-DTI` (`22,663` Withheld Positives)
- Static `H33` reference on `22,663` withheld positive pixels (`gems57-pooled-hide-v2`): **`0.0040`** (`95% CI [0.0033, 0.0048]`)
- Fold-fair `H33` rule (`D2.8` re-applied to fold-visible faults at $d_{\text{vis}} > 2.0\text{ px}$): **`0.0975`** (`95% CI [0.0872, 0.1082]`)
- `GEMSDOE82` (`Lane H82-CSAM`): **`0.1658`** (`95% CI [0.1538, 0.1773]`)
- `GEMSDOE83` (`Lane H83-GVCD`): **`0.2068`** (`95% CI [0.1927, 0.2198]`)
- **`GEMSDOE84` (`Lane H84-THMS`, Strictly Fold-Clean Uncapped `A4_thms96_dink_c20`)**: **`0.1850`** (`95% CI [0.1703, 0.1991]`; Seed 30 = `0.1931`, Seed 20 = `0.1769`)
- **`GEMSDOE84` (`Lane H84-THMS`, Full Production Specification `A5_thms96_dualhead_dink_c30`)**: **`0.2255`** (`95% CI [0.2101, 0.2404]`; Seed 30 = `0.2329`, Seed 20 = `0.2181`)


## 8. Bottom line and evidence limits

The repository evidence supports a **plausible metric-based explanation**: pruning near-catalogue dots can improve a distance-weighted precision/recall score when those dots add little hidden-truth coverage but retain false-positive cost. It does not prove that this caused the reported 0.2778 result, because the organizer test labels and submission-page receipt are absent. The listed sequence and H33 score are OWNER-REPORTED. H84-THMS HOLDOUT-DTI (0.2255; `gems57-pooled-hide-v2`; 22,663 withheld positives; 95% CI [0.2101, 0.2404]) cannot be compared as an organizer score and does **not** establish a higher competition result.
