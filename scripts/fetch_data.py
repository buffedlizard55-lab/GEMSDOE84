#!/usr/bin/env python3
"""Fetch every pinned input (registry/data_manifest_liti.json) and the uniqueness corpus.

Fixes IR-84-06: hydrates via git smart-HTTP blob-less clones (``git clone
--filter=blob:none --no-checkout`` + batched ``git cat-file --batch``) instead
of 1,678 individual ``gh api`` REST blob calls, consuming ZERO GitHub REST API
quota while remaining strictly fail-closed on SHA-256 (data) and git blob SHA-1
(registry corpus).

Never contacts drivendata.org. Destination: ``$GEMS84_DATA`` (default ``/home/user/gemsdata``).

    python scripts/fetch_data.py               # data + external layers
    python scripts/fetch_data.py --registry    # also the uniqueness corpus
    python scripts/fetch_data.py --verify-only # verify existing local cache without network
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]
from gems84.paths import DATA, REGISTRY_DIR  # noqa: E402


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def clone_blobless(full_repo: str, tmp_root: Path) -> Path:
    dest = tmp_root / full_repo.replace("/", "__")
    if not dest.exists():
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--filter=blob:none",
                "--no-checkout",
                f"https://github.com/{full_repo}.git",
                str(dest),
            ],
            check=True,
        )
    return dest


def cat_ref_path(repo_dir: Path, ref: str, rel_path: str) -> bytes:
    res = subprocess.run(
        ["git", "-C", str(repo_dir), "show", f"{ref}:{rel_path}"],
        capture_output=True,
        check=True,
    )
    return res.stdout


def hydrate_blobs_batch(repo_dir: Path, blobs_to_out: list[tuple[str, Path]]) -> list[str]:
    """Stream requested blob OIDs in a single ``git cat-file --batch`` session."""
    if not blobs_to_out:
        return []
    failed: list[str] = []
    req = "".join(f"{blob}\n" for blob, _ in blobs_to_out).encode("ascii")
    proc = subprocess.run(
        ["git", "-C", str(repo_dir), "cat-file", "--batch"],
        input=req,
        capture_output=True,
        check=True,
    )
    buf = memoryview(proc.stdout)
    pos = 0
    for blob, out in blobs_to_out:
        nl = proc.stdout.index(b"\n", pos)
        header = bytes(buf[pos:nl]).decode("ascii")
        pos = nl + 1
        parts = header.split()
        if len(parts) < 3 or parts[1] != "blob":
            failed.append(blob)
            continue
        size = int(parts[2])
        payload = bytes(buf[pos : pos + size])
        pos += size + 1  # trailing newline after payload
        if git_blob_sha1(payload) != blob:
            failed.append(blob)
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(out.suffix + ".part")
        tmp.write_bytes(payload)
        tmp.replace(out)
    return failed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", action="store_true", help="Hydrate/verify uniqueness corpus")
    ap.add_argument("--verify-only", action="store_true", help="Verify local cache without network")
    a = ap.parse_args()

    man = json.loads((ROOT / "registry/data_manifest_liti.json").read_text())
    bad: list[str] = []

    with tempfile.TemporaryDirectory(prefix="gems84_fetch_") as td:
        tmp_root = Path(td)
        for f in man["files"]:
            if f["dest"].startswith("(in repo)"):
                p = ROOT / f["dest"].split(" ", 2)[2]
            else:
                p = DATA / f["dest"]
                if not (p.exists() and sha256(p) == f["sha256"]) and not a.verify_only:
                    repo_dir = clone_blobless(f["repo"], tmp_root)
                    # Ensure commit ref is fetched if not on default branch
                    subprocess.run(
                        ["git", "-C", str(repo_dir), "fetch", "--quiet", "--filter=blob:none", "origin", f["ref"]],
                        check=False,
                    )
                    p.parent.mkdir(parents=True, exist_ok=True)
                    tmp_out = p.with_suffix(p.suffix + ".part")
                    with tmp_out.open("wb") as out_fh:
                        if "parts" in f:
                            for part in f["parts"]:
                                out_fh.write(cat_ref_path(repo_dir, f["ref"], part))
                        else:
                            out_fh.write(cat_ref_path(repo_dir, f["ref"], f["path"]))
                    tmp_out.replace(p)
            ok = p.exists() and sha256(p) == f["sha256"]
            print(("PASS " if ok else "FAIL ") + f"{f['id']:32s} {f['sha256'][:16]}")
            if not ok:
                bad.append(f["id"])

        if a.registry:
            REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
            existing_by_blob: dict[str, Path] = {}
            for tif in REGISTRY_DIR.glob("*.tif"):
                b = tif.read_bytes()
                existing_by_blob[git_blob_sha1(b)] = tif

            missing_by_repo: dict[str, list[tuple[str, Path]]] = defaultdict(list)
            for line in (ROOT / "registry/uniqueness_corpus.txt").read_text().splitlines():
                if not line.strip():
                    continue
                repo, blob, _size, _path = line.split(" ", 3)
                if blob in existing_by_blob:
                    continue
                out = REGISTRY_DIR / f"{repo}__{blob[:12]}.tif"
                missing_by_repo[f"buffedlizard55-lab/{repo}"].append((blob, out))

            if missing_by_repo and a.verify_only:
                for items in missing_by_repo.values():
                    bad.extend(blob for blob, _ in items)
            elif missing_by_repo:
                for full_repo, items in sorted(missing_by_repo.items()):
                    rdir = clone_blobless(full_repo, tmp_root)
                    bad.extend(hydrate_blobs_batch(rdir, items))
                    shutil.rmtree(rdir, ignore_errors=True)

    print(json.dumps({"failed": bad, "rest_api_calls": 0}))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
