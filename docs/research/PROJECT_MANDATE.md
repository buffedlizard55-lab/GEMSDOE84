# Standing project mandate (condensed from the supplied prompt)

This is an operational digest, not a verbatim transcript. Consult the original conversation for the full wording.

- Aim for a genuinely new, scientifically grounded GEMS fault-discovery prediction, not a copied scored submission. Geothermal discovery motivates the work; vent locations are not interchangeable with the competition's fault target.
- Make a valid single-band GeoTIFF easy to download at the beginning of the site, but only when automated gates have passed. Make it unmistakable when downloading/submitting is unsafe.
- Read the entire project context each session. Work autonomously; do not invent facts or ask for credentials. Own the outcome and maximize probability of winning through defensible evidence.
- Work in one assigned method lane. Check full registry surface rank correlation and dot proximity before placement and on final output. Stop and log a duplicate above the specified limits.
- Reuse the shared cached feature stack, evaluate_holdout.py and submission_writer.py. Fix shared tools centrally, never keep a private fork.
- Withhold whole fault segments and their buffers; build all catalogue features from visible segments; mask visible faults pixel-exactly. Pool distance Tversky with alpha 0.2, beta 0.8 and a triangular 300 m kernel.
- Test features individually for leakage. AUC above 0.90 is presumed leakage until resolved.
- Before implementing: propose and rank three to five geological hypotheses, naming exact layers, signature, missing-fault rationale, confounder, novelty and cost. External data must be free/official and demonstrably obtainable before being called viable.
- No score without provenance: HOLDOUT-DTI needs evaluator version, withheld positives and 95% CI; ORGANIZER-CONFIRMED needs a submission-page receipt. Forecasts are not scores. Unverified user-reported numbers are not either class.
- Stop after three experiments or two hours. Promotion requires beating the current spatial holdout best. Slot selection is separate and must respect the current verified weekly cap.
- End with a JSON card: hypothesis, mechanism, named non-fault mimic, holdout/CI, registry comparisons, raster hash, validator results, unique submission name and note of at most 140 characters, promote/negative verdict. Negative results are deliverables.
- Research the provided GEMS repositories and official reference, organize auditable sources, explain H33-2-B2, and never claim improvement without evidence. Conflicting leaderboard claims require live verification.
- Provide an executive-summary subpage with exact submission instructions and limitations. Test multiple passes, review edge cases, open and merge a PR. Record next steps.

## Irregularities to preserve

No single method paragraph was actually present in the supplied prompt. Reported leaderboard values conflict; no receipt was supplied. Initial checkout contains no claimed template pipeline. The full original prompt has not been persisted verbatim in this file.
