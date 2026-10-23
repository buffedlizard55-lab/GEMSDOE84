#!/usr/bin/env python3
"""Build ledger/submissions.csv (brief v2 sections 3 + 7).

Sources, read-only: registry/live_scores.csv (owner-reported live scores =
CLAIM; no submission-page receipts are stored in this repo) and
releases/*.json build receipts from this session type.  Exact-repeat twins
that differ only by an -nan/-zeros/-allfinite suffix (identical scores) are
collapsed into one row with encoding listing both.  The human fills
receipt_score and date from submission-page receipts; nothing here upgrades
a CLAIM to a RECEIPT.

Usage: python scripts/build_ledger.py
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLS = ["site", "name", "id", "score", "evidence", "encoding", "n_dots",
        "sha8", "sha256", "parent", "axis", "value", "pct_changed",
        "status", "predicted_change", "receipt", "receipt_score", "date"]
ENC = ("-nan", "-zeros", "-allfinite", "-zero")


def split_encoding(name: str) -> tuple[str, str]:
    for sfx in ENC:
        if name.endswith(sfx):
            return name[: -len(sfx)], sfx[1:]
    return name, ""


def sha8_of(name: str) -> str:
    tokens = re.split(r"[-_]", name)
    for tok in reversed(tokens):
        if re.fullmatch(r"[0-9a-f]{8,}", tok):
            return tok[:8]
    return ""


def main() -> None:
    rows: list[dict] = []
    collapsed: dict[tuple[str, str, str], dict] = {}
    n_raw = n_collapsed = 0
    with (ROOT / "registry" / "live_scores.csv").open() as f:
        for rec in csv.DictReader(f):
            n_raw += 1
            core, enc = split_encoding(rec["submission_name"])
            key = (rec["site_repo"], core, rec["public_score"])
            if key in collapsed:
                prev = collapsed[key]
                prev["encoding"] = "+".join(
                    sorted(set(filter(None, prev["encoding"].split("+") + [enc]))))
                n_collapsed += 1
                continue
            row = {c: "" for c in COLS}
            row.update(site=rec["site_repo"], name=rec["submission_name"],
                       score=rec["public_score"], evidence="CLAIM",
                       encoding=enc, sha8=sha8_of(core), status="logged",
                       receipt="N")
            collapsed[key] = row
            rows.append(row)
    for receipt_path in sorted((ROOT / "releases").glob("*.json")):
        r = json.loads(receipt_path.read_text())
        diff = r["parent_diff"]
        row = {c: "" for c in COLS}
        row.update(
            site="GEMSDOE84", name=r["file_nan_primary"][:-4], id=r["id"],
            evidence="MODEL", encoding="nan+zeros", n_dots=str(r["n_dots"]),
            sha8=r["sha256_nan"][:8], sha256=r["sha256_nan"],
            parent=r["parent"], axis=r["axis"], value=r["value"],
            pct_changed=str(diff["pct_of_parent_dots_replaced"]),
            status="BUILT",
            predicted_change=(f"{r['predicted_change_MODEL']['central']:+.3f} "
                              f"[{r['predicted_change_MODEL']['range'][0]:+.3f},"
                              f"{r['predicted_change_MODEL']['range'][1]:+.3f}] MODEL"),
            receipt="N")
        rows.append(row)
    out = ROOT / "ledger" / "submissions.csv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out}: {n_raw} owner-reported rows -> "
          f"{n_raw - n_collapsed} after collapsing {n_collapsed} exact-repeat "
          f"twins; +{len(rows) - (n_raw - n_collapsed)} BUILT rows; "
          f"all historic scores CLAIM (receipt=N)")


if __name__ == "__main__":
    main()
