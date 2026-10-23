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


def test_blocked_card_and_no_fake_prediction():
    card = json.loads((ROOT / 'docs/data/run-card.json').read_text())
    assert card['verdict'] in ('negative', 'promote')
    note = card.get('note') or card.get('submission_note') or ''
    assert len(note) <= 140
    assert card.get('submission_authorized') is False
    p = ROOT / card['submission_file']
    assert p.is_file()
    assert hashlib.sha256(p.read_bytes()).hexdigest() == card['audited_artifact']['sha256']


def test_synchronized_cthf_run_cards_and_validated_artifact():
    c1 = (ROOT / 'evidence/run_card_cthf.json').read_text(encoding='utf-8')
    c2 = (ROOT / 'registry/run_card_cthf.json').read_text(encoding='utf-8')
    c3 = (ROOT / 'docs/evidence/run_card_cthf.json').read_text(encoding='utf-8')
    assert c1 == c2 == c3

    card = json.loads(c1)
    tif = ROOT / card['submission_file']
    zip_p = ROOT / card['submission_zip']
    assert tif.is_file() and zip_p.is_file()
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == card['raster_sha256']
    with zipfile.ZipFile(zip_p) as zf:
        assert zf.namelist() == [tif.name]
        assert zf.read(tif.name) == tif.read_bytes()


def test_cthf_pipeline_sklearn_fallback_without_lightgbm():
    import numpy as np
    sys.path.insert(0, str(ROOT / 'vendor'))
    sys.path.insert(0, str(ROOT / 'src'))
    from gems84 import cthf_pipeline as cp

    orig = cp.lgb
    try:
        cp.lgb = None
        rng = np.random.default_rng(84)
        X = rng.normal(size=(240, 6)).astype(np.float32)
        y = (X[:, 0] + 0.5 * X[:, 1] > 0.2).astype(np.int8)
        preds = cp._fit_two_model_ensemble(X[:180], y[:180], X[180:], seed=84)
        assert preds.shape == (60,)
        assert np.isfinite(preds).all() and (preds >= 0.0).all() and (preds <= 1.0).all()
    finally:
        cp.lgb = orig
