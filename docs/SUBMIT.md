# Submit — next slots (human submits from their own account; agent never submits)

Upload **one** file per slot. The `.tif` (NaN outside footprint, per spec) is
primary; the `-zeros.tif` twin has identical dots — use it only if the portal
rejects the primary. Never upload both twins (wastes a slot; they score the
same). After downloading, verify the sha256 matches before uploading.

## Slot 1 — PRUNE B=3

- File: `releases/h33-h33-2-b2-prune3r-20261023-8316df41.tif`
  sha256 `8316df414c25e85c88d9b186ec4f14818d7d02f99ad1a8d0cd839982d2f98880`
- Fallback twin: `…-8316df41-zeros.tif`
  sha256 `af6106f1f6e03795bfe6f95aa9802d7527deced05122e6bb1d105645245810b9`
- Submission name: `h33-h33-2-b2-prune3r-20261023-8316df41`
- Form note (102/140): `Parent h33-h33-2-b2 0.2778 CLAIM; PRUNE B=3+local refill 37654 dots, 5.77% replaced; pred +0.004 MODEL`
- Predicted change: +0.004 [−0.003,+0.011] MODEL vs R0 (not a score).
- Format receipt: all brief-v2 MUST gates PASS on re-read (single band,
  float32, EPSG:32611, 3730×3292, sample transform/bounds, finite [0,1] in
  footprint, NaN outside [resp. zeros], 0/37,654 dots on catalogue, min
  catalogue distance 3.16 px) — `releases/validation/…8316df41.nan.json`.

## Slot 2 — PRUNE B=4 (only per SLOT_PLAN decision tree)

- File: `releases/h33-h33-2-b2-prune4r-20261023-2459d700.tif`
  sha256 `2459d700be1ef5c7ab8a7360bcd8c2c5b86279ba1c1d04d613d37096f752a2d8`
- Fallback twin: `…-2459d700-zeros.tif`
  sha256 `6713c898da7afd2c8c0a3d27563a46cae57403453627dfc635b8305441103614`
- Submission name: `h33-h33-2-b2-prune4r-20261023-2459d700`
- Form note (103/140): `Parent h33-h33-2-b2 0.2778 CLAIM; PRUNE B=4+local refill 37654 dots, 10.16% replaced; pred +0.005 MODEL`
- Predicted change: +0.005 [−0.008,+0.018] MODEL vs R0.
- Format receipt: MUST gates PASS (as above; min catalogue distance 4.12 px)
  — `releases/validation/…2459d700.nan.json`.

After each submission: paste the receipt score + date into the matching BUILT
row of `ledger/submissions.csv` (that is what upgrades CLAIM→RECEIPT), and
fill TOP_PUBLIC + remaining slots. Read results only against the 0.01
evidence bar in `SLOT_PLAN.md`.
