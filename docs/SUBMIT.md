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

---

## `AXIS = PRUNE` (collar sweep) — `d2p5` / `d3p0` / `d4p0`, count held at `37,654`

Second, independent PRUNE implementation (`scripts/build_prune_collar_sweep.py`, receipt `evidence/prune_variants_receipt.json`). The packet above documents `dgt1in` / `dge3refill` / `dgt3refill` from `scripts/build_prune_variants.py`; **`pruned3p0` and `prune-dgt3refill` remove the same 2,171 dots and differ only in the refill floor — submit at most one** (`IR-DEC-12`).

- **Design**: identical to the packet above except the setting — collar `2.5 / 3.0 / 4.0 px`, 1:1 refill from the parent's own ranked pool (`dot_thin(h19_5|h19_4|h16_1|tgc, 2.8) & ~R0 & d_cat >= 3.0`, `19,243` candidates, spaced `>= 2.8 px` from the pruned mask).
- **Brief values not buildable**: `<= 1 px` and `<= 2 px` remove 0 dots from R0 (R0 already excludes `d_cat <= 2 px`); the inward direction is covered by `dgt1in` in the packet above.

### `h33-2-b2-pruned2p5-20261023-45faee56` — collar `2.5 px`
- **File (NaN outside footprint)**: `releases/h33-2-b2-pruned2p5-20261023-45faee56.tif` — `sha256 45faee562e55c0b48d123ebbdf553f17ecfaf24cdd5592c27437c0d316ecb3c8`
- **File (zeros outside footprint, fallback)**: `releases/h33-2-b2-pruned2p5-20261023-45faee56-zeros.tif` — `sha256 d484d54d200126fefbe37868993b4019d836f9bf9afd72bc2faab8cccca614ca`
- **Form note (85 chars)**: `h33-2-b2; PRUNE collar 2.5px (941 dots out, 941 refill at dcat>=3px); pred +0.001 DTI`
- **Gates (re-read from disk)**: `EPSG:32611` · `(3730, 3292)` · `float32` · 1 band · exact transform · no NaN in footprint · values in `[0,1]` · `catalogue_mass = 0.0` · `n_dots = 37654` · `scripts/validate_submission.py` `format_valid = true` on `-zeros.tif` (the spec `.tif` fails only `finite_all`/`range_all`, the NaN-outside conflict of `IR-DEC-06`).
- **Parent-diff**: 941 collar dots out (max `d_cat` 2.2361 px), 941 refill dots in (min `d_cat` 3.0 px, median 13.3417 px), `pct_changed = 5.0%`, `jaccard = 0.951237`.
- **Prediction (MODEL)**: MODEL +0.0000..+0.0020 DTI (lineage-anchored +0.0010 central, refill assumed neutral); ranking arithmetic favors negative.
  - Ranking arithmetic (ranking units, **not** DTI — `IR-DEC-11`): refill gain sum `1448.946` vs collar gain lost `1654.185` → favours the **negative** direction. It is blind to the fact that catalogue pixels are masked out of the labels, and it prices collar dots with a posterior that cannot know this.
- **Mechanism card**:
  - **Hypothesis**: Cutting the collar from 2.0 to 2.5 px removes only the 941 R0 dots in the innermost diagonal shell (d_cat in (2.0, 2.5]); at that distance a dot's 3 px triangular kernel is >83% dominated by masked catalogue pixels, so those dots should pay false-positive mass with little collectable credit. Refilling them from the off-catalogue ridge pool should be weakly positive.
  - **Mechanism**: Under DTI = T / (0.2T + 0.2(S-M) + 0.8|G|) each unit-mass dot adds 0.2(1 - m_q) to the denominator and (1 - 0.2s)dT to the numerator. Known USGS/INGENIOUS pixels are masked pixel-exactly out of the label set, so a dot inside the 3 px (300 m) kernel footprint of a masked catalogue pixel can only collect credit from *new-fault* truth. Collar dots are swapped 1:1 for the highest exact-marginal-gain off-catalogue ridge dots (d_cat >= 3.0 px, r_min = 2.8 px) from the parent's own ranked pool, so total mass and mean spacing are held and only collar geometry changes.
  - **Non-fault mimic**: Alluvial-fan head-cut scarps, pediment slope breaks and playa margins that parallel mapped range-front faults at 200-400 m; these mimic an unmapped splay and would make collar dots productive rather than wasteful.
  - **Predicted sign and size**: MODEL +0.0000..+0.0020 DTI (central +0.0010 from 1.088e-6 DTI per removed collar dot x 941 dots, refill assumed neutral). Note the disagreement: the parent's own masking-blind ranking arithmetic prices the collar dots higher than the refill pool (negative), yet the lineage's one measured collar prune (0.2708 -> 0.2778 CLAIM) moved the other way, which is exactly why this axis is worth a slot. Live changes under 0.010 count as no evidence (public chunks only).
  - **Falsifier**: A live score below 0.2768 (>= 0.0010 under R0's 0.2778 CLAIM) falsifies the claim that the innermost diagonal shell is net false-positive dominated.

### `h33-2-b2-pruned3p0-20261023-26e80847` — collar `3 px`
- **File (NaN outside footprint)**: `releases/h33-2-b2-pruned3p0-20261023-26e80847.tif` — `sha256 26e808472dd6a35eed7ab42762ebada2c7236370e2ca7dc42b4393cdbcd1d9c8`
- **File (zeros outside footprint, fallback)**: `releases/h33-2-b2-pruned3p0-20261023-26e80847-zeros.tif` — `sha256 5a8161562a07dd04fcb87972e23623ce3850cb9571d52f5486c50988e0f4b80d`
- **Form note (85 chars)**: `h33-2-b2; PRUNE collar 3px (2171 dots out, 2171 refill at dcat>=3px); pred +0.002 DTI`
- **Gates (re-read from disk)**: `EPSG:32611` · `(3730, 3292)` · `float32` · 1 band · exact transform · no NaN in footprint · values in `[0,1]` · `catalogue_mass = 0.0` · `n_dots = 37654` · `scripts/validate_submission.py` `format_valid = true` on `-zeros.tif` (the spec `.tif` fails only `finite_all`/`range_all`, the NaN-outside conflict of `IR-DEC-06`).
- **Parent-diff**: 2171 collar dots out (max `d_cat` 3.0 px), 2171 refill dots in (min `d_cat` 3.0 px, median 13.9284 px), `pct_changed = 11.53%`, `jaccard = 0.890973`.
- **Prediction (MODEL)**: MODEL +0.0000..+0.0047 DTI (lineage-anchored +0.0024 central, refill assumed neutral); ranking arithmetic favors negative.
  - Ranking arithmetic (ranking units, **not** DTI — `IR-DEC-11`): refill gain sum `3063.705` vs collar gain lost `3764.559` → favours the **negative** direction. It is blind to the fact that catalogue pixels are masked out of the labels, and it prices collar dots with a posterior that cannot know this.
- **Mechanism card**:
  - **Hypothesis**: Removing every R0 dot within one full kernel radius (300 m) of masked catalogue pixels (2,171 dots, 5.77% of R0) and refilling at matched count with off-catalogue corroborated ridge dots removes mass that can earn almost no credit, because the catalogue pixels underneath are masked out of the label set.
  - **Mechanism**: Under DTI = T / (0.2T + 0.2(S-M) + 0.8|G|) each unit-mass dot adds 0.2(1 - m_q) to the denominator and (1 - 0.2s)dT to the numerator. Known USGS/INGENIOUS pixels are masked pixel-exactly out of the label set, so a dot inside the 3 px (300 m) kernel footprint of a masked catalogue pixel can only collect credit from *new-fault* truth. Collar dots are swapped 1:1 for the highest exact-marginal-gain off-catalogue ridge dots (d_cat >= 3.0 px, r_min = 2.8 px) from the parent's own ranked pool, so total mass and mean spacing are held and only collar geometry changes.
  - **Non-fault mimic**: Alluvial-fan head-cut scarps, pediment slope breaks and playa margins that parallel mapped range-front faults at 200-400 m; these mimic an unmapped splay and would make collar dots productive rather than wasteful.
  - **Predicted sign and size**: MODEL +0.0000..+0.0047 DTI (central +0.0024 from 1.088e-6 DTI per removed collar dot x 2171 dots, refill assumed neutral). Note the disagreement: the parent's own masking-blind ranking arithmetic prices the collar dots higher than the refill pool (negative), yet the lineage's one measured collar prune (0.2708 -> 0.2778 CLAIM) moved the other way, which is exactly why this axis is worth a slot. Live changes under 0.010 count as no evidence (public chunks only).
  - **Falsifier**: A live score below 0.2768 falsifies the collar-false-positive hypothesis and would show that unmapped new-fault truth sits inside 300 m of the known traces (as the organizer allowed), making the collar a productive band.

### `h33-2-b2-pruned4p0-20261023-ff079f66` — collar `4 px`
- **File (NaN outside footprint)**: `releases/h33-2-b2-pruned4p0-20261023-ff079f66.tif` — `sha256 ff079f66304afebb07e6ce0167fa848ebd1920020ce4f96421bb36a489d9a730`
- **File (zeros outside footprint, fallback)**: `releases/h33-2-b2-pruned4p0-20261023-ff079f66-zeros.tif` — `sha256 37be4a3f4bd5d020487f47bed65c08ad665223542f771e5f57b9b90a3ff41c56`
- **Form note (85 chars)**: `h33-2-b2; PRUNE collar 4px (3825 dots out, 3825 refill at dcat>=3px); pred +0.004 DTI`
- **Gates (re-read from disk)**: `EPSG:32611` · `(3730, 3292)` · `float32` · 1 band · exact transform · no NaN in footprint · values in `[0,1]` · `catalogue_mass = 0.0` · `n_dots = 37654` · `scripts/validate_submission.py` `format_valid = true` on `-zeros.tif` (the spec `.tif` fails only `finite_all`/`range_all`, the NaN-outside conflict of `IR-DEC-06`).
- **Parent-diff**: 3825 collar dots out (max `d_cat` 4.0 px), 3825 refill dots in (min `d_cat` 3.0 px, median 12.2066 px), `pct_changed = 20.32%`, `jaccard = 0.815569`.
- **Prediction (MODEL)**: MODEL +0.0000..+0.0083 DTI (lineage-anchored +0.0042 central, refill assumed neutral); ranking arithmetic favors negative.
  - Ranking arithmetic (ranking units, **not** DTI — `IR-DEC-11`): refill gain sum `5103.21` vs collar gain lost `6392.286` → favours the **negative** direction. It is blind to the fact that catalogue pixels are masked out of the labels, and it prices collar dots with a posterior that cannot know this.
- **Mechanism card**:
  - **Hypothesis**: If the collar penalty is monotone, a 4 px exclusion (3,825 dots, 10.16% of R0) should beat the 3 px variant. Along-strike continuations and relay splays of mapped faults live in this band, so the sign is genuinely uncertain: this point measures where the collar-vs-continuation trade turns over.
  - **Mechanism**: Under DTI = T / (0.2T + 0.2(S-M) + 0.8|G|) each unit-mass dot adds 0.2(1 - m_q) to the denominator and (1 - 0.2s)dT to the numerator. Known USGS/INGENIOUS pixels are masked pixel-exactly out of the label set, so a dot inside the 3 px (300 m) kernel footprint of a masked catalogue pixel can only collect credit from *new-fault* truth. Collar dots are swapped 1:1 for the highest exact-marginal-gain off-catalogue ridge dots (d_cat >= 3.0 px, r_min = 2.8 px) from the parent's own ranked pool, so total mass and mean spacing are held and only collar geometry changes.
  - **Non-fault mimic**: Alluvial-fan head-cut scarps, pediment slope breaks and playa margins that parallel mapped range-front faults at 200-400 m; these mimic an unmapped splay and would make collar dots productive rather than wasteful.
  - **Predicted sign and size**: MODEL +0.0000..+0.0083 DTI (central +0.0042 from 1.088e-6 DTI per removed collar dot x 3825 dots, refill assumed neutral). Note the disagreement: the parent's own masking-blind ranking arithmetic prices the collar dots higher than the refill pool (negative), yet the lineage's one measured collar prune (0.2708 -> 0.2778 CLAIM) moved the other way, which is exactly why this axis is worth a slot. Live changes under 0.010 count as no evidence (public chunks only).
  - **Falsifier**: A live score below the 3 px variant falsifies monotonicity of the collar penalty and bounds the optimum collar width at or below 3 px.

**Report-only**: canary `max_auc = 0.5944` over `27` features on `22893` withheld positives (PASS); hide-and-recover `PROXY` R0 `0.00389` → `d2p5` `0.00044` → `d3p0`/`d4p0` `0.00000` — structurally blind to collar geometry, `IR-DEC-09`; SGMC off-catalogue calibrated `PROXY` rises with collar width (`0.06412` → `0.06681`, `0.06754`).

---

## `AXIS = CONCENTRATION` Variants (Built 2026-10-23, `evidence/r0_concentration_variants_20261023.json`)

- **Design**: 5×5 km blocks (50×50 px, origin 0,0; 2,046 blocks with ≥50% footprint). Block prior = mean parent ranking surface `q` over footprint pixels (eligible-block percentiles: p10 0.0748, p50 0.1075, p90 0.1429; means: bottom-half 0.0865, top-half 0.1300, top-quartile 0.1428). Count fixed at 37,654; donors = lowest exact-gain R0 dots in donor blocks; refills = greedy top-gain canonical-pool dots in recipient blocks at `d_cat >= 3.0 px`, `r_min = 2.8 px`. R0 block shares: bottom-half 31.36% (11,807 dots), top-half 66.21%, top-quartile 39.70%; 917 dots outside eligible blocks are frozen in all arms.
- **Capacity finding**: R0 is a maximal 2.8 px packing, so recipient blocks are saturated — measured greedy capacities are 4,287 (top-half) / 2,496 (top-quartile) / 2,494 (bottom-half, spread) extra dots. Doses below are the largest round moves inside that envelope; no off-ridge pool was invented.
- **Block-density CV** (`gems84.snap.density_cv`, dots-per-footprint-pixel std/mean): R0 = 1.883 (1 km) / 0.961 (5 km) / 0.801 (10 km). The brief's reported "best files 0.51–0.59" does not reproduce under this definition at any of these scales (`UNVERIFIED`, definition unstated) and was not used as a target.
- **Ranking audit**: rebuilt ranking reproduces the merged PRUNE `dgt1in` removal set bit-for-bit; shipped MASS drop tails agree only 80.9% / 85.1% (`IR-DEC-13`).

### 1. `5km-t50-move3765` — move 3,765 dots (10.00%; 20.00% symmetric diff) bottom-half → top-half

- **Name**: `h33-h33-2-b2-conc5km-t50-m3765-20261023-6310efe0`
- **File (NaN outside, spec)**: `releases/h33-h33-2-b2-conc5km-t50-m3765-20261023-6310efe0.tif` — `6310efe0df90949cb8e5a8463d450e52fb9ed1aa212e0c045a11ceda70ce5ee5`
- **File (zeros outside, fallback)**: `releases/h33-h33-2-b2-conc5km-t50-m3765-20261023-6310efe0-zeros.tif` — `cb7e964222c6bb5fe71c8163dda26a84e39ff49738b071c69e7d52237e01c537`
- **Form note**: `h33-h33-2-b2; CONC 5km move 3765 (10%) low->high prior blocks, 37654; pred -0.004..+0.013` (89 chars)
- **Format receipt**: EPSG:32611, (3730, 3292), float32, 1 band, transform match; no NaN in footprint; values in [0,1]; catalogue mass 0; refill `d_cat` min 3.0 px; CV 1.847/1.013/0.843 (1/5/10 km); top-half dot share 66.21% → 76.21%.
- **Mechanism card**: Hypothesis — km-scale fault clustering (systems/relays/step-overs) makes high-q blocks richer in unmapped structure per ridge pixel, so geographic concentration at fixed count/ranking gains DTI. Mechanism — only block membership changes; per-dot gain, spacing and collar held. Non-fault mimic — block q tracks survey density (GeoDAWN Areas 1/2 line spacing, lidar/radiometric coverage) and volcanic lineament swarms. Predicted — −0.004 to +0.013 DTI (MODEL credit scenario). Falsifier — live ≤ 0.2758 while spread ≥ R0: high-q blocks are catalogue-complete, residual truth is in quiet blocks.

### 2. `5km-t25-move2400` — move 2,400 dots (6.37%; 12.75% sym) bottom-half → top-quartile

- **Name**: `h33-h33-2-b2-conc5km-t25-m2400-20261023-caadfcce`
- **File (NaN outside, spec)**: `releases/h33-h33-2-b2-conc5km-t25-m2400-20261023-caadfcce.tif` — `caadfccefec8e5202c0b8f10884a972ae49130a79517f10e34d0cf54008a01a7`
- **File (zeros outside, fallback)**: `releases/h33-h33-2-b2-conc5km-t25-m2400-20261023-caadfcce-zeros.tif` — `e264e73a95540812a15e11c2355e33afebb93c8fc3617c5d19461de215d3b2f6`
- **Form note**: `h33-h33-2-b2; CONC 5km move 2400 (6.4%) low->top-quartile blocks, 37654; pred -0.002..+0.009` (92 chars)
- **Format receipt**: as above; CV 1.855/0.999/0.829; top-quartile share 39.70% → 46.07%.
- **Mechanism card**: stronger per-dot contrast into the most saturated blocks (capacity 2,496); prices saturation/kernel-redundancy of infill. Predicted −0.002 to +0.009 (MODEL); pre-registered ≥ spread, unordered vs t50. Falsifier — live < t50 receipt by ≥0.002 with t50 > R0: benefit stops at saturation.

### 3. `spread5km-move2400` — move 2,400 dots (6.37%; 12.75% sym) top-quartile → bottom-half (reverse arm)

- **Name**: `h33-h33-2-b2-spread5km-b50-m2400-20261023-ceb1073d`
- **File (NaN outside, spec)**: `releases/h33-h33-2-b2-spread5km-b50-m2400-20261023-ceb1073d.tif` — `ceb1073d77869b920cd82c6283bb27b68af4c12b95c02416fcacd7ee9bc07422`
- **File (zeros outside, fallback)**: `releases/h33-h33-2-b2-spread5km-b50-m2400-20261023-ceb1073d-zeros.tif` — `bd9e30dc346eca9675fdeecc5d25e21323ee4a299a15351d6059eb2a4f60a0d2`
- **Form note**: `h33-h33-2-b2; SPREAD 5km move 2400 (6.4%) high->low prior blocks, 37654; pred -0.006..+0.003` (92 chars)
- **Format receipt**: as above; CV 1.817/0.901/0.771; bottom-half share 31.36% → 37.73%.
- **Mechanism card**: mirror construction; wins only under catalogue-completeness (high-q blocks already mapped/masked; blind faults remain under quiet, cover-masked blocks). Predicted −0.006 to +0.003 (MODEL). Falsifier (of the CONC prior) — live ≥ both CONC receipts: invert/flatten the km prior.

### REPORT-ONLY diagnostics (`PROXY` — never gates)

| Arm | Fold-clean hide-and-recover (n=22,893 withheld+, 95% CI) | SGMC raw / calibrated (n=62,703) |
|---|---|---|
| R0 | 0.10564 [0.09363, 0.11696] | 0.09606 / 0.06412 |
| conc-t50 | 0.10405 [0.09210, 0.11477] | 0.10042 / 0.06708 |
| conc-t25 | 0.10489 [0.09274, 0.11575] | 0.09913 / 0.06620 |
| spread | 0.10520 [0.09329, 0.11648] | 0.09931 / 0.06633 |

Leakage canary: 27 features, max AUC 0.5944 ≤ 0.90. All fold-clean deltas include 0; withheld truth is catalogue-derived (clustered where mapping is dense), so this PROXY cannot judge the completeness-vs-clustering question — only live receipts can.
