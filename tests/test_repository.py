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
    for page in sorted((ROOT / 'docs').glob('*.html')):
        links = Links()
        links.feed(page.read_text())
        for target in links.targets:
            if '://' not in target and not target.startswith('#'):
                assert (page.parent / target.split('#')[0]).is_file(), (page.name, target)


def test_archived_evidence_integrity():
    for entry in json.loads((ROOT / 'research/source-receipts.json').read_text()):
        assert hashlib.sha256((ROOT / entry['local']).read_bytes()).hexdigest() == entry['sha256']


def test_synchronized_run_cards_and_validated_artifact():
    c1 = (ROOT / 'evidence/run-card.json').read_text()
    c2 = (ROOT / 'evidence/run_card.json').read_text()
    c3 = (ROOT / 'docs/data/run-card.json').read_text()
    assert c1 == c2 == c3, "All 3 machine-readable run card locations must be byte-synchronized"

    card = json.loads(c1)
    assert card['verdict'] in ('negative', 'promote')
    assert card['submission_slots_used'] == 0
    assert len(card['note']) <= 140
    assert len(card['submission_name']) <= 140
    assert card['leakage_canary']['passed'] is True
    assert card['leakage_canary']['max_single_feature_auc'] <= 0.90

    if card['verdict'] == 'negative':
        assert card['submission_authorized'] is False

    sub = card['submission']
    tif_docs = ROOT / 'docs/downloads' / sub['file']
    zip_docs = ROOT / 'docs/downloads' / sub['zip_file']
    tif_sub = ROOT / 'submissions' / sub['file']
    assert tif_docs.is_file() and zip_docs.is_file() and tif_sub.is_file()
    assert tif_docs.read_bytes() == tif_sub.read_bytes()
    assert hashlib.sha256(tif_docs.read_bytes()).hexdigest() == card['raster_sha256']
    with zipfile.ZipFile(zip_docs) as zf:
        assert zf.namelist() == [sub['file']]
        assert zf.read(sub['file']) == tif_docs.read_bytes()


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
