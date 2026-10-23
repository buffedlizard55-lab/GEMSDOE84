# How to Submit — GEMSDOE84 Controlled PRUNE Variants (2026-10-23)

**Parent:** `h33-h33-2-b2` (GEMSDOE32, 37,654 dots, verified sha256 `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`, claimed 0.2778 CLAIM).  
**This session AXIS:** PRUNE — 3 controlled variants, each 37,654 dots (0.73% of 5.17M footprint), zero mass on catalogue.

## Which file to upload (choose ONE per slot)

You (human) submit from *your own registered account* — the agent never contacts `dropbox.com` or `drivendata.org`.

| Priority | File to upload (DriveData “single-band GeoTIFF or .zip containing one GeoTIFF”) | Submission name (≤140 chars) | Note (≤140 chars, copy-paste) | Why |
|---|---|---|---|---|
| **Slot 1 — Recommended first** | `releases/h33-h33-2-b2-PRUNE3-20261023-10737d46-zeros.tif` (`293 KiB`, `float32`, `EPSG:32611`, `3730×3292`) | `h33-h33-2-b2-PRUNE3-20261023-10737d46` | `h33-h33-2-b2 PRUNE3 (≤3px) 37.6k dots 5.77% changed; predicted +0.006 (remove FP, keep blind far)` (107 chars) | Most mechanism-backed: removes 2–3 px ring (2,171 dots), median 19.65→21.54 px, CV 0.799→0.785 |
| Slot 2 — Contrarian | `releases/h33-h33-2-b2-PRUNE1-20261023-29e1ae46-zeros.tif` | `h33-h33-2-b2-PRUNE1-20261023-29e1ae46` | `h33-h33-2-b2 PRUNE1 (≤1px) 37.6k dots 6.76% changed; predicted -0.004 (more FP near catalogue)` (104 chars) | Tests if hidden faults are parallel splinters |
| Slot 3 — Stress | `releases/h33-h33-2-b2-PRUNE4-20261023-f1facecf-zeros.tif` | `h33-h33-2-b2-PRUNE4-20261023-f1facecf` | `h33-h33-2-b2 PRUNE4 (≤4px) 37.6k dots 10.16% changed; predicted +0.002 (aggressive prune)` (104 chars) | Diminishing-returns check |

> **Which twin?** Use the `-zeros.tif` (all 12,279,160 pixels finite, `0.0` outside footprint, `0` on catalogue). The plain `.tif` (NaN outside) is the spec-literal twin — it validates as “no NaN inside footprint, NaN outside” but will trigger the portal’s `“Predicted values must be in range [0, 1]”` IEEE-754 bug (IR-57-NAN-02). Upload *only one* per slot.

## Format receipt (local validator, not organizer acceptance)

All three `-zeros.tif` files **PASS** `vendor/gems57/validate.py` + `scripts/validate_submission.py` re-read from disk:

```
h33-h33-2-b2-PRUNE1-20261023-29e1ae46-zeros.tif  PASS  sha256 29e1ae461adbe24d908b79fbeeb492c06129ec17caabd8256ca4f1fb690c075c  37,654 dots  n_nan 0  min 0.0 max 1.0  zero_on_catalogue True
h33-h33-2-b2-PRUNE3-20261023-10737d46-zeros.tif  PASS  sha256 10737d46c136beed93a5d4eb64bbd46d52554420c61bb8547426c51766cec58f  37,654 dots  n_nan 0  min 0.0 max 1.0  zero_on_catalogue True
h33-h33-2-b2-PRUNE4-20261023-f1facecf-zeros.tif  PASS  sha256 f1facecf6f79155ac24963525d2253cf2838acb519eec9d98ebe1b054de6bb9e  37,654 dots  n_nan 0  min 0.0 max 1.0  zero_on_catalogue True
```

Checks enforced: single-band `float32`, CRS `EPSG:32611`, shape `3730×3292`, transform `100,0,243350,0,-100,4508550`, `no_nan_anywhere`, `range_0_1_guaranteed`, `zero_dots_on_mapped_catalogue`, `outside_footprint_zero`, SHA256 not in ledger.

The NaN twins (`*.tif` without suffix) show `no_nan_anywhere False` (7,114,860 NaN outside, expected) but `in_footprint_all_finite True` — spec-correct, portal-failing.

## Ledger row to fill after submission

`ledger/submissions.csv` has one BUILT row per variant (id, parent, axis, value, n_dots, % changed, sha256, predicted change). After you receive a receipt, fill `receipt_score` and `receipt_date` (YYYY-MM-DD) and keep the receipt PDF/screenshot in `ledger/` (not pushed). Treat live Δ <0.01 as no evidence (public chunks only).

## Steps on DrivenData

1. Go to https://www.drivendata.org/competitions/306/competition-doe-gems/ → “Submit” (logged in as your entity).
2. Upload the chosen `-zeros.tif` (or its `.zip` if you zipped single GeoTIFF). Do NOT upload the NaN twin.
3. Paste the matching **Submission name** and **Note** above (both ≤140 chars; note length shown).
4. Keep the receipt; we will log it as **RECEIPT** (vs CLAIM/PROXY/MODEL) in `ledger/submissions.csv` and re-validate format blind before final file choice.

