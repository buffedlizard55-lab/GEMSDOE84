# AI Use Disclosure — GEMSDOE84 PRUNE Session 2026-10-23

> Required by competition rules (reproducible code, generative-AI disclosure).

## What AI wrote

- Verified manifest hashes for 3 core files (MATCH) and parent R0 `h33-h33-2-b2` sha256 `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9` via `distance_transform_edt` audit.
- Built 3 PRUNE variants from parent’s 37,654 dots using `scipy.distance_transform_edt` on catalogue mask, with random refill (seed 520–522) to hold count, in `releases/` (`-zeros.tif` and `.tif` twins) via `rasterio` with exact `EPSG:32611` CRS/shape/transform.
- Generated `ledger/submissions.csv`, `SLOT_PLAN.md`, `ledger/mechanism_cards.md`, `IRREGULARITIES.md`, `docs/SUBMIT.md` and this file.
- All code is pinned: `requirements.txt` (`numpy`, `scipy`, `rasterio`, `scikit-learn`, etc.), git SHA logged in `run_card.json`-style receipts, fixed seeds.

## What the human decided

- Chose parent R0 `h33-h33-2-b2` as incumbent (0.2778 CLAIM until receipt in `ledger/`).
- Assigned AXIS=PRUNE for this session (per brief §5; if you prefer MASS/CONCENTRATION/etc., say so and we will rebuild).
- Will submit from own registered account (agent never contacts `dropbox.com`/`drivendata.org`), fills `receipt_score`/`receipt_date`, confirms TOP_PUBLIC 0.4413 and deadline 2026-12-03 on competition page, and chooses final file blind.

## Reproducibility

```bash
python -m pytest -q  # format/validator tests
python scripts/validate_submission.py releases/h33-h33-2-b2-PRUNE3-20261023-10737d46-zeros.tif --reference data/bridge/sample_submission.tif
# rebuild: python /tmp/build_prune_variants.py (needs parent tif at /tmp/g32/... + data/bridge/*)
```

