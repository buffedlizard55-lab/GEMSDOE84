# Source register and access limitations

|Source|Authority and use|Verification state|
|---|---|---|
|[DrivenData official reference](https://github.com/drivendataorg/gems-prize-reference-solution)|Organizer reference implementation; compute setup|README and tree retrieved through GitHub; archived locally. CPU execution supported.|
|[DrivenData problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)|Authoritative target, metric and format|User-supplied review pointer; host unavailable under current egress policy. Shared metric is inherited, not freshly certified against this page.|
|[DrivenData data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)|Original competition files|No authenticated access; no credentials requested. Restored public mirrors are not organizer-authenticated.|
|[USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)|Original airborne survey provenance|User-supplied review pointer, not fetched here. Derived uint8 K/Th/U/TC stack obtained from owner GitHub mirror, SHA-256 pinned.|
|[GEMSDOE24 pinned mirror](https://github.com/buffedlizard55-lab/GEMSDOE24/tree/07345ea0604953d7efb858d9cfbc21e20c7aca0b/data)|Cached derived LiDAR and radiometric stack|Retrieved and hash-verified; transformations and upstream accuracy not independently certified.|
|[Shared template](https://github.com/buffedlizard55-lab/60GEMSDOE/tree/b99591eede63c6d45c8a896255b8cd34824fa00b)|Shared evaluator, holdout, writer and validators|Reused from GEMSDOE83 vendor snapshot; every vendored file checked against inherited manifest. A recorded upstream-local uniqueness amendment exists; this run does not use its representation exemptions.|
|[GDR 1391](https://gdr.openei.org/submissions/1391)|Potential geothermal context|Not downloaded or used this run. Availability not certified here.|
|[NLR submission guidance](https://docs.nlr.gov/docs/fy26osti/96647.pdf)|User-requested PDF|Not downloaded or verified here. No claim of compliance with unseen requirements.|

`registry/inventory.json` records resolved commits, artifact paths, blob identifiers and content hashes for linked public predecessor repositories. This inventory is a timestamped snapshot, not an automatically current leaderboard. It does not include private submissions, unlinked files, or later changes. Geometry-mismatched prior artifacts are flagged and nearest-neighbor reprojected **only for comparison**; their original grids are not submission-valid on the current template.

Numbers in archived upstream receipts retain their original labels. They are historical unverified evidence, not automatically adopted HOLDOUT-DTI or ORGANIZER-CONFIRMED results. Current experiment metrics are in `evidence/holdout.json`, with evaluator identity, withheld-positive count and conditional spatial-bootstrap interval. AUC is explicitly a holdout diagnostic and never a competition score.
