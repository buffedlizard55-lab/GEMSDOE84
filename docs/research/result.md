# Final result: negative

**No TIFF is approved, packaged or released. No competition slot was used.**

The new physical surface's maximum full-footprint Spearman correlation against the readable registry was 0.08238. All six feature canaries passed across all four folds (maximum holdout diagnostic AUC 0.56945). This is not evidence of strong predictive ability; the AUCs are weak.

HOLDOUT-DTI (`gems57-pooled-hide-v2`, 11,318 withheld-positive pixels):

|Arm|Pooled DTI|95% spatial-bootstrap CI|
|---|---|---|
|H84-RFD|0.044298|[0.038195, 0.050494]|
|Step-only control|0.044364|[0.037376, 0.051673]|
|Paired difference|−0.000066|[−0.005921, 0.006213]|

The flanking-dipole term did not improve the paired control. The interval includes both beneficial and harmful effects. These are exploratory chunk-holdout results, not full-fault buffered validation, not leaderboard projections, and not organizer-confirmed results.

The production **array**, not a released TIFF, was constructed independently from the cached physical layers. Its decoded-byte SHA-256 is recorded in the run card. Final-dot checking stopped at the first binding duplicate: `17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif` had all candidate dots within its three-pixel support halo. This is a dense probability raster, so the overlap rule labels the placement a duplicate even though its rank correlation is near zero. The rule was applied literally, with no exemption. The remaining final-dot registry comparisons were not performed after this required stop.

The full surface scan recorded one malformed TIFF and five native-grid mismatches. Mismatched grids were reprojected only for comparison and explicitly flagged. No complete uniqueness clearance is claimed.

## Next work, in order

1. Resolve the cross-lane protocol's treatment of dense probability rasters centrally. A support-only veto against broad positive probability fields is not equivalent to identifying copied sparse placements. Do not retroactively waive it for this candidate.
2. Correct and test the shared upstream whole-geological-segment-plus-buffer holdout once. Reproduce the current best under that instrument; do not reuse incomparable historical metrics.
3. Reject the RFD augmentation in its current fixed form. Do not spend a weekly slot on it. Any new lane requires its own preregistration and budget.
4. Establish authenticated official-file hashes and organizer score receipts. A public mirror hash alone does not establish authoritative provenance.
5. Preserve failed artifacts and receipts in a coordinated registry with representation, grid validity, timestamps and immutable hashes. Keep final promotion separate from file-format validation.
