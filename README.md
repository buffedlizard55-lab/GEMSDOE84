# GEMSDOE84 — an auditable fault-discovery pipeline for the DOE GEMS Prize (DrivenData #306)

**Competition:** [DOE GEMS Prize Challenge](https://www.drivendata.org/competitions/306/competition-doe-gems/)
· **Problem description:** [page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
· **Data page (login-walled):** [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
· **Public leaderboard:** [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
· **Reference solution:** [gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution)
· **Site:** <https://buffedlizard55-lab.github.io/GEMSDOE84/> · **Governing brief:** [`NORTH_STAR.md`](NORTH_STAR.md)

> ⚠️ **Read this before downloading anything.** This session's candidate submission
> **FAILED its own validation gate** (it scored below a uniform-random control on our
> holdout — see "What we found" below). It is published for audit/reproducibility only.
> **Do not submit it to the competition as a real entry.** The executive summary at
> [`docs/executive-summary.html`](docs/executive-summary.html) explains exactly how to
> submit *if and when* a future candidate clears the bar.

---

## 0. Executive answer (read this first)

1. **Every score quoted in the brief that started this session (0.2778, 0.4413, 0.3195,
   and all the per-repo numbers like "h33-h33-2-b2: 0.2778") needs a provenance check, and
   we did one.** The public DrivenData leaderboard (fetched live by us, 2026-10-22, see
   [`registry/leaderboard_snapshot.json`](registry/leaderboard_snapshot.json)) really does
   show **#1 `xiaofanhu` 0.4413** — that number is **ORGANIZER-CONFIRMED** (read straight off
   the public leaderboard page, no login needed for *viewing* it, only for submitting). The
   brief's other number, "0.3195", traces to a prior sibling session's own notes claiming a
   2026-10-04 leaderboard snapshot with `#3 DARD = 0.3195`; we did **not** independently
   re-fetch that historical date ourselves (impossible after the fact), so we report it as
   **secondhand, unverified-by-us** rather than organizer-confirmed — it is at least
   *plausible*, since `DARD` is still on today's board, now higher at 0.3289. The lesson we
   draw either way: leaderboards move daily, and a "current highest score" from an old prompt
   should always be re-fetched, never assumed. **Every
   per-repo number attached to a GEMSDOE/1-88 site name (0.2778, 0.2600, 0.1894, etc.) is
   NOT an organizer score.** We opened the actual source repository for the highest one
   ([`buffedlizard55-lab/GEMSDOE32` README](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/README.md),
   fetched 2026-10-22) and it says, in its own README, in bold:
   *"No organizer score exists for this or any artifact here — every number is a local
   proxy measurement."* The buffedlizard55-lab team/participant does **not appear anywhere
   in the public leaderboard's top 50** (we fetched all 50 rows; see the snapshot file).
   **This is the single most important finding of this session and it is an irregularity
   worth flagging**: the brief's framing ("GEMSDOE32 ... h33-h33-2-b2: 0.2778") treats a
   self-reported local holdout proxy as if it were a competition result. It is not one, and
   no session in this lineage — including this one — has ever had a DrivenData account or
   submitted anything to the real portal.
2. **We obtained the real competition data anyway**, without a DrivenData login, because the
   human project owner had already mirrored the exact files (as git blobs, hash-pinned) into
   two public sibling GitHub repositories on an unrestricted machine before this sandbox
   session started. We re-downloaded every file via the GitHub Contents API (the one
   external surface this sandbox can reach) and **independently re-verified every sha256
   ourselves in this session** — see §1 and [`registry/data_manifest.json`](registry/data_manifest.json).
   This is a mirror-consistency proof, **not** an organizer authentication, and is never
   described as one anywhere in this repo.
3. **We built the full pipeline from scratch** (metric, spatially-blocked holdout, feature
   engineering, submission writer + validator) rather than copying another repo's source
   tree, cross-checked our implementation against the organizer's own published equations
   (unit-tested to <1e-4 against a brute-force O(N²) transcription), and cross-validated our
   results' order of magnitude against an independently-computed number in a sibling
   repository's own notes (uniform-random ≈ 0.05–0.06 in both places, different holdout
   construction).
4. **We tested a genuinely new, literature-grounded hypothesis** — a magnetic-demagnetization
   + surface-conductivity "blind alteration corridor" detector, a mechanism documented in
   peer-reviewed geothermal geophysics (Yellowstone, Dixie Valley NV) but, as far as we could
   verify from the public record, not previously implemented in this lineage in this form —
   and it **failed its own holdout validation gate**: at every emission budget we tried, it
   scored **2.8×–4.3× below** a uniform-random control. We diagnosed why (§5) rather than
   hiding the result. **Verdict: NEGATIVE. Not promoted.** Per the run-card protocol,
   negative results are deliverables, and the artifact is shipped labelled as such.
5. **What's actually needed to win this competition** is explained honestly in §7: more
   emission-budget optimization on a *validated* field, and/or new official data this
   sandbox cannot yet reach (see §8, Limitations).

---

## 1. The data: what we have, and exactly how we got it (no DrivenData login used)

This sandbox's outbound network access is restricted to `github.com`, `codeload.github.com`,
`api.github.com`, `registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org`. DrivenData's
data-download page is login-walled and unreachable this way. The human project owner had
already mirrored the competition's own files into two public sibling repos
(`buffedlizard55-lab/GEMSDOE`, `buffedlizard55-lab/GEMSDOE24`) at specific pinned commits on
an unrestricted machine, **before** this session. `scripts/restore_data.py` re-downloads
those exact bytes via `gh api repos/<repo>/contents/<path>?ref=<ref>` (which resolves through
`api.github.com`) and refuses to proceed on any hash mismatch.

| file | sha256 (independently recomputed, this session) | bytes | what it is |
|---|---|---|---|
| `training_features.tif` | `4371c82e3b8339b8…` | 418,912,844 | 19-band float32 GeoTIFF, EPSG:32611, 100 m, 3730×3292. Band list read from the file's own GDAL metadata, not retyped by hand — see [`registry/data_dictionary.json`](registry/data_dictionary.json). |
| `labels.tif` / `existing_faults.tif` | `7ba308ccdc4418b3…` (identical) | 425,830 | int8, {-1 nodata, 0 no-fault, 1 fault}. This is the **public** USGS Quaternary-fault/INGENIOUS raster, **not** the private expert test labels. |
| `sample_submission.tif` / `example_submission.tif` | `2176d08e485aa2cd…` (identical) | 1,599,597 | float32 grid/CRS/transform template. **Caution** (independently re-confirmed): this file has 60,988 pixels equal to `1.0`, sitting exactly on the labelled faults — it is *not* the "predicts total fault absence" file the problem page describes in prose; we build our own all-zero template rather than assume this one is blank. |

Reproduce: `python3 scripts/restore_data.py` (writes `data/restore_receipt.json`, all 5 files
verified `present`/`restored` against the pins above). Data is **not** committed to git (it's
~400 MB and fully reproducible from the pinned manifest) — see `.gitignore`.

**Provenance class:** every file above is `OWNER-MIRROR, HASH-VERIFIED` — never
`ORGANIZER-AUTHENTICATED`. We have no way, from this sandbox, to confirm the mirrored bytes
are bit-identical to what DrivenData currently serves on its login-walled page; we can only
confirm (and did confirm) that they are byte-identical to what every other session in this
lineage has been using.

## 2. The metric — exact transcription, unit-tested

The competition scores a **distance-weighted Tversky index (DTI)**, α=0.2 (false positives),
β=0.8 (false negatives), triangular kernel R=300 m (3 px at 100 m resolution). Formula copied
verbatim from the official page (fetched 2026-10-22,
[page 967 §"Performance metric"](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#mathematical-representation)):

```
k(d)  = max(1 - d/R, 0)
TP_w  = Σ_{g∈G} max_{x: d(x,g)≤R} p(x)·k(d(x,g))
FP_w  = Σ_{x: p(x)>0} p(x)·[1 - max_{g∈G} k(d(x,g))]
FN_w  = Σ_{g∈G} [1 - max_{x: d(x,g)≤R} p(x)·k(d(x,g))]
DTI   = TP_w / (TP_w + α·FP_w + β·FN_w + ε)
```

Implemented in [`src/gems84/metric.py`](src/gems84/metric.py) as an **exact** (not
approximate) vectorised computation — the triangular kernel has finite support, so a
weighted grey-dilation + cropped distance-transform reduction is mathematically identical to
the literal double sum, just fast enough to run on a 3730×3292 grid in a 3.8 GB sandbox.
Verified against a literal O(pixels²) brute-force transcription in
[`tests/test_metric.py`](tests/test_metric.py) (agreement < 1e-4, limited by float32
precision, run with `python3 -m pytest tests/test_metric.py -q`, **5/5 pass**).

## 3. The holdout — hide-and-recover, spatially blocked

[`src/gems84/holdout.py`](src/gems84/holdout.py): the footprint is tiled into a 6×6 grid of
blocks; mapped-fault connected components ("segments") are assigned to whichever block holds
most of their pixels (segments are never split); 6 folds withhold a spatially-dispersed
subset of blocks (checkerboard-style, not one contiguous corner); a 3 px (300 m) buffer ring
around every withheld block is excluded from scoring (neutral zone) so no fold can get credit
or blame from context bleeding across a boundary. Pooled DTI is reported with a 95% CI across
folds. Both H84 hypotheses are pure functions of the physical feature stack (no
catalogue-derived input), so the "derive catalogue-based features only from the visible
faults" rule is vacuously satisfied here — stated explicitly rather than silently skipped —
and the full withhold/mask machinery is implemented and exercised anyway so it's ready for a
catalogue-aware field in a future session.

## 4. The hypotheses — ranked before implementation

Full ledger with physical rationale, literature citations, novelty argument, and external-data
dependency check: [`docs/research/h84-hypotheses.md`](docs/research/h84-hypotheses.md).
Summary:

| # | hypothesis | layers (official band names) | why it should catch an off-catalogue fault | external data needed | rank (expected gain / cost) | status |
|---|---|---|---|---|---|---|
| H84-1 | Demagnetized conductive corridor: local RTP minimum (hydrothermal demagnetization) conjugate with local conductivity high (clay-cap alteration), gated against sharp-gradient contacts, ridge-filtered for linear corridors | `rtp`, `cond_surf`, `tmi_hg` | Blind faults with alteration overprint but no mapped surface rupture produce this joint signature without a surface trace — see literature in §5 of the hypotheses doc | none | **1 (tested)** | **NEGATIVE** |
| H84-3 | Conductivity–basement discordance: local basement high (shallow `depth_to_base_surf`) that is anomalously conductive at surface | `cond_surf`, `depth_to_base_surf` | A horst that is also surface-conductive suggests a near-vertical conduit cross-cutting it | none | **2 (tested)** | **NEGATIVE** |
| H84-4 | Scarp–alteration concordance: topographic scarp (Sato ridge filter on `det_elev`) AND H84-1/3 alteration corridor, required jointly | `det_elev` + H84-1/H84-3 | AND-ing independent morphological + geophysical evidence should raise precision under the metric's harsh FP tax | none | **3 (tested)** | **NEGATIVE** |
| H84-2 | Gravity-curvature saddle at basement-step flanks, gated by seismicity quiescence | `iso_grav_anom`, `iso_grav_anom_hg/vg`, `ieq_n100a15` | Closely resembles prior art already documented in the sibling lineage (basement-step × gravity); lowest novelty | none | 4 (not tested — low novelty) | not run |
| H84-5 | Radiometric alteration ratios (K/Th/U) differenced from the catalogue, using the *official* USGS GeoDAWN radiometric release | not in `training_features.tif` at all — the 19 official bands have **no** radiometric band despite the problem page mentioning radiometrics | K-enrichment/U-mobilization is a classical alteration proxy, complementary to H84-1 | **YES**: USGS GeoDAWN data release, DOI [10.5066/P93LGLVQ](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7) — public-domain, free; obtainability confirmed (a byte-identical uint8-quantised mirror already exists, hash-pinned, in `buffedlizard55-lab/GEMSDOE24`) but was **not pulled into this session** to keep the submission provenance 100% primary-source/official-band-only | 5 (deferred) | not run |

**Leakage canary** (AUC of each single field alone vs. the full visible catalogue, 300k
sampled negatives): H84-1 0.514, H84-3 0.511, fused 0.517, H84-4 0.507, uniform-random control
0.501. **All well below the 0.90 leakage threshold** — no evidence of catalogue leakage in
any tested field (see [`evidence/h84_holdout.json`](evidence/h84_holdout.json) and
[`evidence/h84_4_holdout.json`](evidence/h84_4_holdout.json) for full numbers).

## 5. What we found — a real negative result, with a mechanism

At every emission budget tested (15,000 → 1,000,000 px, i.e. 0.3%–19.4% of the 5,164,300-px
footprint), the fused H84 field scored **2.8×–4.3× below** a uniform-random control of equal
mass on our own holdout (e.g. at 44,090 px: fused **0.0219** vs. random **0.0608**; at
1,000,000 px: fused **0.0601** vs. random **0.1536**). This is **not** explained by leakage
(AUCs are all ≈0.51) — it is explained by a spatial-coverage effect we measured directly:
**8.16% of the entire footprint lies within the 300 m kernel radius of some mapped fault**
(the catalogue is geographically pervasive across this Basin-and-Range terrain), so *any*
spatially-uniform emission earns substantial credit purely from ubiquity, while our field
concentrates its highest-confidence mass in specific conductive sub-basins whose geometry
does not coincide with the basin-margin trend the mapped fault network actually follows. In
other words: the named non-fault mimic we tried to guard against in the hypothesis design
(broad, equant, undeformed basin-fill producing the same magnetic-low/conductivity-high
signature with no fault control) **turned out to dominate the field's extreme tail despite
the ridge-filter guard**. Full numeric trail: [`registry/run_card.json`](registry/run_card.json).

**This does not prove the underlying geological mechanism is wrong** — it proves this
*specific implementation*, scored against the *public* catalogue (which is itself biased
toward well-expressed, easy-to-map surface ruptures, not the blind structures H84-1 targets),
underperforms chance at finding pixels that are *already* in that catalogue. The real
competition scores against *new* faults, a fundamentally different and unmeasurable-from-here
target. That nuance is reported, not used to rescue the result: the verdict stands as
**negative** per the run-card protocol, and this artifact is not promoted to a submission.

## 6. The submission artifact — what's downloadable, and why you should not submit it yet

[`docs/downloads/gemsdoe84-h84-fused-demag-cond-corridor-20261022T000000Z-auditonly-zeros.tif`](docs/downloads/gemsdoe84-h84-fused-demag-cond-corridor-20261022T000000Z-auditonly-zeros.tif)
(primary, 0.0 outside the footprint) and the
[`-nan.tif`](docs/downloads/gemsdoe84-h84-fused-demag-cond-corridor-20261022T000000Z-auditonly-nan.tif)
twin (NaN outside the footprint, spec-literal). Both pass every format check
([`scripts/build_submission.py`](scripts/build_submission.py) +
[`src/gems84/submission.py`](src/gems84/submission.py) validator, full receipts in
[`registry/submission_receipts.json`](registry/submission_receipts.json)):
single-band float32, EPSG:32611, 3730×3292, transform matches the template exactly, all
finite in-footprint values in `[0, 1]`.

**Why two variants, and why "zeros" is primary:** the user of this project reported the
actual portal error *"Predicted values must be in range [0, 1]"* on a NaN-outside file from a
different pipeline. We cannot see the portal's validator code (no login), so we treat this as
a corroborated community finding — nearly every sibling repo that documents the same issue
ships a 0.0-outside file as its primary download for exactly this reason — rather than a
guess, and we ship both so a reviewer can test either. This reasoning is stated here, not
assumed silently.

**Format-valid ≠ competition-ready.** Per §5, this artifact failed its own holdout gate. The
executive summary ([`docs/executive-summary.html`](docs/executive-summary.html)) explains the
real submission steps for when a future candidate clears the bar, and says so explicitly for
this one.

## 7. Suggested next steps (prioritized)

1. **Fix the coverage mismatch, not just the field.** The failure mode in §5 is about *where*
   mass is concentrated, not whether the underlying physics is real. Next session: score H84-1
   restricted to a buffer around the *existing* basin-margin trend (the catalogue itself, used
   only to define *where to look*, never *what value to predict* — this is a legitimate,
   explicitly-allowed use of catalogue geometry as a search prior, distinct from leaking label
   values into the field) and compare against the current unconstrained version.
2. **Try H84-5** (official USGS GeoDAWN radiometric K/Th/U alteration ratios) — data is
   confirmed obtainable (DOI 10.5066/P93LGLVQ, public domain; a hash-pinned mirror already
   exists in `buffedlizard55-lab/GEMSDOE24`). Deferred this session to keep this submission's
   provenance 100% primary-official-band.
3. **Do the full duplicate-lane audit**: pixel-level rank correlation / 3-px dot-overlap
   against every scored raster mirrored in `registry/data_manifest.json`'s `"scored"` group,
   not just an order-of-magnitude cross-check against one sibling repo's published number.
4. **Re-run the det_elev curvature (zero-crossing) transform** that a sibling repo's own
   research found to be the strongest single-channel signal (`curv_s2`, their own measurement,
   evidence class OWNER-REPORT) using OUR implementation and OUR holdout, to get a comparable,
   independently-verified number before trusting it.
5. **Try an actual DrivenData account.** This sandbox has never had one; if the human project
   owner can supply the three-slot weekly submission access described in the brief, our
   `HOLDOUT-DTI` numbers could finally be cross-calibrated against a real `ORGANIZER-CONFIRMED`
   receipt, closing the biggest open uncertainty in this whole lineage (§0.1).

## 8. Limitations — what this sandbox cannot do, and what access would fix it

- **No DrivenData account/login** in this sandbox → cannot submit, cannot see our own private
  score, cannot confirm the mirrored data is current. *Needs:* a DrivenData account with
  competition access, or a human to submit the file and paste back the receipt.
- **No access to `earthquake.usgs.gov`, `sciencebase.gov`, or Dropbox** via the sandboxed shell
  (outbound network is allow-listed to GitHub + package registries only); the `fetch_page` /
  `web_search` tools *can* reach the open web and were used for literature and the public
  leaderboard, but cannot download large binary GeoTIFFs. *Needs:* either those hosts added to
  the sandbox allow-list, or continued reliance on owner-mirrored GitHub copies (works, as
  demonstrated in §1, but adds a human-in-the-loop mirroring step for any *new* official
  dataset, e.g. H84-5's radiometric grids).
- **2 vCPU / 3.8 GB RAM** sandbox: the 3730×3292×19-band stack does not fit comfortably in
  float64; all code here uses float32 and on-demand band loading. A full 35-channel
  gradient-boosted model (as some sibling repos ran) would likely need more memory or
  batched/out-of-core training.
- **No ground truth for the real test set, ever.** Every `HOLDOUT-DTI` number in this repo is
  computed against the *public* USGS/INGENIOUS catalogue, which the competition explicitly
  says is incomplete and the target is faults *not* in it. This is a fundamental, unfixable
  gap from inside any sandbox — not a tooling limitation.

## 9. Repository layout

```
NORTH_STAR.md              the governing brief, reconstructed from the opening prompt (read every session)
README.md                  this file
registry/                  data_manifest.json, data_dictionary.json, run_card.json,
                            submission_receipts.json, leaderboard_snapshot.json
src/gems84/                metric.py, holdout.py, features.py, submission.py
scripts/                   restore_data.py, dump_data_dictionary.py, evaluate_holdout.py,
                            evaluate_h84_4.py, build_submission.py
tests/                     test_metric.py (5/5, brute-force cross-checked), test_submission.py
                            (4/4, format/clipping/validator regression tests)
evidence/                  h84_holdout.json, h84_4_holdout.json (full numeric trails)
docs/                      GitHub Pages site: index, executive-summary, hypotheses,
                            leaderboard, research/, downloads/ (the submission TIFs)
data/                      restored competition files (gitignored, reproducible via
                            scripts/restore_data.py)
```

## 10. How to reproduce everything, end to end

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install numpy scipy rasterio scikit-learn scikit-image pytest
python3 scripts/restore_data.py            # restores + sha256-verifies the 5 core files
python3 -m pytest tests/ -q                # 9/9: metric + submission-format unit tests
python3 scripts/dump_data_dictionary.py    # registry/data_dictionary.json from file metadata
python3 scripts/evaluate_holdout.py        # H84-1 / H84-3 / fused vs random, full sweep
python3 scripts/evaluate_h84_4.py          # H84-4 conjunction test
python3 scripts/build_submission.py        # writes + validates the submission TIFs
```
