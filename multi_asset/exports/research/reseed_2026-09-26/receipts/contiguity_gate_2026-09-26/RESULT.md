# reseed build window-contiguity gate (lead ruling 2026-09-26, path A)

Sequence (each run on synthetic state in the scratchpad; the producer module imported read-only):
1. **Baseline before any change** — device d1efa667 + selftest 1310608e: 20/20 green.
2. **Gate added, OLD selftest** — the rev-0 selftest's own baseline goes RED: `window NOT contiguous: 1 missing anchor(s) at ['2026-09-26T08:00Z']`.
   The rev-0 baseline world carried a 1-anchor hole (its SKIP run) *beyond the replay end* and was certified green — the old
   suite asserted that a hole-carrying build is correct.
3. **Selftest rev 1** — baseline replay extended 40 anchors so the SKIP hole is replay-covered; three new controls:
   RED 1-anchor hole beyond replay end ⇒ STOP; RED the 09-26 outage shape (no run at +4h/+8h, 0 appends at +12h ⇒ 3 missing)
   ⇒ STOP naming all 3; POSITIVE same outage with a covering replay ⇒ build OK, gap histogram {1: 949}. **23/23** (`selftest_rev1_23of23.log`).

Found while testing on the REAL state (read-only dry-run build, 18:1xZ): it STOPs *before* the gate —
`current leg_returns_live.json differs from the snapshot of its own anchor 2026-09-26T08:00Z` — because the 09:00Z reseed install
replaced the file after the 08Z snapshot. `measure_tail` diffs consecutive snapshots, so across an install boundary it cannot
determine the append count. **Path A's next reseed therefore needs the install record (INSTALL_*.json positions) as the
timestamped base for the post-install tail** — a prerequisite, named here, not built.
