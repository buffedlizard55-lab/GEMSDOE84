# Repository review — branch arena/827a9c9e-gemsdoe84

## Scope and stop decision

Read README.md, PROMPT.md, the RFD and LITI run cards, preregistered hypotheses,
shared-tool integrity pins, incumbent anatomy, site builder, independent validator,
CI and Pages workflows. No assigned single-method paragraph appears in the request.
The existing RFD lane is stopped by a literal duplicate veto. Do not start a new
lane or repeat three completed experiments to manufacture a downloadable file.
No new scientific experiment or competition upload was performed in this review.
The user's requirement for a new, cleared downloadable TIFF remains **unmet**.

## What explains H33?

`evidence/incumbent_anatomy.json` records byte-level lineage and owner-reported
scores. The inherited analysis attributes improvement to sparse placement and
removal of dots close to mapped faults, consistent with reduced false-positive
penalty without losing much weighted recovery. This is a conditional explanation,
not causal identification of the hidden truth. The reported 0.2778 is neither a
new HOLDOUT-DTI result nor ORGANIZER-CONFIRMED: no submission-page receipt exists
here. A higher leaderboard score cannot be guaranteed by this evidence. The
request's conflicting leaderboard maxima are not current verified facts.

Official reference code and its archived receipt:
- https://github.com/drivendataorg/gems-prize-reference-solution
- `evidence/official-reference-README.md`

Competition format/metric and source pointers (not freshly retrieved here):
- https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and

## Pass 1 — implementation and verification

Baseline: 31 tests passed after installing requirements into an ignored virtual
environment. Fixed the negative-run site builder: it now rejects TIFF/TIFF/ZIP
artifacts anywhere under docs, including unlinked, uppercase and nested files.
A raster hash alone never clears a download. No old TIFF was copied or renamed.
Added the same guard/render check before Pages uploads its artifact.

## Pass 2 — malformed inputs and edge cases

The compatibility audit previously boolean-indexed wrong-size predictions with
the reference footprint, raising IndexError rather than a machine-readable FAIL.
It now returns FAIL for incompatible shapes or non-real dtypes before indexing.
Every structural rejection explicitly states submission_authorized=false.
Combined finite/range flags now require both finiteness and bounds checks.
Eight regressions cover these release and validation boundaries.

## Pass 3 — request reconciliation

39 tests pass locally; build_site.py regenerates docs without differences.
Shared evaluator/writer hashes remain unchanged; no private evaluator was created.
Existing four geological hypotheses remain in docs/research/hypotheses.md; no new
hypothesis is claimed tested or novel across all sibling repositories. Prior
holdout numbers are inherited evidence, not rerun results. Historical readiness
cards are explicitly marked superseded, not new scientific outcomes.

Unresolved: whole-geological-segment buffered validation in the shared template;
reproduction of the current best on identical leakage-safe folds; complete registry
clearance; original-data authenticity; organizer receipt and current weekly cap.
Outbound access cannot retrieve DrivenData/USGS/Dropbox directly. A GPU is not a
universal requirement (the official reference supports CPU). Data placement alone
is therefore not the sole blocker. A format pass cannot establish scientific
quality, novelty or eligibility. Current automated answer: **DO NOT SUBMIT**.

Next session should coordinate an upstream evaluator correction and the dense
registry blocker with the parallel-run owner, without weakening the literal rule
locally. Only a separately assigned lane and a genuinely better, duplicate-free
holdout result should reach the selector. Keep the existing run card unchanged:
this maintenance review did not generate new scientific evidence.
