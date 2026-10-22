# Three-pass implementation review

## Pass 1 — build and execute

- Inspected the empty starting checkout, predecessor repositories and official reference README/tree.
- Reused pinned shared evaluator, holdout, writer and validators; reused cached derived physical rasters instead of copying prediction TIFFs as features.
- Preregistered four hypotheses and one selected lane before implementation; restored and hash-verified all required data without requesting credentials.
- Indexed linked public repositories at resolved commits and downloaded their distinct TIFF blobs to an ignored cache.
- Implemented canaries, full-footprint pre-placement rank comparisons, fixed-parameter spatial holdout, strict final-dot duplicate stop and guarded packaging.

## Pass 2 — inspect failures and repair

- Found historical H33 ZIP contains no TIFF; recorded byte-level evidence and added warning to the guide.
- Found geometry-mismatched registry rasters. Added explicitly recorded nearest-neighbor comparison alignment; did not treat their native grids as valid submissions.
- Found malformed registry TIFF. Added explicit unreadable-row evidence and blocked complete uniqueness clearance. Did not silently count the error as a passing comparison.
- Added deterministic candidate-bound rank-audit checkpoints so tool repairs do not repeat every expensive comparison or change hypothesis parameters.
- Verified the shared vendor files against their pinned hashes. No metric, holdout or writer implementation was modified.
- Added input hash verification to the pipeline, empty-mask/invalid-budget fail-closed guards and output directory creation before packaging.

## Pass 3 — acceptance and edge cases

- Exercised real shared-writer GeoTIFF and ZIP roundtrip in a temporary fixture, rejection of NaN/infinity/out-of-range values, overwrite refusal, exact visible masking, pooled count/CI reporting and dot separation.
- Kept the scientific verdict distinct from format validity. Missing whole-geological-fault-plus-buffer validation and unreproduced current best block promotion unconditionally.
- Added a site generated from the negative run card, with no substituting historical TIFF or test fixture. The guide explains future submission steps without asserting the current run is eligible.
- Preserved bounded experiment scope. Technical retries repair the same fixed experiments; they are not parameter searches or additional hypotheses.
- Repository checks and deployment status are reported in the PR, not inferred from local success. No organizer submission or weekly slot is used.

## Unmet requirements, explicitly not waived

A guaranteed higher-scoring, globally unique, submission-approved TIFF has **not** been established. Official non-GitHub pages could not be freshly verified under the network policy. The README contains an operational transcription, not the full verbatim original user message. A whole-fault shared-template correction and a coordinated solution to any literal dense-registry overlap veto must happen before a production candidate can be promoted. No claim of complete line-by-line verification of inaccessible sources is made.

Pages configuration was inspected: an existing public legacy Pages site serves `main:/`. Switching it to workflow mode returned HTTP 403 (integration lacks Pages settings permission). The implementation therefore preserves legacy deployment, adds a root redirect to `docs/`, and does not install a conflicting deployment workflow. This permission failure is not evidence of a bad GitHub login.
