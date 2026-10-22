# GEMSDOE84 — auditable GEMS Prize research & submission gate

> **Current status: BLOCKED — no submission GeoTIFF is available to download or submit.**
> At initial review, this checkout contained only this README and Git metadata. There is no competition raster data, cached feature stack, holdout evaluator, submission writer, prior experiment ledger, generated raster, or validation receipt. We will not fabricate a raster, infer a score, or label an unvalidated file as submit-ready.

## Project charter (read before every project task)

### Mission
Develop a scientifically defensible, auditable system for the DOE GEMS Prize Challenge: identify likely geothermal-related faults not present in the existing catalogue; validate proposals with spatially blocked hide-and-recover evaluation; and produce a single-band GeoTIFF that is obviously safe to download only after it passes automated format and scientific gates. Maximize the probability of a meaningful competition result; own the end-to-end outcome. Negative experiments are deliverables. Never present a projection as a score.

### Non-negotiable workflow
1. **Stay in the declared experiment lane.** Reuse the shared template's cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`; fix shared defects at the source, never maintain a private fork. Do not spend a competition submission slot unless the candidate beats the current holdout best.
2. **Holdout protocol:** withhold whole fault segments with a buffer; derive catalogue-based features only from visible faults; mask visible faults pixel-exactly; score pooled DTI with alpha 0.2, beta 0.8, and the official 300 m triangular kernel. Test each feature alone as a leakage canary before trusting a combined result; AUC > 0.90 is presumed leakage until investigated.
3. **Evidence labels:** every reported score must be labeled either `HOLDOUT-DTI` (evaluator version, withheld-positive count, 95% CI) or `ORGANIZER-CONFIRMED` (transcribed from a submission receipt). Never call a projection a score. Keep public leaderboard results distinct from local holdout results.
4. **Uniqueness and drift gate:** compare a candidate surface before placement and final dots against available registry rasters. Stop and mark duplicate if raster rank-correlation exceeds 0.90 or more than 70% of candidate dots are within 3 px of one registry raster. These thresholds are parallel-run controls, not scientific measurements.
5. **Artifact gate:** the final file must match the official reference raster's CRS, bounds, shape, and transform; contain one float32 band; have finite values in [0, 1] throughout the valid footprint; and contain no invalid sentinels or NaNs inside that footprint. Reopen and independently validate the written bytes. Do not show a download action until all gates pass.
6. **Budget:** stop at three experiments or two hours, whichever comes first. Selection/promotion to a real submission slot is a separate selector action under the current weekly cap.
7. **Research:** use official, freely available sources where possible; record links, retrieval dates, license/terms, claims supported, and limitations. Do not claim broader novelty than can be established from this checkout and the cited record.

### Persistent brief
Study the competition task, official rules/data, reference solution, relevant USGS/INGENIOUS sources, and prior local experiment records. Produce and rank 3–5 distinct hypotheses before implementation, naming the feature layers, physical signature, reason it may identify an uncatalogued fault, and differences from this repository. If an external dataset is essential, name the specific official source and verify availability and license first. Validate the leading hypothesis on the blocked holdout before considering a weekly slot. Keep the site readable, current, and auditable, with a prominent executive summary and a clearly downloadable TIF only when it is genuinely validated. Report limitations and irregularities plainly. Run multiple review passes and finish with a JSON run card.

## What is actually verified in this checkout

- The checkout was inspected at the current branch head: the only tracked project file was this README. No raster data, source code, experiment results, or generated submission existed.
- The official DrivenData problem page describes fault mapping, a distance-weighted Tversky index, and GeoTIFF constraints (EPSG:32611, 100 m, matching reference bounds, one float32 layer, confidence values in [0, 1]). Links are listed below.
- The competition data URL resolves to a DrivenData login page in this environment. No authenticated competition download is available to this session.
- Consequently, there is no holdout score, confidence interval, validated TIF, or organizer receipt. The site deliberately has no download link.

## Immediate blockers and safe next steps

1. Place the competition-provided `training_features.tif`, labels, and `sample_submission.tif` in the template's expected data location via an authorized DrivenData session. The data page is login-protected; this agent has no competition account session.
2. Obtain the shared template that contains the cached feature stack plus `evaluate_holdout.py` and `submission_writer.py`. They are **not present** in this repository. Do not recreate them here.
3. Run the shared pipeline, record the evaluator/version, folds, withheld positives, confidence interval, canary results, and registry comparisons. If the candidate does not beat the incumbent holdout best, do not generate/promote a submission.
4. Generate through the shared writer, validate the final file against the exact official sample/reference and footprint, record SHA-256, and then publish the download link with the submission name and a <=140-character note.

## Official links for review

- [DrivenData problem description and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData competition data page (login required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [DrivenData rules](https://www.drivendata.org/competitions/306/competition-doe-gems/rules/)
- [DrivenData public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) (DOI [10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ); USGS page states CC0 1.0 for the release)
- [INGENIOUS project](https://gbcge.org/current-projects/ingenious/)
- [EPSG:32611](https://epsg.io/32611)
- [GEMS technical report PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

## Local checks

```bash
python scripts/check_readiness.py --json
python -m pip install -r requirements-validation.txt
python scripts/validate_submission.py candidate.tif --reference data/sample_submission.tif --json
python -m unittest discover -s tests -v
```

The readiness command exits non-zero while required files/tools are missing. The GeoTIFF validator is a strict format/range audit only: it does not score science, establish uniqueness, or replace the shared submission writer or organizer validation. Use the reference raster for the exact grid; provide `--footprint data/training_features.tif` if its dataset mask is the intended valid-footprint mask. This checkout's tests use synthetic rasters only and do not constitute a competition submission.

## Site
The GitHub Pages-ready site is in [`docs/`](docs/). Start at [`docs/index.html`](docs/index.html); the executive summary is [`docs/executive-summary.html`](docs/executive-summary.html). Its submission panel intentionally states that no download is available until the required data and shared evaluator/writer exist. The machine-readable current status is [`docs/run-card.json`](docs/run-card.json).
