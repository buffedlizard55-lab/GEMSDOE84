# Historical session brief — not an authenticated transcript

Superseded as current status. The prior README called this verbatim; it differs from the current user request. Quoted scores/caps are user/prior-agent statements, not organizer receipts.

## Prior recorded brief

```text
Review our Repo. Look at it. Look at our previous research and sites on the competition:
buffedlizard55-lab/1GEMSDOE
buffedlizard55-lab/GEMSDOE2
buffedlizard55-lab/GEMSDOE3
buffedlizard55-lab/GEMSDOE4
buffedlizard55-lab/5GEMSDOE
buffedlizard55-lab/6GEMSDOE
buffedlizard55-lab/7GEMSDOE
buffedlizard55-lab/8GEMSDOE
buffedlizard55-lab/GEMSDOE9
buffedlizard55-lab/GEMSDOE10
buffedlizard55-lab/GEMSDOE11
buffedlizard55-lab/GEMSDOE12
buffedlizard55-lab/13GEMS
buffedlizard55-lab/GEMSDOE14
buffedlizard55-lab/GEMSDOE15
buffedlizard55-lab/GEMSDOE16
buffedlizard55-lab/GEMSDOE17
buffedlizard55-lab/GEMSDOE18
buffedlizard55-lab/GEMSDOE19
buffedlizard55-lab/GEMSDOE20
buffedlizard55-lab/GEMSDOE21
buffedlizard55-lab/GEMSDOE22
buffedlizard55-lab/GEMSDOE23
buffedlizard55-lab/GEMSDOE24
buffedlizard55-lab/GEMSDOE25
buffedlizard55-lab/GEMSDOE26
buffedlizard55-lab/GEMSDOE27
buffedlizard55-lab/GEMSDOE28
buffedlizard55-lab/29GEMSDOE
buffedlizard55-lab/30GEMSDOE
buffedlizard55-lab/GEMSDOE31
buffedlizard55-lab/GEMSDOE32
buffedlizard55-lab/GEMSDOE33
buffedlizard55-lab/GEMSDOE34
buffedlizard55-lab/GEMSDOE35
buffedlizard55-lab/GEMSDOE36
buffedlizard55-lab/37GEMSDOE
buffedlizard55-lab/38GEMSDOE
buffedlizard55-lab/39GEMSDOE
buffedlizard55-lab/40GEMSDOE
buffedlizard55-lab/41GEMSDOE
buffedlizard55-lab/42GEMSDOE
buffedlizard55-lab/43GEMSDOE
buffedlizard55-lab/44GEMSDOE
buffedlizard55-lab/45GEMSDOE
buffedlizard55-lab/46GEMSDOE
buffedlizard55-lab/47GEMSDOE
buffedlizard55-lab/48GEMSDOE
buffedlizard55-lab/49GEMSDOE
buffedlizard55-lab/50GEMSDOE
buffedlizard55-lab/51GEMSDOE
buffedlizard55-lab/52GEMSDOE
buffedlizard55-lab/53GEMSDOE
buffedlizard55-lab/54GEMSDOE
buffedlizard55-lab/55GEMSDOE
buffedlizard55-lab/56GEMSDOE
buffedlizard55-lab/57GEMSDOE
buffedlizard55-lab/58GEMSDOE
buffedlizard55-lab/59GEMSDOE
buffedlizard55-lab/60GEMSDOE
buffedlizard55-lab/GEMSDOE61
buffedlizard55-lab/GEMSDOE62
buffedlizard55-lab/GEMSDOE63
buffedlizard55-lab/GEMSDOE64
buffedlizard55-lab/GEMSDOE65
buffedlizard55-lab/GEMSDOE66
buffedlizard55-lab/GEMSDOE67
buffedlizard55-lab/GEMSDOE68
buffedlizard55-lab/GEMSDOE69
buffedlizard55-lab/GEMSDOE70
buffedlizard55-lab/GEMSDOE71
buffedlizard55-lab/GEMSDOE72
buffedlizard55-lab/GEMSDOE73
buffedlizard55-lab/GEMSDOE74
buffedlizard55-lab/GEMSDOE75
buffedlizard55-lab/GEMSDOE76
buffedlizard55-lab/GEMSDOE77
buffedlizard55-lab/GEMSDOE78
buffedlizard55-lab/GEMSDOE79
buffedlizard55-lab/GEMSDOE80
buffedlizard55-lab/GEMSDOE81
buffedlizard55-lab/GEMSDOE82
buffedlizard55-lab/GEMSDOE83
buffedlizard55-lab/GEMSDOE84
buffedlizard55-lab/GEMSDOE85
buffedlizard55-lab/GEMSDOE86
buffedlizard55-lab/GEMSDOE87
buffedlizard55-lab/GEMSDOE88

Look at why  h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros from GEMSDOE32 had 0.2778 the highest confirmed score among the GEMSDOE sites. The highest on the leaderboard was .3195 and is now 0.4413 (etiennedufayet). Study, analyze and explain why at a PHD level and how we can score higher.


Think of 3–5 new candidate geological hypotheses we haven't tried yet. For each: which layers it involves, what physical signature it targets, why it should catch faults missing from the USGS/INGENIOUS catalogue rather than faults already in it, and how it differs from our previous implementations. Rank them by expected DTI improvement and implementation cost.


Reuse the template's cached feature stack, evaluate_holdout.py, and submission_writer.py; do not rebuild the data pipeline or metric from scratch. Holdout = hide-and-recover (withhold whole fault segments with a buffer, derive any catalogue-based features only from visible faults, mask visible faults pixel-exactly, score pooled DTI with alpha=0.2, beta=0.8, 300 m triangular kernel). Label every number HOLDOUT-DTI (with evaluator version, number of withheld positives, and 95% CI) or ORGANIZER-CONFIRMED. Never write a projection as a score.
Before testing your hypothesis, run a leakage canary: test each of your features alone on the holdout; any single feature with holdout AUC > 0.90 is leakage until proven otherwise. Before emitting a GeoTIFF, check uniqueness against the registry rasters on both the continuous surface and the final dots: rank correlation must not exceed 0.90, and no more than 70% of your dots may fall within 3 px of any registry raster's dots. Stop after at most 3 experiments or 2 hours.
End with one JSON Run Card containing: hypothesis, mechanism, one named non-fault geological process that could mimic it, holdout DTI + CI, correlation/overlap vs registry, raster sha256, validator output (no NaN inside footprint, values in [0,1], CRS/shape/transform match), submission name + <=140-char note, and verdict (promote or negative).

You MUST generate a unique TIF submission for the competition. Do not copy a previous submission, except for baseline, comparison, learning etc. Make the TIF submission (and ZIP if helpful) easy to download at the very beginning/executive summary. Make sure that it is obvious on the site and executive summary whether the TIF submission is validated and OK to download and submit, without human intervention. We don't want to submit to the competition if there is an error that could be prevented. Remember an error that we have received from the competition before when submitting is "Predicted values must be in range [0, 1]". So we need to prevent this and any other errors from happening. Also give the submission a unique name and a short note (140 characters max) for the submission form on DrivenData.

Do not do the bare minimum. Try your best to analyze everything in the repo and cross-reference what is in the repo, the competition, the goal of the competition and more. Think from first principles and make sure we are heading in the right direction for what this competition wants and needs. Look into how we can maximize our score in the competition while staying true to the rules and scientific method. We have a limit of 3 submissions per week on the competition site.

PARALLEL-RUN PROTOCOL (keep this block verbatim):
1. Lane & uniqueness check: inspect registry/ or prior submissions; pick a genuinely different geological mechanism. Hard gate on BOTH the pre-placement surface AND the final emitted dots: rank-corr <= 0.90 and 3px dot overlap <= 70% against every registry raster.
2. Reuse evaluate_holdout.py and submission_writer.py from the template (hide-and-recover: withhold whole fault segments with buffer, build catalogue-derived features from visible faults only, mask visible faults pixel-exactly, pooled DTI alpha=0.2, beta=0.8, 300m triangular kernel).
3. Label every number HOLDOUT-DTI (with evaluator version, n withheld positives, 95% CI) or ORGANIZER-CONFIRMED. Never state a projected score.
4. Leakage canary: any single feature with holdout AUC > 0.90 is leakage until proven otherwise.
5. End with a JSON Run Card: hypothesis, mechanism, named non-fault mimic, holdout DTI + CI, correlation/overlap vs registry, sha256, validator output (no NaN in footprint, values in [0,1], CRS/shape/transform match), submission name + <=140-char note, verdict (promote | negative).
6. Budget cap: <= 3 experiments or 2 hours; stop and report honestly if negative.

Remember we want to get all of the data and complete the data pipeline (`scripts/download_competition_data.sh` and `scripts/prepare_data.py`) autonomously, with no manual input. Work autonomously without asking the user to do things manually. Verify everything line by line from official trusted sources and provide links for manual review. Flag any irregularities. Zero hallucinations. Make sure the GitHub pages site is user friendly, clean, and everything works, tables look good. Put the prompt in the repo README.md. Make sure you do your work in 3 passes: Pass 1: implement and verify; Pass 2: review what you did for bugs, missing requirements, and edge cases, and fix them; Pass 3: final verification check against the original request. Then create a pull request and merge it to main.
```
