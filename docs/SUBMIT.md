# SUBMISSION PACKET — `AXIS = MASS` Variants of Parent R0 (`h33-h33-2-b2`)

- **Parent R0**: `h33-h33-2-b2` (`GEMSDOE32`, `37,654` unit-mass dots, `d_cat > 2.0 px`, `0.2778` `CLAIM` in `registry/live_scores.csv`)
  - Rebuilt bit-for-bit from `scored_h19_5` (`e27054cf`) $\to$ `dot_thin(r_min=2.8)` = `d2_8` (`44,090` dots, `0.2600` `CLAIM`) $\to$ prune `d_cat <= 2.0 px` = `37,654` dots (`digest8 = e5eb6e7e`).
  - Verified exact SHA-256: `-zeros.tif` = `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`; `-nan.tif` = `baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd`.
- **Portal encoding note**: Both `releases/<id>.tif` (`NaN` outside footprint, per problem description spec) and `releases/<id>-zeros.tif` (`0.0` outside footprint, `nodata=None`, fallback against portal `"Predicted values must be in range [0, 1]"` range check) are emitted and verified from disk.

---

## Slot 1 — `MASS = -10pct` (`33,889` dots, `10.00%` changed vs R0)

- **Name**: `h33-h33-2-b2-mass-drop10pct-20261023-2cde51f3`
- **File (NaN outside footprint, per spec)**: `releases/h33-h33-2-b2-mass-drop10pct-20261023-2cde51f3.tif`
  - `sha256`: `2cde51f32b5a22a4489044904a3fabc3dba8f41a5488bad044d6f12ac0783079`
- **File (Zeros outside footprint, fallback)**: `releases/h33-h33-2-b2-mass-drop10pct-20261023-2cde51f3-zeros.tif`
  - `sha256`: `fa0d0564258f3445ba5756f1585d5d341718196fa37b92ecb91ee66c24fe4e32`
- **Form note ($\le 140$ chars)**:
  `h33-h33-2-b2; MASS -10% (drop 3765 lowest-rank dots -> 33889); pred +0.002 to +0.005 DTI` (88 chars)
- **Format & gate receipt**:
  - `crs = EPSG:32611` | `shape = (3730, 3292)` | `dtype = float32` | `count = 1` | `transform_match = True`
  - `no_nan_in_footprint = True` (`5,167,373` active pixels) | `values_in_[0,1] = True`
  - `catalogue_mass = 0.0` (`0` pixels on `existing_faults.tif`) | `d_cat_min = 2.2361 px`, `median = 19.1050 px`, `p90 = 67.0000 px`
  - `n_dots = 33,889` (`dots_removed = 3,765`, `dots_added = 0`, `pct_changed_vs_r0 = 10.00%`, `jaccard_vs_r0 = 0.900011`)
  - `scripts/validate_submission.py` on `-zeros.tif`: `format_valid = True`
- **Mechanism card (for structural geologist)**:
  - **Hypothesis**: Removing the lowest-ranked 10% (`3,765` dots) of R0 increases live DTI because those tail dots sit on single-channel topographic/geophysical noise or already-covered fault segments where marginal truth credit $\Delta T < 0.0719\text{ px-equiv}$ (the break-even bar at $s_0 = 0.2778$).
  - **Mechanism**: Under $\text{DTI} = T / (0.2T + 0.2(S - M) + 0.8|G|)$, each unit-mass dot adds $0.2(1 - m_q(x))$ to the denominator and $(1 - 0.2s_0)\Delta T(x)$ to the numerator. Dots ranked in the bottom decile of R0 have minimum multi-channel corroboration (`corrob_count <= 1`) and weak H33 multi-physics strike consensus (`H33-A..D`), contributing excess false-positive mass $(S - M)$ without expanding the $300\text{ m}$ max-coverage envelope.
  - **Non-fault mimic**: Erosional pediment dissection scarps, alluvial-fan channel margins, and volcanic flow-lobe edges that trigger a single DEM/openness ridge channel (`h19_5`) without magnetic (RTP/TMI), gravity (isostatic HGM), MT conductivity, or 1 m LiDAR en-echelon scarplet corroboration.
  - **Predicted sign and size of live change**: Positive, `+0.0020` to `+0.0045` DTI on public test (`MODEL`).
  - **Falsifier**: A live score $< 0.2768$ (drop $\ge 0.0010$ below R0's `0.2778` `CLAIM`) falsifies the hypothesis that R0's bottom decile is net-FP-dominated and proves hidden test faults populate low-corroboration DEM ridges.

---

## Slot 2 — `MASS = +10pct` (`41,419` dots, `10.00%` changed vs R0)

- **Name**: `h33-h33-2-b2-mass-add10pct-20261023-ad925bd2`
- **File (NaN outside footprint, per spec)**: `releases/h33-h33-2-b2-mass-add10pct-20261023-ad925bd2.tif`
  - `sha256`: `ad925bd2a42f5b231fa3cb4c5e35fa28aa491602c45c8a6da09df6143494b4b5`
- **File (Zeros outside footprint, fallback)**: `releases/h33-h33-2-b2-mass-add10pct-20261023-ad925bd2-zeros.tif`
  - `sha256`: `dc3444636f8f80661f87fda61a700572a54cb60ab88ae28130f9e5b57fd13100`
- **Form note ($\le 140$ chars)**:
  `h33-h33-2-b2; MASS +10% (add 3765 top-rank dots at dcat>=3px -> 41419); pred -0.003 to +0.003` (94 chars)
- **Format & gate receipt**:
  - `crs = EPSG:32611` | `shape = (3730, 3292)` | `dtype = float32` | `count = 1` | `transform_match = True`
  - `no_nan_in_footprint = True` (`5,167,373` active pixels) | `values_in_[0,1] = True`
  - `catalogue_mass = 0.0` (`0` pixels on `existing_faults.tif`) | `d_cat_min = 2.2361 px` (`added_dots_d_cat_min = 3.0000 px`), `median = 19.2094 px`, `p90 = 67.4285 px`
  - `n_dots = 41,419` (`dots_added = 3,765`, `dots_removed = 0`, `pct_changed_vs_r0 = 10.00%`, `jaccard_vs_r0 = 0.909100`)
  - `scripts/validate_submission.py` on `-zeros.tif`: `format_valid = True`
- **Mechanism card (for structural geologist)**:
  - **Hypothesis**: Adding the next-ranked 10% (`+3,765` dots $\to$ `41,419` dots) from multi-channel corroborated ridge extensions (`h19_4 | h16_1 | tgc_v2_d15 | h19_5`) at $r_{\min} = 2.8\text{ px}$ and $d_{\text{cat}} \ge 3.0\text{ px}$ increases DTI if and only if off-catalogue fault prevalence in those secondary ridges exceeds the $7.2\%$ break-even coverage bar.
  - **Mechanism**: Selects `3,765` candidate dots outside R0's $300\text{ m}$ kernel shadow by lazy greedy maximization of exact marginal DTI gain weighted by `H33-A..D` multi-physics lineament consensus and 1 m LiDAR scarp step height, strictly $\ge 300\text{ m}$ ($3.0\text{ px}$) from all `existing_faults.tif` pixels.
  - **Non-fault mimic**: Intrabasinal playette desiccation cracks, lithologic dike swarms in TMI, and range-parallel strandline terraces that form collinear geophysical/topographic ridges $>300\text{ m}$ off mapped Quaternary faults.
  - **Predicted sign and size of live change**: Bracketing sign, `-0.0030` to `+0.0025` DTI (`MODEL`; achieves `+0.00172` on fold-clean hide-and-recover `PROXY` and `+0.01113` raw / `+0.00550` calibrated on SGMC off-catalogue `PROXY`). Paired with `MASS -10%`, brackets optimal mass $S^*$ on the R0 ranking curve in one week.
  - **Falsifier**: A live score $< 0.2735$ while `MASS -10%` scores $> 0.2785$ falsifies under-allocation and proves the R0 ridge family is already over-budgeted past $S^* \le 37,654$.

---

## Slot 3 — `MASS = -20pct` (`30,123` dots, `20.00%` changed vs R0)

- **Name**: `h33-h33-2-b2-mass-drop20pct-20261023-62bfc392`
- **File (NaN outside footprint, per spec)**: `releases/h33-h33-2-b2-mass-drop20pct-20261023-62bfc392.tif`
  - `sha256`: `62bfc392b6a1e6cbffcf0e1ac7085b6d02a8676044dae8f0df031ffd416e2e5c`
- **File (Zeros outside footprint, fallback)**: `releases/h33-h33-2-b2-mass-drop20pct-20261023-62bfc392-zeros.tif`
  - `sha256`: `53e39cd15731233b7a05ee5a89d53e439a76318453637295dc9be64a7264f929`
- **Form note ($\le 140$ chars)**:
  `h33-h33-2-b2; MASS -20% (drop 7531 lowest-rank dots -> 30123); pred +0.001 to +0.007 DTI` (88 chars)
- **Format & gate receipt**:
  - `crs = EPSG:32611` | `shape = (3730, 3292)` | `dtype = float32` | `count = 1` | `transform_match = True`
  - `no_nan_in_footprint = True` (`5,167,373` active pixels) | `values_in_[0,1] = True`
  - `catalogue_mass = 0.0` (`0` pixels on `existing_faults.tif`) | `d_cat_min = 2.2361 px`, `median = 18.6815 px`, `p90 = 65.8012 px`
  - `n_dots = 30,123` (`dots_removed = 7,531`, `dots_added = 0`, `pct_changed_vs_r0 = 20.00%`, `jaccard_vs_r0 = 0.799995`)
  - `scripts/validate_submission.py` on `-zeros.tif`: `format_valid = True`
- **Mechanism card (for structural geologist)**:
  - **Hypothesis**: Pruning the bottom 20% (`7,531` dots $\to$ `30,123` dots) of R0 tests whether true unmapped test fault prevalence $|G|$ is sparse enough ($< 10,000\text{ px}$) that aggressive denominator compression (`-1,506` units in $0.2S$) outweighs the loss of second-decile ridge coverage.
  - **Mechanism**: Retains only the top 80% (`30,123` dots) of R0 where multi-channel ridge corroboration (`h19_5 + h19_4 + h16_1 + tgc + d15 + ens12`) and `H33-A..D` strike alignment both exceed the 20th-percentile marginal DTI gain threshold.
  - **Non-fault mimic**: Secondary tributary drainage alignments and low-relief piedmont slope breaks that pass 2-channel corroboration but lack deep basement (`depth_to_base_surf` / MT conductivity) or 1 m LiDAR scarplet step support.
  - **Predicted sign and size of live change**: Positive if `MASS -10%` is positive: `+0.0010` to `+0.0065` DTI (`MODEL`). Determines curvature $d^2(\text{DTI})/dS^2$ of the live score with respect to total dot mass.
  - **Falsifier**: A live score $<$ `MASS -10%` and $< 0.2760$ falsifies aggressive pruning and bounds optimal R0 mass firmly inside $[33889, 37654]$.

---

## REPORT-ONLY Diagnostics Summary (`evidence/r0_mass_variants_20261023.json`, `PROXY` — Never Gates)

| Arm | `n_dots` | Fold-Clean Hide & Recover `PROXY` ($n=22,893$, 95% CI) | Shipped Mask Hide & Recover `PROXY` ($n=22,893$, 95% CI) | SGMC Off-Cat Raw DTI `PROXY` ($n=62,703$) | SGMC Off-Cat Coverage `PROXY` | SGMC Calibrated DTI `PROXY` |
|---|---:|---|---|---|---|---|
| **Parent R0 (`h33-h33-2-b2`)** | `37,654` | `0.10564` (`[0.09363, 0.11696]`) | `0.00389` (`[0.00332, 0.00445]`) | `0.09606` | `0.08935` | `0.06412` |
| **Slot 1 (`MASS -10%`)** | `33,889` | `0.10439` (`[0.09228, 0.11565]`) | `0.00393` (`[0.00333, 0.00448]`) | `0.09156` | `0.08402` | `0.06298` |
| **Slot 2 (`MASS +10%`)** | `41,419` | `0.10737` (`[0.09503, 0.11862]`) | `0.00372` (`[0.00318, 0.00427]`) | `0.10719` | `0.10114` | `0.06962` |
| **Slot 3 (`MASS -20%`)** | `30,123` | `0.10149` (`[0.08969, 0.11274]`) | `0.00400` (`[0.00341, 0.00456]`) | `0.08368` | `0.07571` | `0.05940` |

- **Leakage canary (`REPORT ONLY`)**: All `27` features (`01_mag_anom`..`19_det_elev_slope`, `H33-A..D`, `h33_union`, `lidar_scarp_composite`, `corrob_count`, `q_posterior`) passed on the `22,893` withheld positive pixels (`max_single_feature_auc = 0.5949 <= 0.90`).
