# Slot plan — R0 CONCENTRATION (2026-10-23)

**No slot is authorized by this repository.** The human must supply rolling-week slots left/total and current `TOP_PUBLIC` with its date. R0 is **CLAIM 0.2778**, not a receipt. Deadline **2026-12-03 is UNVERIFIED** because DrivenData was not contacted.

## Next three scored slots, in order

| Order | Candidate (NaN-outside main; zeros twin is fallback) | Prediction | What the receipt changes |
|---|---|---|---|
| 1 | `h33-h33-2-b2-concentration10pct-20261023-06d2274f` | MODEL +0.005 | **≥+0.01:** keep the axis and test 15%. **≤−0.01:** stop this axis; do not spend slots 2–3 on it. **Between:** no evidence; make no claim and use the pre-registered 15% arm only if a dose test is still the priority. |
| 2 | `h33-h33-2-b2-concentration15pct-20261023-8950fb40` | MODEL +0.008 | **≥+0.01 and ≥0.01 above slot 1:** test 20% for saturation. Otherwise stop dose escalation; a negative result retires the occupied-block-CV motivation. |
| 3 | `h33-h33-2-b2-concentration20pct-20261023-2bffc619` | MODEL −0.006 | A positive result ≥0.01 contradicts the saturation prediction and requires confirmation before any combination; a negative result supports stopping at the best *receipted* lower dose. Never choose from PROXY results. |

Upload only one encoding per slot. Every arm contains the same mandatory ≥3 px repair, so a delta from R0 is **not a pure concentration estimate**; dose-to-dose receipts are the cleaner comparison.

## Weeks to the deadline

- **Wk1–2 (Oct 23–Nov 5):** the three conditional slots above, then the remaining assigned-axis experiments only if receipts justify them.
- **Wk3–4 (Nov 6–19):** combine at most the two axes with receipted gains ≥0.01; otherwise continue single-axis controls.
- **Wk5–6 (Nov 20–Dec 3):** confirm the final and fallback blind, re-read both formats, and reserve no more than the one-entity limits. There are 41 calendar days (~5.9 weeks); available slots remain unknown.

## Proposed later axes — not built this session

1. **CONCENTRATION / 2 km blocks:** test whether fault-process corridors persist beyond survey-position uncertainty. Confounder: changed block support and the same 3 px repair. Falsifier: a receipted ≥0.01 loss when the 1 km arm gains.
2. **SNAP / TMI+gravity, ≤2 px:** align dots with independent geophysical gradients, not lidar. Confounder: unfaulted lithologic contacts and displacement toward catalogue collars. Falsifier: a receipted ≥0.01 loss despite nonzero mean displacement.
3. **RELIEF / range-front tercile:** test whether concealed range-front splays outperform basin/piedmont mass at fixed count. Confounder: H19 prior is relief-dependent. Falsifier: a receipted ≥0.01 loss or no separation from a relief-matched control.
