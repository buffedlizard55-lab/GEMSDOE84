# GEMSDOE84 — auditable fault-discovery research

## Submission status: BLOCKED — no validated TIFF available

**Do not submit a file from this repository.** No new competition prediction has been generated. A format check alone is not evidence of scientific performance or uniqueness. [Executive summary](docs/executive-summary.html) · [Research review](research/REVIEW.md) · [Run card](docs/data/run-card.json).

Read [the project mandate](research/PROJECT_MANDATE.md), this README and the current run card at the start of every session. Core values: **Maximize P(Win)** through honest evidence and risk-aware experiments; **Own the Outcome** through end-to-end automated checks, not unsupported success claims.

## Review outcome (2026-10-22)

The initial checkout at `4a7ccfac0b0499a2855efee44e957e0ad04abb3f` contained only an 11-byte README. There were no previous-session next steps, scripts, data, model, template cache, registry, or shared evaluator. The supplied prompt does not contain the referenced single lane-method paragraph. These are blockers, not reasons to invent data or a private evaluator.

The upstream GEMSDOE32 audit describes H33-2-B2 as removal of near-catalogue dots from an inherited submission. It also flags a contaminated catalogue holdout. Its surrogate is not an independent hide-and-recover result. No organizer receipt has been obtained. See the pinned evidence and limitations in the research review.

## Reproducible format inspection

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest -q
.venv/bin/python scripts/validate_submission.py data/new_prediction.tif \
  --template data/example_submission.tif --output data/format-validation.json
```

The inspector requires a single-band real GeoTIFF, matching CRS/shape/transform, finite values in the closed unit interval everywhere, and no masked pixels inside the template footprint. It **rejects**, rather than silently clips, invalid predictions. The official template's mask is authoritative; incorrect template metadata must be resolved before using it. This script is an independent format inspector, not a replacement for the shared `submission_writer.py` or `evaluate_holdout.py`.

## Next session: ordered acceptance gates

1. Restore the designated shared template/cache, exact writer/evaluator and full registry, with source commits and hashes. Establish the missing lane before implementing a surface.
2. Restore legally usable competition rasters and whole fault-segment geometries; check provenance, licenses, band names, footprints and integrity. Upstream public mirror pointers exist but are not organizer authentication.
3. Verify the shared evaluator uses buffered whole-segment hide-and-recover; reconstruct catalogue features using visible segments only; mask visible faults pixel-exactly; pool DTI with alpha 0.2, beta 0.8, triangular 300 m kernel. Report withheld positives and segment-bootstrap 95% CI.
4. Run individual feature leakage canaries. AUC above 0.90 blocks use pending investigation. Check surface correlation against every registry surface before placement; check final dots afterward. Correlation above 0.90 OR more than 70% dot proximity within 3 pixels means log duplicate and stop. Missing registry is not a pass.
5. Maximum three experiments or two hours. Beat the current holdout incumbent on the same frozen splits. Record all failures. No calibrated leaderboard proxy may replace this gate.
6. Use the shared writer, re-open the actual output bytes, run format inspection, registry checks and record SHA-256. Only then expose a download with distinct format/research/selector statuses. A separate selector verifies the live weekly cap and authorizes a real slot. This project never submits automatically.

## Hosting and access

The Pages workflow deploys `docs/` on pushes to main; actual deployment depends on repository Pages settings and workflow permissions. GitHub/network access is available. This sandbox's outbound network permits GitHub, npm and PyPI hosts only. DrivenData, USGS, GDR, NLR and Dropbox were not directly verified here. No organizer authentication or current weekly-slot receipt is available. GPU availability was not assessed; the official reference supports CPU training too. A GPU is not a categorical data-placement prerequisite.

This is a negative scientific deliverable plus tested infrastructure, **not completion of the requested new TIFF**. Do not infer a leaderboard score or exhaustive cross-repository uniqueness from this review.

**Hosting irregularity:** the Pages API reports legacy build mode. Changing it to workflow mode returned HTTP 403 for this integration. The committed deployment workflow may require a repository administrator to select GitHub Actions as the Pages source. This is a hosting-permission blocker, not a scientific inspection requirement.
