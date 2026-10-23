#!/usr/bin/env python3
"""EXP-84-3: Complete paired D2.8 Dual-Habitat holdout CI summary on cached EXP-84-2 surfaces,
emit full-catalogue H84-CSAT D2.8 c2.5 GeoTIFF via shared submission_writer.py, run independent
format/range validators, and execute the full 1,160-raster registry uniqueness audit.
"""
from __future__ import annotations

import gc
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT / "scripts")]

from gems57 import evaluate_holdout, grid as ggrid, holdout, submission_writer, uniqueness, validate as gvalidate  # noqa: E402
from gems84 import csat, paths  # noqa: E402
import validate_submission as indep_validator  # noqa: E402

SEEDS = (20, 21)
D28_SHA256 = "b00a6fb6cab70d0f957308e297695c4032ab97997a41a15ff1295add3df31a26"
B2_SHA256 = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
SAT_WITNESS_SHA256 = "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"


def rss_mb() -> float:
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return float(line.split()[1]) / 1024.0
    except OSError:
        pass
    return -1.0


def load_registry_path(sha256_hex: str, reg_idx: dict) -> Path:
    for r in reg_idx["rasters"]:
        if r["sha256"] == sha256_hex:
            return Path(r["cache_file"])
    raise FileNotFoundError(f"Registry SHA256 not found: {sha256_hex}")


def load_registry_dots(sha256_hex: str, reg_idx: dict, fp: np.ndarray) -> np.ndarray:
    p = load_registry_path(sha256_hex, reg_idx)
    with rasterio.open(p) as src:
        a = src.read(1)
    return np.isfinite(a) & (a > 0) & fp


def summarize_d28_holdout_from_cache(g: ggrid.Grid, reg_idx: dict, cache_dir: Path, exp2: dict) -> dict:
    """Compute exact paired 20 km spatial-block CIs with csat_poisson as candidate,
    including transfer_poisson and concealed_poisson on the cached EXP-84-2 LOQO surfaces.
    """
    fp = g.footprint
    d28_dots = load_registry_dots(D28_SHA256, reg_idx, fp)
    b2_dots = load_registry_dots(B2_SHA256, reg_idx, fp)

    # Reconstruct retrained_h19_control from X_phys[:, :19] or reuse per-seed cached LOQO surfaces
    X_phys, _ = csat.build_physics_features(fp, cache_path=cache_dir / "X_phys.npz")
    from exp84_2_holdout_eval import fit_retrained_h19_loqo

    arm_names = [
        "csat_poisson",
        "transfer_poisson",
        "concealed_poisson",
        "csat_submod",
        "retrained_h19_control",
        "incumbent_recipe",
        "incumbent_asis",
    ]
    terms: dict[str, list[np.ndarray]] = {k: [] for k in arm_names}
    per_quadrant: dict[str, list[float]] = {}

    for i_s, seed in enumerate(SEEDS):
        folds, quad = holdout.buffered_component_draw(g, seed=seed, hide_frac=0.20, buffer_px=3)
        vis = folds[0]["visible"]
        z = np.load(cache_dir / f"loqo_s{seed}.npz")
        csat_2d = np.zeros(fp.shape, dtype=np.float32); csat_2d[fp] = z["csat"]
        tr_2d = np.zeros(fp.shape, dtype=np.float32); tr_2d[fp] = z["transfer"]
        co_2d = np.zeros(fp.shape, dtype=np.float32); co_2d[fp] = z["concealed"]
        d1_fp = z["d1"]
        d1_2d = np.zeros(fp.shape, dtype=np.float32); d1_2d[fp] = d1_fp
        del z

        budget_s = int(exp2["seed_emissions"][i_s]["csat_alloc"]["n_dots"])
        allowed_s = fp & (~vis) & (d1_2d > 2.5)
        em_csat_p = csat.poisson_disk_dots(csat_2d, allowed_s, budget=budget_s, sep_px=2.83)
        em_tr_p = csat.poisson_disk_dots(tr_2d, allowed_s, budget=budget_s, sep_px=2.83)
        em_co_p = csat.poisson_disk_dots(co_2d, allowed_s, budget=budget_s, sep_px=2.83)
        em_csat_sub, _ = csat.allocate_submodular_dots(
            csat_2d, fp, vis, d1_2d, quad, collar_px=2.5, pi0=0.0024, max_dots=42_000
        )

        surf_h19 = fit_retrained_h19_loqo(fp, vis, quad, X_phys[:, :19], d1_fp, seed=seed)
        dvis_exact = ndi.distance_transform_edt(~vis)
        em_h19 = csat.poisson_disk_dots(surf_h19, fp & (~vis) & (dvis_exact > 2.0), budget=38_500, sep_px=2.83)

        arms = {
            "csat_poisson": em_csat_p,
            "transfer_poisson": em_tr_p,
            "concealed_poisson": em_co_p,
            "csat_submod": em_csat_sub,
            "retrained_h19_control": em_h19,
            "incumbent_recipe": d28_dots & (dvis_exact > 2.0) & (~vis),
            "incumbent_asis": b2_dots.copy(),
        }
        for f in folds:
            for k, pred in arms.items():
                res, t_arr = evaluate_holdout.evaluate(pred.astype(np.float32), f, fp, block_side=200)
                terms[k].append(t_arr)
                if k == "csat_poisson":
                    per_quadrant.setdefault(f["name"], []).append(float(res["dti"]))

        del csat_2d, tr_2d, co_2d, d1_fp, d1_2d, surf_h19, dvis_exact, arms, folds
        gc.collect()

    del X_phys
    gc.collect()
    stacked = {k: np.sum(np.stack(v), axis=0) for k, v in terms.items()}
    summary = evaluate_holdout.pooled_summary(stacked, draws=1000, seed=520810, candidate="csat_poisson")
    summary["csat_poisson_by_quadrant_mean_dti"] = {
        q: round(float(np.mean(vals)), 5) for q, vals in per_quadrant.items()
    }
    return summary


def main() -> int:
    t0 = time.time()
    cache_dir = paths.DATA / "cache_csat"
    ev_dir = ROOT / "evidence"
    reg_idx_path = ROOT / "registry" / "registry_index.json"
    reg_idx = json.loads(reg_idx_path.read_text(encoding="utf-8"))
    exp1 = json.loads((ev_dir / "exp84_1_canary_and_surface.json").read_text(encoding="utf-8"))
    exp2 = json.loads((ev_dir / "exp84_2_holdout_eval.json").read_text(encoding="utf-8"))

    g = ggrid.load_grid()
    fp, cat = g.footprint, g.catalogue
    quad = holdout.quadrant_ids(fp)

    print(f"[EXP-84-3] Computing paired 20 km spatial-block bootstrap summary for csat_poisson (RSS={rss_mb():.0f}MB)...", flush=True)
    d28_holdout = summarize_d28_holdout_from_cache(g, reg_idx, cache_dir, exp2)
    for k, sc in d28_holdout["scores"].items():
        print(f"  {k:24s}: DTI={sc['dti']:.5f} CI95=[{sc['ci95'][0]:.5f}, {sc['ci95'][1]:.5f}]", flush=True)
    for k, pd in d28_holdout["paired_differences"].items():
        print(f"  csat_poisson minus {k:22s}: {pd['delta']:+.5f} CI95=[{pd['ci95'][0]:+.5f}, {pd['ci95'][1]:+.5f}]", flush=True)

    # Load full-catalogue LOQO surface from EXP-84-1
    csat_full_2d = np.zeros(fp.shape, dtype=np.float32)
    csat_full_2d[fp] = np.load(cache_dir / "csat_full_surf_f32.npy")
    d1_full_2d = np.zeros(fp.shape, dtype=np.float32)
    d1_full_2d[fp] = np.load(cache_dir / "d1_full_f32.npy")

    # Determine automatic calibrated dot budget from pi0=0.0024 (identical protocol to EXP-84-2)
    _, info_full = csat.allocate_submodular_dots(
        csat_full_2d, fp, cat, d1_full_2d, quad, collar_px=2.5, pi0=0.0024, max_dots=42_000
    )
    budget_full = int(info_full["n_dots"])
    allowed_full = fp & (~cat) & (d1_full_2d > 2.5)
    dots_full = csat.poisson_disk_dots(csat_full_2d, allowed_full, budget=budget_full, sep_px=2.83)
    n_emitted = int((dots_full > 0).sum())

    # Stratify emitted dots by distance to mapped catalogue to document concealed-domain reach
    dm_mask = dots_full > 0
    dist_strata = {
        "d_2p5_to_15px": int((dm_mask & (d1_full_2d <= 15.0)).sum()),
        "d_15_to_40px": int((dm_mask & (d1_full_2d > 15.0) & (d1_full_2d <= 40.0)).sum()),
        "d_gt_40px": int((dm_mask & (d1_full_2d > 40.0)).sum()),
        "min_dist_to_catalogue_px": round(float(d1_full_2d[dm_mask].min()), 3),
        "median_dist_to_catalogue_px": round(float(np.median(d1_full_2d[dm_mask])), 3),
    }
    print(f"[EXP-84-3] Full-catalogue emission: n_dots={n_emitted}, strata={dist_strata}", flush=True)

    # Write candidate GeoTIFF via unmodified shared submission_writer.write_submission
    pred_hash8 = hashlib.sha256(np.ascontiguousarray(dots_full).tobytes()).hexdigest()[:8]
    dl_dir = ROOT / "docs" / "downloads"
    dl_dir.mkdir(parents=True, exist_ok=True)
    sub_stem = f"gemsdoe84-h84-csat-d28-20261022T234500Z-{pred_hash8}-zeros"
    sub_tif = dl_dir / f"{sub_stem}.tif"
    for ext in (".tif", ".zip", ".json"):
        p_old = dl_dir / f"{sub_stem}{ext}"
        if p_old.exists():
            p_old.unlink()

    sub_note = (
        "GEMSDOE84 H84-CSAT LOQO dual-habitat 3D contact-depth + strain-transfer "
        "D2.8 c2.5 zeros; holdout DTI 0.1685 vs 0.1056"
    )
    assert len(sub_note) <= 140
    writer_receipt = submission_writer.write_submission(
        sub_tif,
        dots_full,
        paths.BRIDGE / "sample_submission.tif",
        fp,
        note=sub_note,
        name=sub_stem,
        catalogue=cat,
        metadata={
            "lane": "H84-CSAT",
            "holdout_dti": round(float(d28_holdout["scores"]["csat_poisson"]["dti"]), 5),
            "holdout_ci95": [round(float(x), 5) for x in d28_holdout["scores"]["csat_poisson"]["ci95"]],
            "evaluator_version": evaluate_holdout.VERSION,
            "withheld_positive_pixels": 22893,
            "n_dots": n_emitted,
            "collar_px": 2.5,
            "sep_px": 2.83,
        },
    )
    val_gems57 = gvalidate.validate(sub_tif, fp, cat)
    gvalidate.assert_submittable(val_gems57)
    val_indep = indep_validator.audit(sub_tif, paths.BRIDGE / "sample_submission.tif")
    assert val_indep["format_valid"] and val_indep["status"] == "PASS", f"Independent validator failed: {val_indep}"
    for ext in (".tif", ".zip", ".json"):
        os.chmod(dl_dir / f"{sub_stem}{ext}", 0o644)
    print(f"[EXP-84-3] GeoTIFF written & validated: {sub_tif.name} ({sub_tif.stat().st_size} bytes)", flush=True)

    # Full 1,160-raster registry uniqueness audit via unmodified gems57.uniqueness
    print(f"[EXP-84-3] Auditing {sub_tif.name} against all 1,160 registry rasters (RSS={rss_mb():.0f}MB)...", flush=True)
    ta0 = time.time()
    expected_grid = (g.shape, g.crs, g.transform)

    def _prog(i: int, total: int, row: dict) -> None:
        if i % 300 == 0 or i == total:
            print(f"  [dot-audit] {i}/{total} rasters ({time.time() - ta0:.1f}s, RSS={rss_mb():.0f}MB)", flush=True)

    raw_audit = uniqueness.compare_to_registry(
        sub_tif, reg_idx_path, fp, include_reverse=True, progress=_prog, expected_grid=expected_grid
    )
    assert raw_audit["complete_accessible_scan"], "Incomplete registry scan!"
    assert raw_audit["missing_or_invalid"] == 0, f"Invalid registry rows: {raw_audit['missing_or_invalid']}"

    # Attach exact halo_coverage on allowed_cat = fp & ~cat for binding_duplicate_decision
    # Boole's bound: 3-px disk has 29 pixels, so their_dots < 120,000 => halo_coverage <= td*29/5,106,385 < 0.6815 < 0.70.
    print("[EXP-84-3] Computing exact halo_coverage for dense/broad priors (td >= 120,000)...", flush=True)
    allowed_cat = fp & (~cat)
    n_alw = int(allowed_cat.sum())
    enriched_rows = []
    for r in raw_audit["rows"]:
        td = int(r["their_dots"])
        ov = float(r["my_dots_within_3px_of_theirs"])
        if td >= 120_000:
            with rasterio.open(r["file"]) as src:
                a_t = src.read(1)
            sup_t = np.isfinite(a_t) & (a_t > 0) & fp
            hcov = uniqueness.halo_coverage(sup_t, allowed_cat)
        else:
            # Exact mathematical upper bound < 0.6815 < 0.70 (classified as discriminating, fail-closed)
            hcov = min(float(td * 29) / float(n_alw), 0.6815)
        enriched_rows.append({
            **r,
            "forward_overlap": ov,
            "halo_coverage": round(hcov, 6),
        })

    binding = uniqueness.binding_duplicate_decision(enriched_rows)
    two_phase = uniqueness.two_phase_summary(raw_audit["rows"], int(fp.sum()), expected_rasters=len(raw_audit["rows"]))
    sat_cert = uniqueness.saturation_certificate(
        load_registry_path(SAT_WITNESS_SHA256, reg_idx), fp, cat, expected_grid=expected_grid
    )

    disc_rows = [r for r in enriched_rows if r["halo_coverage"] < uniqueness.DENSE_HALO_FRACTION]
    top15_disc_ov = sorted(disc_rows, key=lambda r: r["forward_overlap"], reverse=True)[:15]
    top10_rho = sorted(
        [r for r in enriched_rows if r.get("spearman_full_footprint") is not None],
        key=lambda r: abs(float(r["spearman_full_footprint"])),
        reverse=True,
    )[:10]
    top10_jac = sorted(enriched_rows, key=lambda r: float(r["jaccard_dot_sets"]), reverse=True)[:10]

    print("\n=== EXP-84-3 REGISTRY UNIQUENESS SUMMARY (1,160 RASTERS) ===", flush=True)
    print(f"  Discriminating priors : {binding['discriminating_priors']}", flush=True)
    print(f"  Space-filling priors  : {binding['space_filling_priors']}", flush=True)
    print(f"  Worst disc. overlap   : {binding['worst_forward_overlap']:.5f} ({binding['worst_forward_overlap_file']})", flush=True)
    print(f"  Worst |Spearman rho|  : {binding['worst_abs_spearman']:.5f} ({binding['worst_abs_spearman_file']})", flush=True)
    print(f"  Worst Jaccard (diag.) : {two_phase['like_for_like_reading']['worst_jaccard']:.5f} ({two_phase['like_for_like_reading']['worst_jaccard_submission']})", flush=True)
    print(f"  Byte-unique           : {raw_audit['byte_unique_among_checked']}", flush=True)
    print(f"  Pixel-unique          : {raw_audit['pixel_unique_among_checked']}", flush=True)
    print(f"  Binding duplicate?    : {binding['duplicate']}", flush=True)

    inc_diff = d28_holdout["paired_differences"]["incumbent_recipe"]
    h19_diff = d28_holdout["paired_differences"]["retrained_h19_control"]
    beats_incumbent = bool(inc_diff["delta"] > 0.0 and inc_diff["ci95"][0] > 0.0)
    beats_h19 = bool(h19_diff["delta"] > 0.0 and h19_diff["ci95"][0] > 0.0)
    canary_ok = bool(exp1["leakage_canary"]["passed"])
    pre_surf_ok = bool(exp1["pre_placement_surface_uniqueness"]["passed"])
    dots_unique = bool(
        (not binding["duplicate"])
        and raw_audit["byte_unique_among_checked"]
        and raw_audit["pixel_unique_among_checked"]
        and raw_audit["complete_accessible_scan"]
    )
    format_ok = bool(val_gems57["all_checks_passed"] and val_indep["format_valid"])
    all_gates_pass = bool(format_ok and canary_ok and pre_surf_ok and beats_incumbent and beats_h19 and dots_unique)

    # Save slimmed rows without full 1,160-row bloat in main summary, plus full rows in exp84_3_registry_rows.json
    (ev_dir / "exp84_3_registry_rows.json").write_text(
        json.dumps(
            [
                {
                    "repo": r["repo"],
                    "submission": r["submission"],
                    "sha256": r["sha256"],
                    "their_dots": r["their_dots"],
                    "halo_coverage": r["halo_coverage"],
                    "forward_overlap": round(r["forward_overlap"], 6),
                    "reverse_overlap": round(float(r["their_dots_within_3px_of_mine"]), 6),
                    "spearman_full_footprint": round(float(r["spearman_full_footprint"]), 6)
                    if r["spearman_full_footprint"] is not None
                    else None,
                    "jaccard_dot_sets": round(float(r["jaccard_dot_sets"]), 6),
                }
                for r in enriched_rows
            ],
            indent=1,
        ),
        encoding="utf-8",
    )

    out = {
        "experiment_id": "EXP-84-3",
        "lane": "H84-CSAT",
        "candidate_arm": "csat_poisson",
        "submission_file": f"docs/downloads/{sub_tif.name}",
        "submission_zip": f"docs/downloads/{sub_stem}.zip",
        "submission_receipt": f"docs/downloads/{sub_stem}.json",
        "submission_sha256": val_gems57["sha256"],
        "submission_bytes": sub_tif.stat().st_size,
        "submission_note": sub_note,
        "submission_note_len": len(sub_note),
        "n_dots": n_emitted,
        "distance_strata": dist_strata,
        "prior_budget_calibration": info_full,
        "d28_holdout_summary": d28_holdout,
        "validation_gems57": val_gems57,
        "validation_independent": val_indep,
        "writer_receipt": writer_receipt,
        "registry_uniqueness": {
            "rasters_expected": raw_audit["registry_rasters_expected"],
            "rasters_checked": raw_audit["registry_rasters_checked"],
            "complete_accessible_scan": raw_audit["complete_accessible_scan"],
            "missing_or_invalid": raw_audit["missing_or_invalid"],
            "byte_unique_among_checked": raw_audit["byte_unique_among_checked"],
            "pixel_unique_among_checked": raw_audit["pixel_unique_among_checked"],
            "binding_decision": binding,
            "two_phase_summary": {k: v for k, v in two_phase.items() if k != "literal_firings"},
            "literal_firings_count": len(two_phase["literal_firings"]),
            "saturation_certificate": sat_cert,
            "top_15_discriminating_by_forward_overlap": [
                {
                    "repo": r["repo"],
                    "submission": r["submission"],
                    "sha256": r["sha256"],
                    "their_dots": r["their_dots"],
                    "halo_coverage": r["halo_coverage"],
                    "forward_overlap": round(r["forward_overlap"], 5),
                    "jaccard_dot_sets": round(float(r["jaccard_dot_sets"]), 5),
                    "spearman_full_footprint": round(float(r["spearman_full_footprint"]), 5)
                    if r["spearman_full_footprint"] is not None
                    else None,
                }
                for r in top15_disc_ov
            ],
            "top_10_by_abs_spearman": [
                {
                    "repo": r["repo"],
                    "submission": r["submission"],
                    "sha256": r["sha256"],
                    "their_dots": r["their_dots"],
                    "spearman_full_footprint": round(float(r["spearman_full_footprint"]), 5),
                }
                for r in top10_rho
            ],
            "top_10_by_jaccard": [
                {
                    "repo": r["repo"],
                    "submission": r["submission"],
                    "their_dots": r["their_dots"],
                    "jaccard_dot_sets": round(float(r["jaccard_dot_sets"]), 5),
                    "forward_overlap": round(r["forward_overlap"], 5),
                }
                for r in top10_jac
            ],
        },
        "automated_gates": {
            "format_and_range_valid": format_ok,
            "single_feature_canary_passed": canary_ok,
            "pre_placement_surface_unique": pre_surf_ok,
            "beats_incumbent_recipe_ci95_gt_0": beats_incumbent,
            "beats_retrained_h19_control_ci95_gt_0": beats_h19,
            "final_dots_registry_unique": dots_unique,
            "all_gates_passed": all_gates_pass,
            "verdict": "promote" if all_gates_pass else "negative",
            "ok_to_submit": all_gates_pass,
            "submission_slots_used": 0,
        },
        "elapsed_s": round(time.time() - t0, 2),
    }
    out_path = ev_dir / "exp84_3_emission_and_uniqueness.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\n[EXP-84-3] ALL GATES PASSED = {all_gates_pass} | verdict = {out['automated_gates']['verdict']}", flush=True)
    print(f"[EXP-84-3] Saved {out_path} in {out['elapsed_s']:.1f}s (RSS={rss_mb():.0f}MB).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
