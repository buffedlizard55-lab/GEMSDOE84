import hashlib
import json
import sys
import zipfile
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
    for page in (ROOT / 'docs').glob('*.html'):
        links = Links()
        links.feed(page.read_text())
        for target in links.targets:
            if '://' not in target and not target.startswith('#'):
                assert (page.parent / target.split('#')[0]).is_file(), target


def test_archived_evidence_integrity():
    for entry in json.loads((ROOT / 'research/source-receipts.json').read_text()):
        assert hashlib.sha256((ROOT / entry['local']).read_bytes()).hexdigest() == entry['sha256']


def test_release_card_integrity():
    card = json.loads((ROOT / 'docs/data/run-card.json').read_text())
    assert not card['submission_authorized']
    assert card['submission_slots_used'] == 0
    assert len(card['note']) <= 140
    if card['verdict'] == 'negative':
        assert not card['download_allowed']
        assert card['raster_sha256'] is None
        assert not list((ROOT / 'docs').rglob('*.tif'))
    else:
        assert card['verdict'] == 'promote'
        assert card['download_allowed'] is True
        assert (ROOT / card['submission']['tif']).is_file()
        tif_files = list((ROOT / 'docs/downloads').glob('*.tif'))
        assert 1 <= len(tif_files) <= 4
        assert hashlib.sha256(tif_files[0].read_bytes()).hexdigest() == card['raster_sha256']
