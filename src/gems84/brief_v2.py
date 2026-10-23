"""Fail-closed guards for the owner's GEMS agent brief v2.

These are experiment/format guards, not a metric, a proxy gate or submission
permission. Only full SHA-256 and repeated (parent, axis, value) are deduped.
No correlation, overlap or similarity thresholds are used.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Iterable

import numpy as np

from .parent import sha256_file

AXES = ("MASS", "CONCENTRATION", "SNAP", "PRUNE", "RELIEF", "SPACING", "TRACKB")
R0_ID = "h33-h33-2-b2"
FULL_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class BriefViolation(ValueError):
    """A required input or an experimental hard constraint is not satisfied."""


def canonical_parent(parent: str) -> str:
    """Normalize only the two R0 aliases already present in the committed ledger."""
    name = parent.strip().lower()
    if name == "h33-2-b2" or name.startswith("h33-2-b2 (r0, sha256 c55bafc47005"):
        return R0_ID
    return name


def experiment_key(parent: str, axis: str, value: str) -> tuple[str, str, str]:
    return canonical_parent(parent), axis.strip().upper(), value.strip().lower()


def read_ledger_rows(path: Path) -> list[dict[str, str]]:
    """Read, never regenerate, a ledger. Missing/malformed history fails closed."""
    with Path(path).open(newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"id", "parent", "axis", "value", "sha256", "status"}
        if not required.issubset(reader.fieldnames or ()):
            raise BriefViolation(f"Ledger is missing required columns: {path}")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise BriefViolation(f"Ledger contains repeated column names: {path}")
        rows = list(reader)
    if not rows:
        raise BriefViolation(f"Ledger is empty; experiment history is not established: {path}")
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise BriefViolation(f"Ledger has malformed rows: {path}")
    for row in rows:
        if row["status"].upper() in ("BUILT", "BUILT_REPORTED"):
            if not all(row[key].strip() for key in ("id", "parent", "axis", "value")):
                raise BriefViolation(f"Built row lacks its experiment identity: {path}")
            if not FULL_SHA256.fullmatch(row["sha256"].lower()):
                raise BriefViolation(f"Built row lacks an exact full file hash: {path}")
    return rows


def read_experiment_history(ledger: Path) -> list[dict[str, str]]:
    """Include pinned cross-session reservations without replacing the primary CSV."""
    rows = read_ledger_rows(ledger)
    reservations = Path(ledger).parent / "experiment_reservations.json"
    if reservations.exists():
        document = json.loads(reservations.read_text())
        if (not isinstance(document, dict) or document.get("schema_version") != 1
                or not isinstance(document.get("sources"), list)):
            raise BriefViolation(f"Malformed cross-session reservations: {reservations}")
        for source in document["sources"]:
            if not isinstance(source, dict):
                raise BriefViolation("Malformed cross-session source.")
            source_hash = source.get("ledger_sha256")
            if not isinstance(source_hash, str) or not FULL_SHA256.fullmatch(source_hash):
                raise BriefViolation("Cross-session source ledger must have a full SHA-256 pin.")
            if not source.get("ledger_url") or not isinstance(source.get("experiments"), list):
                raise BriefViolation("Cross-session source provenance/experiment rows are missing.")
            for row in source["experiments"]:
                if not isinstance(row, dict) or not all(
                    isinstance(row.get(key), str) and row[key].strip()
                    for key in ("id", "parent", "axis", "value", "status")
                ):
                    raise BriefViolation("Malformed cross-session experiment reservation.")
                raster_hash = row.get("sha256")
                if not isinstance(raster_hash, str) or not FULL_SHA256.fullmatch(raster_hash):
                    raise BriefViolation("Cross-session raster must have a full SHA-256 pin.")
                rows.append(dict(row))
    return rows


def ledger_hashes(rows: Iterable[dict[str, str]]) -> set[str]:
    """Only exact full file hashes count. A filename's sha8 is not a file hash."""
    return {
        value.strip().lower()
        for row in rows
        for key in ("sha256", "sha256_nan", "sha256_zeros")
        if FULL_SHA256.fullmatch(value := (row.get(key) or "").strip().lower())
    }


def require_new_experiments(
    rows: Iterable[dict[str, str]], parent: str, axis: str | None, values: Iterable[str]
) -> None:
    """Reject an implicit axis and reused pairs before fitting, writing or editing history."""
    if axis is None or axis.strip().upper() not in AXES:
        raise BriefViolation("The human must explicitly assign one AXIS; there is no default.")
    values = list(values)
    if not 1 <= len(values) <= 3 or any(not str(value).strip() for value in values):
        raise BriefViolation("Supply one to three explicit axis values.")
    requested = [experiment_key(parent, axis, str(value)) for value in values]
    if len(set(requested)) != len(requested):
        raise BriefViolation("Requested (parent, axis, value) pairs repeat within this session.")
    used = {
        experiment_key(row["parent"], row["axis"], row["value"])
        for row in rows if row.get("parent") and row.get("axis") and row.get("value")
    }
    repeats = sorted(set(requested) & used)
    if repeats:
        raise BriefViolation(f"Already built/recorded (parent, axis, value); do not rebuild: {repeats}")


def catalogue_clearance(
    dots: np.ndarray, catalogue: np.ndarray, distance_px: np.ndarray, axis: str
) -> dict:
    """Apply >=3 px to ALL emitted dots, not just additions; only PRUNE is exempt.

    PRUNE is still required to have zero mass on catalogue pixels. An unchanged
    R0 dot has no implicit grandfather exception under the supplied brief.
    """
    if axis not in AXES:
        raise BriefViolation(f"Unknown axis: {axis}")
    dots = np.asarray(dots, dtype=bool)
    catalogue = np.asarray(catalogue, dtype=bool)
    distance_px = np.asarray(distance_px)
    if dots.shape != catalogue.shape or dots.shape != distance_px.shape:
        raise BriefViolation("Dot, catalogue and distance grids must have the same shape.")
    distances = distance_px[dots]
    n_cat = int(np.count_nonzero(dots & catalogue))
    n_close = int(np.count_nonzero(distances < 3.0))
    finite = bool(np.isfinite(distances).all())
    return {
        "minimum_distance_px": float(distances.min()) if distances.size else None,
        "catalogue_dots": n_cat,
        "dots_below_3px": n_close,
        "prune_collar_exception": axis == "PRUNE",
        "passed": n_cat == 0 and finite and (axis == "PRUNE" or n_close == 0),
    }


def verify_pinned_files(data_dir: Path, entries: Iterable[dict]) -> list[dict]:
    """Hash every pinned file before raster/feature use. No fetching or credentials."""
    root = Path(data_dir).resolve()
    verified = []
    for entry in entries:
        path = (root / entry["dest"]).resolve()
        if not path.is_relative_to(root):
            raise BriefViolation(f"Input destination escapes the data directory: {entry['id']}")
        expected = entry["sha256"].lower()
        if not FULL_SHA256.fullmatch(expected):
            raise BriefViolation(f"Missing full SHA-256 pin: {entry['id']}")
        actual = sha256_file(path)
        size = path.stat().st_size
        if actual != expected or ("bytes" in entry and size != entry["bytes"]):
            raise BriefViolation(f"Input SHA-256/size mismatch: {entry['id']}")
        verified.append({
            "id": entry["id"], "dest": entry["dest"], "sha256": actual,
            "bytes": size, "verified": True,
            "pin_source": entry.get("pin_source", "registry/data_manifest.json"),
        })
    return verified
