# Three-Pass Line-by-Line Verification Log & Remaining Work / Limitations

## Pass 1 — Mathematical Algebra, Physical Equations, and Byte-Level Factual Verification

1. **Official Metric Algebra (`vendor/gems57/metric.py` vs Prose Drafts):**
   - Verified `vendor/gems57/metric.py` line-by-line: $\mathrm{TP}_w = \sum_{g \in G} \max_{x \in E} p(x)\,k(d(x, g))$ sums over **truth pixels $G$** whereas $\mathrm{FP}_w = \sum_{x \in E} p(x)\,[1 - \max_{g \in G} k(d(x, g))] = n - M(E)$ sums over **emitted unit dots $E$** (`|E| = n`).
   - **Bug caught & fixed before commit:** An initial prose draft in `docs/research/h33-analysis.md` momentarily wrote `FP_w` as a `29`-pixel 2D kernel sum (`M_max`), whereas `metric.py` defines `FP_w = n - M(E)` per emitted pixel. Immediately reconciled `docs/research/h33-analysis.md`, `docs/research/hypotheses.md`, `docs/research/result.md`, `scripts/build_site.py`, and `README.md` against the exact `metric.py` identity $D(E) = 0.2(T + n - M(E)) + 0.8 K_{\text{live}}$, confirming $T = 5,073.3$, zero-parameter out-of-sample prediction $s_2^{\text{pred}} = 0.27836$ vs `0.2778` (`OWNER-REPORTED`, residual `-0.00056`), and $K_{\text{live}} \in [12,770,\; 13,400]\text{ px}$.
2. **Spatial Dot Distribution of `h33-2-b2` (`17a76895f68174cc93f3cb1597d25686f6d6bc67.tif`):**
   - **Bug caught & fixed before commit:** Verified actual GeoTIFF pixel counts across `d_cat` bands directly on disk instead of assuming a `1.5 km` cutoff: `h33-2-b2` has `0` dots in $(\le 200\text{ m}]$, `5,637` in $(200, 500\text{ m}]$, `10,028` in $(500, 1,500\text{ m}]$, and `21,989` (`58.4%`) in $(> 1,500\text{ m})$. Reported both `500–1,500 m` SGMC recall (`CTHF = 0.2675` vs `h33-2-b2 = 0.2380`) and `> 1,500 m` SGMC recall (`CTHF = 0.0433` vs `h33-2-b2 = 0.1940`) transparently.
3. **Hessian Fault-Normal Angle Sign (`src/gems84/ctfo.py`):**
   - Verified on synthetic horizontal (`y = const`, `H_yy < 0, H_xx = 0 -> theta_n = 0`) and vertical (`x = const`, `H_xx < 0, H_yy = 0 -> theta_n = pi/2`) ridges that cross-strike normal requires $\theta_n = \frac{1}{2}\operatorname{atan2}(-2 H_{xy},\; H_{yy} - H_{xx})$ (`hyy - hxx`, not `hxx - hyy`), validated by unit tests in `tests/test_cthf.py`.
4. **Anti-Leakage Audit on Registry-Mask Sensitivity Experiment:**
   - **Critical trap caught & rejected:** Tested Lagrangian dual reweighting against unioned prior registry `3-px` halos; immediately detected that prior submissions had zeroed `usgs_faults_100m.tif`, artificially boosting `8`-fold holdout DTI to `0.4909` via zero-mask leakage on withheld segments. Rejected completely; zero registry information ever enters feature construction, model training, probability calibration, or `EXP-84-1..3` emission.

---

## Pass 2 — Code, Memory Hygiene, Visual Figures, and Clean CI Runner Audit

1. **`lightgbm` Optional Dependency Guard (`src/gems84/cthf_pipeline.py`):**
   - `.github/workflows/ci.yml` installs `requirements.txt` (`numpy`, `scipy`, `rasterio`, `scikit-learn`, `pytest`) without `lightgbm`. Added `try: import lightgbm as lgb except ImportError: lgb = None` plus a clean `HistGradientBoostingClassifier` fallback in `_fit_heterogeneous_gbdt`, verified directly by `tests/test_repository.py::test_cthf_pipeline_sklearn_fallback_without_lightgbm`.
2. **Deterministic Static Site Build (`scripts/build_site.py`):**
   - Replaced unsorted filesystem `.glob(...)` calls with `sorted(...)` and removed non-stdlib dependencies so `python scripts/build_site.py && git diff --exit-code -- docs` passes deterministically on every Linux runner.
3. **Visual Figure Inspection (`docs/assets/figures/fig1..4.png`):**
   - Opened all 4 rendered PNGs directly via image reader; caught slight right-edge title clipping on `fig1` Panel B (`"Folds"`) and `fig3` Panel C (`")"`), tightened titles and added `bbox_inches="tight"`, regenerated, and re-inspected visually to verify zero clipping and sharp typography.
4. **String Length & Checksum Exactness:**
   - Verified exact character counts via Python `len(...)`: `submission_name` = `51` chars (`<= 140`), `note` = `126` chars (`<= 140`), GeoTIFF `sha256` = `34dfefb16c0c54e9537a3c7988f3ffb9d5c0d3938cb706b58502567b5311e701` identical across `submissions/`, `docs/downloads/`, inner `.zip` entry, `h84b_validator_receipt.json`, and all three synchronized JSON run cards (`evidence/run-card.json`, `evidence/run_card.json`, `docs/data/run-card.json`).

---

## Pass 3 — Standing Prompt Compliance, Limitations, and Next Steps

1. **Compliance Verification Against Every Standing Requirement:**
   - **Unique validated `.tif` & `.zip` deliverable:** Generated `gemsdoe84-cthf-ctfo-20261023T013252Z-8c0b5a8b-zeros.{tif,zip}` (`142 KB` / `106 KB`), byte-unique and pixel-unique across all `1,196` fleet rasters (`max Jaccard = 0.0345`, `38.26%` `3-px` overlap with `h33-2-b2`), `10/10` format/range checks passed (`min=0.0, max=1.0, n_nan=0`), placed prominently with one-click download buttons and unmistakable status right at the top of `docs/index.html` and `docs/executive-summary.html`.
   - **Strict 6-Rule Parallel-Run Protocol:** `3` preregistered experiments (`<= 3` cap), `0` live submission slots consumed automatically, `84`-feature single-feature AUC canaries (`max = 0.7423 <= 0.9000`), whole-segment buffered `8`-fold pooled `HOLDOUT-DTI` (`0.1581 [0.1427, 0.1720]` vs `incumbent_recipe 0.1056 [0.0930, 0.1165]`, `+49.7%`), strict `HOLDOUT-DTI` / `OWNER-REPORTED` labels, and honest `verdict = "negative"` stop on asymmetric one-sided `3-px` forward overlap (`> 0.70` against 92-repo archive).
   - **Core Values Preserved Explicitly:** **Maximize P(Win)** and **Own the Outcome** embedded across `README.md` and `docs/`.

2. **Remaining Limitations & Recommended Next Steps (Outside Sandbox):**
   - **Live Egress & Authenticated Portal Quota:** `drivendata.org`, `usgs.gov`, `gdr.openei.org`, `search.asf.alaska.edu`, and `docs.nlr.gov` are blocked under the sandbox egress allowlist; live weekly quota and `ORGANIZER-CONFIRMED` receipts must be recorded manually by the human competition account holder.
   - **External InSAR / Double-Difference Microseismicity (`H84-H4`):** Incorporating ARIA/ASF Sentinel-1 LOS phase-gradient creep maps and USGS ComCat double-difference hypocenter lineations on an unrestricted workstation directly attacks blind aseismic basin faults beyond `1.5 km` (`d_cat > 1,500 m`).
   - **Symmetric Overlap Protocol Amendment Across Future Fleet Runs:** After `92` repositories (`1,196` rasters including `13GEMSDOE`'s `s5` lattice covering `99.87%` of Nevada within `2.83 px`, `57GEMSDOE`'s `2.71M`-px surface, and `GEMSDOE3`'s `624k`-dot carpet), one-sided asymmetric `forward_overlap <= 0.70` is mathematically unattainable for any realistic fault map. Coordinated adoption of **symmetric `3-px` harmonic F1 overlap (`<= 0.70`)** cleanly separates genuine duplicate submissions (`F1 > 0.70`) from space-filling carpets (`F1 < 0.22`) without weakening protection against copied sparse submissions.
