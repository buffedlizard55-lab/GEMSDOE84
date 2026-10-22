# What the H33 result does—and does not—establish

## Evidence chain

Inspected primary project artifacts: [original audit](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json), [candidate implementation](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/src/gems32/h33.py), [validation implementation](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/scripts/run_h33_validation.py). Local archived copies of the audit and earlier experiment receipts are under `evidence/`. These are owner project artifacts, not organizer receipts.

The user's reported H33 result is **0.2778, UNVERIFIED USER-REPORTED**, not ORGANIZER-CONFIRMED. The supplied leaderboard values **0.3195 and 0.4413 are conflicting, UNVERIFIED USER-REPORTED snapshots**. No current maximum can be established from this environment. They must not be used as holdout promotion thresholds.

## Verified construction versus causal explanation

The audit describes H33-2-B2 as deleting dots within two pixels of the mapped catalogue from an existing sparse baseline. Its TIFF has a declared finite zero-outside policy and no mapped-fault positives. This is a **placement/pruning intervention**, not evidence that a new geological sensor discovered more faults. We do not copy that TIFF to construct the new candidate.

The plausible reason pruning can help is reduced false-positive mass for a small loss of unique new-fault coverage. Let T be weighted truth coverage, F weighted false-positive mass, and N the count of hidden truth pixels. With beta b and alpha a, D = (1-b)T + aF + bN, score s=T/D. Removing a set losing coverage L and false-positive mass Q improves the score precisely when:

`(T-L)/(D-(1-b)L-aQ) > T/D`

or, for positive denominators,

`L / Q < a*s / (1-(1-b)*s)`.

This is a conditional algebraic explanation. It is **not** a measurement of L or Q on the private competition labels. Near mapped traces, known pixels themselves are excluded from new-fault scoring, and nearby sparse dots can have redundant kernels. However, proximity alone does not prove a point is a false positive: an unmapped splay can be adjacent to a mapped trace. A paired ablation under the organizer's actual hidden labels would be needed to establish the causal mechanism.

## Why the old validation is not a promotion certificate

The original H33 audit embeds a projected leaderboard number under `predicted_leaderboard_dti` and a `SLOT_ELIGIBLE` flag. Neither is an organizer result. Its declared aggregate catalogue-hidden value does not equal an ordinary average of the four per-quadrant values printed alongside it; those may refer to different estimands, but the artifact does not establish equivalence. Its note exceeds the current short-note policy. No evaluator version, common positive count and paired confidence interval accompany all those fields. Do not reuse those numbers as the current comparable holdout best.

The accompanying zero-mode TIFF and ZIP are independent files. Actual ZIP inspection found one **empty entry named with a `.zip` suffix**, not a TIFF. It is not a valid single-TIFF submission package; see `evidence/h33-zip-inspection.json`. Do not download that historical ZIP to submit. This does not establish that the separately stored historical TIFF is invalid. The shared writer used here verifies single-TIFF ZIP contents by byte roundtrip.

## Can we beat the reported H33 result?

It is possible in principle, but not established by historical scores, plausible physics, or a projection. The defensible sequence is independent physical features, leakage tests, spatially buffered whole-fault recovery, paired comparisons against the reproduced best on identical folds, registry checks, and an all-finite export. Only a real organizer receipt would establish an improved leaderboard result. We do not promise a higher score.

The new lane asks whether opposing *normalized* K/Th curvature flanks co-located with a coherent terrain step identify structure missed by catalogue geometry. This tests a new feature construction instead of simply deleting or adding dots to the H33 submission. Lithologic contacts, alluvial sorting, paleoshorelines and filtering artifacts can mimic the signature. The hypothesis can therefore fail usefully; no mechanism is asserted as established geothermal physics.
