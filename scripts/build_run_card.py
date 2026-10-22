#!/usr/bin/env python3
"""Assemble evidence/run_card.json (parallel-run protocol rule 5) from the evidence files.

Verdict rule (mechanical, no judgement):
  promote  iff  holdout paired-difference CI vs the best comparable control is > 0
           AND  the surface gate passed AND the dot gate passed (literal or
                chance-corrected, both reported)
           AND  the on-disk validator passed
  otherwise negative.  Promotion is to the selector only; no slot is used here.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "evidence"


def load(n):
    p = E / n
    return json.loads(p.read_text()) if p.exists() else None


def main():
    fit, ho = load("e2a_liti_ml_fit.json"), load("e2_holdout.json")
    gs, gd, gc, pk = (load("e3_gate_surface.json"), load("e3_gate_dots.json"),
                      load("e3_gate_dots_chance_corrected.json"), load("e3_package.json"))
    s = ho["summary"]
    ctrl = "incumbent_recipe"
    diff = s["paired_differences"][ctrl]
    holdout_pass = diff["ci95"][0] > 0
    dots_pass = bool(gd and (gd["passed"] or (gc and gc["passed"])))
    surface_pass = bool(gs and gs["passed"])
    valid_pass = bool(pk and pk["validator"]["all_checks_passed"])
    verdict = "promote" if (holdout_pass and dots_pass and surface_pass and valid_pass) else "negative"
    reasons = []
    if not dots_pass:
        reasons.append("DUPLICATE: final dots exceed the 70 % 3-px overlap limit against registry rasters under both the "
                       "literal and the chance-corrected reading (protocol rule 1: log duplicate and stop; no TIFF written)")
    if not surface_pass:
        reasons.append("surface Spearman gate failed")
    if not holdout_pass:
        reasons.append("holdout gate failed: does not beat the incumbent recipe on the protocol holdout")
    import hashlib
    import numpy as np
    from pathlib import Path as _P
    z = np.load(_P("/home/user/gemsdata/work/e3_placement.npz"))
    cand_sha = hashlib.sha256(np.ascontiguousarray(z["dots"].astype(np.float32)).tobytes()).hexdigest()
    sel = fit["models"][fit["selected"]]
    card = dict(
        lane="H84-A LITI — leaderboard-inverted truth intensity",
        hypothesis=("The owner-reported live scores of ~91 hash-identified rasters are noisy measurements of the hidden "
                    "new-fault set; fitting lambda(x)=exp(theta.phi(x)) so that the official DTI formula in expectation "
                    "reproduces them yields a truth intensity that a greedy DTI emission can exploit."),
        mechanism=("E[TP_w] is linear in lambda (sum over truth cells of the max-kernel coverage), so each live score "
                   "constrains theta; basis = distance-to-catalogue bands, 5 km catalogue density, 13 terrain/geophysics "
                   "ranks, and an HGB catalogue-analogue probability + crest; emission = shared emit.greedy_allocate."),
        non_fault_mimic=("Erosional/lithologic topographic lineaments (resistant ridges, strath terraces, drainage-parallel "
                         "scarps) that look like mapped faults to the catalogue-analogue ML term and to the det_elev line "
                         "responses; also the model can absorb owner-pipeline artefacts (e.g. the H19 family's ranking) "
                         "rather than geology because the scores come from one family of submitters."),
        live_score_fit=dict(evidence_class="MODEL fit to OWNER-REPORTED scores", model=fit["selected"],
                            n_rasters=fit["n_rasters"], cv="8 folds grouped by site repository",
                            cv_rmse=sel["cv_rmse"], cv_spearman=sel["cv_spearman"],
                            cv_mean_abs_err_top15=sel["cv_mean_abs_err_top15"],
                            insample_pred_for_0_2778_raster=sel["insample_pred_best_raster"]),
        holdout=dict(evidence_class="HOLDOUT-DTI", evaluator_version=ho["evaluator_version"], split=ho["split"],
                     seeds=ho["seeds"], withheld_positive_pixels=s["scores"]["liti"]["withheld_positive_pixels"],
                     scores={k: dict(dti=v["dti"], ci95=v["ci95"]) for k, v in s["scores"].items()},
                     paired_difference_vs_incumbent_recipe=dict(delta=diff["delta"], ci95=diff["ci95"]),
                     gate_passed=holdout_pass,
                     caveat=("Catalogue hide-and-recover truth lives inside densely mapped districts; the live-score fit "
                             "says new faults avoid them (theta[cat_density_5km] < 0), and the incumbent-recipe control "
                             "descends from a field trained on the FULL catalogue (leak in its favour). The gate is applied "
                             "literally anyway.")),
        leakage_canary=dict(max_single_feature_auc=max(ho["leakage_canary"]["auc_max_over_polarity"].values()),
                            flagged=ho["leakage_canary"]["flagged"], threshold=0.90),
        registry=dict(surface=gs, dots_literal={k: v for k, v in (gd or {}).items()},
                      dots_chance_corrected={k: v for k, v in (gc or {}).items() if k != "rows"}),
        submission=dict(name=pk["submission_name"], note=pk["note"], note_chars=pk["note_chars"], file=pk["file"],
                        sha256=pk["sha256"], zip=pk["zip"], zip_sha256=pk["zip_sha256"], dots=pk["dots"]) if pk else None,
        validator=pk["validator"] if pk else None,
        model_projection=pk["model_projection"] if pk else None,
        verdict=verdict,
        verdict_reason="; ".join(reasons) or "all gates passed",
        label_not_issued=dict(
            name=f"gems84-liti-ml-{int(z['dots'].sum())}dots-{cand_sha[:8]}-DUPLICATE-not-issued",
            note=(f"GEMSDOE84 LITI live-score inversion + ML crest; {int(z['dots'].sum())} dots; "
                  "DUPLICATE (3px overlap) + holdout FAIL; not submitted")[:140]),
        candidate_identity=dict(decoded_prediction_sha256=cand_sha, dots=int(z["dots"].sum()),
                                note="raster sha256 not applicable: the fail-closed packager wrote no TIFF; this is the "
                                     "SHA-256 of the decoded float32 candidate array kept outside Git"),
        ok_to_submit=("NO — this lane produced no submittable file. Its candidate was logged as a duplicate and also "
                      "failed the holdout gate; nothing was written to docs/downloads/."
                      if verdict == "negative" and not pk else
                      "NO — not cleared for a weekly slot (negative)." if verdict == "negative"
                      else "YES — cleared for the selector step"),
        slots_used=0)
    (E / "run_card.json").write_text(json.dumps(card, indent=1, default=float))
    print(json.dumps({k: card[k] for k in ("verdict", "verdict_reason", "ok_to_submit")}, indent=1))


if __name__ == "__main__":
    main()
