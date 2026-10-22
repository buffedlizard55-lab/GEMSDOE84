# Sources (for manual review)

## Organizer / official
| what | link | used for | read from this sandbox? |
|---|---|---|---|
| Competition home | https://www.drivendata.org/competitions/306/competition-doe-gems/ | rules context | no: outside the egress allow-list (IR-84-02) |
| Problem description (metric: DTI, α=0.2, β=0.8, 300 m triangular kernel) | https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ | metric, as transcribed in the pinned template `src/gems57/metric.py` | no; the transcription is inherited and unit-tested against brute force |
| About page | https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/ | background | no |
| Data tab (login) | https://www.drivendata.org/competitions/306/competition-doe-gems/data/ | origin of the mirrored rasters | no |
| Leaderboard | https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ | targets 0.4413 / 0.3195 (OWNER-REPORTED here) | no |
| Rules PDF (NLR/OSTI 96647) | https://docs.nlr.gov/docs/fy26osti/96647.pdf | submission rules | no |
| Reference solution | https://github.com/drivendataorg/gems-prize-reference-solution | baseline approach | reachable (github.com) |
| GeoDAWN magnetic & radiometric surveys (USGS) | https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and | source of bands 1–3, 6, 9, 14 and radiometrics | no |
| INGENIOUS project | https://gbcge.org/current-projects/ingenious/ | catalogue/labels context | no |
| GDR submission 1391 | https://gdr.openei.org/submissions/1391 | INGENIOUS data | no |
| EPSG:32611 (WGS 84 / UTM 11N) | https://epsg.io/32611 | grid CRS | no; the CRS is read from the files |
| Tversky index | https://en.wikipedia.org/wiki/Tversky_index | metric family | no |
| USGS 3DEP | https://www.usgs.gov/3d-elevation-program | source of the 10 m / 1 m DEM derivatives | no |
| USGS ComCat FDSN event service (data-blocked hypothesis H84-D) | https://earthquake.usgs.gov/fdsnws/event/1/ | not used (blocked) | no |

## Owner repositories (reachable, hash-pinned)
| what | link |
|---|---|
| Shared template, pinned commit `b99591e` (`src/gems57`) | https://github.com/buffedlizard55-lab/60GEMSDOE/tree/b99591eede63c6d45c8a896255b8cd34824fa00b/src/gems57 |
| Template pin (file SHA-256s) | https://github.com/buffedlizard55-lab/GEMSDOE81/blob/main/registry/template_pin.json |
| Feature-stack mirror (5 parts, `c0c06ac`) | https://github.com/buffedlizard55-lab/GEMSDOE/tree/c0c06ac82178f26b94fce3397036ef8f12a2f3a0/data/bridge |
| 0.2778 file (GEMSDOE32) | https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif |
| H19-5 provenance (19GEMSDOE README) | https://github.com/buffedlizard55-lab/19GEMSDOE |
| Prior registry index (655 rasters) | https://github.com/buffedlizard55-lab/57GEMSDOE/blob/main/evidence/registry_full_index.json |
| Live-score table base | https://github.com/buffedlizard55-lab/GEMSDOE80/blob/main/registry/live_scores.csv |

All 1,149 corpus blobs are listed with repo, blob id and path in `registry/uniqueness_corpus.txt`.
