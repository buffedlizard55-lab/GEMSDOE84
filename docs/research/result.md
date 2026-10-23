# Final Result (`Lane H84-B: H84-TCDH`): `PROMOTE` (`OK TO DOWNLOAD & SUBMIT`)

- **Canonical Run Card:** [`evidence/run_card.json`](../../evidence/run_card.json)
- **Promoted GeoTIFF (`.tif`):** `docs/downloads/gems84-h84b-tcdh-twostrat-39000d-20261022T235800Z-zeros.tif` (`141,933` bytes, `SHA-256: 89abda09900ade5092c00491ef72d97b1d0ae9b1c3fe8f9383259ca7e6a0443b`)
- **Promoted DrivenData Archive (`.zip`):** `docs/downloads/gems84-h84b-tcdh-twostrat-39000d-20261022T235800Z-zeros.zip` (`106,347` bytes, `SHA-256: 982310d80c2a1129...`)
- **Weekly Live Slots Spent Automatically:** `0` (`submission_slots_used = 0`)

## Summary of Protocol Gate Results

1. **Leakage Canary (`EXP-84B-1`):** All 52 single-feature symmetric AUCs `<= 0.7724 <= 0.90` on buffered whole-component holdout (`PASSED`).
2. **Holdout Superiority (`EXP-84B-2`, `HOLDOUT-DTI`, `gems57-pooled-hide-v2`, `n = 22,893` withheld positives):**
   - `alloc_twostrat_nms3_39k`: **`0.1234`** (`95% CI [0.1113, 0.1363]`)
   - `incumbent_h33_b2_recipe`: **`0.1056`** (`95% CI [0.0944, 0.1166]`)
   - Paired difference: **`+0.0178` (`95% CI [+0.0040, +0.0321]`, `+16.8%` relative gain)**
3. **Registry Uniqueness (`EXP-84B-3`, `1,163` rasters):**
   - Gate 3A Continuous Surface: `max |Spearman rho| = 0.2629 <= 0.90` (`PASSED`)
   - Gate 3B Post-Placement Dots: `worst_forward_overlap = 0.6760 <= 0.70` across all `1,092` discriminating priors (`worst |Spearman| = 0.0380 <= 0.90`, `binding_duplicate_decision = False`, `PASSED`)
4. **Dual Automated GeoTIFF Validation (`Gate 3C`):** Passed all 15 `vendor/gems57/validate.py` checks and all 10 `scripts/validate_submission.py` checks (`float32`, `3730 x 3292`, `EPSG:32611`, `[0.0, 1.0]`, `nodata = None`, `n_nan = 0`, `n_inf = 0`, `0` catalogue pixels, `0` outside-footprint pixels).

*(Historical note: earlier exploratory lanes `H84-RFD` [PR #5, chunked holdout `0.04430`] and `H84-A LITI` [PR #7, live-score inversion `0.00867`, archived in `docs/liti/`] remain permanently marked `negative`.)*
