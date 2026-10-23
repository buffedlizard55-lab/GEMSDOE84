# R0 CONCENTRATION mechanism cards — 2026-10-23

## Controlled construction

Parent R0 (`h33-h33-2-b2`; **CLAIM 0.2778**, no receipt) was rebuilt byte-for-byte before any variant. The prior is fixed **H19-5 positive-support density in aligned 1 km (10×10 px) blocks**. Donors visit ascending-prior blocks and receivers descending-prior blocks, one move per block per pass. Receivers are vacant H19-5 support chosen by within-block max-min distance. Total mass remains 37,654 unit dots.

The literal ≥3 px rule required a shared compliance repair first (1,611 dots; see `IRREGULARITIES.md`). Thus “moved” below is the clean dose from the compliant parent; “R0 relocated” includes that repair. All-footprint-block density CV uses dots per footprint cell and includes zero-dot blocks; occupied-block count CV is a separate diagnostic.

| Arm | Moved dots | Exact moved | R0 relocated incl. compliance | Density CV: R0 → arm | Occupied-count CV: R0 → arm |
|---|---:|---:|---:|---:|---:|
| 10% | 3,765 | 9.998938% | 13.209752% | 1.885205 → 2.181383 | 0.618731 → 0.597742 |
| 15% | 5,648 | 14.999734% | 18.027301% | 1.885205 → 2.261623 | 0.618731 → 0.553546 |
| 20% | 7,530 | 19.997875% | 22.494290% | 1.885205 → 2.418171 | 0.618731 → 0.503472 |

## Card 1 — 10% (`06d2274f`)

- **Hypothesis:** a small reallocation from diffuse, low-support blocks into better-supported structural corridors can recover fault credit without materially increasing local redundancy.
- **Mechanism:** move 3,765 dots across 3,765 donor and 3,765 receiver blocks; preserve count and H19 support for every concentration-added dot.
- **Non-fault mimic:** pluvial shoreline benches, alluvial-fan distributary networks, or unfaulted lithologic contacts can create the same dense aligned lineaments without a fault.
- **Predicted live change:** **MODEL +0.005** (subjective plausible range −0.008 to +0.015, not a CI).
- **Falsifier:** a same-arm live change ≤−0.01. Any absolute change <0.01 is no evidence.

## Card 2 — 15% (`8950fb40`)

- **Hypothesis:** the middle dose captures more of the high-prior corridor population while retaining enough spatial coverage; its occupied-block count CV enters the brief's reported 0.51–0.59 range without using that range as a gate.
- **Mechanism:** move 5,648 dots across 5,648 donor and 5,648 receiver blocks using the same frozen sequences as the other arms.
- **Non-fault mimic:** the same depositional and lithologic lineaments may become more convincing as independent blocks are sampled, even though they are not fault-related.
- **Predicted live change:** **MODEL +0.008** (subjective plausible range −0.012 to +0.020, not a CI).
- **Falsifier:** a same-arm live change ≤−0.01, or failure to improve over the 10% arm by ≥0.01 when escalation is proposed.

## Card 3 — 20% (`2bffc619`)

- **Hypothesis:** the largest dose exhausts genuinely distinct high-prior corridors and begins to trade away too much broad coverage, so the dose response turns negative.
- **Mechanism:** move 7,530 dots; all 6,160 frozen donor and receiver blocks are used, with a second pass through some blocks. Occupied-count CV falls below the reported range while full-domain density CV rises.
- **Non-fault mimic:** repeated sampling of the same shoreline, fan, or contact systems can imitate corridor confirmation while adding false-positive mass.
- **Predicted live change:** **MODEL −0.006** (subjective plausible range −0.022 to +0.010, not a CI).
- **Falsifier:** a same-arm live gain ≥0.01 contradicts the saturation prediction and requires confirmation before combination with another axis.

## Report-only diagnostics

- **Catalogue PROXY:** 22,893 withheld-positive pixel instances (21,032 unique), 1,000 paired spatial-block bootstrap draws. R0 PROXY DTI 0.003885 [0.003318, 0.004453]; the compliant parent and all three arms are 0 [0,0]. This instrument is inherited-full-catalogue and especially sensitive to the mandatory collar repair; it is not a live score or gate.
- **Leakage canary (PROXY):** maximum direction-free single-feature AUC **0.589333** across eight fold-draws; below the 0.90 stop-and-investigate threshold.
- **SGMC control (PROXY):** R0 0.093694; compliant parent 0.095652; 10% 0.088872; 15% 0.086094; 20% 0.082497. Domain is footprint with `d_catalogue > 3 px`; these are auxiliary mapped-fault controls, not organizer truth.
- **Decision rule:** no PROXY or MODEL value selects a file. Only human-supplied submission receipts can become RECEIPT evidence.
