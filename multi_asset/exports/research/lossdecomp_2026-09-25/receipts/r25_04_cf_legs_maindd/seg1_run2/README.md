> **Created:** 2026-09-26 02:2xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4) | **Status:** R25-04 main-drawdown counterfactual, SEGMENT 1 of 2 (device cf_legs.py rev 3, 2f72eb1d, commit 48a9844be) | **Invalidated by:** a change of the snapshots / ledger / price snapshot / device

# Counterfactual leg contribution — segment 1 (09-17 12Z … 09-21 12Z, 25 anchors)
**Not a continuous chain with segment 2** (../seg2_run2). Every arm restarts from production's state at 09-17 12Z. Named limitation: the leg is "removed from the segment start".
- 09-17 12Z ran the old tree (combo_stage b5c698f9, `--tree-at`); the other 24 anchors ran the NC-era producer copy.
- Segment 0 (09-16 12Z … 09-17 08Z) cannot be rebuilt (../SEG0_FEASIBILITY.md).

Baseline green first:
- checks 50/50 True: base == production target_live **bitwise** at 25/25 anchors; base book == executor L2 at 25/25.
- The base P&L equals the r25_03 layered-book L2 P&L at every anchor (max |diff| 3.4e-12 USDT; Σ −6,431.67 in both).
- All 25 anchors are priced, with 0 unpriced names in every arm.

| leg | Σ contribution USDT (25 anchors) | largest anchors |
|---|---|---|
| funding momentum | **+794.3** | 09-20T12Z −1,850.6; 09-20T16Z +1,297.9; 09-18T16Z +1,097.7; 09-19T20Z +972.0; 09-19T16Z −941.1 |
| King | −97.5 | 09-20T16Z −258.8; 09-19T04Z −202.1; 09-20T08Z +173.0 |
| F10 | −89.2 | 09-20T08Z +146.3; 09-21T00Z +115.5 |

Book P&L Σ over the segment: base −6,431.7; without funding −7,226.0; without King −6,334.2; without F10 −6,342.5.

## Reading, plain
- No single leg carries this segment's loss. Removing any one of them leaves the book between −6.3k and −7.2k.
- Removing the funding leg makes the segment **worse** by 794 USDT, although funding is volatile anchor by anchor (−1,851 to +1,298).
- Contributions are not additive (the reshape re-neutralises; the legs interact), and 25 anchors support no significance claim.
- For scale, the same anchors layer by layer (r25_03, same prices): producer raw L0 −11,117.7 → reshaped L1 −6,577.2 → clamped L2 −6,431.7 → readback L5 −6,434.5.
- Execution (L2 → L5) costs −2.8. The reshape step shrank the raw producer book's loss by 4,540; the clamp added +145.

**Not attributable to the old skip gate** (lead, from the news2 measurement): in live trading the old producer skip gate held back only 1 of 17,600 book-member cells (ONEUSDT 09-18T04Z, short −0.00587, 4 h late). The replay-side contamination that reached the book is 191 cells / 39 anchors. The funding-leg reading here must not be attributed to the skip gate; its size cannot carry it.

## Both segments side by side (separate chains, never summed as one)
| segment | anchors | base book (= layered L2) | funding | King | F10 |
|---|---|---|---|---|---|
| 0 — 09-16 12Z … 09-17 08Z | 6 | −3,079.7 | **not rebuildable** | — | — |
| 1 — 09-17 12Z … 09-21 12Z | 25 | −6,431.7 | +794.3 | −97.5 | −89.2 |
| 2 — 09-21 20Z … 09-24 04Z | 15 | +233.1 | −1,005.1 | +607.8 | −64.5 |

(09-21 16Z has no rebalance record in the 46-anchor window.) The signs of the funding and King readings flip between segments; with separate chains, no pooled figure is given.

Files: CF_LEGS.json, CF_LEGS_RUNS.json, run.log, combo_logs/ (100 arm logs), SUMMARY.json (built with assertions), RUN_COMMAND.sh (verbatim), SHA256SUMS.
