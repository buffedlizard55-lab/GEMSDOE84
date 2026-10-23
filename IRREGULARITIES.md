# IRREGULARITIES — session of 2026-10-23 (branch `arena/1c8a6632-gemsdoe84`)

Only items that change a decision are listed, per the brief. Each carries what was measured,
where, and the decision it forces.

---

## IR-84-S1 — The session brief's uniqueness protocol contradicts `AGENTS.md` / `NORTH_STAR.md`

`AGENTS.md` says the H84 lane is **STOPPED** under a "literal any-registry-raster duplicate
protocol", and `NORTH_STAR.md` binding rule 1 forbids a raster whose rank correlation with any
registry raster exceeds 0.90 or whose dots overlap one registry raster by more than 70 % at
3 px. The session brief says the opposite: *"Do NOT apply rank-correlation or dot-overlap
'uniqueness' thresholds. Dedupe only on exact hash and on repeated (parent, axis, value)."*

**Decision taken:** the brief is the later, explicit instruction from the same owner and it
conflicts only with a repo-internal protocol, not with the official rules, so this session
followed the brief. Every variant here is a deliberate 6–27 % edit of one named parent and
would fail a 0.70-overlap gate by construction. **If the owner still wants the old protocol in
force, none of these three files may be submitted** — say so and they will be re-labelled
research-only.

## IR-84-S2 — Hard constraint 4 ("keep ≥ 3 px from catalogue") conflicts with the SNAP spec ("same exclusions") for this parent

Measured from the hash-verified parent (`evidence/r0_rebuild_receipt.json`): R0 has **0 dots at
`d_cat <= 2 px`** (it *is* the `B=2` prune) but **1,611 dots at 2.236 ≤ `d_cat` < 3.0 px**
(2,171 at `d_cat <= 3.0`, median 19.65 px). So the parent itself does not satisfy the brief's
"≥ 3 px" ring, and a SNAP variant that both (a) preserved the parent's exclusions and (b)
satisfied "≥ 3 px" cannot exist.

**Decision taken:** the three built variants preserve the parent's own exclusion
(`footprint & ~catalogue & d_cat > 2.0`) so that position is the *only* thing that changes, and
zero mass sits on catalogue pixels (gated per file). Pushing the 1,611 ring dots outward would
have added a second mechanism (PRUNE) to a SNAP file; the upstream instrument also ranks `B=3`
*below* `B=2` (`evidence/h33_validation.json`, LM 0.26437 vs 0.26792), so it is unlikely to be
free. **If the owner reads constraint 4 literally, these files are non-compliant and a
PRUNE-axis build is required instead.**

## IR-84-S3 — `README.md` section 4 mis-states the parent's anatomy, in the direction that would mislead a slot decision

`README.md` §4 claims *"Exactly 37,643 / 37,654 (99.97 %) of `h33-2-b2`'s dots lie at Euclidean
distance 1 ≤ d_cat ≤ 2 px"* and builds an argument on it. Measured from the hash-verified bytes
this session: **0 dots at `d_cat <= 2 px`**, median `d_cat` 19.65 px, mean 29.0 px, p90 68.0 px
— identical to `evidence/incumbent_anatomy.json` (`dots_dcat_le2: 0`). The README claim is
false. The parent is *not* a catalogue-hugging file; it is a mid-field emission, which is
exactly why a SNAP arm (positional accuracy) is a different question from a PRUNE arm
(catalogue-flank mass).

**Decision taken:** planning used the measured anatomy, not the README. The README's CURRENT
STATE block was rewritten; §4 was left untouched because the brief allows only CURRENT STATE
edits — it still needs an owner edit.

## IR-84-S4 — `ledger/raw_paste.txt` does not exist; the parent's ranking does not exist

Two gaps the brief assumed away:

1. `ledger/` did not exist at all. `ledger/submissions.csv` was therefore built from this
   repo's own committed score records (`registry/live_scores.csv`, 99 owner-reported rows, and
   the dated official snapshot in `docs/evidence/upstream-score-ledger.csv`), collapsing 4 exact
   repeats. **No submission-page receipt is committed anywhere in this repo**
   (`receipts_committed = 0`), so `0.2778` stays a **CLAIM**, and `TOP_PUBLIC = 0.3195` is a
   **2026-10-03 manual snapshot** that the owner must refresh.
2. MASS assumes a rebuildable parent ranking. There is none: R0's dots come from `dot_thin`, a
   deterministic BFS Poisson-disk walk with **no score**
   (`GEMSDOE24/src/gems/thinning.py`, restored and read this session), and the H19-5 field's own
   recipe lives in `buffedlizard55-lab/GEMSDOE19`, which returns `Not Found` from
   `api.github.com`. **Decision taken:** SNAP was built instead, and MASS is proposed in
   `SLOT_PLAN.md` as blocked on a human-named ranking.

## IR-84-S5 — Competition rasters and mirrored competition inputs are in public GitHub repositories

The pinned inputs (including the 418 MB `training_features.tif` mirror and the parent R0
GeoTIFFs) are published in `buffedlizard55-lab/GEMSDOE`, `/GEMSDOE24`, `/GEMSDOE28` and
`/GEMSDOE32`, and this repo additionally ships submission GeoTIFFs under `docs/downloads/` and
`submissions/`. This session restored them by SHA-256 from those mirrors
(`evidence/input_restore_receipt.json`, egress limited to `codeload.github.com`; drivendata.org
and dropbox.com were never contacted, no credential was read or written). **The competition
data-use terms were not checked and this session was not able to check them** — flagging, not
fixing. New files were written to `releases/` only, and no new raster was published to any
GitHub Pages site or release.

## IR-84-S6 — Both report-only instruments came back mildly negative, and monotone in dose

Not a gate, recorded so it cannot be lost: on the catalogue hide-and-recover PROXY
(`gems57-pooled-hide-v2`, 22,641 withheld positives) the three variants sit **0.00002–0.00010
below** R0's 0.00438, and on the SGMC control **0.0005–0.0027 below** R0's 0.09606 — in both
cases ordered by how many dots moved. Mechanically expected (snapping onto gradient crests
moves dots *off* the catalogue flank, which is what those two proxies measure) and neither
instrument is validated, but it is the reason `SLOT_PLAN.md` puts the **smallest** dose in
slot 1 rather than the one with the biggest MODEL projection.
