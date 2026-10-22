# Standing brief (read at the start of every session)

> Copied from the project owner's session prompt (2026-10-22). Treat it as the
> requirements spec. Scores below are **OWNER-REPORTED** unless an organizer
> receipt is attached; the leaderboard values quoted (0.4413 current GEMSDOE-listed
> high score, 0.3195 earlier public leader) could not be re-read from this sandbox
> because drivendata.org is outside the egress allow-list (see `docs/irregularities.md`).

## Highest urgency

MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS
SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. IT MUST BE OBVIOUS WHETHER IT IS
OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.

There should be an easy to download submission tif file as described by the prompt.
The inspection needs to be done through the project and needs to be validated for
submission without human intervention.

## PARALLEL-RUN PROTOCOL — read first

This session is one of several running from this same prompt.

1. **LANE.** Your lane is the single method paragraph below. Stay inside it. If your
   raster's rank-correlation with any registry raster exceeds 0.90, or more than 70%
   of your dots fall within 3 px of one registry raster's dots, you have drifted into
   another lane: log it as a duplicate and stop. Check this on the surface before
   placement AND on the final dots.
2. **REUSE, DON'T REBUILD.** Use the template's cached feature stack,
   `evaluate_holdout.py` and `submission_writer.py`. Holdout = hide-and-recover:
   withhold whole fault segments with a buffer, derive every catalogue-based feature
   only from the visible faults, mask visible faults pixel-exactly, score pooled DTI
   (alpha 0.2, beta 0.8, 300 m triangular kernel). If a shared tool is wrong, fix it
   once in the template and report it; never keep a private fork.
3. **LABEL EVERY NUMBER** as HOLDOUT-DTI (evaluator version, number of withheld
   positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt).
   A projection is never written as a score.
4. **LEAKAGE CANARY.** Test each feature alone on the holdout before trusting any
   result. AUC above 0.90 means leakage until proven otherwise.
5. **RUN CARD.** End with one JSON card: hypothesis; mechanism; the named non-fault
   process that could mimic it; holdout DTI + CI; correlation/overlap vs registry;
   raster sha256; validator output (no NaN inside the footprint, values in [0,1],
   CRS/shape/transform match); submission name + note of at most 140 characters;
   verdict promote / negative. Negative results are deliverables.
6. **BUDGET.** Stop after 3 experiments or 2 hours. Do not pick submissions:
   promotion to a real slot is a separate selector step, within the weekly cap shown
   on the submission page.

## Questions to answer

* Study the highest family score — GEMSDOE32
  `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778`
  (<https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html>).
  Why and how did it get the highest score, and can we generate a submission that
  scores higher? Answer with PhD-level judgement, then use the answer to generate a
  unique TIF unlike any on the GEMSDOE sites. Verify line by line, no hallucinations.
* Before implementing, generate 3–5 untried geological hypotheses, each naming the
  layer(s), the physical signature, why it should catch a fault missing from the
  USGS/INGENIOUS catalogue, and how it differs from anything already implemented.
  Rank by expected DTI improvement and cost. Validate the top candidate on the
  spatially-blocked holdout before touching a weekly slot. If a candidate needs new
  external data, name the free official source and check it is obtainable.
* Do deep research on the scientific discovery of geothermal systems, store the
  knowledge from official sources, be contrarian but grounded.
* The site must make the downloadable TIF obvious (executive summary at the very top),
  with a unique name and a short note (e.g. "clustering with k=25"); an executive
  summary subpage must explain exactly how to submit. A previous download failed
  with "Predicted values must be in range [0, 1]" — every file must be all-finite and
  in [0, 1].
* Submission page text: "You can submit a single-band GeoTIFF (.tif) file, or a .zip
  file containing a single GeoTIFF, with your predictions. It must match the
  submission format's CRS, shape, and geotransform."
* Core values: **Maximize P(Win)** and **Own the Outcome**.
* Multi-pass: implement + verify; review for bugs/assumptions/edge cases; re-check
  against the request. Then open a PR, merge it to main, and list remaining work and
  limitations.

## Family results supplied by the owner (OWNER-REPORTED live scores)

The complete table (103 scored rows, GEMSDOE … GEMSDOE77) is machine-readable in
[`registry/live_scores.csv`](registry/live_scores.csv); rows for GEMSDOE78–88 were
listed without scores. Key rows: GEMSDOE32 h33-2-b2 0.2778 · GEMSDOE36 Anderson PINN
0.2750 · GEMSDOE28 h36-1 0.2710 / h27-4 0.2708 · GEMSDOE25 d2.8 0.2600 ·
GEMSDOE70 0.2478 · GEMSDOE24 d1.5 0.2477.

## Official links

* Competition: <https://www.drivendata.org/competitions/306/competition-doe-gems/>
* Problem description (metric): <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
* About: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/>
* Data (login): <https://www.drivendata.org/competitions/306/competition-doe-gems/data/>
* Leaderboard: <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>
* Rules PDF: <https://docs.nlr.gov/docs/fy26osti/96647.pdf>
* Reference solution: <https://github.com/drivendataorg/gems-prize-reference-solution>
* GeoDAWN surveys: <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>
* INGENIOUS: <https://gbcge.org/current-projects/ingenious/> · GDR 1391: <https://gdr.openei.org/submissions/1391>
* EPSG:32611: <https://epsg.io/32611> · Tversky index: <https://en.wikipedia.org/wiki/Tversky_index>
