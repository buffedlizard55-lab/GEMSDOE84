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

## `AXIS = PRUNE` Variants (session 2026-10-23, branch `arena/5be6452b-gemsdoe84`) — fixed-count collar sweep

- **Queue position**: Slots 1–3 remain the MASS files above (see `SLOT_PLAN.md`). `PRUNE d_cat>3px` is queued as slot 5; `PRUNE d_cat>1px` is a conditional bracketing arm (slot 6 only if the `>3px` receipt is inconclusive). Upload one file per slot.
- **AXIS provenance**: Brief v2 left the session AXIS blank for the human; PRUNE was agent-selected as next in the `SLOT_PLAN.md` sequence and is recorded as such (IR-DEC-08). `TOP_PUBLIC` and slot quota remain UNVERIFIED.
- **IR-DEC-07 (ranking pipeline fix)**: the refill/trim ranking below uses the MASS session's recorded recipe with the float32 nodata-sentinel cleaned at band unpack. Without the cleaning, H33-A silently collapses to a constant surface (float32 mean overflow) and the committed MASS masks do not reproduce (602–2,246 px/arm); with it they reproduce to ≤12 boundary dots per arm and this session's fold-clean R0 PROXY (0.10564) and canary max AUC (0.5949) match the MASS session's recorded values.
- **Lineage identities (measured)**: `d2_8` 44,090 dots → `& (d_cat>1)` = pinned 0.2708 CLAIM solo file (40,199) → `& (d_cat>2)` = R0 (37,654, rebuilt byte-identical). Ring counts: (1,2] px = 2,545 dots; (2,3] px = 2,171 dots.

### `h33-h33-2-b2-prune-dcatgt3px-20261023-a7d86ed4` — PRUNE `dcat>3px-refill37654` (37,654 dots, 11.53% changed vs R0)

- **File (NaN outside footprint, per spec)**: `releases/h33-h33-2-b2-prune-dcatgt3px-20261023-a7d86ed4.tif` — `sha256: a7d86ed4266cf3c9e408fccb6ee81aee43bddf18c49a5e54a9436b5a9d36f5f0`
- **File (zeros outside footprint, fallback)**: `releases/h33-h33-2-b2-prune-dcatgt3px-20261023-a7d86ed4-zeros.tif` — `sha256: 33e07daaf88fdc844dee18770795842c6fbf0794835069827a47e0375b429af2`
- **Form note (≤140 chars)**: `h33-h33-2-b2; PRUNE dcat>3px refill to 37654 (swap 2171 ring dots); pred +0.001 to +0.007` (89 chars)
- **Predicted live change (MODEL)**: +0.001 to +0.007 DTI (MODEL: swap 2,171 misregistration-halo ring dots for top-ranked >3 px ridge dots at fixed count)
- **Format & gate receipt** (re-read from disk): `EPSG:32611`, `(3730, 3292)`, float32, 1 band, transform = sample submission; no NaN inside footprint (5,167,373 px); values in [0,1]; catalogue mass 0.0; `d_cat` min/median/p90 = 3.1623 / 21.0238 / 68.884 px; +2171/−2171 dots; Jaccard vs R0 = 0.890973; `validate_submission.py` on `-zeros.tif`: format_valid = True.
- **Construction**: {'collar_px': 3.0, 'target_dots': 37654, 'kept_after_collar': 35483, 'refill_pool_dots': 18908, 'adjustment': 'refill', 'refill_dots': 2171, 'refill_gain_sum_model': 2986.342, 'refill_gain_mean_model': 1.375561}
- **Mechanism card (for a structural geologist)**:
  - *Hypothesis*: R0's 2,171 dots at 2.24-3.00 px (224-300 m) from a catalogue trace are mostly off-position re-detections of the catalogue faults themselves, not unmapped splays. Replacing them with the top-ranked corroborated ridge dots lying >3 px (>300 m) from every catalogue pixel, at unchanged count 37,654, increases live DTI.
  - *Mechanism*: GeoDAWN Area 2 was flown at ~400 m line spacing, so lineament positions are uncertain by about the 300 m kernel radius (https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7): a ridge detected within ~300 m of a mapped trace is most parsimoniously that same fault, misregistered. The organizers mask known pixels pixel-exactly and score neighbouring pixels against new-fault truth only (https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516), so a re-detection dot's kernel credit falls on masked pixels that are not in the test truth set: it pays the alpha-weighted false-positive cost and earns ~nothing. The parent's lineage already tightened this collar twice (44,090 dots 0.2600 CLAIM -> d_cat>1 40,199 dots 0.2708 CLAIM -> d_cat>2 37,654 dots 0.2778 CLAIM) but cut mass each time, so the collar effect was never isolated; this arm extends the collar to the kernel radius at fixed mass, refilling by the parent's own exact-marginal-gain ranking.
  - *Non-fault mimic / confounder*: Two confounders. (1) The signal being removed could be real: unmapped parallel splays, relay strands or fault-zone widening within 300 m of a mapped trace count as new fault per the organizers (https://community.drivendata.org/t/where-do-you-draw-the-line/11536). (2) The refill targets could be non-faults: lithologic contacts, dike-swarm magnetic lineaments or strandline terraces >300 m from mapped faults (the same mimic class as the MASS +10% arm).
  - *Predicted sign and size*: Positive: +0.001 to +0.007 DTI (MODEL). Decomposition: the confounded d_cat>1 -> d_cat>2 step gained +0.0070 CLAIM while also removing 2,545 dots of mass; attributing roughly half of that to the collar gives ~+0.003 for removing 2,171 comparable ring dots, plus a refill value near break-even (the MASS +10% arm's marginal dots are predicted -0.003..+0.0025). The parent ranking q itself values near-catalogue dots highly (its ridge fields respond to the known faults), so q-based gain sums understate the case for tightening; only a live receipt adjudicates. Per brief section 5, a live change under 0.01 on the public chunks is no evidence either way.
  - *Falsifier*: A receipt at or below 0.2678 (R0 CLAIM 0.2778 minus the 0.01 no-evidence band) falsifies the misregistration-halo hypothesis and proves the (2,3] px ring carries real unmapped test splays worth more than the best >3 px refill dots. A receipt at or above 0.2878 supports it. Between the two: no evidence on public chunks; do not spend another collar slot until a MASS receipt fixes the parent mass.

### `h33-h33-2-b2-prune-dcatgt1px-20261023-f5c7e4fb` — PRUNE `dcat>1px-trim37654` (37,654 dots, 13.24% changed vs R0)

- **File (NaN outside footprint, per spec)**: `releases/h33-h33-2-b2-prune-dcatgt1px-20261023-f5c7e4fb.tif` — `sha256: f5c7e4fb3db30907dd361c89018e4cb937620f963fe27a3809a9d1ba205da56d`
- **File (zeros outside footprint, fallback)**: `releases/h33-h33-2-b2-prune-dcatgt1px-20261023-f5c7e4fb-zeros.tif` — `sha256: 80551b8399134306e043ca120c812e9e1fe5f65dbaaec90165082140bfa01770`
- **Form note (≤140 chars)**: `h33-h33-2-b2; PRUNE dcat>1px rank-trim to 37654 (2492 ring dots in); pred -0.007 to +0.001` (90 chars)
- **Predicted live change (MODEL)**: -0.007 to +0.001 DTI (MODEL: re-admit (1,2] px ring dots, rank-trimmed to 37,654; bracketing arm for the collar curve)
- **Format & gate receipt** (re-read from disk): `EPSG:32611`, `(3730, 3292)`, float32, 1 band, transform = sample submission; no NaN inside footprint (5,167,373 px); values in [0,1]; catalogue mass 0.0; `d_cat` min/median/p90 = 1.4142 / 17.4642 / 65.7343 px; +2492/−2492 dots; Jaccard vs R0 = 0.875853; `validate_submission.py` on `-zeros.tif`: format_valid = True.
- **Construction**: {'collar_px': 1.0, 'target_dots': 37654, 'kept_after_collar': 40199, 'adjustment': 'rank_trim', 'trimmed_dots': 2545, 'trimmed_gain_sum_model': 2129.9199}
- **Mechanism card (for a structural geologist)**:
  - *Hypothesis*: Loosening the collar from >2 px to >1 px -- re-admitting the 2,545 lineage dots at 141-200 m from catalogue traces and dropping the same number of lowest-ranked dots elsewhere to hold 37,654 -- decreases live DTI if those ring dots are misregistered re-detections of mapped faults, and increases it if they are unmapped near-trace splays.
  - *Mechanism*: This is the historical 0.2708 CLAIM emission's collar (measured identity: solo == d2_8 & (d_cat > 1)) rebuilt at R0's mass. The 0.2708 -> 0.2778 step mixed collar tightening with a 6.3% mass cut; holding the count at 37,654 by the parent's exact-marginal-gain ranking isolates the collar. Together with R0 (d_cat>2) and the d_cat>3 arm, the three receipts would trace the fixed-mass collar response curve. Note the ranking q is structurally favourable to ring dots (its inputs respond to the known faults themselves), so the trim retains the ring dots q likes most -- the strongest form of the loose-collar case this lineage can make.
  - *Non-fault mimic / confounder*: The ring dots' topographic/geophysical ridges can be produced by the mapped fault's own scarp, damage-zone fracturing or juxtaposed-lithology contact offset by survey misregistration -- signal that is real geology but is the catalogue fault, whose pixels are masked out of the test truth. Alluvial fan-head trenching along the range front produces the same 100-200 m offset lineaments without any fault.
  - *Predicted sign and size*: Negative: -0.007 to +0.001 DTI (MODEL) -- the reverse of the lineage's d_cat>1 -> d_cat>2 gain, net of the mass effect that this arm removes. This is a bracketing/diagnostic arm, not a score-maximising one; SLOT_PLAN holds it conditional on the d_cat>3 receipt being inconclusive.
  - *Falsifier*: A receipt at or above 0.2878 (R0 CLAIM + 0.01) falsifies the misregistration-halo model of the near-catalogue ring and would redirect the campaign toward near-trace splay hunting. At or below 0.2678 it corroborates the model. Between: no evidence on public chunks.

### REPORT-ONLY diagnostics for the PRUNE arms (`evidence/r0_prune_variants_20261023.json`, PROXY — never gates)

| Arm | n_dots | Fold-clean hide-and-recover PROXY (n=22,893, 95% CI) | Shipped-mask PROXY | SGMC raw DTI PROXY (n=62,703) | SGMC coverage | SGMC calibrated DTI |
|---|---:|---|---|---:|---:|---:|
| Parent R0 | 37,654 | 0.10564 ([0.09363, 0.11696]) | 0.00389 ([0.00332, 0.00445]) | 0.09606 | 0.08935 | 0.06412 |
| PRUNE d_cat>3px | 37,654 | 0.10486 ([0.09296, 0.11579]) | 0.00000 ([0.00000, 0.00000]) | 0.10137 | 0.09437 | 0.06772 |
| PRUNE d_cat>1px | 37,654 | 0.10358 ([0.09156, 0.11460]) | 0.03013 ([0.02604, 0.03395]) | 0.09331 | 0.08676 | 0.06226 |

- Fold-clean paired deltas vs R0: `>3px` −0.0008 (95% CI [−0.0022, +0.0005], spans 0); `>1px` −0.0021 (CI [−0.0032, −0.0011], excludes 0). On withheld-catalogue recovery, loosening loses and tightening is neutral; live truth (unmapped splays near known traces) is a different regime — which is why these receipts, not this PROXY, decide the collar.
- Shipped-mask `>3px` = 0.00000 is a **construction artifact** (IR-DEC-09): every shipped dot is >3 px from the *full* catalogue including withheld pixels, so the 300 m kernel earns exactly zero there. It says nothing about live quality.
- SGMC truth excludes a 3 px catalogue dilation band, so the SGMC column is structurally biased toward the tighter collar (IR-DEC-09): do not rank the two PRUNE arms by it.
- Leakage canary: max single-feature AUC = 0.5949 over 27 features (≤ 0.90, passed).
