# Forensic & Mathematical Analysis of `GEMSDOE32`'s `H33-2-B2` (`0.2778`)

## 1. Provenance Classification

- **`0.2778` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`, `GEMSDOE32`):** **`OWNER-REPORTED`** (private team submission score recorded in `registry/live_scores.csv`).
- **`0.4413` (`#1 xiaofanhu`, 27 submissions; `#2 cfld__ = 0.3904`; `#3 Batik Shirt Brothers = 0.3904`; `#4 BrandenKMurray = 0.3713`; `#5 No Fault of Our Own = 0.3539`):** **`ORGANIZER-CONFIRMED`** via live retrieval of <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> on `2026-10-22`.
- **`0.3195` (cited in user prompt):** Corresponds to an earlier top-tier snapshot now near rank `#21` (`kinghorton42 = 0.3261`) / `#22` (`li002666 = 0.3183`) (`ORGANIZER-CONFIRMED`).

## 2. Exact Zero-New-TP Algebraic Proof (`evidence/incumbent_anatomy.json`)

Under the official Distance-Tolerant IoU (`alpha = 0.2`, `beta = 0.8`, `R = 300 m` / `3 px` linear triangular kernel `k(d) = max(1 - d/3, 0)`):

```
DTI = TP_w / (TP_w + 0.2 * FN_w + 0.8 * FP_w)
```

Byte-exact comparison across `19GEMSDOE` (`h19-5`), `GEMSDOE24` (`d1-5`), `GEMSDOE25` (`d2-8`), and `GEMSDOE32` (`h33-1-b1`, `h33-2-b2`) establishes that every step is a strict subset pruning operation adding **zero** new fault pixels:

| Stage | Nonzero Pixels / Dots | Live DTI (`OWNER-REPORTED`) | Mechanism |
|---|---:|---:|---|
| `h19-5` (`19GEMSDOE`) | `121,131` | `0.1922` | Continuous ridge lines waste `0.8 * FP_w` on overlapping 300 m halos |
| `dotted-h19-5-d1-5` (`GEMSDOE24`) | `60,069` | `0.2477` | Discrete dot thinning cuts `FP_w` by ~50% while retaining halo union |
| `dotted-h19-5-d2-8` (`GEMSDOE25`) | `44,090` | `0.2600` | Wider spacing along fault strike reduces residual halo overlap |
| `h33-1-b1` (`d_cat > 1 px`) | `40,199` | `0.2708` | Removes `3,891` dots adjacent to pixel-exact masked `existing_faults.tif` |
| `h33-2-b2` (`d_cat > 2 px`) | `37,654` | **`0.2778`** | Removes `2,545` dots in `1 < d_cat <= 2 px`; zero-TP formula predicts **`0.27836`** (`-0.00056` residual) |

Solving the exact two-equation system from `d2-8 -> h33-1-b1` yields denominator `D_0 = 19,549.6` and weighted recall `TP_w = 5,073.3`. Removing `2,545` dots in `1 < d_cat <= 2 px` with zero true-positive loss predicts `0.27836` vs observed `0.2778`. Pushing isotropic collar pruning further (`B >= 3 px`, tested in `GEMSDOE37` `0.2602` and `GEMSDOE77` `0.2698`) amputates genuine along-strike fault-tip extensions and lowers DTI.

## 3. Historical ZIP Defect (`IR-84-12`)

Byte inspection (`evidence/h33-zip-inspection.json`) confirmed that `GEMSDOE32`'s archived `.zip` contained an empty `.zip` member rather than a `.tif`. Our shared `vendor/gems57/submission_writer.py` verifies single-member `.tif` ZIP byte identity automatically on write.

## 4. Path Beyond the `~0.295` Pruning Ceiling

Because precision pruning cannot increase `TP_w`, advancing toward top leaderboard performance (`0.35–0.44`) requires:
1. **New subsurface & hydrothermal fault discovery** (`GeoDAWN` multi-altitude tilt-worm persistence + `DOE GDR 1391` INGENIOUS `2 m` thermal/sinter/spring upflow + Coulomb transtension).
2. **Anisotropic tip-preserving collar masking** (`1 < d_cat <= 2 px` retained at fault tips, pruned along lateral flanks).
3. **`sep = 3 px` (`300 m`) minimum inter-dot spacing** across a Two-Stratum corridor + concealed-basin architecture (`H84-TCDH`).
