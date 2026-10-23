# H84B-UAS results + correction to the H33 forensic record (2026-10-23)

## 1. IR-84B-02 (CRITICAL): prior H33 distance forensics were wrong
Direct measurement this session on the SHA-256-verified H33 file
(`c55bafc4700...`, 219,065 B, fetched from GEMSDOE32 `docs/downloads/`):
dots 37,654 ✓ · binary {0,1} ✓ · 0 on catalogue ✓ · min inter-dot 2.828 px ✓ ·
**d_cat: min 2.236 px, median 19.65 px, p90 68.0 px, max 219.3 px; only 34.7% within
12 px; 35.8% beyond 30 px.**
`research/why-h33-scored-02778.md` §1/§4 claims median 5.385 px, max 12.000 px, "0 dots
beyond 1.2 km" — **contradicted**. "Bottleneck 1 (1.2 km truncation)" and every design
justification built on it (incl. parts of H84-THMS) must be re-read with this correction.
The collar/pruning genealogy (37,654 = D2.8 minus 2-px collar dots, score chain
0.2600→0.2708→0.2778, all ORGANIZER-CONFIRMED per owner receipts) is *not* impugned by
this — only the distance-distribution claims are.

## 2. Why H33 scored 0.2778 (corrected PhD reading)
H33 wins because of *emission hygiene on a wide-area field*, not catalogue hugging:
(1) binary {0,1} + zeros outside footprint (portal-safe, full kernel weight);
(2) Poisson r=2.83 px ≈ kernel radius 3 px — the empirically near-optimal fixed spacing
    under the max-kernel (this session: two adaptive-spacing mechanisms both LOSE to it);
(3) 2-px catalogue collar removes pure-FP dots in the digitisation halo;
(4) budget 37,654 ≈ 0.73% of footprint, spread over ALL distance bands (median ~2 km
    from catalogue) following the H19-5 multiline-corroborated ridge ranking.
What caps it at 0.2778 vs leaderboard 0.4413 (OWNER-REPORTED): with spacing, collar, and
budget all near their fixed-parameter optima, the only remaining lever with headroom is
the **ranking quality of the underlying surface** (which 37,654 of 5.17M px), i.e.
precision of the top-ranked tail. This session's distance-blind bagged-HGB surface
(μ AUC 0.685–0.702 per fold on withheld segments) reaches HOLDOUT-DTI 0.1703 under a
strict whole-segment block holdout — not directly comparable to live scores, but the
programme implication is: stop varying emission geometry; improve top-tail ranking
(better features/labels), or find genuinely new signal (e.g. 1 m LiDAR full coverage).

## 3. H84B-UAS experimental record (all HOLDOUT-DTI, evaluator in evidence JSONs)
Pooled over 4 spatial folds, 59,282 withheld positives, budget-matched 37,653 dots:
- A0 fixed 2.83 px control: **0.1703 [0.1457, 0.1983]** (reproduced exactly in EXP-3)
- A1 σ-adaptive spacing: 0.1570 [0.1311, 0.1872] — FALSIFIED (σ = decision-boundary
  ambiguity, raw AUC 0.61–0.64 FOR faults; thinning high-σ cut TP 9,542→8,752)
- A2 A1 + far-field quota: 0.1571 — quota added nothing
- A3 soft fractional: 0.1356 — negative as linear-fractional (bang-bang) theory predicts
- A4 μ-sharpness-adaptive spacing: 0.1561 [0.1305, 0.1862] — FALSIFIED
Canary (EXP-1): max single-channel symmetric AUC 0.5735 ≤ 0.90 PASS (59 distance-blind
channels). Verdict: **lane negative**. The shipped candidate TIF is the A0 control
surface (full-catalogue training), labelled UNPROMOTED; H84-THMS remains this repo's
primary promoted file. Selector decides any portal use (protocol §6).

## 4. Can anything beat 0.2778? (judgement, not a score)
Yes in principle — the 0.4413 OWNER-REPORTED leader proves headroom exists — but the
evidence now says the path is top-tail ranking precision at fixed emission hygiene
(binary, ~2.8 px, collar >2 px, ~38k dots), not new emitters. Highest-P(win) next
steps: (i) label-side improvements (segment-level PU learning against unlabelled
faults among "negatives"); (ii) full-coverage 1 m LiDAR scarp stack (fixes the 24.6%
gap with survey data, not interpolation); (iii) ensemble diversity across *feature
families* (rank-average decorrelated surfaces) evaluated at fixed budget on the same
block holdout. Each must beat HOLDOUT-DTI 0.1703 (this evaluator) before any portal slot.
