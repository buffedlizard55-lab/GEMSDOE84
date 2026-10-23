"""Regression guards across all downloadable GEMSDOE84 artifacts (promoted H84-KTHM + archived H84-CSAT & H84-THMS)."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KTHM_NAME = "gems84-h84-kthm-tworegime-58000px-20261022T235900Z-zeros"
THMS_NAME = "gems84-h84-thms-dink300-37654dots-20261022-2f4190b4-zeros"
CSAT_NAME = "gemsdoe84-h84-csat-d28-20261022T234500Z-a5483424-zeros"
CTHF_NAME = "gemsdoe84-cthf-ctfo-20261023T013252Z-8c0b5a8b-zeros"
ALLOWED_PREFIXES = (KTHM_NAME, THMS_NAME, CSAT_NAME, CTHF_NAME)


def test_docs_downloads_contains_only_verified_candidate_binaries():
    bins = [p.name for p in (ROOT / "docs/downloads").iterdir() if p.suffix.lower() in {".tif", ".tiff", ".zip"}]
    assert bins, "verified downloads missing"
    assert all(b.startswith(ALLOWED_PREFIXES) for b in bins), f"unexpected binary in docs/downloads: {bins}"
    assert not any("nan" in b.lower() for b in bins)


def test_no_nan_tif_anywhere_under_docs():
    bad = [str(p) for p in (ROOT / "docs").rglob("*") if p.suffix.lower() in {".tif", ".tiff"} and "nan" in p.name.lower()]
    assert bad == []


def test_archived_tif_sha_matches_fresh_audit():
    audit = json.loads((ROOT / "evidence/fresh_audit_20261023.json").read_text())
    h = hashlib.sha256((ROOT / "submissions" / f"{THMS_NAME}.tif").read_bytes()).hexdigest()
    assert h == audit["tif"]["sha256"]
    assert audit["format_range_gate_pass"] is True
    assert audit["values"]["n_nan"] == 0 and audit["values"]["in_range_0_1"] is True
    assert len(audit["portal_note"]) <= 140


def test_sources_use_competition_306_not_311():
    assert "competitions/311" not in (ROOT / "registry/sources.json").read_text()


def test_promoted_kthm_and_archived_csat_integrity():
    kthm = json.loads((ROOT / "evidence/run_card.json").read_text())
    assert kthm["verdict"] == "promote"
    assert kthm["safe_to_submit"] is True
    assert kthm["submission_authorized"] is False
    assert kthm["submission_slots_used"] == 0
    for rel in (f"docs/downloads/{KTHM_NAME}.tif", f"submissions/{KTHM_NAME}.tif"):
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == kthm["raster_sha256"]

    card = json.loads((ROOT / "evidence/run_card_csat.json").read_text())
    assert card["verdict"] == "negative"
    assert card["submission_authorized"] is False
    assert card["submission_slots_used"] == 0
    assert card["note_chars"] <= 140 and len(card["note"]) <= 140
    assert card["validator_output"]["all_checks_passed"] is True
    assert card["independent_validator_output"]["format_valid"] is True
    for rel in (f"docs/downloads/{CSAT_NAME}.tif", f"submissions/{CSAT_NAME}.tif"):
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == card["raster_sha256"]
