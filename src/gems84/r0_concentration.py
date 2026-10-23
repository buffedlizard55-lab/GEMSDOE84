"""Controlled 1-km block-concentration variants of the verified H33 R0 parent.

No live-score feedback, leaderboard access, label probing, rank-correlation gate, or
new geological feature is used.  All distances are Euclidean pixel distances.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

R0_ID = "h33-h33-2-b2"
R0_SHA256 = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
R0_DOTS = 37_654
BLOCK_PX = 10
SEED = 20261023


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_binary(path: Path, footprint: np.ndarray | None = None) -> np.ndarray:
    with rasterio.open(path) as src:
        a = src.read(1)
    out = np.isfinite(a) & (a > 0)
    return out if footprint is None else out & footprint


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


@dataclass
class BlockGeometry:
    height: int
    width: int
    side: int = BLOCK_PX

    def __post_init__(self) -> None:
        self.nbx = (self.width + self.side - 1) // self.side
        self.nby = (self.height + self.side - 1) // self.side
        self.nblocks = self.nbx * self.nby
        yy, xx = np.indices((self.height, self.width), sparse=True)
        self.ids = ((yy // self.side) * self.nbx + (xx // self.side)).astype(np.int32)

    def counts(self, mask: np.ndarray) -> np.ndarray:
        return np.bincount(self.ids[np.asarray(mask, bool)], minlength=self.nblocks)

    def window(self, block: int) -> tuple[slice, slice, int, int]:
        y0 = (int(block) // self.nbx) * self.side
        x0 = (int(block) % self.nbx) * self.side
        return slice(y0, min(self.height, y0 + self.side)), slice(x0, min(self.width, x0 + self.side)), y0, x0


def _cv(values: np.ndarray) -> float | None:
    values = np.asarray(values, dtype=np.float64)
    if not values.size or float(values.mean()) == 0.0:
        return None
    return float(values.std() / values.mean())


def block_report(mask: np.ndarray, geom: BlockGeometry, footprint: np.ndarray,
                 eligible: np.ndarray) -> dict:
    dots = geom.counts(mask).astype(np.float64)
    foot_n = geom.counts(footprint).astype(np.float64)
    eligible_n = geom.counts(eligible).astype(np.float64)
    occupied = dots > 0
    foot = foot_n > 0
    elig = eligible_n > 0
    return {
        "dots": int(dots.sum()),
        "occupied_blocks": int(occupied.sum()),
        "all_footprint_block_density_cv": _cv(dots[foot] / foot_n[foot]),
        "all_eligible_block_density_cv": _cv(dots[elig] / eligible_n[elig]),
        "occupied_block_dot_count_cv": _cv(dots[occupied]),
        "occupied_block_density_cv_footprint": _cv(dots[occupied] / foot_n[occupied]),
        "density_definition": "population std/mean; 1-km blocks; zero-dot blocks included except occupied-only diagnostics",
    }


def make_compliant_parent(r0: np.ndarray, h19: np.ndarray, eligible: np.ndarray,
                          geom: BlockGeometry) -> tuple[np.ndarray, dict]:
    """Apply the brief's literal >=3px rule while minimizing block-allocation drift.

    R0 has 1,611 dots at 2<d_cat<3.  Each is replaced once.  Within each block,
    H19 support is preferred, then max-min spacing against the strict parent.
    Only blocks lacking enough vacancies use a nearest global eligible vacancy.
    """
    strict = r0 & eligible
    removed = r0 & ~eligible
    n_remove = int(removed.sum())
    out = strict.copy()
    support = h19 & eligible
    distance = distance_transform_edt(~strict)
    rem_n = geom.counts(removed)
    r0_n = geom.counts(r0)
    off_support = 0
    deficits: list[tuple[int, int]] = []
    for block in np.flatnonzero(rem_n):
        n = int(rem_n[block])
        ys, xs, y0, x0 = geom.window(int(block))
        avail = eligible[ys, xs] & ~out[ys, xs]
        yy, xx = np.nonzero(avail)
        if not len(yy):
            take = 0
        else:
            gy = yy + y0
            gx = xx + x0
            base_score = distance[gy, gx].copy()
            support_bonus = support[gy, gx].astype(np.float64) * 1_000_000.0
            take = min(n, len(yy))
            for _ in range(take):
                k = int(np.argmax(base_score + support_bonus))
                out[gy[k], gx[k]] = True
                if not support[gy[k], gx[k]]:
                    off_support += 1
                base_score = np.minimum(base_score, np.hypot(gy - gy[k], gx - gx[k]))
                base_score[k] = -1e9
                support_bonus[k] = 0.0
        if take < n:
            ry, rx = np.nonzero(removed[ys, xs])
            deficits.extend((int(y + y0), int(x + x0)) for y, x in zip(ry[: n - take], rx[: n - take]))
    for y, x in deficits:
        found = None
        for radius in range(1, max(r0.shape)):
            y0, y1 = max(0, y - radius), min(r0.shape[0], y + radius + 1)
            x0, x1 = max(0, x - radius), min(r0.shape[1], x + radius + 1)
            yy, xx = np.nonzero(eligible[y0:y1, x0:x1] & ~out[y0:y1, x0:x1])
            if len(yy):
                gy, gx = yy + y0, xx + x0
                flat = gy * r0.shape[1] + gx
                k = np.lexsort((flat, np.hypot(gy - y, gx - x)))[0]
                found = int(gy[k]), int(gx[k])
                break
        if found is None:
            raise RuntimeError(f"no compliant vacancy for {(y, x)}")
        out[found] = True
        if not support[found]:
            off_support += 1
    if int(out.sum()) != int(r0.sum()):
        raise AssertionError("compliance repair changed dot count")
    if (out & ~eligible).any():
        raise AssertionError("compliance repair left a dot inside the exclusion")
    count_diff = geom.counts(out).astype(int) - r0_n.astype(int)
    info = {
        "reason": "R0 conflicts with the brief's literal >=3 Euclidean px non-PRUNE exclusion",
        "r0_dots_at_2_lt_distance_lt_3": n_remove,
        "replacement_dots": n_remove,
        "same_block_replacements": n_remove - len(deficits),
        "outside_original_block_replacements": len(deficits),
        "off_h19_support_replacements": int(off_support),
        "blocks_with_changed_dot_count": int(np.count_nonzero(count_diff)),
        "maximum_absolute_block_count_change": int(np.abs(count_diff).max()),
        "remaining_off_h19_support_dots": int((out & ~h19).sum()),
        "confound": "All arms share this repair; live R0 deltas are not pure concentration effects.",
    }
    return out, info


def _round_robin(sequences: list[list[int]]) -> np.ndarray:
    out: list[int] = []
    if not sequences:
        return np.empty(0, dtype=np.int64)
    for rank in range(max(map(len, sequences))):
        for seq in sequences:
            if rank < len(seq):
                out.append(seq[rank])
    return np.asarray(out, dtype=np.int64)


def make_concentration_sequences(parent: np.ndarray, h19: np.ndarray, eligible: np.ndarray,
                                 prior: np.ndarray, geom: BlockGeometry,
                                 largest_fraction: float = 0.20) -> tuple[np.ndarray, np.ndarray, dict]:
    n_parent = int(parent.sum())
    max_move = int(n_parent * largest_fraction)
    parent_n = geom.counts(parent)
    support = h19 & eligible
    vacancy_n = geom.counts(support & ~parent)
    occupied = np.flatnonzero(parent_n > 0)
    occupied = occupied[np.lexsort((occupied, prior[occupied]))]
    cutoff = int(np.searchsorted(np.cumsum(parent_n[occupied]), max_move)) + 1
    donor_blocks = occupied[:cutoff]
    receiver_candidates = np.flatnonzero(vacancy_n > 0)
    receiver_candidates = receiver_candidates[np.lexsort((receiver_candidates, -prior[receiver_candidates]))]
    receiver_blocks = receiver_candidates[: len(donor_blocks)]
    if vacancy_n[receiver_blocks].sum() < max_move:
        raise RuntimeError("insufficient high-prior H19 vacancies")

    donor_sequences: list[list[int]] = []
    for block in donor_blocks:
        ys, xs, y0, x0 = geom.window(int(block))
        yy, xx = np.nonzero(parent[ys, xs])
        donor_sequences.append(((yy + y0) * parent.shape[1] + xx + x0).astype(np.int64).tolist())
    donors = _round_robin(donor_sequences)

    distance = distance_transform_edt(~parent)
    receiver_sequences: list[list[int]] = []
    for block in receiver_blocks:
        ys, xs, y0, x0 = geom.window(int(block))
        yy, xx = np.nonzero((support & ~parent)[ys, xs])
        gy, gx = yy + y0, xx + x0
        score = distance[gy, gx].copy()
        seq: list[int] = []
        for _ in range(len(gy)):
            k = int(np.argmax(score))
            seq.append(int(gy[k] * parent.shape[1] + gx[k]))
            score = np.minimum(score, np.hypot(gy - gy[k], gx - gx[k]))
            score[k] = -1.0
        receiver_sequences.append(seq)
    receivers = _round_robin(receiver_sequences)
    if len(donors) < max_move or len(receivers) < max_move:
        raise AssertionError("ranked sequence is shorter than the largest dose")
    info = {
        "donor_blocks": int(len(donor_blocks)),
        "receiver_blocks": int(len(receiver_blocks)),
        "donor_pool_dots": int(len(donors)),
        "receiver_pool_vacancies": int(len(receivers)),
        "donor_prior_cutoff": float(prior[donor_blocks[-1]]),
        "receiver_prior_cutoff": float(prior[receiver_blocks[-1]]),
        "donor_order": "ascending block prior, one per block per pass, flat raster order within block",
        "receiver_order": "descending block prior, one per block per pass, within-block max-min distance",
    }
    return donors, receivers, info


def apply_dose(parent: np.ndarray, donors: np.ndarray, receivers: np.ndarray,
               fraction: float, eligible: np.ndarray) -> tuple[np.ndarray, dict]:
    n_parent = int(parent.sum())
    n_move = int(n_parent * fraction)
    if not 0 < n_move <= len(donors) or n_move > len(receivers):
        raise ValueError("dose exceeds frozen donor/receiver sequence")
    out = parent.copy()
    out.ravel()[donors[:n_move]] = False
    out.ravel()[receivers[:n_move]] = True
    if int(out.sum()) != n_parent:
        raise AssertionError("dose did not preserve count")
    if (out & ~eligible).any():
        raise AssertionError("dose emitted outside the eligible domain")
    return out, {
        "requested_fraction": float(fraction),
        "moved_dots": int(n_move),
        "moved_pct_of_37654": float(100.0 * n_move / n_parent),
    }


def parent_diff(parent: np.ndarray, candidate: np.ndarray) -> dict:
    removed = parent & ~candidate
    added = candidate & ~parent
    n = int(parent.sum())
    moved = (int(removed.sum()) + int(added.sum())) / 2.0
    return {
        "parent_dots": n,
        "candidate_dots": int(candidate.sum()),
        "removed_parent_dots": int(removed.sum()),
        "added_candidate_dots": int(added.sum()),
        "symmetric_difference_pixels": int((removed | added).sum()),
        "relocated_dot_equivalent": moved,
        "relocated_pct_of_parent_including_compliance": float(100.0 * moved / n),
        "symmetric_difference_pct_of_parent": float(100.0 * int((removed | added).sum()) / n),
    }


def raster_profile(template: Path) -> dict:
    with rasterio.open(template) as src:
        profile = src.profile.copy()
    profile.update(driver="GTiff", dtype="float32", count=1, compress="deflate",
                   predictor=3, zlevel=9, tiled=True, blockxsize=256, blockysize=256)
    return profile


def write_mask(path: Path, mask: np.ndarray, footprint: np.ndarray,
               template: Path, mode: str) -> None:
    profile = raster_profile(template)
    if mode == "nan":
        profile.update(nodata=np.nan)
        arr = np.where(footprint, mask.astype(np.float32), np.nan).astype(np.float32)
    elif mode == "zeros":
        profile.update(nodata=None)
        arr = np.where(footprint, mask.astype(np.float32), 0.0).astype(np.float32)
    else:
        raise ValueError(mode)
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr, 1)


def rebuild_r0_and_verify(base: np.ndarray, catalogue: np.ndarray, footprint: np.ndarray,
                          labels_template: Path, reference: Path, work_dir: Path) -> dict:
    distance = distance_transform_edt(~catalogue)
    mask = base & footprint & (distance > 2.0)
    if int(mask.sum()) != R0_DOTS or not np.array_equal(mask, read_binary(reference, footprint)):
        raise RuntimeError("R0 mask does not match the pinned parent; STOP")
    path = work_dir / "r0-rebuilt-zeros.tif"
    write_mask(path, mask, footprint, labels_template, "zeros")
    got = sha256(path)
    if got != R0_SHA256 or path.read_bytes() != reference.read_bytes():
        raise RuntimeError(f"R0 byte rebuild mismatch: {got}; STOP")
    return {"sha256": got, "dots": int(mask.sum()), "byte_exact": True,
            "rule": "40,199-dot H27-4 base minus dots with Euclidean d_catalogue <= 2 px"}


def validate_raster(path: Path, template: Path, footprint: np.ndarray,
                    catalogue: np.ndarray, distance_to_catalogue: np.ndarray,
                    mode: str, expected_dots: int = R0_DOTS) -> dict:
    with rasterio.open(template) as ref, rasterio.open(path) as src:
        arr = src.read(1)
        checks = {
            "geotiff": src.driver == "GTiff",
            "single_band": src.count == 1,
            "dtype_float32": src.dtypes == ("float32",),
            "shape_matches": (src.height, src.width) == (ref.height, ref.width),
            "crs_matches": src.crs == ref.crs,
            "transform_matches": src.transform == ref.transform,
            "bounds_match": src.bounds == ref.bounds,
            "no_infinity": bool(not np.isinf(arr).any()),
            "no_nan_inside_footprint": bool(not np.isnan(arr[footprint]).any()),
            "inside_footprint_in_0_1": bool(np.all((arr[footprint] >= 0) & (arr[footprint] <= 1))),
            "zero_catalogue_mass": bool(not np.any(arr[catalogue] != 0)),
            "unit_mass_dots": bool(np.all((arr[footprint] == 0) | (arr[footprint] == 1))),
            "expected_dot_count": bool(np.count_nonzero(arr[footprint] > 0) == expected_dots),
            "literal_minimum_3px": bool(np.all(distance_to_catalogue[arr > 0] >= 3.0)),
        }
        if mode == "nan":
            checks["nan_outside_footprint"] = bool(np.all(np.isnan(arr[~footprint])))
            checks["nodata_is_nan"] = bool(src.nodata is not None and np.isnan(src.nodata))
        elif mode == "zeros":
            checks["zeros_outside_footprint"] = bool(np.all(arr[~footprint] == 0))
            checks["all_finite"] = bool(np.isfinite(arr).all())
            checks["all_values_in_0_1"] = bool(np.all((arr >= 0) & (arr <= 1)))
        else:
            raise ValueError(mode)
    result = {
        "file": str(path),
        "mode": mode,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "n_dots": int(np.count_nonzero(arr > 0)),
        "checks": checks,
        "all_checks_passed": bool(all(checks.values())),
        "scope": "local re-read format/exclusion receipt; not organizer acceptance or a live score",
    }
    if not result["all_checks_passed"]:
        raise ValueError(f"validation failed for {path}: {[k for k, v in checks.items() if not v]}")
    return result


def inventory_hashes(inventory_path: Path) -> set[str]:
    value = json.loads(inventory_path.read_text())
    found: set[str] = set()
    def walk(x) -> None:
        if isinstance(x, dict):
            for key, item in x.items():
                if key == "sha256" and isinstance(item, str) and len(item) == 64:
                    found.add(item)
                else:
                    walk(item)
        elif isinstance(x, list):
            for item in x:
                walk(item)
    walk(value)
    return found
