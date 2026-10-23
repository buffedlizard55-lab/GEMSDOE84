# SUBMISSION PACKET — `AXIS = MASS` & `AXIS = SNAP` Variants of Parent R0 (`h33-h33-2-b2`)

- **Parent R0**: `h33-h33-2-b2` (`GEMSDOE32`, `37,654` unit-mass dots, `d_cat > 2.0 px`, `0.2778` `CLAIM` in `registry/live_scores.csv`)
  - Rebuilt bit-for-bit from `scored_h19_5` (`e27054cf`) $\to$ `dot_thin(r_min=2.8)` = `d2_8` (`44,090` dots, `0.2600` `CLAIM`) $\to$ prune `d_cat <= 2.0 px` = `37,654` dots (`digest8 = e5eb6e7e`).
  - Verified exact SHA-256: `-zeros.tif` = `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`; `-nan.tif` = `baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd`.
- **Portal encoding note**: Both `releases/<id>.tif` (`NaN` outside footprint, per problem description spec) and `releases/<id>-zeros.tif` (`0.0` outside footprint, `nodata=None`, fallback against portal `"Predicted values must be in range [0, 1]"` range check) are emitted and verified from disk.

---

## Slot 1 (`AXIS = MASS`) — `MASS = -10pct` (`33,889` dots, `10.00%` changed vs R0)

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

## Slot 2 (`AXIS = MASS`) — `MASS = +10pct` (`41,419` dots, `10.00%` changed vs R0)

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
  - `catalogue_mass = 0.0` (`0` pixels on `existing_faults.tif`) | `d_cat_min = 2.2361 px` (`added_dots_d_cat_min = 3.0000 px`), `median = 19.2354 px`, `p90 = 67.4759 px`
  - `n_dots = 41,419` (`dots_added = 3,765`, `dots_removed = 0`, `pct_changed_vs_r0 = 10.00%`, `jaccard_vs_r0 = 0.909100`)
  - `scripts/validate_submission.py` on `-zeros.tif`: `format_valid = True`
- **Mechanism card (for structural geologist)**:
  - **Hypothesis**: Adding the next-ranked 10% (`+3,765` dots $\to$ `41,419` dots) from multi-channel corroborated ridge extensions (`h19_4 | h16_1 | tgc_v2_d15 | h19_5`) at $r_{\min} = 2.8\text{ px}$ and $d_{\text{cat}} \ge 3.0\text{ px}$ increases DTI if and only if off-catalogue fault prevalence in those secondary ridges exceeds the $7.2\%$ break-even coverage bar.
  - **Mechanism**: Selects `3,765` candidate dots outside R0's $300\text{ m}$ kernel shadow by lazy greedy maximization of exact marginal DTI gain weighted by `H33-A..D` multi-physics lineament consensus and 1 m LiDAR scarp step height, strictly $\ge 300\text{ m}$ ($3.0\text{ px}$) from all `existing_faults.tif` pixels.
  - **Non-fault mimic**: Intrabasinal playette desiccation cracks, lithologic dike swarms in TMI, and range-parallel strandline terraces that form collinear geophysical/topographic ridges $>300\text{ m}$ off mapped Quaternary faults.
  - **Predicted sign and size of live change**: Bracketing sign, `-0.0030` to `+0.0025` DTI (`MODEL`; achieves `+0.00172` on fold-clean hide-and-recover `PROXY` and `+0.01113` raw / `+0.00550` calibrated on SGMC off-catalogue `PROXY`). Paired with `MASS -10%`, brackets optimal mass $S^*$ on the R0 ranking curve in one week.
  - **Falsifier**: A live score $< 0.2735$ while `MASS -10%` scores $> 0.2785$ falsifies under-allocation and proves the R0 ridge family is already over-budgeted past $S^* \le 37,654$.

---

## Slot 3 (`AXIS = MASS`) — `MASS = -20pct` (`30,123` dots, `20.00%` changed vs R0)

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
  - `catalogue_mass = 0.0` (`0` pixels on `existing_faults.tif`) | `d_cat_min = 2.2361 px`, `median = 18.6815 px`, `p90 = 65.7951 px`
  - `n_dots = 30,123` (`dots_removed = 7,531`, `dots_added = 0`, `pct_changed_vs_r0 = 20.00%`, `jaccard_vs_r0 = 0.799995`)
  - `scripts/validate_submission.py` on `-zeros.tif`: `format_valid = True`
- **Mechanism card (for structural geologist)**:
  - **Hypothesis**: Pruning the bottom 20% (`7,531` dots $\to$ `30,123` dots) of R0 tests whether true unmapped test fault prevalence $|G|$ is sparse enough ($< 10,000\text{ px}$) that aggressive denominator compression (`-1,506` units in $0.2S$) outweighs the loss of second-decile ridge coverage.
  - **Mechanism**: Retains only the top 80% (`30,123` dots) of R0 where multi-channel ridge corroboration (`h19_5 + h19_4 + h16_1 + tgc + d15 + ens12`) and `H33-A..D` strike alignment both exceed the 20th-percentile marginal DTI gain threshold.
  - **Non-fault mimic**: Secondary tributary drainage alignments and low-relief piedmont slope breaks that pass 2-channel corroboration but lack deep basement (`depth_to_base_surf` / MT conductivity) or 1 m LiDAR scarplet step support.
  - **Predicted sign and size of live change**: Positive if `MASS -10%` is positive: `+0.0010` to `+0.0065` DTI (`MODEL`). Determines curvature $d^2(\text{DTI})/dS^2$ of the live score with respect to total dot mass.
  - **Falsifier**: A live score $<$ `MASS -10%` and $< 0.2760$ falsifies aggressive pruning and bounds optimal R0 mass firmly inside $[33889, 37654]$.

---

## `AXIS = SNAP` Variants (Also Built in `releases/` & Logged in `ledger/submissions.csv`)

1. **`h33-2-b2-snap1p4px-g0p02-20261023-0b6a2ab2`** (`37,654` dots, `6.416%` moved, mean shift `1.383 px`):
   - `.tif` `sha256`: `535bcc04b99b119670d6398fc3801ee9ad4b7f4467c6c7c8e9f4569ebf4d4bc7`
   - `-zeros.tif` `sha256`: `24239d99cf95c06186060c192c862c822d31d5632073e0de27c0443565dd1c5e`
   - Form note: `R0 + snap 1p4px-g0p02 (2,416/37,654 dots moved, mean 1.38 px); predicted +0.004..+0.011`
2. **`h33-2-b2-snap2p0px-g0p02-20261023-b2019f55`** (`37,654` dots, `11.027%` moved, mean shift `1.910 px`):
   - `.tif` `sha256`: `2d9c6f7253b8b3502b4ca0160c71b1aa6950dfe3585f0bfcd56dc85433073811`
   - `-zeros.tif` `sha256`: `259a8d88eb3f06a557f20a24fc137f6d8b3cf66f36ffe2e4221417561b960d38`
   - Form note: `R0 + snap 2p0px-g0p02 (4,152/37,654 dots moved, mean 1.91 px); predicted +0.007..+0.018`
3. **`h33-2-b2-snap2p0px-g0p01-20261023-7bdaa58b`** (`37,654` dots, `26.467%` moved, mean shift `1.898 px`):
   - `.tif` `sha256`: `f5b5b8c9e1e1d819e7aeea04e3b4be7f4d7abc5e75fc220293e9b83df8437e05`
   - `-zeros.tif` `sha256`: `9bec3cc89934e86823a8bb8fc7aebb80552566b5e44c89206a2f9d4c7eb1b481`
   - Form note: `R0 + snap 2p0px-g0p01 (9,966/37,654 dots moved, mean 1.90 px); predicted +0.018..+0.044`

---

## REPORT-ONLY Diagnostics Summary (`evidence/r0_mass_variants_20261023.json`, `PROXY` — Never Gates)

| Arm | `n_dots` | Fold-Clean Hide & Recover `PROXY` ($n=22,893$, 95% CI) | Shipped Mask Hide & Recover `PROXY` ($n=22,893$, 95% CI) | SGMC Off-Cat Raw DTI `PROXY` ($n=62,703$) | SGMC Off-Cat Coverage `PROXY` | SGMC Calibrated DTI `PROXY` |
|---|---:|---|---|---|---|---|
| **Parent R0 (`h33-h33-2-b2`)** | `37,654` | `0.10564` (`[0.09363, 0.11696]`) | `0.00389` (`[0.00332, 0.00445]`) | `0.09606` | `0.08935` | `0.06412` |
| **Slot 1 (`MASS -10%`)** | `33,889` | `0.10439` (`[0.09228, 0.11565]`) | `0.00393` (`[0.00333, 0.00448]`) | `0.09156` | `0.08402` | `0.06298` |
| **Slot 2 (`MASS +10%`)** | `41,419` | `0.10737` (`[0.09503, 0.11862]`) | `0.00372` (`[0.00318, 0.00427]`) | `0.10719` | `0.10114` | `0.06962` |
| **Slot 3 (`MASS -20%`)** | `30,123` | `0.10149` (`[0.08969, 0.11274]`) | `0.00400` (`[0.00341, 0.00456]`) | `0.08368` | `0.07571` | `0.05940` |

- **Leakage canary (`REPORT ONLY`)**: All `27` features (`01_mag_anom`..`19_det_elev_slope`, `H33-A..D`, `h33_union`, `lidar_scarp_composite`, `corrob_count`, `q_posterior`) passed on the `22,893` withheld positive pixels (`max_single_feature_auc = 0.5949 <= 0.90`).

---

## `AXIS = PRUNE` Variants (Built 2026-10-23, Queued After MASS/SNAP — see `SLOT_PLAN.md`)

Collar geometry at fixed count `37,654` (the historical `0.2600 -> 0.2708 -> 0.2778` CLAIM ladder confounded collar with mass; these do not). Parent R0 rebuilt bit-for-bit again this session (`evidence/r0_prune_variants_20261023.json`; solo `0.2708` base verified identical to `d2_8 & d_cat>1`, `40,199` dots). Upload only one encoding per slot (`.tif` per spec, `-zeros.tif` fallback).

### 1. `dcat>=3px-refill` (submit first of the three)
- **Name**: `h33-h33-2-b2-prune-dge3refill-20261023-3745ebf6`
- **Files**: `releases/h33-h33-2-b2-prune-dge3refill-20261023-3745ebf6.tif` (`sha256`: `3745ebf6c4d5c6506bcbb4360616271de3da84f8842be17cd5e92201a329ed16`) · `-zeros.tif` (`sha256`: `c960774fe90a1df4560e5df23e0083aece4ca0bc7ace8db3d010cde03ec523c1`)
- **Form note (88 chars)**: `h33-h33-2-b2; PRUNE collar >=3px, replace 1611 diag dots refilled, 37654; pred 0..+0.003`
- **Format receipt**: `crs = EPSG:32611`, `shape = (3730, 3292)`, `dtype = float32`, `count = 1`, no NaN inside footprint, values in `[0,1]`, `catalogue_mass = 0.0`, `n_dots = 37,654` (`+1,611 / -1,611`, `8.56%` changed, `d_cat_min = 3.0000 px`, median `20.6155 px`), `scripts/validate_submission.py`: `format_valid = True`.
- **Mechanism card**: Hypothesis — R0's `1,611` dots at `224–283 m` (`sqrt5/sqrt8 px`) are the remnant of a `>2.0 px` (not `>=3 px`) prune and still spend kernel mass on the masked catalogue halo; replacing them with top-ranked ridge dots at `d_cat >= 3.0 px` gains slightly. Mimic — true en-echelon relay steps / hanging-wall splays `220–290 m` off a master fault. Predicted `0.000 to +0.003` DTI (MODEL). Falsifier — a live drop `> 0.001` vs R0 proves the `(2,3) px` ring carries real unmapped splays.

### 2. `dcat>1px-swapin` (the bracket / falsification arm)
- **Name**: `h33-h33-2-b2-prune-dgt1in-20261023-02ad0d5c`
- **Files**: `releases/h33-h33-2-b2-prune-dgt1in-20261023-02ad0d5c.tif` (`sha256`: `02ad0d5cb9836ebc868ceabbfd4a966836f98b473dc0f33004bf4f42e41936d2`) · `-zeros.tif` (`sha256`: `ffb1c3264b166bc6ae46df42db5954d605222d614438dff82d60c1c24ceb7ad0`)
- **Form note (88 chars)**: `h33-h33-2-b2; PRUNE collar >1px swap-in 2545 ring dots, count 37654; pred -0.002..-0.006`
- **Format receipt**: as above; `n_dots = 37,654` (`+2,545` ring dots at `1<d_cat<=2` / `-2,545` lowest-gain R0 dots, `13.52%` changed, `d_cat_min = 1.4142 px`, median `17.0880 px`), `format_valid = True`. Zero catalogue mass; the `>=3 px` rule is relaxed only under the Brief's AXIS=PRUNE exception.
- **Mechanism card**: Hypothesis — the `100–200 m` ring is net-negative at fixed count (organizer masks catalogue pixels exactly; neighbours score vs new-fault truth only). Mimic — the mapped trace misregistered by `100–200 m` in source linework. Predicted `-0.002 to -0.006` DTI (MODEL). Falsifier — a receipt `>= 0.2778` proves the `0.2708 -> 0.2778` step was pure mass, not collar.

### 3. `dcat>3px-refill`
- **Name**: `h33-h33-2-b2-prune-dgt3refill-20261023-10ce9ad1`
- **Files**: `releases/h33-h33-2-b2-prune-dgt3refill-20261023-10ce9ad1.tif` (`sha256`: `10ce9ad11aa5bd6b26cdcfdf6a069b0f4a80a1df971bb4981834f2a404fef7f2`) · `-zeros.tif` (`sha256`: `c05d1524d71ff12a5bca61af02b222d03f93c0afbcdab7e8a9a298eb507f110f`)
- **Form note (92 chars)**: `h33-h33-2-b2; PRUNE collar >3px, replace 2171 ring dots refilled, 37654; pred -0.001..+0.003`
- **Format receipt**: as above; `n_dots = 37,654` (`+2,171 / -2,171`, `11.53%` changed, `d_cat_min = 3.1623 px`, median `21.0238 px`), `format_valid = True`.
- **Mechanism card**: Hypothesis — tests whether ANY dot whose 300 m kernel touches a mapped trace is net-negative at fixed count (Brief PRUNE `<=3 px` point). Mimic — newly mapped strands of existing systems, explicitly in the organizer's "new fault" definition, sitting inside the vacated halo. Predicted `-0.001 to +0.003` DTI (MODEL). Falsifier — scoring `> 0.001` below `dge3refill` shows the exact-`3.0 px` ring carries truth.

### REPORT-ONLY diagnostics (`evidence/r0_prune_variants_20261023.json`, PROXY — never gates)

| Arm | `n_dots` | Fold-clean PROXY ($n=22,893$) | Paired $\Delta$ vs R0 (95% CI) | SGMC raw / cal DTI PROXY ($n=62,703$) |
|---|---:|---|---|---|
| R0 | `37,654` | `0.10564` `[0.09363, 0.11696]` | — | `0.09606` / `0.06412` |
| `dgt1in` | `37,654` | `0.10327` `[0.09132, 0.11414]` | `-0.00238` `[-0.00370, -0.00117]` | `0.09292` / `0.06200` |
| `dge3refill` | `37,654` | `0.10566` `[0.09346, 0.11685]` | `+0.00002` `[-0.00098, +0.00105]` | `0.09973` / `0.06662` |
| `dgt3refill` | `37,654` | `0.10489` `[0.09291, 0.11584]` | `-0.00075` (CI straddles 0) | `0.10074` / `0.06730` |

- Leakage canary: `27` features, `max_single_feature_auc = 0.5944 <= 0.90` (passed). Shipped-mask holdout is `0.03051` for `dgt1in` and `0.0` for the outward collars by construction (shipped masks exclude the full catalogue; only the fold-clean column is interpretable). Per the brief, a live change `< 0.01` is no evidence on its own — the ordered pattern across the three collar receipts is the measurement.
