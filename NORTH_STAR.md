# North Star — read this at the start of every session on this repo

**Honesty note (so this file is never mistaken for something it isn't):** the project owner's
original instructions for this repo were given as a very long, multi-part, repeated prompt.
By the time this file was written, that original raw text was no longer available to the
agent — only a condensed internal session summary of it was. What follows is a careful,
point-by-point reconstruction from that summary, organized to preserve every binding
requirement, including the two named Arena Core Values. It is **not** a verbatim transcript
of the original prompt, and no future session should treat it as one or re-publish it as
"verbatim" without first checking it against the actual original text if that ever becomes
available again. Treat it as the standing, binding instructions for this repo — equivalent in
force to the original — until a human explicitly supersedes it or supplies the true original
text.

## Core Values (Arena)

**Maximize P(Win).** "Maximize the Probability of Winning" is our decision-making framework.
In every decision we weigh tradeoffs, assess risk, and choose the path that maximizes the
probability that we win this prize. We set aside our emotions and make tough decisions in
order to maximize P(Win). It frees us from constraints and clarifies that we must put the
outcome first.

**Own the Outcome.** We own results end to end — not just our individual slice of the work.
When problems arise and we have the means to act, we act without waiting for permission or
assignment. We treat failure and success as signals and use them to improve. We stay
accountable to the final outcome.

## The parallel-run protocol (binding on every experiment run in this repo)

1. **LANE.** Stay inside a single method paragraph per session. If a raster's rank
   correlation with any registry raster exceeds 0.90, or more than 70% of its dots fall
   within 3 px of one registry raster's dots, that is a duplicate lane: log it and stop.
   Check this on the surface before placement AND on the final dots.
2. **REUSE, DON'T REBUILD.** Use the template's cached feature stack, `evaluate_holdout.py`
   and `submission_writer.py`. Holdout = hide-and-recover: withhold whole fault segments
   with a buffer, derive every catalogue-based feature only from the visible faults, mask
   visible faults pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular
   kernel). If a shared tool is wrong, fix it once in the template and report it; never keep
   a private fork.
3. **LABEL EVERY NUMBER** as HOLDOUT-DTI (evaluator version, number of withheld positives,
   95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is
   never written as a score.
4. **LEAKAGE CANARY.** Test each feature alone on the holdout before trusting any result.
   AUC above 0.90 means leakage until proven otherwise.
5. **RUN CARD.** End with one JSON card: hypothesis; mechanism; the named non-fault process
   that could mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256;
   validator output (no NaN inside the footprint, values in [0,1], CRS/shape/transform
   match); submission name + note of at most 140 characters; verdict promote / negative.
   Negative results are deliverables.
6. **BUDGET.** Stop after 3 experiments or 2 hours. Do not pick submissions: promotion to a
   real slot is a separate selector step, within the weekly cap shown on the submission
   page.

## The mission

Place top of the leaderboard for the DOE GEMS Prize (DrivenData competition #306) by
generating a UNIQUE, validated, obviously-submittable GeoTIFF — never a copy of a prior
submission except for learning. Every number must be labelled with its evidence class.
Research must be autonomous, reproducible, grounded in official/free sources with links
provided for manual review, and free of hallucination. Irregularities must be flagged, not
hidden. Negative results must be reported, not suppressed.

The site must make the download-and-submit path obvious from the first screen: a one-click
GeoTIFF download and an executive summary that explains, step by step, how to submit it to
<https://www.drivendata.org/competitions/306/competition-doe-gems/>.

See `README.md` for the current state of the project, `registry/run_card.json` for the
latest scored run card, and `docs/research/` for the hypothesis ledger.
