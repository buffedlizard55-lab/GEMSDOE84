#!/usr/bin/env python3
"""Restore and SHA-256-verify the pinned inputs this session actually consumes.

Why this exists
---------------
``scripts/restore_data.py`` re-streams the whole upstream repository tarball once per
*part* of a split file (five streams of ~400 MB for ``training_features``).  This script
streams each ``(repo, ref)`` tarball **once**, extracts every wanted path from that single
pass, assembles split files, and fails closed on any hash mismatch.  It only ever contacts
``codeload.github.com`` (never drivendata.org, never dropbox.com) and never reads or writes
credentials.

Pins come from ``registry/data_manifest.json``.  The parent R0 pair (``h33-h33-2-b2``) and
its 0.2708 base are not in that manifest; their SHA-256 pins are taken from this repo's own
evidence (``evidence/h33-original-audit.json`` and ``evidence/h33_validation.json``) and are
declared in ``EXTRA_PINS`` below so the fail-closed behaviour is identical.

Usage
-----
    python scripts/restore_pinned_inputs.py                 # everything this session needs
    python scripts/restore_pinned_inputs.py --ids labels    # one input
    python scripts/restore_pinned_inputs.py --keep-tarballs # reuse cached tarballs

Destination: ``.cache/gems_data`` (git-ignored; the receipt is committed).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "data_manifest.json"
TARBALL_CACHE = ROOT / ".cache" / "upstream"
DEFAULT_TARGET = ROOT / ".cache" / "gems_data"

# Inputs this session consumes, by manifest id.
DEFAULT_IDS = (
    "labels",
    "existing_faults",
    "sample_submission",
    "training_features",
    "ext_lidar_scarp_features_u8",
    "ext_geodawn_rad_u8",
    "ext_geodawn_extensions_u8",
    "ext_derived_sgmc_faults_100m_u8",
    "scored_h19_5",
    "scored_d15_scored",
    "scored_d28_unscored",
)

# Parent lineage rasters.  Pins copied verbatim from this repo's committed evidence:
#   evidence/h33-original-audit.json  -> R0 zeros / nan
#   evidence/h33_validation.json      -> "base" (the 0.2708 GEMSDOE28 emission)
EXTRA_PINS = (
    {
        "id": "parent_r0_h33_2_b2_zeros",
        "repo": "buffedlizard55-lab/GEMSDOE32",
        "ref": "main",
        "path": "docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
        "dest": "parent/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
        "sha256": "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9",
        "pin_source": "evidence/h33-original-audit.json:zeros_tif.sha256 and "
                      "evidence/incumbent_anatomy.json:rasters.h33_2_b2.sha256",
    },
    {
        "id": "parent_r0_h33_2_b2_nan",
        "repo": "buffedlizard55-lab/GEMSDOE32",
        "ref": "main",
        "path": "docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif",
        "dest": "parent/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif",
        "sha256": "baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd",
        "pin_source": "evidence/h33-original-audit.json:nan_tif.sha256",
    },
    {
        "id": "parent_base_h27_4_r1_solo_nan",
        "repo": "buffedlizard55-lab/GEMSDOE28",
        "ref": "main",
        "path": "docs/downloads/gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif",
        "dest": "parent/gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif",
        "sha256": "ab02300152248fdda04e988e2cd2a0c13f35eec42fcf670a15e8b76b19e24a73",
        "pin_source": "evidence/h33_validation.json:base.sha256",
    },
    {
        "id": "parent_base_h27_4_r1_solo_allfinite",
        "repo": "buffedlizard55-lab/GEMSDOE28",
        "ref": "main",
        "path": "docs/downloads/gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-allfinite.tif",
        "dest": "parent/gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-allfinite.tif",
        "sha256": "2fc94a38d77f74d4f4ed1a97a83e7bb71a1ceea090515ec641e6681cc47c44c8",
        "pin_source": "evidence/incumbent_anatomy.json:rasters.h27_4_r1.sha256",
    },
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tarball_for(repo: str, ref: str, keep: bool) -> Path:
    """Return a local tarball of ``repo`` at ``ref``, downloading it once if needed."""
    TARBALL_CACHE.mkdir(parents=True, exist_ok=True)
    local = TARBALL_CACHE / f"{repo.split('/')[-1]}-{ref[:12]}.tar.gz"
    if local.exists() and local.stat().st_size > 0:
        return local
    tmp = local.with_suffix(".partial")
    url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
    req = urllib.request.Request(url, headers={"User-Agent": "GEMSDOE84-PinnedRestore/1.0"})
    print(f"    GET {url}", flush=True)
    with urllib.request.urlopen(req, timeout=600) as resp, tmp.open("wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    tmp.replace(local)
    if not keep:
        # keep anyway: the caller decides deletion once all extractions are done
        pass
    return local


def extract_paths(tarball: Path, wanted: dict[str, Path]) -> dict[str, Path]:
    """Single-pass extraction of ``{member_suffix_or_path: dest}`` from a repo tarball."""
    got: dict[str, Path] = {}
    with tarfile.open(tarball, mode="r|gz") as tf:
        for member in tf:
            if not member.isfile():
                continue
            rel = member.name.split("/", 1)[1] if "/" in member.name else member.name
            dest = wanted.get(rel)
            if dest is None:
                continue
            fobj = tf.extractfile(member)
            if fobj is None:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(dest.suffix + ".partial")
            with tmp.open("wb") as out:
                while True:
                    chunk = fobj.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
            tmp.replace(dest)
            got[rel] = dest
    return got


def restore(entries: list[dict], target: Path, keep_tarballs: bool) -> list[dict]:
    target.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    # Group by (repo, ref) so each archive is streamed exactly once.
    groups: dict[tuple[str, str], list[dict]] = {}
    for e in entries:
        groups.setdefault((e["repo"], e["ref"]), []).append(e)

    for (repo, ref), group in sorted(groups.items()):
        # Already-verified files are skipped without touching the network.
        pending = []
        for e in group:
            if "parts" not in e:
                dest = target / e["dest"]
                if dest.exists() and dest.stat().st_size == e.get("bytes") \
                        and sha256_file(dest) == e["sha256"]:
                    results.append(_row(e, "present", target))
                    continue
            pending.append(e)
        if not pending:
            continue

        tarball = tarball_for(repo, ref, keep_tarballs)
        wanted: dict[str, Path] = {}
        for e in pending:
            if "parts" in e:
                for part in e["parts"]:
                    wanted[part] = target / "raw_parts" / Path(part).name
            else:
                wanted[e["path"]] = target / e["dest"]

        got = extract_paths(tarball, wanted)
        missing = sorted(set(wanted) - set(got))
        if missing:
            raise SystemExit(f"MISSING MEMBER in {repo}@{ref}: {missing}")

        for e in pending:
            if "parts" in e:
                tmp = target / (e["dest"] + ".assembling")
                with tmp.open("wb") as out:
                    for part in e["parts"]:
                        src = target / "raw_parts" / Path(part).name
                        with src.open("rb") as fh:
                            while True:
                                chunk = fh.read(1 << 20)
                                if not chunk:
                                    break
                                out.write(chunk)
                        src.unlink()
                got_sha = sha256_file(tmp)
                if got_sha != e["sha256"]:
                    tmp.unlink(missing_ok=True)
                    raise SystemExit(f"HASH MISMATCH {e['id']}: {got_sha} != {e['sha256']}")
                tmp.replace(target / e["dest"])
            else:
                dest = target / e["dest"]
                got_sha = sha256_file(dest)
                if got_sha != e["sha256"]:
                    dest.unlink(missing_ok=True)
                    raise SystemExit(f"HASH MISMATCH {e['id']}: {got_sha} != {e['sha256']}")
            results.append(_row(e, "restored", target))

        if not keep_tarballs:
            tarball.unlink(missing_ok=True)
    return results


def _row(e: dict, status: str, target: Path) -> dict:
    return {
        "id": e["id"],
        "repo": e["repo"],
        "ref": e["ref"],
        "dest": e["dest"],
        "status": status,
        "bytes": (target / e["dest"]).stat().st_size,
        "sha256": e["sha256"],
        "verified": True,
        "pin_source": e.get("pin_source", "registry/data_manifest.json"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ids", default="default", help="comma-separated ids, 'default' or 'all'")
    ap.add_argument("--target-dir", default=str(DEFAULT_TARGET))
    ap.add_argument("--keep-tarballs", action="store_true")
    ap.add_argument("--receipt", default=str(ROOT / "evidence" / "input_restore_receipt.json"))
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text())
    by_id = {f["id"]: f for f in manifest["files"]}
    pins = list(manifest["files"]) + list(EXTRA_PINS)
    by_id_all = {f["id"]: f for f in pins}

    if args.ids == "all":
        want = [f["id"] for f in pins]
    elif args.ids == "default":
        want = list(DEFAULT_IDS) + [e["id"] for e in EXTRA_PINS]
    else:
        want = [s.strip() for s in args.ids.split(",") if s.strip()]
    unknown = [w for w in want if w not in by_id_all]
    if unknown:
        raise SystemExit(f"unknown ids: {unknown}")

    target = Path(args.target_dir)
    print(f"[restore] target={target}")
    results = restore([by_id_all[w] for w in want], target, args.keep_tarballs)
    for r in results:
        print(f"  {r['status']:>8}  {r['dest']:64s} sha256={r['sha256'][:12]}... ({r['bytes']:,} B)")

    receipt = {
        "schema_version": 1,
        "note": "SHA-256-verified restore of the pinned inputs used this session. "
                "Integrity-pinned mirrors, NOT organizer-authenticated.",
        "egress_hosts_contacted": ["codeload.github.com"],
        "storage_root": str(target),
        "verified_files_count": len(results),
        "all_hashes_match": all(r["verified"] for r in results),
        "files": results,
    }
    Path(args.receipt).write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"[restore] receipt -> {args.receipt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
