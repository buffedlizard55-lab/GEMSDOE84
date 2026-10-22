"""GEMSDOE84 -- parallel-lane workspace for DrivenData competition #306 (DOE GEMS Prize).

This package hosts more than one session's ("lane's") code side by side, per the project's
parallel-run protocol (see README.md "Parallel-session integration" and the per-lane
sections). `basis.py`, `liti.py`, `mlfield.py`, `paths.py` belong to the LITI lane
(`arena/9dbb1208`) and reuse the pinned shared template in `vendor/gems57` (metric
arithmetic, hide-and-recover holdout, greedy emission, validation, uniqueness, submission
writer) unmodified. `metric.py`, `holdout.py`, `features.py`, `submission.py` belong to the
H84-DEMAG lane (`arena/4ac2f662`), which independently re-implemented and unit-tested its own
metric/holdout/writer from the organizer's published equations rather than depending on
`vendor/gems57` (that dependency did not exist yet when this lane's branch diverged).

Every public claim either lane's code or docs makes is labelled with one of:
  OFFICIAL            -- read verbatim from the competition page / USGS / a peer-reviewed source, with a link.
  HOLDOUT-DTI          -- computed in this checkout from hash-pinned bytes, on OUR OWN spatially-blocked
                           holdout of the public fault catalogue. Never the real (private) organizer score.
  ORGANIZER-CONFIRMED  -- copied from an actual DrivenData submission-page receipt, or read directly off
                           the public leaderboard page (which does not require a login to view).
  MODEL / PROJECTION   -- an estimate conditioned on an unverified anchor. Never written as a score.
"""
