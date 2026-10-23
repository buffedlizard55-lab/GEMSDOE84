# SUBMIT — what the human uploads, in slot order

Built 2026-10-23 from parent **R0 = `h33-h33-2-b2`** (SHA-256
`c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`, rebuilt byte-identically —
`evidence/r0_rebuild_receipt.json`). **The agent never submits.** Upload one file per slot from
your own registered account, at <https://www.drivendata.org/competitions/306/competition-doe-gems/>.

**Upload the `-zeros.tif` twin.** All three `-zeros.tif` files were re-checked with the repo's
independent validator and passed every check
(`python scripts/validate_submission.py <file> --template …/sample_submission.tif` →
`format_valid: true`, footprint 5,167,373 px, exit 0). The `.tif` NaN twins match the brief's
"null/NaN outside the footprint" wording but **fail that validator's all-finite rule**
(`finite_all: false`), which is the historical `IR-57-NAN-02` failure mode; the brief records
that the two encodings score identically, so the zeros twin is the safer upload and the NaN twin
is the fallback.

---

## Slot 1 — `h33-2-b2-snap1p4px-g0p02-20261023-0b6a2ab2`

- **File:** `releases/h33-2-b2-snap1p4px-g0p02-20261023-0b6a2ab2-zeros.tif` (219,328 B,
  SHA-256 `24239d99cf95c06186060c192c862c822d31d5632073e0de27c0443565dd1c5e`)
- **Name:** `h33-2-b2-snap1p4px-g0p02-20261023-0b6a2ab2`
- **Note (87 / 140 chars):**
  `R0 + snap 1p4px-g0p02 (2,416/37,654 dots moved, mean 1.38 px); predicted +0.004..+0.011`
- **Change vs R0:** 2,416 of 37,654 dots (**6.416 %**) moved, mean 1.383 px, max 1.414 px, each
  onto a stronger `tmi_hg` / `iso_grav_anom_hg` crest inside a 1.42 px disc. Count, mass and
  exclusions unchanged.
- **Format receipt (re-read from disk):** EPSG:32611 · 3730×3292 · float32 · 1 band ·
  transform `(100, 0, 243350, 0, -100, 4508550)` · nodata `None` · 37,654 dots ·
  in-footprint min 0.0 max 1.0, 0 NaN of 5,167,373 · outside footprint 7,111,787 cells all 0.0 ·
  0 dots on catalogue pixels · min `d_cat` 2.236 px (parent's exclusion preserved, see
  `IRREGULARITIES.md` IR-84-S2) · 1 km block-density CV 1.8834 → 1.8819.
- **Predicted live change:** `+0.004 … +0.011` (**MODEL**). Treat anything under `+0.01` as no
  evidence.

## Slot 2 — `h33-2-b2-snap2p0px-g0p02-20261023-b2019f55`

- **File:** `releases/h33-2-b2-snap2p0px-g0p02-20261023-b2019f55-zeros.tif` (219,126 B,
  SHA-256 `259a8d88eb3f06a557f20a24fc137f6d8b3cf66f36ffe2e4221417561b960d38`)
- **Name:** `h33-2-b2-snap2p0px-g0p02-20261023-b2019f55`
- **Note (87 / 140 chars):**
  `R0 + snap 2p0px-g0p02 (4,152/37,654 dots moved, mean 1.91 px); predicted +0.007..+0.018`
- **Change vs R0:** 4,152 dots (**11.027 %**) moved, mean 1.910 px, max 2.000 px; same gate,
  window 2.0 px.
- **Format receipt:** identical shape/CRS/dtype/band/transform/nodata; 37,654 dots; in-footprint
  min 0.0 max 1.0, 0 NaN; 7,111,787 outside cells all 0.0; 0 dots on catalogue; min `d_cat`
  2.236 px; CV 1.8834 → 1.8819.
- **Predicted live change:** `+0.007 … +0.019` (**MODEL**). Spend this slot only if slot 1 came
  back `>= +0.01`.

## Slot 3 — `h33-2-b2-snap2p0px-g0p01-20261023-7bdaa58b`

- **File:** `releases/h33-2-b2-snap2p0px-g0p01-20261023-7bdaa58b-zeros.tif` (219,274 B,
  SHA-256 `9bec3cc89934e86823a8bb8fc7aebb80552566b5e44c89206a2f9d4c7eb1b481`)
- **Name:** `h33-2-b2-snap2p0px-g0p01-20261023-7bdaa58b`
- **Note (87 / 140 chars):**
  `R0 + snap 2p0px-g0p01 (9,966/37,654 dots moved, mean 1.90 px); predicted +0.018..+0.044`
- **Change vs R0:** 9,966 dots (**26.467 %**) moved, mean 1.898 px, max 2.000 px; loosest gate.
- **Format receipt:** identical shape/CRS/dtype/band/transform/nodata; 37,654 dots; in-footprint
  min 0.0 max 1.0, 0 NaN; 7,111,787 outside cells all 0.0; 0 dots on catalogue; min `d_cat`
  2.236 px; CV 1.8834 → 1.8855.
- **Predicted live change:** `+0.018 … +0.044` (**MODEL**). Top of the dose ladder; run it only
  if slots 1 and 2 were both positive.

---

## Before you upload

1. Refresh **TOP_PUBLIC** and **slots left this week** in the README CURRENT STATE block and in
   `SLOT_PLAN.md`; this session could not read drivendata.org.
2. Read `IRREGULARITIES.md` **IR-84-S1** (uniqueness protocol conflict) and **IR-84-S2**
   (≥3 px ring vs the parent's own exclusion). Either one can veto these files.
3. After each score comes back, put it in `ledger/submissions.csv`
   (`receipt = Y`, `receipt_score`, `date`) — that is the only thing that turns a CLAIM into a
   RECEIPT.

Reproduce everything with:

```bash
python scripts/restore_pinned_inputs.py     # sha256-verified inputs (codeload.github.com only)
python scripts/rebuild_r0.py                # parent must rebuild byte-identical
python scripts/build_snap_variants.py       # build + gate + write releases/
python scripts/build_ledger.py              # ledger/submissions.csv
python scripts/measure_snap_reports.py      # REPORT-ONLY: proxy, canary, SGMC control
python -m pytest -q                         # 112 tests, incl. the metric-algebra and rebuild gates
```
