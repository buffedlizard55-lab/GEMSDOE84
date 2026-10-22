#!/usr/bin/env python3
"""E3 -- live LITI emission, uniqueness gates, fail-closed packaging, run card.

Stages (run in this order; ``surface`` and ``dots`` may run in parallel):
  place    lambda from the E2a-selected theta (catalogue features from the FULL
           catalogue, ML columns trained on the full catalogue) and the shared
           template's greedy_allocate dots -> $GEMS84_DATA/work/e3_placement.npz
  surface  Spearman(lambda, each of the 1,143 registry rasters) <= 0.90
  dots     template uniqueness.compare_array_to_registry on the final dots
           (Spearman <= 0.90 AND <= 70 % of dots within 3 px of any one raster)
  package  only if BOTH gates passed: submission_writer.write_submission (validates
           in memory, on disk and as a one-TIFF ZIP), model projections, run card.
If a gate fails the session logs a duplicate and stops (no TIFF is produced).
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]; sys.path.insert(0, str(ROOT / "scripts"))
from gems57 import emit, uniqueness  # noqa: E402
from gems57.grid import load_grid  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems57.validate import validate  # noqa: E402
from gems84 import basis, liti  # noqa: E402
from gems84.paths import BRIDGE, WORK  # noqa: E402

INCUMBENT = Path("/home/user/ref/60GEMSDOE/registry/rasters/GEMSDOE32__h33-2-b2-zeros.tif")


def _design_full(fp, cat, cols):
    X, names, oncat = basis.full_basis(fp, cat)
    X = np.concatenate([X, np.load(WORK / "ml_cols_live.npy")], axis=1)   # ml_prob, ml_ridge (E2a)
    return X, oncat


def place():
    t0 = time.time()
    g = load_grid(BRIDGE); fp, cat = g.footprint, g.catalogue
    sel = np.load(WORK / "liti_ml_selected.npz")
    theta, cols = sel["theta"], [int(c) for c in sel["cols"]]
    X, oncat = _design_full(fp, cat, cols)
    lam_fp = liti.full_lambda(theta, X[:, np.asarray(cols[1:]) - 1], ~oncat)
    del X
    lam = np.zeros(fp.shape, np.float32); lam[fp] = lam_fp
    G = float(lam.sum())
    alloc = emit.greedy_allocate(np.clip(lam, 0, 1), fp & ~cat, G)
    dots = alloc.emitted & fp & ~cat
    np.savez_compressed(WORK / "e3_placement.npz", lam=lam, dots=dots, G=G,
                        surrogate_dti=alloc.surrogate_dti, rounds=alloc.rounds)
    print(dict(G_model=round(G), dots=int(dots.sum()), surrogate_dti_model=round(alloc.surrogate_dti, 4),
               seconds=round(time.time() - t0, 1)))


def gate(kind):
    t0 = time.time()
    g = load_grid(BRIDGE); fp = g.footprint
    z = np.load(WORK / "e3_placement.npz")
    index = json.loads((ROOT / "registry/registry_index.json").read_text())
    if kind == "surface":
        lam = z["lam"]
        rep = uniqueness.compare_array_to_registry((lam / lam.max()).astype(np.float32), index, fp,
                                                   include_reverse=False)
        rows = [r for r in rep["rows"] if "error" not in r]
        worst = max(rows, key=lambda r: r["spearman_full_footprint"] or -1)
        res = dict(gate="surface", reading="Spearman only (a whole-footprint surface trivially overlaps everything)",
                   worst_spearman=worst["spearman_full_footprint"], worst_submission=worst["submission"],
                   checked=len(rows), errors=len(rep["rows"]) - len(rows), limit=uniqueness.RHO_LIMIT,
                   passed=bool(worst["spearman_full_footprint"] <= uniqueness.RHO_LIMIT
                               and len(rows) == len(rep["rows"])))
    else:
        rep = uniqueness.compare_array_to_registry(z["dots"].astype(np.float32), index, fp)
        res = dict(gate="dots", **{k: rep[k] for k in (
            "unique", "worst_dot_overlap", "worst_overlap_submission", "worst_spearman_full_footprint",
            "worst_rho_submission", "worst_jaccard_dot_sets", "worst_jaccard_submission",
            "registry_rasters_checked", "registry_rasters_expected", "complete_accessible_scan",
            "duplicate_count", "missing_or_invalid", "verdict")},
            rho_limit=uniqueness.RHO_LIMIT, overlap_limit=uniqueness.OVERLAP_LIMIT, passed=bool(rep["unique"]))
        keep = ("repo", "submission", "file", "sha256", "their_dots", "my_dots_within_3px_of_theirs",
                "their_dots_within_3px_of_mine", "spearman_full_footprint", "jaccard_dot_sets",
                "duplicate_by_rho", "duplicate_by_overlap", "identical_decoded_predictions", "error")
        (ROOT / "evidence/e3_gate_dots_rows.json").write_text(json.dumps(
            [{k: r[k] for k in keep if k in r} for r in rep["rows"]], indent=0, default=float))
    res["seconds"] = round(time.time() - t0, 1)
    (ROOT / f"evidence/e3_gate_{kind}.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res, indent=1, default=float))


def package():
    t0 = time.time()
    gs = json.loads((ROOT / "evidence/e3_gate_surface.json").read_text())
    gd = json.loads((ROOT / "evidence/e3_gate_dots.json").read_text())
    cc_path = ROOT / "evidence/e3_gate_dots_chance_corrected.json"
    gc = json.loads(cc_path.read_text()) if cc_path.exists() else {"passed": False}
    dots_ok = gd["passed"] or gc["passed"]   # literal, or chance-corrected (IR-84-03); both recorded
    if not (gs["passed"] and dots_ok):
        (ROOT / "evidence/e3_duplicate_stop.json").write_text(json.dumps(dict(surface=gs, dots=gd, chance=gc), indent=1))
        raise SystemExit("uniqueness gate failed -> logged as duplicate; stopping without a TIFF")
    g = load_grid(BRIDGE); fp, cat = g.footprint, g.catalogue
    z = np.load(WORK / "e3_placement.npz")
    dots = z["dots"]; pred = dots.astype(np.float32)
    sel = np.load(WORK / "liti_ml_selected.npz")
    theta, cols = sel["theta"], [int(c) for c in sel["cols"]]
    # model projections on the exact E1/E2a Monte-Carlo sample
    from e1_liti_fit import N_SAMPLE, SEED
    X, oncat = _design_full(fp, cat, cols)
    nfp = int(fp.sum())
    samp = np.sort(np.random.default_rng(SEED).choice(nfp, N_SAMPLE, replace=False))
    fy, fx = np.nonzero(fp); ys, xs = fy[samp], fx[samp]
    Phi = np.concatenate([np.ones((N_SAMPLE, 1), np.float32), X[samp].astype(np.float32)], axis=1)[:, cols]
    del X
    support = ~oncat[samp]; w = nfp / N_SAMPLE

    def project(a):
        c, m = liti.coverage_at(a.astype(np.float32), ys, xs)
        des = liti.Design(Phi=Phi, support=support, C=c[None], Mm=m[None],
                          S=np.array([float(a.sum())]), w=w, names=[])
        return float(liti.predict(theta, float(sel["eta_logit"]), des)[0][0])

    with rasterio.open(INCUMBENT) as s:
        inc = s.read(1)
    inc = np.where(np.isfinite(inc) & fp, inc, 0).astype(np.float32)
    proj_cand, proj_inc = project(pred), project(inc)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dsha = hashlib.sha256(np.ascontiguousarray(pred).tobytes()).hexdigest()[:8]
    n = int(dots.sum())
    name = f"gems84-liti-ml-{n}dots-{ts}-{dsha}-zeros"
    nr = json.loads((ROOT / "evidence/e2a_liti_ml_fit.json").read_text())["n_rasters"]
    note = f"GEMSDOE84 LITI: truth intensity inverted from {nr} live-scored rasters + ML crest; greedy DTI dots; holdout gate FAILED"
    assert len(note) <= 140, len(note)
    out_dir = ROOT / "docs/downloads"
    tif = out_dir / f"{name}.tif"
    receipt = write_submission(tif, pred, BRIDGE / "sample_submission.tif", fp, note=note, name=name,
                               catalogue=cat, metadata=dict(lane="LITI (H84-A)", model_projection=proj_cand))
    val = validate(tif, fp, cat)
    res = dict(submission_name=name, note=note, note_chars=len(note), file=tif.name,
               sha256=receipt["sha256"], bytes=receipt["bytes"], zip=receipt["zip_file"],
               zip_sha256=receipt["zip_sha256"], dots=n,
               validator=dict(all_checks_passed=val["all_checks_passed"], checks=val["checks"],
                              n_nan=val["n_nan"], min=val["min"], max=val["max"], meta=val["meta"],
                              on_catalogue_positive_pixels=val.get("on_catalogue_positive_pixels")),
               model_projection=dict(evidence_class="MODEL-PROJECTION (never a score)",
                                     candidate=proj_cand, incumbent_h33_2_b2=proj_inc,
                                     incumbent_owner_reported_live=0.2778,
                                     surrogate_dti_of_greedy=float(z["surrogate_dti"])),
               seconds=round(time.time() - t0, 1))
    (ROOT / "evidence/e3_package.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "place"
    {"place": place, "surface": lambda: gate("surface"), "dots": lambda: gate("dots"),
     "package": package}[stage]()
