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
    assert card['verdict'] == 'negative'
    assert not card['submission_authorized']
    assert not card.get('approved_for_weekly_slot', False)
    assert card['submission_slots_used'] == 0
    assert len(card['note']) <= 140
    tifs = list((ROOT/'docs').rglob('*.tif'))
    if not tifs:
        assert card['raster_sha256'] is None
    else:
        assert len(tifs) == 1
        assert hashlib.sha256(tifs[0].read_bytes()).hexdigest() == card['raster_sha256']
