# GEMSDOE84 — evidence-first fault discovery

**Read this operating brief at the beginning of every session.**

## Submission status

The site and `evidence/run-card.json` are the release authority. **A local format pass is not permission to submit.** No weekly slot is used by this project. A negative result, duplicate veto, missing evidence, or an incomparable holdout best blocks promotion. The download area must never quietly substitute an older submission.

This repository started with only an eleven-byte README. There was no pre-existing training pipeline, cached feature stack, evaluator, data or site. Current work restores integrity-pinned public mirrors and reuses the shared evaluator/writer without editing their implementations.

## User request: standing project brief

This is the operational transcription of the supplied long, repetitive request (not a verbatim archive). Its requirements remain the acceptance criteria:

- Generate a scientifically distinct, uniquely named single-band GeoTIFF, with a note no longer than 140 characters. Make it downloadable at the beginning of a clean GitHub Pages site, with unmistakable submit/do-not-submit status and an executive-summary submission guide. Never copy a previous submission except for education/comparison.
- Match the competition sample's CRS, shape and affine transform; ensure all values are finite in [0,1], no NaNs inside the footprint, no sentinel values, and pixel-exact visible-fault masking. Investigate the reported range error rather than assuming its cause.
- Work autonomously. Inspect the repository and prior sessions first; research official free sources; preserve auditable links, provenance and limitations; never invent data, scores, receipts, verification or novelty. Automate validation rather than require a human inspector.
- Before implementation, propose 3–5 geological hypotheses naming layers, physical transforms, missing-fault rationale, non-fault confounders, difference from existing code, expected-benefit ranking and cost. Check data availability before calling a hypothesis viable. Do not confuse geothermal-vent discovery with the contest's fault-prediction target.
- Parallel-run protocol: stay in one method lane; stop on rank correlation >0.90 or >70% of dots within 3 pixels of any registry raster. Check surfaces before placement and final dots. Do not exempt dense rasters or lattices from this literal rule.
- Reuse shared cached features, `evaluate_holdout.py` and `submission_writer.py`; do not privately fork incorrect tools. Hold out whole fault segments with a buffer; derive catalogue features solely from visible faults; pool DTI with alpha 0.2, beta 0.8 and a 300 m triangular kernel. Report template deviations prominently.
- Run every feature alone as a leakage canary; AUC >0.90 means leakage until resolved. Report HOLDOUT-DTI with evaluator version, withheld positives and 95% CI. Only a submission-page receipt earns ORGANIZER-CONFIRMED status. Projections are not scores.
- End with one JSON run card: hypothesis, mechanism, named non-fault mimic, holdout plus CI, registry correlation/overlap, raster SHA-256, validator output, name/note, verdict promote/negative. Negative results are deliverables. Stop after three experiments or two hours. Promotion to a real slot is a separate selector action within the live weekly cap.
- Investigate GEMSDOE32's user-reported H33 result and the listed predecessor sites; distinguish score reports from organizer evidence. The request gives conflicting leaderboard maxima (0.3195 and 0.4413); neither is verified current here. Do not promise to exceed them.
- Build an auditable source/knowledge record for reuse, review limitations and next steps, automate updates honestly (timestamped retrieval is not a perpetual live feed), and execute three review passes. Open a PR and merge it if checks pass.
- Keep **Maximize P(Win)** and **Own the Outcome** as project values: prefer honest falsification and strong controls to unsupported promotion; own reproducibility and end-to-end release safety.

Original competition/review pointers supplied by the user:
- https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
- https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- https://github.com/drivendataorg/gems-prize-reference-solution
- https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html
- https://docs.nlr.gov/docs/fy26osti/96647.pdf
- https://gdr.openei.org/submissions/1391
- https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- https://gbcge.org/current-projects/ingenious/
- https://epsg.io/32611

## Reproduce

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
python scripts/restore_data.py --ids labels,existing_faults,sample_submission,ext_lidar_scarp_features_u8,ext_geodawn_rad_u8
.venv/bin/python scripts/inventory.py
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/run_lane.py
.venv/bin/python scripts/build_site.py
.venv/bin/python -m pytest -q
```

`gh` must already be authenticated to retrieve the public mirror blobs. No secrets belong in this repo. Raw data, the registry raster cache and virtual environment are ignored. Only receipts, code and appropriately cleared small deliverables are committed. The restore script validates SHA-256; those hashes establish mirror consistency, not original organizer authenticity.

## Limits and next session

- Outbound access is limited to GitHub and package registries. No independent current DrivenData, USGS, GDR or NLR retrieval, authenticated competition download, leaderboard receipt or weekly-cap lookup is possible here.
- No method paragraph was supplied; H84-RFD is an explicitly selected exploratory lane. Novelty is scoped to the indexed public artifacts, never universal.
- The inherited evaluator segments branches into short chunks. It does **not** establish the requested whole-geological-fault plus buffer validation. The shared tool was reused unchanged; this deficiency blocks promotion and needs one upstream correction, not a private fork.
- Current holdout best must be reproduced with exactly the same masks, folds, budgets and evaluator before a promotion comparison. Prior reported numbers are not automatically comparable.
- A literal overlap rule may veto every candidate if a registry raster densely covers the footprint. Do not weaken the rule silently. Record the counterexample and request a coordinated protocol decision in a future session.
- Do not consume a real submission slot, claim leaderboard improvement, or package a duplicate just to produce a download button.

The full machine-readable result is `evidence/run-card.json`; source inventory is `registry/inventory.json`; hypothesis preregistration is `docs/research/hypotheses.md`.

## Parallel-session integration

Other sessions merged readiness tooling and unexecuted hypothesis proposals while this experiment ran. Their original front pages and README are preserved under `research/concurrent-readiness/`, their source receipts and validators remain intact, and their old JSON cards are marked historical/superseded. They are not additional experiments in H84-RFD. The canonical measured run is `evidence/run-card.json`. Readiness presence checks now point at this lane's actual cache/vendor paths; presence still never authorizes a submission. The combined suite passes 27 tests locally. The existing Pages workflow from those merged changes is retained; deployment success must be checked independently.
