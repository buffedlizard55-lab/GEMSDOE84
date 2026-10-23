# GEMSDOE84 — Crack-Tip Hydrothermal-Geopotential Posterior (`CTHF`) & Comonotonic 1D-Trace Fractional Optimization (`CTFO`)

**Core Values:** **Maximize P(Win)** · **Own the Outcome**

---

## Executive Release Summary & One-Click Validated Submission Artifacts

| Field | Verified Value |
|---|---|
| **Generated Unique GeoTIFF (`.tif`)** | [`docs/downloads/gemsdoe84-cthf-ctfo-20261023T013252Z-8c0b5a8b-zeros.tif`](docs/downloads/gemsdoe84-cthf-ctfo-20261023T013252Z-8c0b5a8b-zeros.tif) (`142 KB`; mirrored in `submissions/`) |
| **Verified Single-TIFF Archive (`.zip`)** | [`docs/downloads/gemsdoe84-cthf-ctfo-20261023T013252Z-8c0b5a8b-zeros.zip`](docs/downloads/gemsdoe84-cthf-ctfo-20261023T013252Z-8c0b5a8b-zeros.zip) (`106 KB`; exact inner `.tif` byte roundtrip) |
| **Unique Submission Name (`51` chars)** | `gemsdoe84-cthf-ctfo-20261023T013252Z-8c0b5a8b-zeros` |
| **Short Portal Note (`126 / 140` chars)** | `GEMSDOE84 H84-B CTHF+CTFO: FFT upward-continued pullback + GDR-1391 F2mDAB/sinter + crack-tip relay + Dinkelbach 1D-trace dots` |
| **GeoTIFF `SHA-256`** | `34dfefb16c0c54e9537a3c7988f3ffb9d5c0d3938cb706b58502567b5311e701` |
| **Decoded `float32` Array `SHA-256`** | `8c0b5a8b4ffc849b81106f62239f5f9bde6e5eb54c08068873d570112e1550fa` |
| **Format & Portal Range Validation** | **`PASS` (`10 / 10` checks)** — `GTiff`, `count=1`, `float32`, `3730 x 3292`, `EPSG:32611`, affine `(100, 0, 243350, 0, -100, 4508550)`, strictly finite in `[0.0, 1.0]`, `0` NaN, `0` Inf, `41,500` unit dots, `0` mapped-fault positives (prevents `"Predicted values must be in range [0, 1]"` error) |
| **Single-Feature Leakage Canaries** | **`PASS`** (`84` features tested; `max |AUC| = 0.7423 <= 0.9000`, `0` violations; [`evidence/h84b_leakage_canaries.json`](evidence/h84b_leakage_canaries.json)) |
| **Pooled 8-Fold `HOLDOUT-DTI`** | **`0.1581`** (`95% CI [0.1427, 0.1720]`, `gems57-pooled-hide-v2`, `22,893` withheld positive px) — **`+0.0525 (+49.7%)`** over `incumbent_recipe = 0.1056` (`95% CI [+0.0370, +0.0676]`); equal-budget `37,654`-dot `CTFO = 0.1578` vs `NMS = 0.1458` (**`+0.0120` pure packing lift across `8 / 8` folds**) |
| **Uniqueness vs `1,196` Fleet Rasters** | **`byte_unique = True`, `pixel_unique = True`** · Pre-placement surface `max |Spearman rho| = 0.6953 <= 0.90` (**PASS**) · Final GeoTIFF `max |Spearman rho| = 0.1086 <= 0.90` (**PASS**) · Exact dot Jaccard `<= 0.0345` · `3-px` overlap vs `h33-2-b2` = **`38.26%` (`61.7%` novel; `2.40%` 1-px)** · One-sided `3-px` forward overlap exceeds `0.70` against 92-repo archive carpets/lattices |
| **Automated Release Verdict** | **`HOLD / DO NOT AUTO-SUBMIT` (`verdict = "negative"`, `0` live weekly slots consumed automatically)** — Strict compliance with Parallel-Run Protocol Rules 1 & 6; validated `.tif` and `.zip` published right at the top of [`docs/index.html`](docs/index.html) and [`docs/executive-summary.html`](docs/executive-summary.html) for explicit human selector review |

---

## 1. Forensic Analysis: Why `h33-h33-2-b2-zeros` (`GEMSDOE32`) Scored `0.2778` (`OWNER-REPORTED`)

Pixel-exact set algebra across `1,196` SHA-verified `3730 x 3292` rasters from `92` sibling `GEMSDOE*` repositories proves a strict nested subset chain with **zero added pixels** at every step (`evidence/incumbent_anatomy.json`, [`docs/research/h33-analysis.md`](docs/research/h33-analysis.md)):

$$E_{\text{h19-5}}\;(121,131;\;0.1922) \;\supset\; E_{\text{d1.5}}\;(60,069;\;0.2477) \;\supset\; E_{\text{d2.8}}\;(44,090;\;0.2600) \;\supset\; E_{\text{h27-4-r1}}\;(40,199;\;0.2708) \;\supset\; E_{\text{h33-2-b2}}\;(37,654;\;\mathbf{0.2778}).$$

Under the official DrivenData DTI formula (`vendor/gems57/metric.py`, $\alpha = 0.2, \beta = 0.8$, $R = 300\text{ m} = 3\text{ px}$ triangular kernel $k(d) = \max(1 - d/3, 0)$), $1 - \beta = 0.2 = \alpha$ collapses the denominator linearly:

$$D(E) = 0.2\,\bigl(T + n - M(E)\bigr) + 0.8\,K_{\text{live}}.$$

1. **Why pruning `0 < d_cat <= 200 m` increased live DTI (`+0.0178` `OWNER-REPORTED`):** Deleting `3,891` lateral collar dots in $(\le 100\text{ m}]$ (`0.2600 -> 0.2708`) solves covered hidden truth **with zero free parameters**: $T = 0.2 \times 3,891 / (1/0.2600 - 1/0.2708) = \mathbf{5,073.3\text{ px-wt}}$, which predicts the subsequent `2,545`-dot `(100, 200 m]` deletion score out-of-sample as **`0.27836`** vs **`0.2778`** (`OWNER-REPORTED`, residual `-0.00056`), bounding live hidden fault pixels to **$K_{\text{live}} \in [12,770,\; 13,400]\text{ px}$** ($\approx 13,085 \pm 315\text{ px}$).
2. **Why `h33-2-b2` plateaued at `0.2778`:** Its underlying ranking (`h19-5`) uses only `100 m` detrended elevation slope + power-law catalogue distance with greedy `d = 2.8 px` circle thinning, ignoring `1 m` 3DEP LiDAR micro-scarps, `10 m` fluvial $\chi / k_{sn}$ knickpoint steps, upward-continued potential-field footwall pullbacks, DOE GDR-1391 `F2mDAB` shallow thermal probes & Quaternary sinters, crack-tip stress cones, and oriented 1D-trace submodular packing.

---

## 2. Preregistered Geological & Decision-Theoretic Hypotheses ([`docs/research/hypotheses.md`](docs/research/hypotheses.md))

| Rank | ID | Hypothesis & Mechanism | Named Non-Fault Mimic | Cost | Status |
|---:|---|---|---|---|---|
| **1** | **`H84-H1`** | **Comonotonic 1D-Trace Fractional Optimization (`CTFO`) + Lake Lahontan Shoreline Counter-Filter:** Hessian fault-normal cross-strike self-credit $Q_{\text{1D-trace}}(x)$ + Charnes–Cooper submodular CELF allocation (`+8.52%` `TP_w` at identical `37,654` dot budget across `8/8` folds) | Pleistocene Lake Lahontan wave-cut shoreline benches (`~1,265–1,348 m` ASL Sehoo highstand) | Low–Med | **Implemented & Validated (`+0.0123` lift over identical-posterior NMS)** |
| **2** | **`H84-H2`** | **2D FFT Harmonic Upward-Continued Potential Worms & $60^\circ$ Footwall Subcrop Pullback (`HUPW`):** Multi-altitude upward continuation of gravity/magnetic tilt worms pulled back updip using local `depth_to_base_surf`, fused with `1 m` LiDAR & `10 m` $\chi$ | Intrusive pluton margins & buried caldera ring dikes | Low–Med | **Implemented & Validated (`EXP-84-1 = 0.0953` pure physics)** |
| **3** | **`H84-H3`** | **Advective Hydrothermal Upflow, 2 m Probe (`F2mDAB`) & Quaternary Sinter/Travertine Conduits (`AHFV`) + Crack-Tip Relays:** DOE GDR-1391 `3,800` `2 m` temperature probes, `709` sinters, `27,092` geothermometers + Cowie–Scholz propagation cones fused via Noisy-OR | Stratiform outflow plumes in permeable piedmont gravels | Low | **Implemented & Validated (`+0.0505` posterior lift in `EXP-84-2`)** |
| **4** | **`H84-H4`** | **Sentinel-1 InSAR Creep Gradients & Double-Difference Microseismic Planes (`ISD-DD`)** | Agricultural groundwater pumping subsidence bowls | High | **Documented; external hosts blocked by sandbox network allowlist** |

---

## 3. Pooled 8-Fold Buffered Whole-Segment Holdout Results (`gems57-pooled-hide-v2`)

| Arm | Dots | `HOLDOUT-DTI` | `95% Cluster CI` | `TPw` | `FPw` | Paired $\Delta$ vs `incumbent_recipe` |
|---|---:|---:|---|---:|---:|---|
| **`EXP_84_3_CTHF_CTFO`** | **`41,500`** | **`0.1581`** | **`[0.1427, 0.1720]`** | **`5,420.6`** | **`74,419.4`** | **`+0.0525 [+0.0370, +0.0676]` (`+49.7%`)** |
| **`EXP_84_3_EQBUDGET_37654`** | **`37,654`** | **`0.1578`** | **`[0.1426, 0.1714]`** | **`5,183.7`** | **`67,509.5`** | **`+0.0522 [+0.0369, +0.0671]`** |
| **`EXP_84_2_CTHF_NMS`** | `37,654` | `0.1458` | `[0.1312, 0.1595]` | `4,776.8` | `67,427.5` | `+0.0402 [+0.0261, +0.0545]` |
| **`incumbent_recipe` (`h33-2-b2` rule)** | `~39,600` | `0.1056` | `[0.0930, 0.1165]` | `3,524.1` | `71,694.6` | `0.0000` (baseline control) |
| **`EXP_84_1_HUPW_NMS` (`0` cat features)** | `37,654` | `0.0953` | `[0.0811, 0.1089]` | `3,041.6` | `64,993.1` | `-0.0103 [-0.0235, +0.0031]` |
| **`incumbent_asis` (shipped `h33-2-b2`)** | `37,654` | `0.0039` | `[0.0033, 0.0045]` | `126.1` | `70,593.8` | `-0.1018 [-0.1127, -0.0892]` |

![Pooled 8-Fold Holdout Ablation](docs/assets/figures/fig1_holdout_ablation.png)

---

## 4. Standing Operating Prompt & Core Values (Preserved Verbatim)

Full verbatim prompt preserved in [`PROMPT.md`](PROMPT.md):
- **Core Values:** **Maximize P(Win)** and **Own the Outcome** — prioritize falsifiable geophysics, leak-free whole-segment spatial validation, exact mathematical optimization of the competition metric, complete transparency on every protocol gate, and end-to-end automated validation without human guesswork.
- **Parallel-Run Protocol (Rules 1–6):** Single lane (`H84-B`); pre-placement surface & post-placement dot registry audits (`<= 0.90` Spearman, `<= 0.70` 3-px overlap logged faithfully across literal and halo-coverage readings); shared `vendor/gems57/` tools SHA-pinned in `registry/template_pin.json`; strict `HOLDOUT-DTI` vs `OWNER-REPORTED` vs `ORGANIZER-CONFIRMED` labels; single-feature AUC canaries (`<= 0.90`); synchronized machine-readable JSON run cards (`evidence/run-card.json`, `evidence/run_card.json`, `docs/data/run-card.json`); `<= 3` experiments; `0` live weekly slots consumed automatically.

---

## 5. Reproduction & Verification Commands

```bash
# 1. Install environment (CI-compatible standard scientific Python stack)
python -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Run full Lane H84-B 3-experiment holdout ablation + production + 1,196-raster audit
.venv/bin/python -u scripts/run_h84b_experiments.py

# 3. Validate GeoTIFF format, [0, 1] finiteness, EPSG:32611 grid & SHA-256 offline
.venv/bin/python scripts/validate_submission.py \
  docs/downloads/gemsdoe84-cthf-ctfo-20261023T013252Z-8c0b5a8b-zeros.tif \
  --template data/bridge/sample_submission.tif \
  --output evidence/h84b_validator_receipt.json

# 4. Regenerate diagnostic figures, synchronized run cards, and GitHub Pages site
.venv/bin/python scripts/generate_figures_and_runcards.py
.venv/bin/python scripts/build_site.py

# 5. Execute full automated verification suite & CI diff check
.venv/bin/python -m pytest -q
git diff --exit-code -- docs
```

---

## 6. Honest Limitations & Recommended Next Steps

1. **Holdout-vs-Live Domain Shift:** Whole-segment holdout hides segments from `usgs_faults_100m.tif`, concentrating posterior mass near mapped splay/relay corridors (`83.7%` of `EXP-84-3` dots at `200–1,500 m`, `0.2675` SGMC recall in `500–1,500 m` vs `0.2380` for `h33-2-b2`), whereas live hidden truth exhibits negative `5 km` catalogue density (`theta = -10.82`; `h33-2-b2` places `58.4%` of dots beyond `1,500 m`). Combining `CTFO` (`+8.52%` `TP_w` at identical dot count) with live-regime `d_cat > 1.5 km` prior calibration + external InSAR/microseismicity (`H84-H4`) on an unrestricted machine is the highest-leverage next step.
2. **Fleet Overlap Saturation:** Across `92` repositories (`1,196` rasters including `13GEMSDOE`'s regular `5-px` lattice covering `99.87%` of Nevada within `2.83 px`, `57GEMSDOE`'s `2.71M`-px continuous surface, and `GEMSDOE3`'s `624k`-dot carpet), one-sided `forward_overlap <= 0.70` blocks every realistic fault map despite `max Jaccard = 0.0345` and `38.26%` `3-px` overlap against `h33-2-b2`. Adopting symmetric `3-px` harmonic F1 overlap (`<= 0.70`) at the portfolio selector layer resolves space-filler vetoes cleanly.
3. **Sandbox Network Boundaries:** `drivendata.org` is outside the sandbox allowlist; all historical scores are strictly labelled `OWNER-REPORTED`, and `0` live weekly slots were spent automatically.
