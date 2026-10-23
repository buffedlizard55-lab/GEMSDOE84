#!/usr/bin/env python3
"""Build the AXIS=SNAP variants of parent R0 (``h33-h33-2-b2``), gate them, and log them.

One controlled edit per file: every dot keeps its mass and its exclusions; only its position
may change, and only toward a stronger TMI / isostatic-gravity horizontal-gradient response
within a fixed disc.  Nothing else about the parent is touched -- no mass change, no refill,
no new signal, no re-thinning.

Gates enforced here (brief section 6, MUST):
  * format check against ``sample_submission.tif`` (CRS, shape, transform, dtype, band count,
    values in [0, 1], no NaN inside the footprint, NaN outside for the ``.tif`` twin);
  * zero mass on catalogue pixels;
  * SHA-256 not already present in ``ledger/submissions.csv``;
  * parent-diff statistics recorded (dots moved, % changed, displacement, response gain);
  * the written file is re-read from disk and re-measured before it is logged.

Report-only measurements (holdout PROXY, leakage canary, SGMC control) live in
``scripts/measure_snap_reports.py`` and are never gates.

All fixed settings are already built; an explicit --axis SNAP and the pair guard
now stop a repeated build before any output writes. Use preflight_brief_v2.py to
audit the existing bytes. Strict >=3 px clearance has no parent-dot exception.

Usage:  python scripts/build_snap_variants.py --axis SNAP [--data-dir .cache/gems_data]
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems84.parent import (  # noqa: E402
    R0_ZEROS_SHA256,
    emit_dots,
    load_grid,
    rebuild_r0_mask,
    sha256_file,
    verify_r0_file,
)
from gems84.snap import density_cv, edge_response, snap_dots  # noqa: E402
from gems84.brief_v2 import (  # noqa: E402
    BriefViolation, catalogue_clearance, read_experiment_history, require_new_experiments,
)

PARENT_ID = "h33-2-b2"
DATE_TAG = "20261023"
AXIS = "snap"

# The three variants: one 2x2-corner factorial on (window, gate strength).
# margin is expressed in the fused response's own units, where 1.0 == the 99.5th percentile of
# the band inside the footprint (see gems84.snap.robust_unit).
VARIANTS = (
    {
        "value": "1p4px-g0p02",
        "window_px": 1.42,
        "margin": 0.02,
        "hypothesis": (
            "R0's dots are placed by a purely geometric BFS Poisson-disk walk over the H19-5 "
            "lineament field, so a dot can sit 1 px off the geophysical edge that nominated the "
            "lineament. Under the 300 m triangular kernel that misplacement costs up to 1/3 of "
            "the credit available from a truth pixel."
        ),
        "mechanism": (
            "Each dot may move to the highest fused tmi_hg / iso_grav_anom_hg response inside a "
            "1.42 px (8-neighbour) disc, but only if that response beats its own by >= 0.02 of "
            "the robust-unit dynamic range. Count, mass and exclusions are unchanged."
        ),
        "mimic": (
            "Unfaulted lithologic contacts, dike/swarm margins, pluton edges, caldera ring "
            "fractures and alluvial-fan apron breaks produce the same horizontal-gradient crest "
            "in both bands; snapping onto them moves mass off faults and onto contacts."
        ),
    },
    {
        "value": "2p0px-g0p02",
        "window_px": 2.0,
        "margin": 0.02,
        "hypothesis": (
            "Same mechanism, larger search disc: GeoDAWN Area 2 was flown at ~400 m line "
            "spacing, so lineament positions are uncertain by about the 300 m kernel radius and "
            "the correcting displacement is often 2 px, not 1 px."
        ),
        "mechanism": (
            "Identical rule with a 2.0 px Euclidean disc (24 neighbours). Compared with "
            "1p4px-g0p02 this isolates the window; compared with 2p0px-g0p01 it isolates the "
            "gate strength."
        ),
        "mimic": (
            "A wider disc also reaches further off the mapped trace, so it can jump onto a "
            "parallel but unrelated gradient (e.g. a buried paleo-topographic step or a "
            "Lahontan shoreline break) that is not a fault."
        ),
    },
    {
        "value": "2p0px-g0p01",
        "window_px": 2.0,
        "margin": 0.01,
        "hypothesis": (
            "If the mechanism is real, the live gain should grow with the number of decisive "
            "snaps (dose-response). This arm loosens the gate at the same window and moves "
            "roughly 2.4x more dots."
        ),
        "mechanism": (
            "Identical 2.0 px disc with a 0.01 gate, i.e. any neighbour that is measurably "
            "stronger than the dot's own pixel qualifies."
        ),
        "mimic": (
            "A loose gate is dominated by small response differences on a smooth, noisy surface, "
            "so most moves are effectively random w.r.t. new-fault truth; this arm is also the "
            "one most exposed to gradient noise from survey tie-line seams."
        ),
    },
)

# Denominator of the live-anchored DTI inversion recorded in evidence/h33_validation.json
# (pair D2.8 0.2600 / 40,199 dots -> H27-4-R1-SOLO 0.2708 / 40,199-3,891 dots):
#   T ~= 5,073.29, D ~= 18,734.44  ->  DTI = 0.2708.
# For a pure position change with no mass change, dDTI ~= dT / D.  MODEL, not a score.
LIVE_ANCHOR_DENOMINATOR = 18734.44
LIVE_ANCHOR_TP = 5073.29
LIVE_ANCHOR_PAIR_DTI = 0.2708


def git_sha() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # pragma: no cover
        return "unknown"


def content_sha8(mask: np.ndarray) -> str:
    """Upstream naming convention: first 8 hex of SHA-256 over the packed dot mask."""
    import hashlib
    return hashlib.sha256(np.packbits(np.asarray(mask, bool).ravel())).hexdigest()[:8]


def read_ledger(path: Path) -> tuple[dict[str, str], dict[str, dict]]:
    """Return (hash -> owning row id, id -> row) for the existing ledger."""
    hashes: dict[str, str] = {}
    by_id: dict[str, dict] = {}
    if not path.exists():
        return hashes, by_id
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            rid = (row.get("id") or "").strip()
            if rid:
                by_id[rid] = row
            for col in ("sha256", "sha256_zeros", "sha256_nan"):
                v = (row.get(col) or "").strip()
                if len(v) == 64:
                    hashes[v] = rid
            s8 = (row.get("sha8") or "").strip()
            if len(s8) == 8:
                hashes[s8] = rid
    return hashes, by_id


def check_format(path: Path, grid, template: Path, mode: str) -> dict:
    """Hard format gate against sample_submission.tif, re-read from disk."""
    import rasterio
    with rasterio.open(template) as t:
        want_crs, want_tf = str(t.crs), tuple(round(float(v), 4) for v in tuple(t.transform)[:6])
    with rasterio.open(path) as ds:
        arr = ds.read(1)
        got_crs, got_tf = str(ds.crs), tuple(round(float(v), 4) for v in tuple(ds.transform)[:6])
        nodata = ds.nodata
        meta = dict(crs=got_crs, shape=[ds.height, ds.width], dtype=ds.dtypes[0],
                    count=ds.count, transform=list(got_tf),
                    nodata=(None if nodata is None or (isinstance(nodata, float) and np.isnan(nodata))
                            else float(nodata)),
                    nodata_repr=str(nodata))
    inside, outside = arr[grid.foot], arr[~grid.foot]
    checks = {
        "crs_matches_template": got_crs == want_crs == "EPSG:32611",
        "transform_matches_template": got_tf == want_tf,
        "shape_3730x3292": [ds.height, ds.width] == [3730, 3292],
        "dtype_float32": ds.dtypes[0] == "float32",
        "single_band": ds.count == 1,
        "in_footprint_all_finite": bool(np.isfinite(inside).all()),
        "in_footprint_in_0_1": bool(np.all((inside >= 0.0) & (inside <= 1.0))),
        "zero_mass_on_catalogue": int(((arr > 0.5) & grid.catalogue).sum()) == 0,
        "outside_footprint_ok": bool(np.all(np.isnan(outside))) if mode == "nan"
                                else bool(np.all(outside == 0.0)),
    }
    checks["all_passed"] = all(v for k, v in checks.items())
    return {"checks": checks, "meta": meta,
            "dots": int((inside > 0.5).sum()),
            "in_footprint_min": float(inside.min()), "in_footprint_max": float(inside.max())}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--axis", required=True, choices=["SNAP"],
                    help="Human-assigned axis, never inferred from a historical script.")
    ap.add_argument("--data-dir", default=str(ROOT / ".cache" / "gems_data"))
    ap.add_argument("--releases", default=str(ROOT / "releases"))
    ap.add_argument("--ledger", default=str(ROOT / "ledger" / "submissions.csv"))
    ap.add_argument("--receipt", default=str(ROOT / "evidence" / "snap_variants_receipt.json"))
    args = ap.parse_args()

    # Pair deduplication precedes response calculation and directory/file writes.
    # IDs, axis case and R0 aliases cannot be used to rebuild a recorded setting.
    try:
        history = read_experiment_history(ROOT / "ledger" / "submissions.csv")
        if Path(args.ledger).resolve() != (ROOT / "ledger" / "submissions.csv").resolve():
            history.extend(read_experiment_history(Path(args.ledger)))
        require_new_experiments(
            history, PARENT_ID, args.axis, (spec["value"] for spec in VARIANTS),
        )
    except (BriefViolation, OSError) as exc:
        ap.error(str(exc))

    t0 = time.time()
    data_dir = Path(args.data_dir)
    releases = Path(args.releases)
    releases.mkdir(parents=True, exist_ok=True)
    template = data_dir / "sample_submission.tif"

    grid = load_grid(data_dir)
    r0, base = rebuild_r0_mask(data_dir)
    r0_verify = verify_r0_file(data_dir / "parent" /
                               "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif", grid)
    if r0_verify["sha256"] != R0_ZEROS_SHA256:
        raise SystemExit("parent R0 file does not match its pin; refusing to build variants")
    # Verify the exact parent, but do not silently grandfather its diagonal collar.
    parent_allowed = grid.foot & ~grid.catalogue & (grid.d_cat > 2.0)
    allowed = grid.off_catalogue_3px
    if int((r0 & ~parent_allowed).sum()) != 0:
        raise SystemExit("parent dots violate the parent's own exclusion; recipe drift")

    print(f"[snap] R0 dots = {int(r0.sum()):,}  min d_cat = {grid.d_cat[r0].min():.3f} px")
    print(f"[snap] R0 1 km block-density CV = {density_cv(r0, grid.foot, 10):.4f}")
    resp, resp_diag = edge_response(data_dir / "training_features.tif", grid)
    print("[snap] response bands: " + ", ".join(b["name"] for b in resp_diag["response"]["bands"]))

    ledger_hashes, ledger_by_id = read_ledger(Path(args.ledger))
    rows: list[dict] = []
    kept_from_ledger: list[dict] = []
    for spec in VARIANTS:
        vid = f"{PARENT_ID}-{AXIS}{spec['value']}-{DATE_TAG}"
        res = snap_dots(r0, resp, allowed, spec["window_px"], margin=spec["margin"])
        mask = res.mask
        sha8 = content_sha8(mask)
        file_id = f"{vid}-{sha8}"
        prior = ledger_by_id.get(file_id)
        prior_tif = releases / f"{file_id}.tif"
        if prior is not None and prior_tif.exists() \
                and (prior.get("sha256") or "") == sha256_file(prior_tif):
            kept_from_ledger.append(prior)
            print(f"[snap] {file_id}: already in the ledger with the same sha256; not rebuilt")
            continue

        # ---- hard gates on the mask, before anything is written -----------------------
        gate_mask = {
            "count_preserved": int(mask.sum()) == int(r0.sum()) == 37654,
            "one_dot_per_pixel": bool(np.array_equal(mask, mask.astype(bool))),
            "zero_on_catalogue": int((mask & grid.catalogue).sum()) == 0,
            "inside_footprint": int((mask & ~grid.foot).sum()) == 0,
            "strict_catalogue_clearance_ge_3": catalogue_clearance(
                mask, grid.catalogue, grid.d_cat, args.axis
            )["passed"],
            "differs_from_parent": not np.array_equal(mask, r0),
        }
        if not all(gate_mask.values()):
            raise SystemExit(f"mask gate failed for {file_id}: {gate_mask}")

        nan_path = releases / f"{file_id}.tif"
        zeros_path = releases / f"{file_id}-zeros.tif"
        emit_dots(mask, grid, nan_path, mode="nan")
        emit_dots(mask, grid, zeros_path, mode="zeros")

        # ---- re-read from disk and gate the bytes ------------------------------------
        nan_chk = check_format(nan_path, grid, template, "nan")
        zeros_chk = check_format(zeros_path, grid, template, "zeros")
        nan_sha = sha256_file(nan_path)
        zeros_sha = sha256_file(zeros_path)
        dup = sorted({h for h in (nan_sha, zeros_sha)
                      if h in ledger_hashes and ledger_hashes[h] != file_id})
        gate_file = {
            "nan_format_ok": nan_chk["checks"]["all_passed"],
            "zeros_format_ok": zeros_chk["checks"]["all_passed"],
            "sha256_not_in_ledger": not dup,
            "reread_dot_count_matches": nan_chk["dots"] == zeros_chk["dots"] == int(mask.sum()),
        }
        if not all(gate_file.values()):
            raise SystemExit(f"file gate failed for {file_id}: {gate_file} {nan_chk['checks']}")

        # ---- parent-diff statistics ---------------------------------------------------
        moved = res.stats["dots_moved"]
        pct = res.stats["pct_dots_moved"]
        # MODEL projection: dDTI ~= dT / D with D from the recorded live-anchor inversion.
        # Scenario band: 10%..25% of moved dots end one full pixel closer to a truth pixel they
        # are the nearest dot to (kernel gain 1/3 each); 0% if snaps are uncorrelated with truth.
        dT_lo, dT_hi = 0.10 * moved / 3.0, 0.25 * moved / 3.0
        pred_lo = dT_lo / LIVE_ANCHOR_DENOMINATOR
        pred_hi = dT_hi / LIVE_ANCHOR_DENOMINATOR
        note = (f"R0 + snap {spec['value']} ({moved:,}/{int(r0.sum()):,} dots moved, "
                f"mean {res.stats['mean_displacement_px']:.2f} px); predicted "
                f"{pred_lo:+.3f}..{pred_hi:+.3f}")
        if len(note) > 140:
            note = note[:137] + "..."

        receipt = {
            "schema_version": 1,
            "id": file_id,
            "parent": PARENT_ID,
            "parent_sha256_zeros": R0_ZEROS_SHA256,
            "parent_score": "0.2778 (CLAIM: owner-reported; no receipt in ledger/)",
            "axis": AXIS,
            "value": spec["value"],
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "git_sha": git_sha(),
            "recipe": {
                "inputs": [
                    "parent R0 rebuilt byte-identically by scripts/rebuild_r0.py",
                    "training_features.tif band 3 tmi_hg + band 18 iso_grav_anom_hg "
                    "(sha256 4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5)",
                ],
                "response": "per-band: nodata-fill with footprint median -> gaussian sigma=1.0 px "
                            "-> robust_unit (median/IQR z, 1.0 = 99.5th pct) -> pixel-wise max",
                "window_px": spec["window_px"],
                "margin": spec["margin"],
                "allowed_targets": "footprint & ~catalogue & d_cat >= 3.0 px (strict Brief v2)",
                "determinism": "no RNG; candidates ordered by response, then distance, then (dy,dx)",
                "seed": None,
            },
            "mechanism_card": {
                "hypothesis": spec["hypothesis"],
                "mechanism": spec["mechanism"],
                "non_fault_mimic": spec["mimic"],
                "predicted_sign": "positive",
                "predicted_live_change": f"{pred_lo:+.4f} to {pred_hi:+.4f} (MODEL)",
                "prediction_basis": (
                    f"pure position change => dDTI ~= dT / D with D = {LIVE_ANCHOR_DENOMINATOR:.2f} "
                    f"from the recorded live-anchor inversion (T = {LIVE_ANCHOR_TP:.2f}, "
                    f"DTI = {LIVE_ANCHOR_PAIR_DTI}) in evidence/incumbent_anatomy.json; "
                    "scenario = 10%-25% of moved dots close one full pixel of gap "
                    "(kernel gain 1/3 each). Evidence class MODEL, not a score."
                ),
                "no_evidence_threshold": 0.01,
                "falsifier": (
                    f"live change <= {pred_lo:+.3f} (i.e. < 0.01 above the parent's 0.2778 CLAIM) "
                    "means no evidence for the snap mechanism; a live change of -0.01 or worse "
                    "falsifies it and says the TMI/gravity crests R0 was pulled onto are "
                    "non-fault contacts."
                ),
            },
            "parent_diff": {
                **res.stats,
                "block_density_cv_1km_parent": density_cv(r0, grid.foot, 10),
                "block_density_cv_1km_variant": density_cv(mask, grid.foot, 10),
                "min_d_cat_parent_px": float(grid.d_cat[r0].min()),
                "min_d_cat_variant_px": float(grid.d_cat[mask].min()),
                "median_d_cat_parent_px": float(np.median(grid.d_cat[r0])),
                "median_d_cat_variant_px": float(np.median(grid.d_cat[mask])),
            },
            "gates": {"mask": gate_mask, "file": gate_file,
                      "all_passed": all(gate_mask.values()) and all(gate_file.values())},
            "files": {
                "nan": {"path": str(nan_path.relative_to(ROOT)), "sha256": nan_sha,
                        "bytes": nan_path.stat().st_size, **nan_chk},
                "zeros": {"path": str(zeros_path.relative_to(ROOT)), "sha256": zeros_sha,
                          "bytes": zeros_path.stat().st_size, **zeros_chk},
            },
            "form_note": note,
            "form_note_chars": len(note),
        }
        (releases / f"{file_id}.json").write_text(json.dumps(receipt, indent=2) + "\n")
        ledger_hashes.update({nan_sha: file_id, zeros_sha: file_id, sha8: file_id})
        rows.append({
            "id": file_id,
            "site": "GEMSDOE84",
            "name": file_id,
            "score": "",
            "evidence_class": "BUILT (unscored)",
            "encoding": "nan+zeros",
            "n_dots": int(mask.sum()),
            "pct_changed": pct,
            "sha8": sha8,
            "sha256": nan_sha,
            "sha256_zeros": zeros_sha,
            "parent": f"{PARENT_ID} (R0, sha256 {R0_ZEROS_SHA256[:12]}...)",
            "axis": AXIS,
            "value": spec["value"],
            "status": "BUILT",
            "receipt": "N",
            "receipt_score": "",
            "predicted_change": f"{pred_lo:+.4f}..{pred_hi:+.4f}",
            "date": "",
            "form_note": note,
            "notes": (f"window {spec['window_px']} px, gate {spec['margin']}, "
                      f"{moved:,} dots moved, mean displacement "
                      f"{res.stats['mean_displacement_px']:.3f} px"),
        })
        print(f"[snap] {file_id}: moved {moved:,} ({pct}%) "
              f"mean disp {res.stats['mean_displacement_px']:.3f} px, "
              f"predicted {pred_lo:+.4f}..{pred_hi:+.4f}")

    summary = {
        "schema_version": 1,
        "axis": AXIS,
        "built_this_run": len(rows),
        "carried_forward_from_ledger": len([r for r in kept_from_ledger
                                            if r.get("id") not in {x["id"] for x in rows}]),
        "parent": {
            "id": PARENT_ID,
            "sha256_zeros": R0_ZEROS_SHA256,
            "dots": int(r0.sum()),
            "min_d_cat_px": float(grid.d_cat[r0].min()),
            "score": "0.2778 CLAIM (owner-reported, no receipt)",
        },
        "response_surface": resp_diag["response"],
        "variants": rows + [r for r in kept_from_ledger
                            if r.get("id") not in {x["id"] for x in rows}],
        "elapsed_s": round(time.time() - t0, 1),
    }
    Path(args.receipt).write_text(json.dumps(summary, indent=2) + "\n")
    # Carry forward BUILT rows that already existed so a re-run does not drop them.
    all_rows = rows + [r for r in kept_from_ledger
                       if r.get("id") not in {x["id"] for x in rows}]
    (ROOT / "ledger" / "_snap_rows.json").write_text(json.dumps(all_rows, indent=2) + "\n")
    print(f"[snap] receipt -> {args.receipt}")
    print(f"[snap] releases -> {releases} ({len(rows)} built this run, "
          f"{len(kept_from_ledger)} carried forward; 2 encodings each)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
