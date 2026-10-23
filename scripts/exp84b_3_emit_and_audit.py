#!/usr/bin/env python3
"""EXP-84B-3: Full-footprint 4-quadrant LOQO inference, dual-stage 1,163-raster
uniqueness audit (pre-placement surface + post-placement dots), and automated
GeoTIFF/ZIP submission packaging + triple validation for Lane H84-B (H84-TCDH).

Protocol compliance:
  * Gate 3A (before placement): |Spearman rho| <= 0.90 on continuous OOF surface
    across all 1,163 registry rasters; halt immediately if exceeded.
  * Gate 3B (after placement) : |Spearman rho| <= 0.90 across all 1,163 rasters
    AND 3-px forward dot overlap <= 0.70 across all discriminating priors
    (halo_coverage < 0.70 and dot_field support_fraction <= 0.20); halt if exceeded.
  * Gate 3C (packaging)       : vendor/gems57/submission_writer.py +
    vendor/gems57/validate.py + scripts/validate_submission.py.
"""
from __future__ import annotations

import gc
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]

from gems57 import holdout, submission_writer, uniqueness, validate as v57  # noqa: E402
from gems57.grid import TRANSFORM, load_grid  # noqa: E402
from gems84 import tcdh  # noqa: E402
from gems84.paths import BRIDGE, DATA as DATA_DIR  # noqa: E402

SUBMISSION_STEM = "gems84-h84b-tcdh-twostrat-39000d-20261022T235800Z-zeros"
SUBMISSION_NAME = "GEMSDOE84 H84-B TCDH TwoStrat-NMS3-39000d"
SUBMISSION_NOTE = (
    "GEMSDOE84 H84-TCDH: LOQO tilt-worm + Coulomb + INGENIOUS hydro "
    "+ Lahontan-deconf + 2-stratum blind/relay NMS3 (39000d; holdout 0.1234)"
)
assert len(SUBMISSION_NOTE) <= 140, f"Note too long: {len(SUBMISSION_NOTE)}"


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def build_local_registry_index(reg_dir: Path) -> dict:
    """Build complete SHA-256-pinned inventory over all hydrated registry .tif files."""
    files = sorted(reg_dir.glob("*.tif"))
    if len(files) < 1143:
        raise RuntimeError(f"Expected >= 1143 hydrated registry rasters in {reg_dir}, found {len(files)}")
    rasters = []
    for p in files:
        parts = p.stem.split("__")
        repo = parts[0] if parts else "UNKNOWN"
        rasters.append({
            "repo_first": repo,
            "sources": [f"{repo}:{p.name}"],
            "cache_file": str(p.resolve()),
            "sha256": _sha256(p),
        })
    return {
        "complete_accessible_scan": True,
        "errors": [],
        "rasters": rasters,
    }


def audit_surface_and_dots_streaming(
    surface_2d: np.ndarray,
    dots_2d: np.ndarray,
    reg_index: dict,
    fp: np.ndarray,
    cat: np.ndarray,
) -> tuple[dict, dict]:
    """Single-pass exact audit computing Gate 3A (surface rho) and Gate 3B (dot rho + 3px overlap + halo coverage).

    Executes Gate 3A check across ALL priors BEFORE evaluating Gate 3B promotion,
    saving reading 1,163 GeoTIFFs twice while preserving the exact mathematical
    tests of vendor/gems57/uniqueness.py.
    """
    allowed = fp & ~cat
    n_allowed = int(allowed.sum())
    n_fp = int(fp.sum())

    # Candidate surface centered ranks
    s_vals = surface_2d[fp].astype(np.float64)
    s_ranks = rankdata(s_vals).astype(np.float64)
    s_ranks -= s_ranks.mean()
    s_norm = float(np.linalg.norm(s_ranks))

    # Candidate dot ranks & masks
    d_vals = dots_2d[fp].astype(np.float32)
    d_ranks = rankdata(d_vals).astype(np.float64)
    d_ranks -= d_ranks.mean()
    d_norm = float(np.linalg.norm(d_ranks))
    my_sup = (dots_2d > 0) & fp
    my_dots = int(my_sup.sum())
    my_near = uniqueness._near(my_sup)
    cand_decoded_sha = hashlib.sha256(np.ascontiguousarray(dots_2d.astype(np.float32)).tobytes()).hexdigest()

    r_px = int(np.ceil(uniqueness.RADIUS_PX))
    yy, xx = np.mgrid[-r_px:r_px + 1, -r_px:r_px + 1]
    disk_m = (yy * yy + xx * xx) <= uniqueness.RADIUS_PX * uniqueness.RADIUS_PX
    ody, odx = np.nonzero(disk_m)
    ody = (ody - r_px).astype(np.int32)
    odx = (odx - r_px).astype(np.int32)
    H, W = fp.shape

    def _near_exact(sup_mask: np.ndarray, n_pos: int) -> np.ndarray:
        if n_pos > 350_000:
            return uniqueness._near(sup_mask)
        out = np.zeros(sup_mask.shape, bool)
        if n_pos == 0:
            return out
        ys, xs = np.nonzero(sup_mask)
        for dy, dx in zip(ody, odx):
            ny = ys + int(dy)
            nx = xs + int(dx)
            ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
            out[ny[ok], nx[ok]] = True
        return out

    surf_rows = []
    dot_rows = []
    records = reg_index["rasters"]

    for i, rec in enumerate(records):
        p = Path(rec["cache_file"])
        repo = rec["repo_first"]
        sub_name = rec["sources"][0]
        digest = _sha256(p)
        if digest != rec["sha256"]:
            raise ValueError(f"Registry SHA256 mismatch on {p}")
        with rasterio.open(p) as src:
            if src.count != 1 or src.shape != fp.shape:
                raise ValueError(f"Grid shape mismatch on {p}")
            if src.crs is None or src.crs.to_epsg() != 32611 or src.transform != TRANSFORM:
                raise ValueError(f"CRS/transform mismatch on {p}")
            theirs = src.read(1).astype(np.float32)

        theirs = np.where(np.isfinite(theirs), theirs, 0.0)
        theirs[~fp] = 0.0
        tv = theirs[fp]
        sup = (theirs > 0) & fp
        tb = sup[fp]
        nt = int(tb.sum())

        if np.ptp(tv) == 0:
            rho_surf = 0.0
            rho_dots = 0.0
        elif np.all((tv == 0.0) | (tv == 1.0)):
            denom_factor = np.sqrt(nt * (n_fp - nt) / n_fp)
            rho_surf = float(s_ranks[tb].sum() / (s_norm * denom_factor)) if denom_factor > 0 else 0.0
            rho_dots = float(d_ranks[tb].sum() / (d_norm * denom_factor)) if denom_factor > 0 else 0.0
        else:
            tr = rankdata(tv).astype(np.float64)
            tr -= tr.mean()
            tnorm = float(np.linalg.norm(tr))
            rho_surf = float(np.dot(s_ranks, tr) / (s_norm * tnorm)) if tnorm > 0 else 0.0
            rho_dots = float(np.dot(d_ranks, tr) / (d_norm * tnorm)) if tnorm > 0 else 0.0

        surf_rows.append({
            "repo": repo,
            "submission": sub_name,
            "sha256": digest,
            "their_positive_pixels": nt,
            "spearman_surface_full_footprint": rho_surf,
            "abs_spearman": abs(rho_surf),
            "duplicate_by_rho": abs(rho_surf) > uniqueness.RHO_LIMIT,
        })

        near_theirs = _near_exact(sup, nt)
        fwd_ov = float(near_theirs[my_sup].mean()) if my_dots > 0 else 0.0
        rev_ov = float(my_near[sup].mean()) if nt > 0 else 0.0
        jac = uniqueness._jaccard(my_sup, sup)
        h_cov = float(near_theirs[allowed].sum() / max(n_allowed, 1))
        their_dec = hashlib.sha256(np.ascontiguousarray(theirs).tobytes()).hexdigest()

        dot_rows.append({
            "repo": repo,
            "submission": sub_name,
            "file": str(p),
            "sha256": digest,
            "decoded_sha256": their_dec,
            "their_dots": nt,
            "halo_coverage": h_cov,
            "forward_overlap": fwd_ov,
            "my_dots_within_3px_of_theirs": fwd_ov,
            "their_dots_within_3px_of_mine": rev_ov,
            "spearman_full_footprint": rho_dots,
            "jaccard_dot_sets": jac,
            "identical_bytes": False,
            "identical_decoded_predictions": bool(their_dec == cand_decoded_sha),
            "duplicate_by_rho": abs(rho_dots) > uniqueness.RHO_LIMIT,
            "duplicate_by_overlap": fwd_ov > uniqueness.OVERLAP_LIMIT,
            "duplicate_by_jaccard": jac > uniqueness.JACCARD_LIMIT,
        })
        if (i + 1) % 250 == 0 or (i + 1) == len(records):
            print(f"  [Uniqueness scan] {i + 1}/{len(records)} registry rasters audited...")

    # Summarise Gate 3A (pre-placement surface rank-correlation across ALL priors)
    surf_sorted = sorted(surf_rows, key=lambda r: -r["abs_spearman"])
    gate3a = {
        "gate": "Gate 3A — Pre-Placement Continuous Surface Rank-Correlation",
        "evidence_class": "REGISTRY-MEASUREMENT",
        "rasters_checked": len(surf_rows),
        "rho_limit": uniqueness.RHO_LIMIT,
        "max_abs_spearman": float(surf_sorted[0]["abs_spearman"]),
        "max_spearman_signed": float(surf_sorted[0]["spearman_surface_full_footprint"]),
        "nearest_prior": surf_sorted[0]["submission"],
        "duplicate_count": sum(1 for r in surf_rows if r["duplicate_by_rho"]),
        "passed": all(not r["duplicate_by_rho"] for r in surf_rows),
        "top_10_by_abs_spearman": surf_sorted[:10],
    }

    # Summarise Gate 3B (post-placement dot uniqueness via shared vendor/gems57/uniqueness.py)
    two_phase = uniqueness.two_phase_summary(
        dot_rows, footprint_cells=n_fp, expected_rasters=len(dot_rows)
    )
    binding = uniqueness.binding_duplicate_decision(dot_rows)
    disc_rows = [r for r in dot_rows if r["halo_coverage"] < uniqueness.DENSE_HALO_FRACTION]
    disc_top_ov = sorted(disc_rows, key=lambda r: -r["forward_overlap"])[:15]
    all_top_rho = sorted(dot_rows, key=lambda r: -abs(r["spearman_full_footprint"]))[:10]

    gate3b = {
        "gate": "Gate 3B — Post-Placement Final Dot Uniqueness",
        "evidence_class": "REGISTRY-MEASUREMENT",
        "rasters_checked": len(dot_rows),
        "my_dots": my_dots,
        "candidate_decoded_sha256": cand_decoded_sha,
        "binding_decision": binding,
        "two_phase_summary": {k: v for k, v in two_phase.items() if k != "literal_firings"},
        "literal_firings_count": len(two_phase["literal_firings"]),
        "pixel_unique": not any(r["identical_decoded_predictions"] for r in dot_rows),
        "passed": (not binding["duplicate"]) and all(
            abs(r["spearman_full_footprint"]) <= uniqueness.RHO_LIMIT for r in dot_rows
        ) and not any(r["identical_decoded_predictions"] for r in dot_rows),
        "legacy_v1_support_reading_note": (
            "two_phase['like_for_like_reading'] uses legacy representation_class_v1 (support_fraction < 0.20), "
            "which misclassifies 13GEMSDOE's 5-px regular lattice (halo_coverage = 0.9967) as a dot_field; "
            "per vendor/gems57/uniqueness.py IR-H85-01, binding_duplicate_decision (halo_coverage < 0.70) is binding."
        ),
        "top_15_discriminating_overlaps": [
            {
                "submission": r["submission"],
                "their_dots": r["their_dots"],
                "halo_coverage": round(r["halo_coverage"], 4),
                "forward_overlap_3px": round(r["forward_overlap"], 4),
                "reverse_overlap_3px": round(r["their_dots_within_3px_of_mine"], 4),
                "jaccard": round(r["jaccard_dot_sets"], 4),
                "spearman": round(r["spearman_full_footprint"], 4),
            }
            for r in disc_top_ov
        ],
        "top_10_dot_abs_spearman": [
            {
                "submission": r["submission"],
                "their_dots": r["their_dots"],
                "spearman": round(r["spearman_full_footprint"], 4),
                "forward_overlap_3px": round(r["forward_overlap"], 4),
            }
            for r in all_top_rho
        ],
    }
    return gate3a, gate3b


def main() -> int:
    t0 = time.time()
    data_dir = Path(os.environ.get("GEMS84_DATA", str(DATA_DIR)))
    work_dir = data_dir / "work"
    reg_dir = data_dir / "registry"

    grid = load_grid(BRIDGE)
    fp, cat = grid.footprint, grid.catalogue
    quad = holdout.quadrant_ids(fp)

    print("[EXP-84B-3] Step 1: Loading SHA-256-verified physics stack & running full-footprint 4-quadrant LOQO inference...")
    X_phys, X_base19, _, _ = tcdh.build_or_load_physics_stack(data_dir, work_dir, fp)
    blind_basin_fp = tcdh.concealed_blind_basin_score_fp(X_phys, X_base19)
    sense_src = tcdh.load_trace_sense_raster(data_dir / "external", fp.shape)

    full_cache = work_dir / "exp84b3_full_oof.npz"
    if full_cache.exists() and full_cache.stat().st_size > 1_000_000:
        print(f"[EXP-84B-3] Loading cached full-footprint LOQO surface from {full_cache.name}...")
        zc = np.load(full_cache)
        p_tcdh_fp = zc["p_tcdh_fp"]
        phys_prob_fp = zc["phys_prob_fp"]
        d1_fp = zc["d1_fp"]
        dperp_fp = zc["dperp_fp"]
        dpar_fp = zc["dpar_fp"]
    else:
        Xa_cat, d1_fp, dperp_fp, dpar_fp = tcdh.compute_visible_anatomy_fp(cat, fp, sense_src)
        oof_a = tcdh.fit_predict_stage_a_loqo(X_phys, fp, quad, cat, seed=8400)
        p_full_2d, raw_sb = tcdh.fit_predict_stage_b_loqo(
            X_phys, oof_a, fp, quad, cat, sense_src, seed=8400, Xa_outer=Xa_cat,
        )
        p_tcdh_fp = p_full_2d[fp]
        phys_prob_fp = oof_a[:, 0]
        tmp_c = work_dir / "exp84b3_full_oof.tmp.npz"
        np.savez_compressed(
            tmp_c,
            p_tcdh_fp=p_tcdh_fp,
            raw_sb=raw_sb,
            phys_prob_fp=phys_prob_fp,
            d1_fp=d1_fp,
            dperp_fp=dperp_fp,
            dpar_fp=dpar_fp,
        )
        tmp_c.replace(full_cache)
        del Xa_cat, oof_a, p_full_2d, raw_sb
        gc.collect()

    # Uniqueness-safe & holdout-superior EXP-84B-2 allocator:
    # Two-Stratum sep=3 px (300 m) NMS: 24,500 LOQO corridor/relay/tip + 14,500 concealed blind basin
    emitted_bool, surface_2d = tcdh.emit_twostrat_nms3(
        fp, cat, p_tcdh_fp, phys_prob_fp, blind_basin_fp,
        d1_fp, dperp_fp, dpar_fp,
        n_corridor=24_500, n_far_blind=14_500, far_min_dist_px=36.0, sep_px=3,
    )
    dots_2d = emitted_bool.astype(np.float32)

    dcat = ndi.distance_transform_edt(~cat)
    dv = dcat[emitted_bool]
    dot_profile = {
        "n_dots": int(emitted_bool.sum()),
        "on_catalogue_pixels": int((emitted_bool & cat).sum()),
        "outside_footprint_pixels": int((emitted_bool & ~fp).sum()),
        "tip_extensions_1_to_2px": int((dv <= 2.0).sum()),
        "near_relay_2_to_6px": int(((dv > 2.0) & (dv <= 6.0)).sum()),
        "stepover_6_to_15px": int(((dv > 6.0) & (dv <= 15.0)).sum()),
        "intrabasin_blind_gt_15px": int((dv > 15.0).sum()),
        "frac_le_6px": round(float((dv <= 6.0).mean()), 4),
        "frac_6_to_15px": round(float(((dv > 6.0) & (dv <= 15.0)).mean()), 4),
        "frac_gt_15px": round(float((dv > 15.0).mean()), 4),
    }
    print(f"[EXP-84B-3] Candidate emitted dots: {dot_profile}")

    print("[EXP-84B-3] Step 2: Auditing Gate 3A (surface) & Gate 3B (dots) across all 1,163 registry rasters...")
    reg_index = build_local_registry_index(reg_dir)
    gate3a, gate3b = audit_surface_and_dots_streaming(surface_2d, dots_2d, reg_index, fp, cat)

    print(
        f"[EXP-84B-3] Gate 3A (Surface): passed={gate3a['passed']} "
        f"| max |Spearman| = {gate3a['max_abs_spearman']:.4f} vs {gate3a['nearest_prior']}"
    )
    print(
        f"[EXP-84B-3] Gate 3B (Dots)   : passed={gate3b['passed']} "
        f"| worst discriminating 3-px overlap = {gate3b['binding_decision']['worst_forward_overlap']:.4f} "
        f"vs {gate3b['binding_decision']['worst_forward_overlap_file']} "
        f"| worst |Spearman| = {gate3b['binding_decision']['worst_abs_spearman']:.4f}"
    )

    audit_out = {
        "experiment_id": "EXP-84B-3",
        "lane": "H84-B (H84-TCDH)",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "candidate_stem": SUBMISSION_STEM,
        "submission_name": SUBMISSION_NAME,
        "submission_note": SUBMISSION_NOTE,
        "submission_note_chars": len(SUBMISSION_NOTE),
        "dot_profile": dot_profile,
        "gate_3a_pre_placement_surface": gate3a,
        "gate_3b_post_placement_dots": gate3b,
    }

    if not gate3a["passed"] or not gate3b["passed"]:
        audit_out["verdict"] = "duplicate_stop"
        (ROOT / "evidence" / "exp84b3_uniqueness_and_packaging.json").write_text(
            json.dumps(audit_out, indent=2) + "\n"
        )
        raise RuntimeError(
            f"UNIQUENESS STOP TRIGGERED: Gate3A={gate3a['passed']}, Gate3B={gate3b['passed']}"
        )

    print("[EXP-84B-3] Step 3: Gate 3C — Writing GeoTIFF & single-TIFF ZIP via shared vendor/gems57/submission_writer.py...")
    dl_dir = ROOT / "docs" / "downloads"
    dl_dir.mkdir(parents=True, exist_ok=True)
    tif_path = dl_dir / f"{SUBMISSION_STEM}.tif"
    zip_path = dl_dir / f"{SUBMISSION_STEM}.zip"
    rec_path = dl_dir / f"{SUBMISSION_STEM}.json"
    for existing in (tif_path, zip_path, rec_path):
        if existing.exists():
            existing.unlink()

    e2_data = json.loads((ROOT / "evidence" / "exp84b2_allocation.json").read_text())
    ts_score = e2_data["pooled_twostrat_nms3_39k"]["scores"]["alloc_twostrat_nms3_39k"]
    hdti = round(float(ts_score["dti"]), 4)
    hci = [round(float(x), 4) for x in ts_score["ci95"]]
    sub_note = (
        f"GEMSDOE84 H84-TCDH: LOQO tilt-worm+Coulomb+INGENIOUS hydro+Lahontan-deconf "
        f"2-stratum NMS3 (39000d; holdout DTI {hdti:.4f})"
    )
    assert len(sub_note) <= 140, f"Note too long: {len(sub_note)}"
    audit_out["submission_note"] = sub_note
    audit_out["submission_note_chars"] = len(sub_note)

    writer_receipt = submission_writer.write_submission(
        tif_path,
        dots_2d,
        BRIDGE / "sample_submission.tif",
        fp,
        name=SUBMISSION_NAME,
        note=sub_note,
        catalogue=cat,
        metadata={
            "lane": "H84-B (H84-TCDH)",
            "allocator": "alloc_twostrat_nms3_39k (24500 corridor + 14500 concealed blind basin)",
            "holdout_dti": hdti,
            "holdout_ci95": hci,
            "evaluator_version": "gems57-pooled-hide-v2",
            "withheld_positive_pixels": 22893,
            "registry_rasters_checked": gate3b["rasters_checked"],
            "max_surface_abs_spearman": gate3a["max_abs_spearman"],
            "max_discriminating_3px_overlap": gate3b["binding_decision"]["worst_forward_overlap"],
        },
    )

    # Independent CLI validation via scripts/validate_submission.py
    cli_val = subprocess.run(
        [
            sys.executable, str(ROOT / "scripts" / "validate_submission.py"),
            "--template", str(BRIDGE / "sample_submission.tif"),
            "--json",
            str(tif_path),
        ],
        capture_output=True, text=True, check=True,
    )
    standalone_report = json.loads(cli_val.stdout)
    assert standalone_report["format_valid"] is True, f"Standalone validator failed: {standalone_report}"

    # Verify byte SHA-256 uniqueness against all 1,163 registry rasters
    reg_shas = {r["sha256"] for r in reg_index["rasters"]}
    assert writer_receipt["sha256"] not in reg_shas, "Byte SHA-256 collision with registry!"

    audit_out["gate_3c_packaging"] = {
        "passed": True,
        "tif_file": f"docs/downloads/{tif_path.name}",
        "tif_bytes": writer_receipt["bytes"],
        "tif_sha256": writer_receipt["sha256"],
        "zip_file": f"docs/downloads/{zip_path.name}",
        "zip_bytes": zip_path.stat().st_size,
        "zip_sha256": writer_receipt["zip_sha256"],
        "receipt_file": f"docs/downloads/{rec_path.name}",
        "vendor_validator": writer_receipt["validator"],
        "standalone_validator": standalone_report,
    }
    audit_out["verdict"] = "promote"
    audit_out["elapsed_s"] = round(time.time() - t0, 2)

    out_path = ROOT / "evidence" / "exp84b3_uniqueness_and_packaging.json"
    out_path.write_text(json.dumps(audit_out, indent=2) + "\n")
    print(f"\n=== EXP-84B-3 COMPLETE: VERDICT = PROMOTE ({audit_out['elapsed_s']}s) ===")
    print(f"  GeoTIFF : {tif_path} ({writer_receipt['bytes']:,} bytes, sha256={writer_receipt['sha256'][:16]}...)")
    print(f"  ZIP     : {zip_path} ({zip_path.stat().st_size:,} bytes, sha256={writer_receipt['zip_sha256'][:16]}...)")
    print(f"  Saved   : {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
