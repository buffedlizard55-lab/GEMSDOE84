#!/usr/bin/env python3
"""Build ``ledger/submissions.csv`` -- one row per scored or built submission.

The brief asks for ``ledger/submissions.csv`` built from ``ledger/raw_paste.txt``.  That paste
does not exist in this repository, so the ledger is built from the repo's own committed score
records instead, and the substitution is recorded in ``IRREGULARITIES.md``:

* ``registry/live_scores.csv``      -- owner-reported live scores of the GEMSDOE fleet
  (evidence class CLAIM: no submission-page receipt is committed anywhere in this repo);
* ``docs/evidence/upstream-score-ledger.csv`` -- the dated manual read of the official public
  leaderboard (evidence class OFFICIAL_SNAPSHOT, read 2026-10-03);
* ``ledger/_snap_rows.json``        -- rows for files this session BUILT (status BUILT, receipt N).

Repeats are collapsed exactly as the brief instructs: identical content digest + identical
score (the NaN-outside / zeros-outside twins and the cross-site re-uploads of one file), never
on a similarity threshold.

Usage:  python scripts/build_ledger.py
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "registry" / "live_scores.csv"
SNAPSHOT = ROOT / "docs" / "evidence" / "upstream-score-ledger.csv"
ANATOMY = ROOT / "evidence" / "incumbent_anatomy.json"

COLUMNS = [
    "id", "site", "name", "score", "evidence_class", "encoding", "n_dots", "pct_changed",
    "sha8", "sha256", "sha256_zeros", "parent", "axis", "value", "status", "receipt",
    "receipt_score", "predicted_change", "date", "form_note", "notes",
]

ENCODING_TOKENS = ("zeros", "nan", "allfinite", "nanoutside", "nan-outside")

# Dot counts measured from hash-verified bytes in evidence/incumbent_anatomy.json, keyed by the
# content-digest token that appears in the upstream file name.  Nothing here is inferred.
DOTS_BY_TOKEN = {
    "e27054cf": 121131,   # h19-5 solid field, owner-reported 0.1922
    "989f59505db1": 60069,  # dotted h19-5 d1.5, owner-reported 0.2477
    "e56ea318af89": 44090,  # dotted h19-5 d2.8, owner-reported 0.2600
    "8acb75e1f2cc": 40199,  # h27-4-r1-solo d2.8, owner-reported 0.2708
    "e5eb6e7e": 37654,    # h33-h33-2-b2 = R0, owner-reported 0.2778
    "b531dae0a36f": 37660,  # h36-1-rung30-blind-r1, owner-reported 0.2710
}
PARENT_BY_TOKEN = {
    "e5eb6e7e": "h27-4-r1-solo-d2-8 (8acb75e1f2cc)",
    "8acb75e1f2cc": "dotted-h19-5-d2-8 (e56ea318af89)",
    "e56ea318af89": "h19-5 (e27054cf)",
    "989f59505db1": "h19-5 (e27054cf)",
}
SHA256_BY_TOKEN = {
    "e27054cf": "ec1f9b56b83ce33cad781ceb9f104b18fb4f2ff785263a4e89616af4aabdee8d",
    "989f59505db1": "68d0e2e4fcc594f9a23f56c44b885fee733d026d39be55e18ad2a07289525310",
    "e56ea318af89": "91eae1ca42ec845eaa8c2ba32da49806e24751743459b8a10017c479bbe639b8",
    "8acb75e1f2cc": "ab02300152248fdda04e988e2cd2a0c13f35eec42fcf670a15e8b76b19e24a73",
    "e5eb6e7e": "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9",
    "b531dae0a36f": "7c74270ad48fa0b865163853046a6d3815967c5bf37bbda5b74ca7fa22583a32",
}

HEX = re.compile(r"(?<![0-9a-f])([0-9a-f]{8,40})(?![0-9a-f])")


def encoding_of(name: str) -> tuple[str, str]:
    """Return (encoding, name-without-encoding-token)."""
    low = name.lower()
    for tok in ENCODING_TOKENS:
        if low.endswith("-" + tok) or low.endswith("_" + tok) or low.endswith(tok):
            return tok, name[: len(name) - len(tok)].rstrip("-_")
    return "", name


def digest_of(name: str) -> str:
    cands = HEX.findall(name.lower())
    return cands[-1] if cands else ""


def collapse_key(site: str, name: str, score: str) -> str:
    enc, core = encoding_of(name)
    dig = digest_of(core)
    return f"{dig or core}|{score}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "ledger" / "submissions.csv"))
    ap.add_argument("--snap-rows", default=str(ROOT / "ledger" / "_snap_rows.json"))
    ap.add_argument("--mass-rows", default=str(ROOT / "ledger" / "_mass_rows.json"))
    ap.add_argument("--prune-rows", default=str(ROOT / "ledger" / "_prune_rows.json"))
    ap.add_argument("--concentration-rows",
                    default=str(ROOT / "ledger" / "_concentration_rows.json"))
    ap.add_argument("--prune-sweep-rows",
                    default=str(ROOT / "ledger" / "_prune_sweep_rows.json"))
    args = ap.parse_args()

    rows: list[dict] = []

    # 1. owner-reported fleet scores (CLAIM) -------------------------------------------
    with LIVE.open(newline="") as fh:
        for r in csv.DictReader(fh):
            name = r["submission_name"].strip()
            enc, core = encoding_of(name)
            dig = digest_of(core)
            rows.append({
                "id": name, "site": r["site_repo"].strip(), "name": name,
                "score": r["public_score"].strip(), "evidence_class": "CLAIM",
                "encoding": enc, "n_dots": DOTS_BY_TOKEN.get(dig, ""), "pct_changed": "",
                "sha8": dig, "sha256": SHA256_BY_TOKEN.get(dig, ""), "sha256_zeros": "",
                "parent": PARENT_BY_TOKEN.get(dig, ""), "axis": "", "value": "",
                "status": "SUBMITTED", "receipt": "N", "receipt_score": "",
                "predicted_change": "", "date": "", "form_note": "",
                "notes": "owner-reported; no submission-page receipt in this repo",
            })

    # 2. dated manual read of the official public leaderboard (OFFICIAL_SNAPSHOT) ------
    skipped_snapshot_rows: list[str] = []
    if SNAPSHOT.exists():
        with SNAPSHOT.open(newline="") as fh:
            for r in csv.DictReader(fh):
                if "leaderboard" not in (r.get("site") or "").lower():
                    continue
                try:
                    float(r["score"])
                except ValueError:
                    # e.g. the "rank-1..5 re-read confirmation" row, whose score cell holds a
                    # list of values; it duplicates the per-rank rows above.
                    skipped_snapshot_rows.append(r["submission"])
                    continue
                rows.append({
                    "id": f"leaderboard-{r['submission']}", "site": "official public leaderboard",
                    "name": r["submission"], "score": r["score"].strip(),
                    "evidence_class": "OFFICIAL_SNAPSHOT", "encoding": "", "n_dots": "",
                    "pct_changed": "", "sha8": "", "sha256": "", "sha256_zeros": "",
                    "parent": "", "axis": "", "value": "", "status": "OTHER_TEAM",
                    "receipt": "N", "receipt_score": "", "predicted_change": "",
                    "date": (r.get("as_of_utc") or "").strip(), "form_note": "",
                    "notes": (r.get("notes") or "").strip() or "public leaderboard only; "
                             "no file attribution; not our submission",
                })

    # 3. files BUILT this session ------------------------------------------------------
    for extra_path in (Path(args.snap_rows), Path(args.mass_rows), Path(args.prune_rows),
                       Path(args.prune_sweep_rows), Path(args.concentration_rows)):
        if extra_path.exists():
            rows.extend(json.loads(extra_path.read_text()))

    # collapse exact repeats (same content digest or same core name, same score) -------
    collapsed: dict[str, dict] = {}
    for r in rows:
        key = collapse_key(r["site"], r["name"], str(r.get("score", "")))
        if key not in collapsed:
            collapsed[key] = dict(r)
            collapsed[key]["_sites"] = [r["site"]]
            collapsed[key]["_enc"] = [r.get("encoding") or ""]
            continue
        cur = collapsed[key]
        if r["site"] not in cur["_sites"]:
            cur["_sites"].append(r["site"])
        if (r.get("encoding") or "") not in cur["_enc"]:
            cur["_enc"].append(r.get("encoding") or "")
    out_rows = []
    for cur in collapsed.values():
        sites = cur.pop("_sites")
        encs = [e for e in cur.pop("_enc") if e]
        row = {c: cur.get(c, "") for c in COLUMNS}
        row["site"] = "+".join(sites)
        row["encoding"] = "+".join(sorted(set(encs)))
        if len(sites) > 1 or len(set(encs)) > 1:
            row["notes"] = ((row["notes"] + "; ") if row["notes"] else "") + \
                "collapsed exact repeat (same digest, same score)"
        out_rows.append(row)

    order = {"BUILT": 0, "SUBMITTED": 1, "OTHER_TEAM": 2}
    def _score(r: dict) -> float:
        try:
            return float(r["score"])
        except (TypeError, ValueError):
            return -1.0

    out_rows.sort(key=lambda r: (order.get(r["status"], 9), -_score(r), r["name"]))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(out_rows)

    built = [r for r in out_rows if r["status"] == "BUILT"]
    subm = [r for r in out_rows if r["status"] == "SUBMITTED"]
    top = max((float(r["score"]) for r in out_rows if r["status"] == "OTHER_TEAM" and r["score"]),
              default=None)
    best = max((float(r["score"]) for r in subm if r["score"]), default=None)
    summary = {
        "rows": len(out_rows), "built": len(built), "submitted_claim": len(subm),
        "receipts_committed": sum(1 for r in out_rows if r["receipt"] == "Y"),
        "best_claim": best, "top_public_snapshot": top,
        "collapsed_repeats": len(rows) - len(out_rows),
        "skipped_nonnumeric_snapshot_rows": skipped_snapshot_rows,
    }
    print(json.dumps(summary, indent=2))
    (out.parent / "_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
