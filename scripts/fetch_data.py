#!/usr/bin/env python3
"""Fetch every pinned input (registry/data_manifest_liti.json) and the uniqueness corpus.

Fail-closed: a file is accepted only if its SHA-256 (data) or git blob SHA-1
(registry corpus) matches the pin. Uses zero-API-quota codeload tarball streaming
for repository archive fetches (with gh raw fallback) so fresh-clone restoration
completes in ~45 s without exhausting the 5,000 req/hr GitHub REST API quota.
Never contacts drivendata.org. Destination: $GEMS84_DATA (default ~/.cache/gemsdata
if present, else /home/user/gemsdata).

    python scripts/fetch_data.py            # data + external layers
    python scripts/fetch_data.py --registry # also the uniqueness corpus
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tarfile
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]
from gems84.paths import DATA, REGISTRY_DIR  # noqa: E402


def gh_raw(endpoint: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".part")
    with tmp.open("wb") as fh:
        subprocess.run(["gh", "api", endpoint, "-H", "Accept: application/vnd.github.raw"], stdout=fh, check=True)
    tmp.replace(out)


def stream_repo_tarball_paths(owner_repo: str, ref: str, want_paths: dict[str, Path]) -> None:
    """Stream codeload tarball once per (repo, ref) without touching GitHub REST quota."""
    url = f"https://codeload.github.com/{owner_repo}/tar.gz/{ref}"
    token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=False).stdout.strip()
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"token {token}")
    with urllib.request.urlopen(req, timeout=120) as resp:
        with tarfile.open(fileobj=resp, mode="r|gz") as tf:
            for member in tf:
                if not member.isfile():
                    continue
                rel = member.name.split("/", 1)[1] if "/" in member.name else member.name
                dest = want_paths.get(rel)
                if dest is not None:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    fobj = tf.extractfile(member)
                    if fobj is not None:
                        tmp = dest.with_suffix(dest.suffix + ".part")
                        tmp.write_bytes(fobj.read())
                        tmp.replace(dest)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", action="store_true")
    a = ap.parse_args()
    man = json.loads((ROOT / "registry/data_manifest_liti.json").read_text())
    bad = []

    # Group missing non-chunked files by (repo, ref) for zero-quota tarball streaming
    grouped: dict[tuple[str, str], dict[str, Path]] = defaultdict(dict)
    for f in man["files"]:
        if f["dest"].startswith("(in repo)") or "parts" in f:
            continue
        p = DATA / f["dest"]
        if not (p.exists() and sha256(p) == f["sha256"]):
            grouped[(f["repo"], f["ref"])][f["path"]] = p

    for (owner_repo, ref), mapping in grouped.items():
        try:
            stream_repo_tarball_paths(owner_repo, ref, mapping)
        except Exception:
            pass

    for f in man["files"]:
        if f["dest"].startswith("(in repo)"):
            p = ROOT / f["dest"].split(" ", 2)[2]
        else:
            p = DATA / f["dest"]
            if not (p.exists() and sha256(p) == f["sha256"]):
                if "parts" in f:
                    chunks = []
                    for i, part in enumerate(f["parts"]):
                        c = DATA / f"_part{i}"
                        gh_raw(f"repos/{f['repo']}/contents/{part}?ref={f['ref']}", c)
                        chunks.append(c)
                    p.parent.mkdir(parents=True, exist_ok=True)
                    with p.open("wb") as out:
                        for c in chunks:
                            out.write(c.read_bytes())
                            c.unlink()
                else:
                    gh_raw(f"repos/{f['repo']}/contents/{f['path']}?ref={f['ref']}", p)
        ok = p.exists() and sha256(p) == f["sha256"]
        print(("PASS " if ok else "FAIL ") + f"{f['id']:32s} {f['sha256'][:16]}")
        if not ok:
            bad.append(f["id"])

    if a.registry:
        REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
        need_by_repo: dict[str, dict[str, tuple[str, Path]]] = defaultdict(dict)
        entries = []
        for line in open(ROOT / "registry/uniqueness_corpus.txt"):
            repo, blob, size, path = line.rstrip("\n").split(" ", 3)
            out = REGISTRY_DIR / f"{blob}.tif"
            entries.append((repo, blob, path, out))
            if not (out.exists() and git_blob_sha1(out.read_bytes()) == blob):
                need_by_repo[repo][path] = (blob, out)

        # Stream each repo tarball once via codeload (0 GitHub REST API calls!)
        for repo, rel_map in need_by_repo.items():
            try:
                url = f"https://codeload.github.com/buffedlizard55-lab/{repo}/tar.gz/HEAD"
                token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=False).stdout.strip()
                req = urllib.request.Request(url)
                if token:
                    req.add_header("Authorization", f"token {token}")
                with urllib.request.urlopen(req, timeout=120) as resp:
                    with tarfile.open(fileobj=resp, mode="r|gz") as tf:
                        for member in tf:
                            if not member.isfile():
                                continue
                            rel = member.name.split("/", 1)[1] if "/" in member.name else member.name
                            if rel in rel_map:
                                fobj = tf.extractfile(member)
                                if fobj is not None:
                                    raw = fobj.read()
                                    want_blob, out_p = rel_map[rel]
                                    if git_blob_sha1(raw) == want_blob:
                                        out_p.write_bytes(raw)
            except Exception:
                pass

        # Fallback to exact git blob SHA endpoint only for any historical non-HEAD blobs
        for repo, blob, path, out in entries:
            if not (out.exists() and git_blob_sha1(out.read_bytes()) == blob):
                gh_raw(f"repos/buffedlizard55-lab/{repo}/git/blobs/{blob}", out)
            if not (out.exists() and git_blob_sha1(out.read_bytes()) == blob):
                bad.append(blob)

    print(json.dumps({"failed": bad}))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
