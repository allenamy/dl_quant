> **Created:** 2026-09-25 18:3xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4) | **Status:** R25-04 main-drawdown counterfactual, SEGMENT 2 of 2 (device cf_legs.py rev 2, 4ea5568b, commit 19d153436) | **Invalidated by:** a change of the snapshots / ledger / price snapshot / device

# Counterfactual leg contribution — segment 2 (09-21 20Z … 09-24 04Z, 15 anchors)
**Not a continuous chain with segment 1.** Every arm restarts from production's state at 09-21 20Z. Named limitation, as approved: the leg is "removed from the segment start", not from the start of the drawdown.

Baseline green first:
- checks 30/30 True: base arm == production target_live **bitwise** at 15/15 anchors; base book == executor L2 (< 1 USDT) at 15/15.
- Independent cross-check: the base book P&L equals the r25_03 layered-book L2 P&L (LAYERED_BOOK.json, device 67fb70ca) at every anchor, max |diff| 1.1e-12 USDT; Σ +233.08 in both. The two chains share the price snapshot; the pricing code is written separately.

| leg | Σ contribution USDT (15 anchors) | largest anchors |
|---|---|---|
| funding momentum | **−1,005.1** | 09-23T12Z −1,709.0; 09-22T16Z +603.0; 09-23T08Z −450.6; 09-23T16Z +314.8 |
| King | +607.8 | 09-23T12Z +217.2; 09-23T08Z +160.3; 09-23T20Z +157.1 |
| F10 | −64.5 | 09-23T04Z −99.4; 09-23T12Z −81.8 |

- Book P&L Σ over the segment: base +233.1; without funding +1,238.1; without King −374.7; without F10 +297.6.
- Contributions are not additive (the reshape re-neutralises, the legs interact). No significance claim on 15 anchors.
- Unpriced: at 09-24T04Z one name had no price in the interval, in every arm, with a different notional per arm (base 798.9, no_fund 587.7, no_king 1,104.0, no_f10 865.7 USDT). That anchor's contributions exclude different unpriced notional per arm. All other anchors are fully priced.

## Where the main drawdown sits (layered L2, same 46-anchor window as r25_03_layered_old_window)
| range | anchors | L2 P&L USDT | covered by |
|---|---|---|---|
| 09-16 12Z … 09-17 08Z | 6 | −3,079.7 | **no segment** (the approved segments start at 09-17 12Z) |
| 09-17 12Z … 09-21 12Z | 25 | −6,431.7 | segment 1 (runs in the 21:00Z window, `--tree-at` pre-fp2-6b tree) |
| 09-21 20Z … 09-24 04Z | 15 | +233.1 | this segment |

09-21 16Z has no rebalance record in the 46-anchor window. Segment 2 is not a loss segment. The drawdown is in segment 1 and in the uncovered first 6 anchors.

Files: CF_LEGS.json, CF_LEGS_RUNS.json, run.log, combo_logs/ (60 arm logs), SUMMARY.json (built with assertions: 30/30 checks, max |base − layered L2| < 0.01), RUN_COMMAND.sh (verbatim), SHA256SUMS.
