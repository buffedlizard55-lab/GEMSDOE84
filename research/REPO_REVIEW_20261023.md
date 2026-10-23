# Archived repository review — superseded 2026-10-23

This review documented an earlier fail-closed state based on incomplete 359-raster uniqueness coverage. It is superseded by [`SESSION_REVIEW_20261023.md`](SESSION_REVIEW_20261023.md), which records a stricter, literal duplicate-stop finding from a SHA-pinned registry witness.

## Current decision

**NEGATIVE — DO NOT SUBMIT.** The H84-THMS research TIFF is format-valid, but its forward 3-pixel overlap with the pinned witness is 1.0, above the 0.70 gate. This is a protocol-level duplicate under the user's literal support rule, not proof of copying. A full registry scan is not needed to establish this failure; one valid counterexample suffices. No new TIFF or slot was used.

The old 359-raster audit is historical subset evidence. The archived `HOLDOUT-DTI 0.2255` result is not certified leakage-free because the production-like holdout path used full-catalogue registry halos. No candidate HOLDOUT-DTI or ORGANIZER-CONFIRMED submission score is claimed by the current audit. See [`registry/release_status.json`](../registry/release_status.json) and [`evidence/release-audit-20261023.json`](../evidence/release-audit-20261023.json).
