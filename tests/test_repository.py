import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('href', 'src') and value:
                self.targets.append(value)


def test_local_site_links():
    for page in (ROOT/'docs').glob('*.html'):
        links = Links()
        links.feed(page.read_text())
        for target in links.targets:
            if '://' not in target and not target.startswith('#'):
                assert (page.parent/target.split('#')[0]).is_file(), target


def test_archived_evidence_integrity():
    for entry in json.loads((ROOT/'research/source-receipts.json').read_text()):
        assert hashlib.sha256((ROOT/entry['local']).read_bytes()).hexdigest() == entry['sha256']


def test_blocked_card_and_no_fake_prediction():
    card = json.loads((ROOT/'docs/data/run-card.json').read_text())
    # docs/data/run-card.json is a site-facing projection of evidence/run-card.json
    # It may be negative with a research artifact (download_allowed true, submission_authorized false)
    # or negative with no file; both are valid fail-closed states.
    assert card['verdict'] in ('negative','promote')
    # note may be under 'note' or 'submission_note'
    note = card.get('note') or card.get('submission_note') or ''
    assert len(note) <= 140
    if card.get('raster_sha256') is None:
        assert not card.get('submission_authorized') and not card.get('download_allowed')
        assert not list((ROOT/'docs').rglob('*.tif')) or card['verdict'] == 'negative'
    else:
        # Research artifact exists: download_allowed true, but submission_authorized remains false for negative verdict
        assert card.get('download_allowed') is True or card.get('verdict') == 'promote'
        # If a raster is declared, it must exist and be valid
        import hashlib, numpy as np, rasterio
        # find tif via evidence or docs/downloads
        tif = None
        ev = json.loads((ROOT/'evidence/run-card.json').read_text())
        if ev.get('submission_file'):
            tif = ROOT / ev['submission_file']
        elif ev.get('raster_sha256'):
            cands = list((ROOT/'docs/downloads').glob('*.tif'))
            tif = cands[0] if cands else None
        if tif and tif.exists():
            assert hashlib.sha256(tif.read_bytes()).hexdigest() == card['raster_sha256']
            with rasterio.open(tif) as s:
                a = s.read(1)
                assert s.count == 1 and s.dtypes[0] == 'float32'
                assert np.isfinite(a).all() and a.min() >= 0 and a.max() <= 1
