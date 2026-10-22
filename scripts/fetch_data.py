#!/usr/bin/env python3
"""Fetch every pinned input (registry/data_manifest_liti.json) and the uniqueness corpus.

Fail-closed: a file is accepted only if its SHA-256 (data) or git blob SHA-1
(registry corpus) matches the pin.  Uses the authenticated ``gh`` CLI (GitHub API).
Never contacts drivendata.org.  Destination: $GEMS84_DATA (default /home/user/gemsdata).

    python scripts/fetch_data.py            # data + external layers
    python scripts/fetch_data.py --registry # also the 1,149-blob uniqueness corpus
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
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


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", action="store_true")
    a = ap.parse_args()
    man = json.loads((ROOT / "registry/data_manifest_liti.json").read_text())
    bad = []
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
                        gh_raw(f"repos/{f['repo']}/contents/{part}?ref={f['ref']}", c); chunks.append(c)
                    with p.open("wb") as out:
                        for c in chunks:
                            out.write(c.read_bytes()); c.unlink()
                else:
                    gh_raw(f"repos/{f['repo']}/contents/{f['path']}?ref={f['ref']}", p)
        ok = p.exists() and sha256(p) == f["sha256"]
        print(("PASS " if ok else "FAIL ") + f"{f['id']:32s} {f['sha256'][:16]}")
        if not ok:
            bad.append(f["id"])
    if a.registry:
        for line in open(ROOT / "registry/uniqueness_corpus.txt"):
            repo, blob, size, path = line.rstrip("\n").split(" ", 3)
            out = REGISTRY_DIR / f"{blob}.tif"
            if not out.exists():
                gh_raw(f"repos/buffedlizard55-lab/{repo}/git/blobs/{blob}", out)
            b = out.read_bytes()
            if hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest() != blob:
                bad.append(blob)
    print(json.dumps({"failed": bad}))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
