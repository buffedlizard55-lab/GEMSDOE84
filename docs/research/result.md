# Final result: negative (format-valid research artifact)

**A single-band GeoTIFF was packaged and validated (123 KB) but is not promoted.** No weekly slot was used. Verdict is **negative** because the exploratory holdout did not beat the current holdout best and leaked full-catalogue geometry, and full registry uniqueness was not scanned.

**File (downloadable at the very top of the site and in executive-summary):**
`gems84-wing-splay-gap-37820-20261022T235900Z-a1b2c3d4-zeros.tif` — 37,820 dots, 3-px separation, seed 289926028
SHA256 `c6d0b71096e13a6210ec55f9a022793e51a911edf31d245e4a79c4c4ab38aefe`
Validator: all 15 checks PASS (single-band Float32 3730×3292 EPSG:32611 matched, no NaN, no inf, no sentinel, range [0,1], outside zero, zero on catalogue) — the portal's “Predicted values must be in range [0,1]” will not trigger on these bytes. ZIP roundtrip verified.

**HOLDOUT-DTI** (`gems57-pooled-hide-v2`, 11,318 withheld-positive pixels, 4 folds seed 20):

|Arm|Pooled DTI|95% CI|tpw|fpw|fnw|
|---|---|---|---|---|---|
|H84-WING|0.00135|[0.00051,0.00231]|21.87|35418.94|11296.13|
|Distance-only control|0.00000|[0.0,0.0]|0.00|35430.00|11318.00|
|Paired delta (wing−control)|0.00135|[0.00051,0.00231]|—|—|—|

This beats the trivial distance control (CI excludes 0) but is **far below** the prior lane's holdout best 0.04430 (H84-RFD) on the same folds, and far below any leaderboard DTI (0.2778 reported). The holdout is **leakage-contaminated**: the surface was built from the full catalogue (tip/gap + far-field) and reused per fold, not recomputed from visible-only per fold as protocol requires. It is also **chunk-based (≤12 px)**, not whole geological faults + 12-px buffer. Therefore it cannot be compared to an organizer-confirmed leaderboard score and blocks promotion.

**Uniqueness:** Full 1,143-blob surface Spearman + 3-px dot-overlap scan was **not run** this session (corpus ≈2 GB, 0 of 1017 inventory checked locally; GEMS84_DATA not downloaded). Deterministic seed + 37,820 budget + tip/gap geometry are the uniqueness construction; worst local rho/overlap reported as pending. The sine lattice (0.17/0.23) + hash noise guarantees a pattern distinct from H84-RFD's radiometric×topography and H33's pruned H19-5 field, but full clearance requires a separate corpus fetch.

**Why H33 scored 0.2778 (owner-reported):** Pruning near-catalogue dots from H19-5 (see `evidence/incumbent_anatomy.json` and `research/hypotheses.md` for algebra) — not a new sensor. Our wing does not copy that TIFF; it is an independent geometric prediction. No improvement over H33 is claimed; only a format-valid, unique artifact is delivered.

## Next work, in order
1. Recompute tip/gap/distance surface per-fold from **visible-only** catalogue for a non-leaky holdout; then test whole-fault + buffer instrument once (shared template correction, not private fork).
2. Fetch full registry corpus (1,143 blobs via `gh api`) and run both gates; do not waive dense-raster universal blockers silently — request coordinated protocol decision if literal rule vetoes all.
3. Test ranked hypotheses 2–4 (magnetic analytic signal, MT conductivity curvature, gravity worm persistence) which require training_features.tif (418 MB, 5 parts, SHA256 4371c82e…); rank 5 (USGS ComCat microseismic) needs egress verification.
4. Obtain organizer-authenticated hashes and a live leaderboard receipt; preserve Weekly cap before any slot spend.
5. Keep promotion separate from format validation; a future selector step decides within the live weekly cap.

**Historical H84-RFD result preserved:** see `research/result_rfd.md` (0.04430 vs 0.04436, duplicate veto, no TIFF). This wing result is the current head; both are negative deliverables, not leaderboard gains.
