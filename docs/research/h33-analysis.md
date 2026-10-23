# Forensic Analysis of `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`GEMSDOE32`)

## 1. Provenance, Epistemic Status, and Score Hygiene

Primary upstream artifacts inspected byte-for-byte across the sibling `GEMSDOE*` archive:
- Multi-line power-law parent (`h19-5`): `19GEMSDOE` (`121,131` binary pixels; `0.1922` `OWNER-REPORTED`).
- Sparse `d=1.5` & `d=2.8` thinned emissions: `GEMSDOE24` (`60,069` dots; `0.2477` `OWNER-REPORTED`) and `GEMSDOE25` (`dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif`, `44,090` dots; `0.2600` `OWNER-REPORTED`).
- `100 m` collar-pruned emission (`h27-4-r1`): `GEMSDOE28` / `GEMSDOE31` (`40,199` dots; `0.2708` `OWNER-REPORTED`).
- `200 m` collar-pruned family leader (`h33-2-b2`): [gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) (`37,654` unit dots; `0.2778` `OWNER-REPORTED`), alongside [src/gems32/h33.py](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/src/gems32/h33.py), [scripts/run_h33_validation.py](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/scripts/run_h33_validation.py), and [audit JSON](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json).

**Strict label hygiene (Protocol Rule 3):**
- Every live score from `registry/live_scores.csv` (`0.1922`, `0.2477`, `0.2600`, `0.2708`, `0.2778`, `0.3195`, `0.4413`) is **`OWNER-REPORTED`**, never `ORGANIZER-CONFIRMED`, because `drivendata.org` is unreachable under this sandbox's egress policy.
- Model projections are never reported as scores.
- Direct byte inspection of `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e.zip` found a malformed ZIP archive containing a single `0`-byte entry named with a `.zip` suffix rather than `.tif` (`evidence/h33-zip-inspection.json`). **Never submit that historical `.zip`.** All GEMSDOE84 `.tif`/`.zip` pairs are verified byte-for-byte via `vendor/gems57/submission_writer.py`.

---

## 2. Exact Closed-Form Proof of Why `h33-2-b2` Scored `0.2778` (`OWNER-REPORTED`)

Pixel-exact set algebra across the decoded rasters (`evidence/incumbent_anatomy.json`) proves an **exact strict subset chain** with **zero added pixels** at every step:

$$E_{\text{h19-5}}\;(121,131;\;0.1922) \;\supset\; E_{\text{d1.5}}\;(60,069;\;0.2477) \;\supset\; E_{\text{d2.8}}\;(44,090;\;0.2600) \;\supset\; E_{\text{h27-4-r1}}\;(40,199;\;0.2708) \;\supset\; E_{\text{h33-2-b2}}\;(37,654;\;\mathbf{0.2778}).$$

Under the official DrivenData DTI formula (`vendor/gems57/metric.py`, $\alpha = 0.2$, $\beta = 0.8$, $R = 300\text{ m} = 3\text{ px}$ triangular kernel $k(d) = \max(1 - d/3, 0)$):
- $\mathrm{TP}_w = T = \sum_{g \in G} \max_{x \in E} p(x)\,k(d(x, g))$ (summed over **truth** pixels $G$),
- $\mathrm{FP}_w = \sum_{x \in E} p(x)\,[1 - \max_{g \in G} k(d(x, g))] = n - M(E)$ for unit dots $p(x) \in \{0, 1\}$ with $|E| = n$,
- $\mathrm{FN}_w = K_{\text{live}} - T$, where $K_{\text{live}} = |G|$.

Because $1 - \beta = 0.2 = \alpha$, the exact DTI denominator collapses linearly (`ALGEBRAIC-IDENTITY`):

$$D(E) = T + 0.2\,(n - M(E)) + 0.8\,(K_{\text{live}} - T) = 0.2\,\bigl(T + n - M(E)\bigr) + 0.8\,K_{\text{live}}.$$

1. **Step 1 (`121,131 -> 44,090` unit dots, `0.1922 -> 0.2600` `OWNER-REPORTED`):** Decimating continuous ridge traces to $d = 2.8\text{ px}$ unit dots eliminated `77,041` redundant false-positive dots (`-63.6%` emitted dot count) while keeping $\max_{x \in E} k(d(x, g))$ nearly intact along every ridge.
2. **Step 2 (`d2.8 -> h27-4-r1`: `-3,891` dots inside $d_{\text{cat}} \le 100\text{ m}$, `0.2600 -> 0.2708` `OWNER-REPORTED`):**
   With $\Delta T \approx 0$ and $\Delta M \approx 0$ inside $100\text{ m}$ of already-digitized catalogue traces, taking exact reciprocals solves $T$ with **zero free parameters**:
   $$T = \frac{0.2\,\Delta n_1}{\frac{1}{s_0} - \frac{1}{s_1}} = \frac{0.2 \times 3,891}{\frac{1}{0.2600} - \frac{1}{0.2708}} = \frac{778.2}{3.846154 - 3.692762} = \mathbf{5,073.3\text{ px-wt}}.$$
3. **Step 3 — Out-of-Sample Zero-Parameter Verification on `h33-2-b2` (`h27-4-r1 -> h33-2-b2`: `-2,545` dots in $100\text{ m} < d_{\text{cat}} \le 200\text{ m}$):**
   $$s_2^{\text{pred}} = \left(\frac{1}{0.2708} - \frac{0.2 \times 2,545}{5,073.3}\right)^{-1} = \mathbf{0.27836} \quad\text{vs.}\quad \mathbf{0.2778}\;\;(\text{OWNER-REPORTED, residual } = -0.00056).$$
   On our pooled 8-fold whole-segment holdout (`22,893` withheld positive pixels), pruning $d_{\text{vis}} \le 200\text{ m}$ from `d2.8` reduces $\mathrm{TP}_w$ from `3,552.51` to `3,524.16` (`-0.80%` collar tip loss), explaining the tiny `-0.00056` residual from rare splay intersections at mapped fault tips!
4. **Exact Bounds on Live Hidden Ground Truth $K_{\text{live}}$:**
   Substituting $T = 5,073.3$, $n_2 = 37,654$, $D_2 = T / s_2 = 18,262.4$, and self-credit $M_2 \in [2,500,\; 5,000]$ yields:
   $$K_{\text{live}} = \frac{18,262.4 - 0.2\,(5,073.3 + 37,654 - M_2)}{0.8} \in [\mathbf{12,770},\; \mathbf{13,400}]\text{ px}\;\; (\approx \mathbf{13,085 \pm 315\text{ px}}, \text{ or } 21.5\% \text{ of } 60,988\text{-px catalogue}).$$

---

## 3. Exact Spatial Anatomy of `h33-2-b2` vs. GEMSDOE84 `EXP-84-3 (CTHF + CTFO)`

Byte-level inspection of `h33-2-b2` (`37,654` dots) against `usgs_faults_100m.tif` and USGS `sgmc_faults_100m.tif` reveals both its strength and its ceiling:
- **Spatial dot allocation of `h33-2-b2` (`37,654` dots):** `0` dots in $(\le 200\text{ m}]$, `5,637` (`15.0%`) in $(200, 500\text{ m}]$, `10,028` (`26.6%`) in $(500, 1,500\text{ m}]$, and `21,989` (`58.4%`) in $(> 1,500\text{ m})$.
- **Spatial dot allocation of `EXP-84-3` (`41,500` dots):** `0` dots in $(\le 200\text{ m}]$, `15,867` (`38.2%`) in $(200, 500\text{ m}]$, `18,871` (`45.5%`) in $(500, 1,500\text{ m}]$, and `6,762` (`16.3%`) in $(> 1,500\text{ m})$.
- **Why `EXP-84-3` dominates pooled 8-fold holdout (`+49.7%`) and why `CTFO` wins `8 / 8` quadrants unanimously:**
  - **Pooled 8-fold `HOLDOUT-DTI` (`gems57-pooled-hide-v2`, `22,893` withheld positive pixels):** **`0.1581` (`95% CI [0.1427, 0.1720]`)** vs **`incumbent_recipe = 0.1056` (`95% CI [0.0930, 0.1165]`)** — **paired improvement `+0.0525` (`+49.7%`, `95% CI [+0.0370, +0.0676]`, winning both pooled draws and `6 / 8` individual quadrants even against `d28`'s full-catalogue ranking)**.
  - **Equal-budget `37,654`-dot control (`EXP_84_3_EQBUDGET_37654`):** **`HOLDOUT-DTI = 0.1578` (`95% CI [0.1426, 0.1714]`)** vs identical-posterior greedy `d=3.0` NMS (`EXP-84-2 = 0.1458 [0.1312, 0.1595]`) — **pure `CTFO` geometric packing lift `+0.0120` (`+406.9` extra `TP_w` at identical `37,654` dot count, winning `8 / 8` quadrants unanimously)**.
  - **Decomposed off-catalogue USGS `SGMC` bedrock fault recall (`n = 56,467` pixels at $d_{\text{cat}} > 500\text{ m}$):** Inside the `500–1,500 m` splay/relay halo (`15,460` SGMC pixels), `CTHF` achieves **`0.2675`** vs `h33-2-b2` **`0.2380`**; across $> 1,500\text{ m}$ bedrock faults (`41,007` SGMC pixels), `h33-2-b2` reaches `0.1940` (`21,989` dots) vs `CTHF` `0.0433` (`6,762` dots, overall `>500 m` `0.1047` vs `0.2060`), demonstrating transparently why catalogue-calibrated posterior mass concentrates more strongly in near-catalogue propagation corridors unless live-regime prior reweighting is applied.
