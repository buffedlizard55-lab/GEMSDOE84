"""2026-10-23 regression guards (IR-84-08/09): only the H84-THMS review artifact is downloadable."""
import hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
NAME = "gems84-h84-thms-dink300-37654dots-20261022-2f4190b4-zeros"

def test_docs_downloads_contains_only_primary_review_binaries():
    bins = [p.name for p in (ROOT/"docs/downloads").iterdir() if p.suffix.lower() in {".tif",".tiff",".zip"}]
    assert bins, "promoted download missing"
    assert all(b.startswith(NAME) for b in bins), f"non-promoted binary in docs/downloads: {bins}"
    assert not any("nan" in b.lower() for b in bins)

def test_no_nan_tif_anywhere_under_docs():
    bad = [str(p) for p in (ROOT/"docs").rglob("*") if p.suffix.lower() in {".tif",".tiff"} and "nan" in p.name.lower()]
    assert bad == []

def test_promoted_tif_sha_matches_fresh_audit():
    audit = json.loads((ROOT/"evidence/fresh_audit_20261023.json").read_text())
    h = hashlib.sha256((ROOT/"submissions"/f"{NAME}.tif").read_bytes()).hexdigest()
    assert h == audit["tif"]["sha256"]
    assert audit["format_range_gate_pass"] is True
    assert audit["values"]["n_nan"] == 0 and audit["values"]["in_range_0_1"] is True
    assert len(audit["portal_note"]) <= 140
    assert audit["docs_downloads_inventory"]
    assert all(item["submission_authorized"] is False for item in audit["docs_downloads_inventory"])
    assert all(item["is_primary_review_artifact"] for item in audit["docs_downloads_inventory"])

def test_sources_use_competition_306_not_311():
    assert "competitions/311" not in (ROOT/"registry/sources.json").read_text()
