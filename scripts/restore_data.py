#!/usr/bin/env python3
"""Restore and SHA-256-verify the competition data files listed in registry/data_manifest.json.

Why this script exists (read before touching it): DrivenData's data-download page for
competition #306 is login-walled, and this sandbox has outbound network access to
github.com / api.github.com / codeload.github.com only (plus pypi for packages). The human
project owner mirrored the competition's own GeoTIFFs into public sibling GitHub repos
(buffedlizard55-lab/GEMSDOE and buffedlizard55-lab/GEMSDOE24) on an unrestricted machine
*before* this session started. This script re-downloads those exact bytes via the GitHub
Contents API (which the sandbox *can* reach) and verifies every file against the sha256
pinned in the manifest before it is trusted by anything else in this repository.

A hash match proves "these bytes are identical to the ones every other session in this
lineage already used" -- it is NOT an organizer authentication and is never claimed as one.

Usage:
    python3 scripts/restore_data.py              # restore everything
    python3 scripts/restore_data.py --group core # just the 5 core files
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_via_gh(repo: str, ref: str, path: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    if not shutil.which("gh"):
        raise SystemExit(
            "The `gh` CLI is required (and is pre-authenticated in the Arena sandbox). "
            "Install/auth it, or adapt this function to use `curl -H 'Authorization: "
            "token $GH_TOKEN' https://api.github.com/repos/<repo>/contents/<path>?ref=<ref> "
            "-H 'Accept: application/vnd.github.raw'`."
        )
    with tmp.open("wb") as out:
        subprocess.run(
            [
                "gh", "api", f"repos/{repo}/contents/{path}?ref={ref}",
                "-H", "Accept: application/vnd.github.raw",
            ],
            stdout=out,
            check=True,
        )
    tmp.replace(dest)


def restore_entry(entry: dict, root: Path) -> dict:
    dest = root / entry["dest"]
    if dest.exists() and sha256_file(dest) == entry["sha256"]:
        status = "present"
    else:
        if "parts" in entry:
            tmp = dest.with_suffix(dest.suffix + ".assembling")
            tmp.parent.mkdir(parents=True, exist_ok=True)
            with tmp.open("wb") as out:
                for part in entry["parts"]:
                    p = root / "raw_parts" / Path(part).name
                    fetch_via_gh(entry["repo"], entry["ref"], part, p)
                    with p.open("rb") as src:
                        shutil.copyfileobj(src, out, 1 << 20)
                    p.unlink()
            tmp.replace(dest)
        else:
            fetch_via_gh(entry["repo"], entry["ref"], entry["path"], dest)
        got = sha256_file(dest)
        if got != entry["sha256"]:
            dest.unlink(missing_ok=True)
            raise SystemExit(
                f"HASH MISMATCH for {entry['id']}: got {got}, expected {entry['sha256']}. "
                "Refusing to trust this file -- flag for manual review."
            )
        status = "restored"
    return {
        "id": entry["id"], "dest": entry["dest"], "group": entry["group"],
        "status": status, "bytes": dest.stat().st_size, "sha256": entry["sha256"],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--group", default="all", choices=["core", "all"])
    ap.add_argument("--manifest", default=str(ROOT / "registry" / "data_manifest.json"))
    ap.add_argument("--target-dir", default=str(ROOT / "data"))
    args = ap.parse_args()

    man = json.loads(Path(args.manifest).read_text())
    root = Path(args.target_dir)
    root.mkdir(parents=True, exist_ok=True)
    raw_parts = root / "raw_parts"

    results = []
    for e in man["files"]:
        if args.group == "all" or e["group"] == args.group:
            r = restore_entry(e, root)
            results.append(r)
            print(f"{r['status']:>8}  {e['dest']:40s}  sha256={r['sha256'][:16]}...  OK")
    shutil.rmtree(raw_parts, ignore_errors=True)

    receipt = {"schema_version": 1, "verified_files_count": len(results),
               "storage_root": str(root), "files": results}
    (root / "restore_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"\nVerified {len(results)} files against pinned sha256. Receipt: data/restore_receipt.json")


if __name__ == "__main__":
    main()
