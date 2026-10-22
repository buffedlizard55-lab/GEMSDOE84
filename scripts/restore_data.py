#!/usr/bin/env python3
"""Restore and verify SHA-256-pinned competition mirrors listed in registry/data_manifest.json.

Mirrors are owner-supplied public GitHub blobs (DrivenData files are login-walled at
https://www.drivendata.org/competitions/306/competition-doe-gems/data/).
Integrity-pinned, NOT organizer-authenticated. Fails closed on any hash mismatch.
Uses raw github.com / codeload.github.com streams first (avoiding api.github.com rate limits)
with local SHA-256 deduplication across scored/ and gh api fallback.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(repo: str, ref: str, path: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    tar_url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
    try:
        import tarfile

        req = urllib.request.Request(tar_url, headers={"User-Agent": "GEMSDOE84-Restore/1.0"})
        with urllib.request.urlopen(req, timeout=180) as resp:
            with tarfile.open(fileobj=resp, mode="r|gz") as tf:
                suffix = "/" + path.lstrip("/")
                for member in tf:
                    if member.isfile() and member.name.endswith(suffix):
                        fobj = tf.extractfile(member)
                        if fobj is not None:
                            with tmp.open("wb") as out:
                                shutil.copyfileobj(fobj, out, 1 << 20)
                            tmp.replace(dest)
                            return
    except Exception:
        tmp.unlink(missing_ok=True)

    try:
        with tmp.open("wb") as out:
            subprocess.run(
                [
                    "gh",
                    "api",
                    f"repos/{repo}/contents/{path}?ref={ref}",
                    "-H",
                    "Accept: application/vnd.github.raw",
                ],
                stdout=out,
                check=True,
            )
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)


def build_local_sha_index(root: Path) -> Dict[str, Path]:
    idx: Dict[str, Path] = {}
    for sub in (root, root / "external", root / "scored"):
        if not sub.is_dir():
            continue
        for p in sub.iterdir():
            if p.is_file() and not p.name.endswith(".partial"):
                idx[sha256_file(p)] = p
    return idx


def restore_entry(entry: dict, root: Path, sha_idx: Dict[str, Path]) -> dict:
    dest = root / entry["dest"]
    want_sha = entry["sha256"]
    if dest.exists() and sha256_file(dest) == want_sha:
        return {
            "id": entry["id"],
            "dest": entry["dest"],
            "status": "present",
            "bytes": dest.stat().st_size,
            "sha256": want_sha,
        }
    if want_sha in sha_idx and sha_idx[want_sha].exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sha_idx[want_sha], dest)
        return {
            "id": entry["id"],
            "dest": entry["dest"],
            "status": "present",
            "bytes": dest.stat().st_size,
            "sha256": want_sha,
        }
    if "parts" in entry:
        tmp = dest.with_suffix(".assembling")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        with tmp.open("wb") as out:
            for part in entry["parts"]:
                p = root / "raw_parts" / Path(part).name
                fetch(entry["repo"], entry["ref"], part, p)
                with p.open("rb") as src:
                    shutil.copyfileobj(src, out, 1 << 20)
                p.unlink()
        got = sha256_file(tmp)
        if got != want_sha:
            tmp.unlink(missing_ok=True)
            raise SystemExit(f"HASH MISMATCH {entry['id']}: {got} != {want_sha}")
        tmp.replace(dest)
    else:
        fetch(entry["repo"], entry["ref"], entry["path"], dest)
        got = sha256_file(dest)
        if got != want_sha:
            dest.unlink(missing_ok=True)
            raise SystemExit(f"HASH MISMATCH {entry['id']}: {got} != {want_sha}")
    sha_idx[want_sha] = dest
    return {
        "id": entry["id"],
        "dest": entry["dest"],
        "status": "restored",
        "bytes": dest.stat().st_size,
        "sha256": want_sha,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ids", default="all", help="comma-separated manifest ids or 'all'")
    ap.add_argument("--manifest", default=str(ROOT / "registry" / "data_manifest.json"))
    ap.add_argument("--target-dir", default=str(ROOT / ".cache" / "gems_data"))
    args = ap.parse_args()

    man = json.loads(Path(args.manifest).read_text())
    root = Path(args.target_dir)
    root.mkdir(parents=True, exist_ok=True)
    sha_idx = build_local_sha_index(root)
    want = None if args.ids == "all" else set(args.ids.split(","))
    results = []
    for e in man["files"]:
        if want is None or e["id"] in want:
            r = restore_entry(e, root, sha_idx)
            results.append(r)
            print(f"{r['status']:>8}  {e['dest']:60s} sha256={r['sha256'][:12]}...", flush=True)

    receipt = {
        "schema_version": 1,
        "verified_files_count": len(results),
        "storage_root": str(root),
        "files": results,
    }
    for out_p in (
        ROOT / "data" / "restore_receipt.json",
        ROOT / "evidence" / "data_receipt.json",
        ROOT / "docs" / "evidence" / "data_receipt.json",
    ):
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"Verified {len(results)} files -> data/restore_receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
