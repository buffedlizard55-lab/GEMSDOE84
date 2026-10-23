# Irregularities — only items that change a decision (2026-10-23)

1. **README's R0 anatomy is inverted.** README §4 claims 99.97% of R0's dots
   lie 1–2 px from the catalogue ("parallel splinter harvest"). Measured on
   the sha-verified file: 0 dots ≤2 px, 2,171 ≤3 px, median 19.6 px (matches
   `evidence/incumbent_anatomy.json`). R0 wins by *deleting* near-trace dots,
   not harvesting them. Any strategy built on the README story (e.g. adding
   collar mass) points the wrong way. README text outside CURRENT STATE was
   left untouched per brief; treat §4 as superseded.
2. **Protocol supersession (human decision, 2026-10-23).** `AGENTS.md` /
   `NORTH_STAR.md` record a STOP under the rank-correlation/dot-overlap
   duplicate protocol. The human confirmed brief v2 is the explicit protocol
   revision for this work: no 0.90/0.70 thresholds; dedupe on exact sha256 and
   repeated (parent, axis, value) only. Future sessions: brief v2 + this file
   outrank the STOP text for R0-variant work; the STOP still describes the old
   H84 lanes correctly.
3. **No receipts anywhere.** Every live number incl. R0 0.2778 is CLAIM
   (owner-reported). TOP_PUBLIC, slots left/total, and the 2026-12-03 deadline
   were left TBD by the human; the repo's 2026-10-22 snapshot (top 0.4413) is
   owner-reported and is **not** used as a target. No slot decision that needs
   a target number can be made until the human pastes receipts + TOP_PUBLIC.
4. **Shared vendor tooling cannot emit the brief-spec primary encoding.**
   `vendor/gems57` writer/validator enforce all-finite (zeros-outside) only.
   Brief v2 requires NaN-outside primary + zeros fallback, so variants were
   written with the scored parent's own GeoTIFF profile and gated by new
   `scripts/validate_release.py`. Vendor code was not modified (pins intact).
   Note the family's scored R0 file is the `-zeros` twin; upload ONE twin.
5. **Competition-derived rasters are already in public fleet repos**
   (this repo's `submissions/`, `docs/downloads/`, sibling mirrors of inputs).
   Data-use terms are unchecked (brief §4.2). This session kept *inputs* out
   of git (fetched to `$GEMS84_DATA`, hash-pinned) and followed repo
   convention only for *prediction* files in `releases/`. Human decision
   needed: repo visibility / terms review before adding more.
6. **The hide-and-recover PROXY mechanically zeroes collar variants.**
   Withheld truth is a subset of the same catalogue the lineage pruned
   against, so any B≥3 file scores exactly 0.0000 as-is (R0: 0.0044). The
   instrument cannot rank PRUNE variants; it is reported in
   `ledger/proxy_report_20261023.json` and must never gate slots 1–2.
7. **Brief's block-CV "0.51–0.59" does not reproduce for R0** under
   density-CV over >50%-footprint blocks: 1.37 at 2 km, 0.90 at 5 km.
   Definition/block-size mismatch; a CONCENTRATION session must state its
   definition first rather than targeting 0.51–0.59.
8. **Stale restore receipt.** `data/restore_receipt.json` claims 23 verified
   files under `.cache/gems_data`, absent in this checkout. Only the three
   bridge files plus the eight pins fetched/verified this session are
   verified here; all other manifest entries are UNVERIFIED in this
   environment (not fetched; PRUNE did not need them).
