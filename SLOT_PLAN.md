# SLOT PLAN — one entity, 3 scored slots/rolling week, one final file

- **Today / deadline**: 2026-10-23 → 2026-12-03 (**UNVERIFIED**, human to confirm on the competition page) = 41 days ≈ 5.9 weeks → max ~18 slots. Slots left this week / total: **UNVERIFIED (human to supply)**. `TOP_PUBLIC`: **UNVERIFIED** — the repo's 0.3195 snapshot was read 2026-10-03 (OFFICIAL_SNAPSHOT, stale) and is not a target.
- **Parent R0**: `h33-h33-2-b2` (GEMSDOE32), 37,654 unit dots at `d_cat > 2 px`, 0.2778 **CLAIM** (no organizer receipt in repo; `ledger/submissions.csv` receipts = 0). Rebuilt byte-identically again this session (`evidence/r0_rebuild_receipt_20261023_prune.json`).
- **BUILT, unscored (8 files = 8 potential slots)**: MASS ×3, SNAP ×3, PRUNE ×2 — `h33-h33-2-b2-prune-dcatgt3px-20261023-a7d86ed4` (swap 2,171 ring dots, 11.53% changed) and `h33-h33-2-b2-prune-dcatgt1px-20261023-f5c7e4fb` (2,492 ring dots in, 13.24% changed), both at exactly 37,654 dots (`evidence/r0_prune_variants_20261023.json`). This session's AXIS was agent-selected, not human-assigned (IR-DEC-08); IR-DEC-07 fixed the silent H33-A band-sentinel failure in the ranking pipeline.
- **Evidence discipline**: every number below is CLAIM / MODEL / PROXY as labelled; a live change < 0.01 on the public chunks is **no evidence** (brief §5); the human records `receipt_score` + date in the ledger after each manual upload. Upload **one** file per slot (`.tif` = NaN outside footprint per spec; `-zeros.tif` only if the portal rejects NaN).

## Next 3 slots in order (Week 1 — AXIS=MASS, unchanged)

| Slot | File (`releases/`) | Change vs R0 | Predicted (MODEL) | What the receipt changes |
|---:|---|---|---|---|
| 1 | `h33-h33-2-b2-mass-drop10pct-20261023-2cde51f3` | −3,765 lowest-ranked dots → 33,889 | +0.0020..+0.0045 | > R0: R0 is over-budgeted, 33,889-dot parent candidate; slot 3 tests deeper. < R0: tail decile earns its keep. |
| 2 | `h33-h33-2-b2-mass-add10pct-20261023-ad925bd2` | +3,765 next-ranked dots → 41,419 | −0.0030..+0.0025 | > R0: test-set prevalence supports >37.6k dots. < R0: secondary ridges dilute below break-even. |
| 3 | `h33-h33-2-b2-mass-drop20pct-20261023-62bfc392` | −7,531 dots → 30,123 | +0.0010..+0.0065 | With slots 1–2, fits DTI(S) at S ∈ {30123, 33889, 37654, 41419} and locks S\* before any combination build. |

Fold-clean hide-and-recover (PROXY, n=22,893): R0 0.10564 [0.09363, 0.11696]; drop10 0.10439; add10 0.10737; drop20 0.10149 — report-only, historically −0.87..+0.54 correlated with live.

## Week 2 (slots 4–6) — SNAP mid-dose, then PRUNE tighten

| Slot | File | Predicted (MODEL) | What the receipt changes |
|---:|---|---|---|
| 4 | `h33-2-b2-snap2p0px-g0p02-20261023-b2019f55` (4,152 dots moved ≤2 px, mean 1.91 px) | +0.0074..+0.0185 | Mid-dose SNAP: ≥ R0+0.01 ⇒ positional correction is real, spend slot 6 on high-dose `…snap2p0px-g0p01-20261023-7bdaa58b`. |
| 5 | `h33-h33-2-b2-prune-dcatgt3px-20261023-a7d86ed4` | +0.001..+0.007 | ≥ R0+0.01 ⇒ misregistration-halo model supported; build conditional `d_cat>4 px` next session. ≤ R0−0.01 ⇒ (2,3] px ring carries real splays; collar stays at 2 px. |
| 6 | Conditional: SNAP high-dose (above) if slot 4 ≥ R0+0.01; else PRUNE `h33-h33-2-b2-prune-dcatgt1px-20261023-f5c7e4fb` (pred −0.007..+0.001, bracketing arm) **only if** slot 5 lands in the no-evidence band and collar remains the key unknown; else SNAP low-dose `h33-2-b2-snap1p4px-g0p02-20261023-0b6a2ab2` for dose-response. | — | Do not spend slot 6 on a second collar arm if slot 5 was decisive. |

PRUNE fold-clean PROXY (n=22,893): R0 0.10564; `d_cat>3` 0.10486 (Δ −0.0008, CI spans 0); `d_cat>1` 0.10358 (Δ −0.0021, CI excludes 0). SGMC control is structurally biased toward the tight collar on this axis (IR-DEC-09) — never rank the PRUNE arms by it.

## Weeks 3–6

- **Weeks 3–4 (slots 7–12)**: combine the winning single axes only — rebuild at S\* with (winning collar) × (winning SNAP dose), one interaction per build, same ranking pipeline (post-IR-DEC-07). Any axis whose receipts all sit in the no-evidence band stays at its R0 setting.
- **Weeks 5–6 (slots 13–18)**: confirm the best combination once, choose the final file + one fallback, re-validate both formats from disk, and hold slots in reserve. TRACKB (≥1 km strike-consistent traces, GeoJSON + raster + per-trace evidence paragraphs) is Phase-2 preparation, not a weekly slot, unless the human decides otherwise.

## Proposed for later sessions (not built)

1. **Conditional `PRUNE d_cat>4 px` (refill to S\*)** — only if slot 5 ≥ R0+0.01. *Mechanism*: extends the collar beyond the 300 m kernel radius; tests whether the halo is really bounded by positional uncertainty. *Confounder*: genuine splays at 300–400 m from mapped traces. *Falsifier*: scores below the `d_cat>3` receipt.
2. **`TIP_CONE`** — shift 10% of dots from isolated intrabasinal ridges (`d_cat > 40 px`) into ±22°, 0.3–2.5 km along-strike cones ahead of catalogue fault terminations, corroborated by gravity-gradient / LiDAR scarplets. *Mechanism*: normal faults grow by tip propagation and relay linkage. *Confounder*: fan-head trenches at fault tips. *Falsifier*: live < R0 while the SGMC control rises (whole unmapped structures, not tip extensions).
3. **`SUBSURFACE_ANCHOR`** — reallocate 10% of dots from DEM-only ridges (`corrob_count == 1`) to basement-depth / MT-conductivity step ridges under Quaternary cover and the 24.6% of footprint without 1 m LiDAR. *Mechanism*: blind hydrothermal faults image in basement/MT steps where scarps are buried. *Confounder*: playa brine conductors, caldera ring contacts. *Falsifier*: live < MASS−10% receipt (worse than just deleting the bottom decile).
4. The earlier `COLLAR_REFILL` proposal is **built** as slot 5 above — with one recorded difference: the shipped arm swaps all 2,171 dots at `d_cat ∈ (2,3] px` including the 560 at exactly 3.0 px, where the proposal kept those (≥3 px).
