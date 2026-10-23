# Human submission card — R0 CONCENTRATION

**BUILT, not submitted and not authorized.** The human must confirm the one-entity rolling-week allowance, current `TOP_PUBLIC`, and data-use terms. Use the NaN-outside main file per the brief; the `-zeros.tif` twin is only a fallback. Upload **one file per slot**, following `SLOT_PLAN.md`.

| Slot | File in workspace (`releases/`) | Submission name | Form note (≤140 chars) | Format receipt |
|---|---|---|---|---|
| 1 | `h33-h33-2-b2-concentration10pct-20261023-06d2274f.tif` | `h33-h33-2-b2-concentration10pct-20261023-06d2274f` | `R0; move 3,765 dots (9.999%) across 1km H19 prior blocks; fixed >=3px repair; MODEL +0.005.` | `releases/h33-h33-2-b2-concentration10pct-20261023-06d2274f.json` |
| 2 | `h33-h33-2-b2-concentration15pct-20261023-8950fb40.tif` | `h33-h33-2-b2-concentration15pct-20261023-8950fb40` | `R0; move 5,648 dots (15.000%) across 1km H19 prior blocks; fixed >=3px repair; MODEL +0.008.` | `releases/h33-h33-2-b2-concentration15pct-20261023-8950fb40.json` |
| 3 | `h33-h33-2-b2-concentration20pct-20261023-2bffc619.tif` | `h33-h33-2-b2-concentration20pct-20261023-2bffc619` | `R0; move 7,530 dots (19.998%) across 1km H19 prior blocks; fixed >=3px repair; MODEL -0.006.` | `releases/h33-h33-2-b2-concentration20pct-20261023-2bffc619.json` |

## Re-read receipts and hashes

- 10% main SHA-256 `06d2274fa5e9c8d6935aec84f533cf5e9d2a8aa5059c80ab61abb7c36b1fff93`; zeros `01cd93c18297c4cb2aebe38814307281bf7250ed60fa8b1159f2da1e29df12b3`.
- 15% main SHA-256 `8950fb40314b1bc8e00a029c1a9015e8b088b1d8cdc6266b911e90c53acd6a2b`; zeros `7a4f939d02ae176eecbbdd4897d46b18ba35d6d02765baaa9a9cf6e7b7985a8c`.
- 20% main SHA-256 `2bffc6193a6746906fa3ecffdf484694e8b0874e3bbf154f54eabb5200f09d07`; zeros `bc2f2b217d4dd53e36a1dfd8009593ec2a2df0a174345a7886ee7db0bbcb1cf5`.

All six files were re-read from disk: single-band float32, EPSG:32611, sample shape/transform/bounds, unit mass in [0,1], 37,654 dots, zero catalogue mass, and every dot at Euclidean distance ≥3 px. Main files have no NaN inside and NaN outside; fallbacks are all finite with zero outside. Local PASS is not organizer acceptance.

After each human submission, copy the actual receipt score and date into `ledger/submissions.csv`. Do not replace CLAIM with RECEIPT from memory or from the leaderboard.
