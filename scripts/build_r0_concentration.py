#!/usr/bin/env python3
"""Build three frozen CONCENTRATION arms after a byte-exact R0 reproduction.

No DrivenData page is contacted.  The human submits nothing through this code.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems84.r0_concentration import (  # noqa: E402
    BLOCK_PX, R0_DOTS, R0_ID, BlockGeometry, apply_dose, block_report,
    inventory_hashes, make_compliant_parent, make_concentration_sequences,
    parent_diff, read_binary, rebuild_r0_and_verify, sha256, validate_raster,
    write_json, write_mask,
)
from gems57 import evaluate_holdout as shared_eval  # noqa: E402
from gems57.grid import Grid  # noqa: E402
from gems57.holdout import buffered_component_draw  # noqa: E402
from gems57.metric import dti_exact  # noqa: E402

DATE = "20261023"
AXIS = "CONCENTRATION"
VALUES = (("10pct", 0.10, "MODEL +0.005"), ("15pct", 0.15, "MODEL +0.008"),
          ("20pct", 0.20, "MODEL -0.006"))
LEDGER_COLUMNS = ["id", "site", "name", "parent", "axis", "value", "n_dots",
                  "pct_changed", "sha256", "sha8", "encoding", "score", "receipt",
                  "status", "predicted_change", "receipt_score", "date", "source"]
FILES = {
    "sample": "sample_submission.tif",
    "labels": "labels.tif",
    "existing": "existing_faults.tif",
    "h19": "scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif",
    "base": "lineage/gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif",
    "r0": "lineage/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
    "sgmc": "external/derived_sgmc_faults_100m_u8.tif",
}
REQUIRED_IDS = ["sample_submission", "labels", "existing_faults", "scored_h19_5",
                "r0_base_h27_4", "r0_reference_zeros", "ext_derived_sgmc_faults_100m_u8"]


def initialize_ledger(path: Path) -> list[dict]:
    if path.exists():
        with path.open(newline="") as stream:
            return list(csv.DictReader(stream))
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with (ROOT / "registry/live_scores.csv").open(newline="") as stream:
        for raw in csv.DictReader(stream):
            name = raw["submission_name"]
            is_r0 = name == "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros"
            digest = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9" if is_r0 else ""
            rows.append({**{c: "" for c in LEDGER_COLUMNS},
                         "id": f"{raw['site_repo']}:{name}", "site": raw["site_repo"],
                         "name": name, "n_dots": str(R0_DOTS) if is_r0 else "",
                         "sha256": digest, "sha8": digest[:8], "score": raw["public_score"],
                         "receipt": "N", "status": "CLAIM", "source": "registry/live_scores.csv"})
    # Collapse only exact repeated rows; distinct sites and encodings remain auditable.
    unique = list({tuple(row.get(c, "") for c in LEDGER_COLUMNS): row for row in rows}.values())
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=LEDGER_COLUMNS)
        writer.writeheader()
        writer.writerows(unique)
    return unique


def write_ledger(path: Path, rows: list[dict]) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=LEDGER_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def verify_inputs(data_dir: Path) -> dict:
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    by_id = {entry["id"]: entry for entry in manifest["files"]}
    receipt = {}
    for key, rel in FILES.items():
        path = data_dir / rel
        if key == "sample": ident = "sample_submission"
        elif key == "labels": ident = "labels"
        elif key == "existing": ident = "existing_faults"
        elif key == "h19": ident = "scored_h19_5"
        elif key == "base": ident = "r0_base_h27_4"
        elif key == "r0": ident = "r0_reference_zeros"
        else: ident = "ext_derived_sgmc_faults_100m_u8"
        expected = by_id[ident]["sha256"]
        got = sha256(path)
        if got != expected:
            raise RuntimeError(f"input hash mismatch for {ident}: {got} != {expected}")
        receipt[ident] = {"path": str(path), "sha256": got, "bytes": path.stat().st_size,
                          "status": "VERIFIED"}
    receipt["unused_manifest_entries"] = [e["id"] for e in manifest["files"] if e["id"] not in REQUIRED_IDS]
    return receipt


def make_folds(footprint: np.ndarray, catalogue: np.ndarray):
    grid = Grid(footprint=footprint, catalogue=catalogue, crs="EPSG:32611",
                transform=None, height=footprint.shape[0], width=footprint.shape[1])
    folds = []
    for seed in (20, 21):
        seed_folds, _ = buffered_component_draw(grid, seed=seed, hide_frac=0.20,
                                                buffer_px=3, boundary_px=12)
        for fold in seed_folds:
            fold = dict(fold)
            fold["seed"] = seed
            folds.append(fold)
    return folds


def canary_report(folds: list[dict], footprint: np.ndarray, prior_grid: np.ndarray) -> dict:
    rows = []
    for fold in folds:
        active = footprint & fold["region"] & ~fold["masked_known"]
        truth = fold["truth"][active]
        if not truth.any() or truth.all():
            continue
        auc = float(roc_auc_score(truth.astype(np.uint8), prior_grid[active]))
        rows.append({"seed": fold["seed"], "fold": fold["name"], "auc": auc,
                     "direction_free_auc": max(auc, 1.0 - auc),
                     "active_pixels": int(active.sum()), "withheld_positives": int(truth.sum())})
    maximum = max((r["direction_free_auc"] for r in rows), default=None)
    return {"evidence_class": "PROXY", "feature": "H19-5 support density in fixed 1-km blocks",
            "folds": rows, "max_direction_free_auc": maximum,
            "stop_threshold": 0.90, "stop_required": bool(maximum is not None and maximum > 0.90),
            "caveat": "Inherited full-catalogue H19 lineage; diagnostic only, never a live gate."}


def proxy_report(folds: list[dict], footprint: np.ndarray, masks: dict[str, np.ndarray]) -> dict:
    terms = {name: [] for name in masks}
    unique_hidden = np.zeros(footprint.shape, dtype=bool)
    for fold in folds:
        unique_hidden |= fold["hidden_all"]
        for name, mask in masks.items():
            _result, block_terms = shared_eval.evaluate(mask, fold, footprint, block_side=200)
            terms[name].append(block_terms)
    pooled = {name: np.sum(parts, axis=0) for name, parts in terms.items()}
    anchor = "concentration15pct"
    all_summary = shared_eval.pooled_summary(pooled, draws=1000, seed=520810, candidate=anchor)
    paired = {}
    for name in masks:
        if name == "r0":
            continue
        summary = shared_eval.pooled_summary({"r0": pooled["r0"], name: pooled[name]},
                                             draws=1000, seed=520810, candidate=name)
        paired[name] = summary["paired_differences"]["r0"]
    return {"evidence_class": "PROXY", "evaluator_version": shared_eval.VERSION,
            "scores": all_summary["scores"], "paired_vs_r0": paired,
            "bootstrap": all_summary["bootstrap"], "implementation_sha256": all_summary["implementation_sha256"],
            "unique_withheld_positive_pixels": int(unique_hidden.sum()),
            "withheld_positive_pixel_instances": all_summary["scores"]["r0"]["withheld_positive_pixels"],
            "caveat": "Catalogue hide-and-recover on an inherited full-catalogue lineage; not leakage-free training validation, not a live score, and never a gate."}


def sgmc_report(path: Path, masks: dict[str, np.ndarray], footprint: np.ndarray,
                distance: np.ndarray) -> dict:
    truth_source = read_binary(path, footprint)
    valid = footprint & (distance > 3.0)
    truth = truth_source & valid
    scores = {}
    for name, mask in masks.items():
        result = dti_exact(mask.astype(np.float32), truth, valid=valid)
        scores[name] = {"dti": result["dti"], "tp": result["tp"], "fp": result["fp"],
                        "fn": result["fn"], "n_emitted_in_domain": result["n_emitted"]}
    return {"evidence_class": "PROXY", "control": "derived SGMC off-catalogue faults",
            "domain": "footprint with Euclidean d_catalogue > 3 px", "truth_pixels": int(truth.sum()),
            "results": scores, "caveat": "SGMC is an auxiliary mapped-fault control, not organizer truth or a live score."}


def mechanism(value: str, prediction: str) -> dict:
    return {
        "hypothesis": "New-fault credit is concentrated in kilometres-scale corridors with dense H19-5 structural support; diffuse low-support blocks contain more expendable false-positive dots.",
        "mechanism": f"Move the {value} dose from ascending-prior to descending-prior 1-km blocks at fixed total mass, round-robin to avoid unnecessary local packing; receiver pixels remain on H19-5 support.",
        "non_fault_mimic": "Pluvial shoreline benches, alluvial-fan distributary networks, and unfaulted lithologic contacts can form dense aligned H19-5 lineaments without new faults.",
        "predicted_live_change": prediction,
        "prediction_class": "MODEL subjective projection frozen before diagnostics; not a score or confidence interval",
        "falsifier": "A same-arm live decrease of at least 0.01 falsifies the predicted sign. Any absolute live change below 0.01 is no evidence.",
        "compliance_confound": "All arms share the mandatory >=3px repair; only dose-to-dose comparisons isolate concentration.",
    }


def validate_only(data_dir: Path) -> int:
    evidence = json.loads((ROOT / "evidence/r0_concentration_build.json").read_text())
    with rasterio.open(data_dir / FILES["sample"]) as src:
        footprint = np.isfinite(src.read(1))
    catalogue = read_binary(data_dir / FILES["labels"], footprint)
    distance = distance_transform_edt(~catalogue)
    results = []
    for variant in evidence["variants"]:
        for key, mode in (("main", "nan"), ("zeros", "zeros")):
            results.append(validate_raster(ROOT / variant["files"][key], data_dir / FILES["sample"],
                                           footprint, catalogue, distance, mode))
    print(json.dumps({"status": "PASS", "files_re_read": len(results), "results": results}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".cache/gems_data")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        return validate_only(args.data_dir)

    verification = verify_inputs(args.data_dir)
    ledger_path = ROOT / "ledger/submissions.csv"
    ledger = initialize_ledger(ledger_path)
    duplicates = [v for v, _f, _p in VALUES if any(r.get("parent") == R0_ID and
                  r.get("axis") == AXIS and r.get("value") == v for r in ledger)]
    if duplicates:
        raise RuntimeError(f"(parent, axis, value) already built: {duplicates}")

    with rasterio.open(args.data_dir / FILES["sample"]) as src:
        footprint = np.isfinite(src.read(1))
    catalogue = read_binary(args.data_dir / FILES["labels"], footprint)
    base = read_binary(args.data_dir / FILES["base"], footprint)
    r0 = read_binary(args.data_dir / FILES["r0"], footprint)
    h19 = read_binary(args.data_dir / FILES["h19"], footprint)
    parent_receipt = rebuild_r0_and_verify(base, catalogue, footprint, args.data_dir / FILES["labels"],
                                           args.data_dir / FILES["r0"], ROOT / ".cache/r0_build")
    distance = distance_transform_edt(~catalogue)
    eligible = footprint & ~catalogue & (distance >= 3.0)
    geom = BlockGeometry(*footprint.shape, side=BLOCK_PX)
    eligible_n = geom.counts(eligible)
    support_n = geom.counts(h19 & eligible)
    prior = np.divide(support_n, eligible_n, out=np.zeros(geom.nblocks, dtype=np.float64), where=eligible_n > 0)
    prior_grid = prior[geom.ids].astype(np.float32)

    # The canary is evaluated before placement. Other diagnostics remain report-only.
    folds = None
    canary = {"status": "NOT_RUN"}
    try:
        folds = make_folds(footprint, catalogue)
        canary = canary_report(folds, footprint, prior_grid)
        write_json(ROOT / "evidence/r0_concentration_canary.json", canary)
    except Exception as exc:
        canary = {"status": "ERROR_REPORT_ONLY", "error": str(exc)}
        folds = None
    if canary.get("stop_required"):
        raise RuntimeError("single-feature AUC > 0.90; STOP and investigate before placement")

    compliant, compliance = make_compliant_parent(r0, h19, eligible, geom)
    compliance["block_report_r0"] = block_report(r0, geom, footprint, eligible)
    compliance["block_report_compliant"] = block_report(compliant, geom, footprint, eligible)
    donors, receivers, pools = make_concentration_sequences(compliant, h19, eligible, prior, geom)
    masks = {"r0": r0, "compliance_only": compliant}
    dose_info = {}
    for value, fraction, _prediction in VALUES:
        mask, info = apply_dose(compliant, donors, receivers, fraction, eligible)
        name = f"concentration{value}"
        masks[name] = mask
        info.pop("donor_blocks_touched", None)
        info["donor_blocks_touched"] = int(len(np.unique(geom.ids.ravel()[donors[: info["moved_dots"]]])))
        info["receiver_blocks_touched"] = int(len(np.unique(geom.ids.ravel()[receivers[: info["moved_dots"]]])))
        dose_info[name] = info

    proxy = {"status": "NOT_RUN"}
    if folds is not None:
        try:
            proxy = proxy_report(folds, footprint, masks)
        except Exception as exc:
            proxy = {"status": "ERROR_REPORT_ONLY", "error": str(exc), "evidence_class": "PROXY"}
    try:
        sgmc = sgmc_report(args.data_dir / FILES["sgmc"], masks, footprint, distance)
    except Exception as exc:
        sgmc = {"status": "ERROR_REPORT_ONLY", "error": str(exc), "evidence_class": "PROXY"}
    write_json(ROOT / "evidence/r0_concentration_proxy.json", proxy)
    write_json(ROOT / "evidence/r0_concentration_sgmc.json", sgmc)

    known_hashes = inventory_hashes(ROOT / "registry/inventory.json")
    known_hashes.update(r.get("sha256", "") for r in ledger if r.get("sha256"))
    new_hashes: set[str] = set()
    variants = []
    releases = ROOT / "releases"
    work = ROOT / ".cache/r0_build"
    for value, _fraction, prediction in VALUES:
        name = f"concentration{value}"
        mask = masks[name]
        stem = f"{R0_ID}-{name}-{DATE}"
        tmp_main = work / f"{stem}-main.tif"
        tmp_zeros = work / f"{stem}-zeros.tif"
        write_mask(tmp_main, mask, footprint, args.data_dir / FILES["sample"], "nan")
        write_mask(tmp_zeros, mask, footprint, args.data_dir / FILES["sample"], "zeros")
        main_sha = sha256(tmp_main)
        zeros_sha = sha256(tmp_zeros)
        if main_sha in known_hashes or zeros_sha in known_hashes or main_sha in new_hashes or zeros_sha in new_hashes:
            raise RuntimeError(f"exact raster hash already registered for {name}")
        new_hashes.update((main_sha, zeros_sha))
        variant_id = f"{stem}-{main_sha[:8]}"
        main_path = releases / f"{variant_id}.tif"
        zeros_path = releases / f"{variant_id}-zeros.tif"
        os.replace(tmp_main, main_path)
        os.replace(tmp_zeros, zeros_path)
        main_validation = validate_raster(main_path, args.data_dir / FILES["sample"], footprint,
                                          catalogue, distance, "nan")
        zeros_validation = validate_raster(zeros_path, args.data_dir / FILES["sample"], footprint,
                                           catalogue, distance, "zeros")
        main_validation["file"] = str(main_path.relative_to(ROOT))
        zeros_validation["file"] = str(zeros_path.relative_to(ROOT))
        info = dose_info[name]
        moved = info["moved_dots"]
        note = (f"R0; move {moved:,} dots ({info['moved_pct_of_37654']:.3f}%) across 1km H19 prior blocks; "
                f"fixed >=3px repair; {prediction}.")
        if len(note) > 140:
            raise AssertionError("submission note exceeds 140 chars")
        variant = {
            "id": variant_id, "parent": R0_ID, "axis": AXIS, "value": value,
            "status": "BUILT", "n_dots": int(mask.sum()), "pct_changed": info["moved_pct_of_37654"],
            "sha256": main_sha, "zeros_sha256": zeros_sha, "predicted_change": prediction,
            "submission_name": variant_id, "form_note": note, "form_note_chars": len(note),
            "files": {"main": str(main_path.relative_to(ROOT)), "zeros": str(zeros_path.relative_to(ROOT))},
            "dose": info, "parent_diff": parent_diff(r0, mask),
            "compliant_parent_diff": parent_diff(compliant, mask),
            "block_report": block_report(mask, geom, footprint, eligible),
            "remaining_off_h19_support_dots": int((mask & ~h19).sum()),
            "mechanism_card": mechanism(value, prediction),
            "validation": {"main": main_validation, "zeros": zeros_validation},
            "proxy": proxy.get("scores", {}).get(name),
            "proxy_delta_vs_r0": proxy.get("paired_vs_r0", {}).get(name),
            "sgmc_control": sgmc.get("results", {}).get(name),
        }
        sidecar = releases / f"{variant_id}.json"
        write_json(sidecar, variant)
        variant["format_receipt"] = str(sidecar.relative_to(ROOT))
        variants.append(variant)
        ledger.append({**{c: "" for c in LEDGER_COLUMNS}, "id": variant_id,
                       "site": "GEMSDOE84", "name": variant_id, "parent": R0_ID,
                       "axis": AXIS, "value": value, "n_dots": str(R0_DOTS),
                       "pct_changed": f"{info['moved_pct_of_37654']:.9f}", "sha256": main_sha,
                       "sha8": main_sha[:8], "encoding": "nan-outside", "receipt": "N",
                       "status": "BUILT", "predicted_change": prediction,
                       "source": "scripts/build_r0_concentration.py"})
    write_ledger(ledger_path, ledger)
    git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    aggregate = {
        "schema": "r0-concentration-build-v1", "date": DATE, "git_sha": git_sha,
        "script_sha256": sha256(Path(__file__)),
        "module_sha256": sha256(ROOT / "src/gems84/r0_concentration.py"),
        "seed": 20261023, "input_verification": verification, "parent_rebuild": parent_receipt,
        "axis": AXIS, "block_size": "1 km = 10 x 10 100-m pixels",
        "prior": "H19-5 positive support / strictly eligible pixels per block",
        "compliance": compliance, "pools": pools, "variants": variants,
        "proxy_receipt": "evidence/r0_concentration_proxy.json",
        "canary_receipt": "evidence/r0_concentration_canary.json",
        "sgmc_receipt": "evidence/r0_concentration_sgmc.json",
        "submission_authorized": False, "submission_slots_used": 0,
        "top_public": "UNSUPPLIED", "weekly_slots_left": "UNSUPPLIED",
    }
    write_json(ROOT / "evidence/r0_concentration_build.json", aggregate)
    print(json.dumps({"status": "BUILT", "parent": parent_receipt,
                      "variants": [{"id": v["id"], "sha256": v["sha256"],
                                    "moved_pct": v["pct_changed"], "note": v["form_note"]} for v in variants],
                      "canary_max_auc": canary.get("max_direction_free_auc")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
