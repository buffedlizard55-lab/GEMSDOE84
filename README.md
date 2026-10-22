# GEMSDOE84 — Leaderboard-Inverted Truth Intensity (LITI) lane

> **Read first, every session:** [`PROMPT.md`](PROMPT.md) is the standing brief
> (parallel-run protocol, uniqueness rules, the "obvious download" requirement, and
> the core values *Maximize P(Win)* and *Own the Outcome*). Then read
> [`evidence/run_card.json`](evidence/run_card.json) for the current state.

**Site:** https://buffedlizard55-lab.github.io/GEMSDOE84/. The front page answers
*"is it OK to submit?"* before anything else.

## Executive summary

| question | answer |
|---|---|
| Is there a TIF to submit from this lane? | **No.** The candidate (27,445 dots) passed the surface-correlation gate but was logged as a **duplicate** by the dot-overlap gate (literal and chance-corrected readings). It also **failed** the protocol holdout gate. The fail-closed packager therefore wrote **no TIFF**, so nothing can be submitted by mistake. Verdict: **negative** (`evidence/run_card.json`). |
| Why did `h33-h33-2-b2` score 0.2778? | Byte-exact lineage: the 0.2600 dotted H19-5 field minus every dot ≤ 100 m (0.2708) and then ≤ 200 m (0.2778) from a mapped fault. The metric algebra explains both steps to within 0.0006 DTI if the deleted dots earned zero credit (`evidence/incumbent_anatomy.json`). The limit is the field's precision, not its emission. |
| What is new and reusable? | A multi-basis truth intensity inverted from the whole owner-reported live-score table, using the official DTI formula in expectation. On repos held out of the fit it ranks rasters with CV Spearman 0.907 and RMSE 0.034 (score SD ≈ 0.084) (`evidence/e2a_liti_ml_fit.json`). It is a cheap pre-screen any lane can use before spending a slot. |
| Slots used | 0 |

## Reproduce (CPU only; ~45 min, mostly the two 1,143-raster uniqueness scans)

```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python scripts/fetch_data.py --registry     # pinned inputs + 1,149-blob uniqueness corpus (needs gh auth)
python scripts/build_registry_index.py      # 1,143 hash-verified grid rasters
python scripts/analyze_incumbent.py         # why 0.2778
python scripts/e1_liti_fit.py               # experiment 1: physics-only inversion
python scripts/e2_liti_ml_fit.py            # experiment 2a: + catalogue-analogue ML crest
python scripts/e2_holdout.py                # experiment 2b: protocol holdout (shared evaluator)
python scripts/e3_emit_submission.py place  # experiment 3: emission
python scripts/e3_emit_submission.py surface & python scripts/e3_emit_submission.py dots; wait
python scripts/e3_chance_corrected.py
python scripts/e3_emit_submission.py package   # fail-closed: writes a TIFF only if both gates pass
python scripts/build_run_card.py && python scripts/build_site.py
python -m pytest -q
```

`registry/live_score_matches.json` was built by `scripts/match_live_scores.py`, using
the 57GEMSDOE registry index as its second argument. Large inputs stay outside Git under
`$GEMS84_DATA` (default `/home/user/gemsdata`).

## Layout
* `src/gems57/` — shared template, **unmodified** (60GEMSDOE@`b99591e`; hashes checked by `tests/test_gems84.py`)
* `src/gems84/` — lane code: `basis.py` (basis maps), `liti.py` (inversion), `mlfield.py` (catalogue-analogue field)
* `scripts/` — experiments, gates, packaging, run card, site build
* `registry/` — live scores (OWNER-REPORTED), score↔raster links, uniqueness corpus/index, data manifest
* `evidence/` — every number shown anywhere, as JSON
* `docs/` — GitHub Pages site, research notes (`docs/research/h84-hypotheses.md`), irregularities, sources

## Limitations and next steps
See `docs/irregularities.md` and section 4 of the site's research page: a fair holdout control,
an owner ruling on the dense-raster overlap defect (IR-84-03), organizer receipts for live
scores, LITI as a prior for other lanes, and data blocked in this sandbox (ComCat, InSAR) or needing a GPU.
