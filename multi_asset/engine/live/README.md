# engine/live — the T+1 live shadow

> **创建:** 2026-07-20 JST | **Session:** fable multi-asset-v2 (0B) | **状态:** live (0C GO, cron installed) | **作废条件:** 面板口径/腿构成/引擎 canonical 变更, 或迁移到实时 REST 源

A server-resident daily job that continues the four-leg book out-of-sample: pull the latest public
archives, splice the panel tail, run fold_4 inference + the C1 chain, emit unit-gross positions,
accrue a dual-curve paper P&L, and publish a C4 signal-health report. It is the hardest continuous
validation of the full chain and the partner's integration reference.

## Pipeline (daily, `run_daily.sh`, cron 09:00 UTC)

```
ingest        build_tail.py --build     latest CDN daily archives -> splice onto the frozen panel ->
                                        wide_dl_live.npz (historical-recompute parity 0.99999)
signal        signal_loop.py --emit     fold_4 king/S2 inference (member-masked, live-safe) + funding/SIZE
                                        formulas -> combine -> 4h-sync netting -> UNIT-GROSS positions ->
                                        exports/live/positions/positions_YYYYMMDD_HH.json
paper P&L     paper_pnl.py              mark to realized 4h return under a conservative maker fill
                                        (k=900, fill 0.51, cost 1.9 calm / 2.9 stress) -> dual curve A/B
monitor       monitor.py               rolling rank-IC vs realized return, regime-aware baseline -> daily_report.json
```

## Key design points

- **DataSource abstraction** (`datasource.py`). Reads market data through a pluggable interface. Where
  the live REST API (`fapi.binance.com`) is reachable, bind `RESTDataSource` (real-time); otherwise
  bind `CDNDataSource` — the public `data.binance.vision` archive (T+1 daily). Nothing downstream
  depends on which is bound; the shadow runs at **T+1** on the CDN and would run real-time on REST.
- **Positions schema = the backtest data package's `target_weight`** (unit-gross Σ|w|=1, market-neutral
  Σw≈0, per-symbol). The historical data package and the live feed are the same interface — the partner
  moves from backtesting history to receiving daily files with no switching cost.
- **c2 dual-curve** (funding is monthly-archived, so the open month has no live funding):
  - **Curve A (provisional, 3-leg)** — what this feed can actually trade now (funding dropped).
  - **Curve B (backfilled, 4-leg)** — what a real-time feed with live funding would get; the open-month
    funding is a premium-index proxy until the monthly archive backfills it. Always reported beside A;
    **A/B difference = a free monthly estimate of the funding leg's current-month attribution.**
- **Funding-interval cache** (`funding_intervals.json`). The funding_ema EMA span is set from each
  coin's **full-history median interval** (some alts changed 8h↔4h; the frozen panel used the full-
  history median). This reproduces the frozen span exactly (overlap FUND_EMA rank-corr 0.99995,
  per-coin min 1.0). Cache once; it is stable.
- **Regime-aware C4 baseline.** The decay alarm compares the rolling rank-IC to the **current-year**
  engine level (2026 ≈ 0.062), not the full-history average (0.076) — so a 2026-normal reading near
  0.059 reads as healthy, not decaying.

## Validation

- **Overlap (ingest caliber).** A fresh CDN pull of a closed month rebuilds the panel to CLOSE/QVOL
  byte parity (2e-8) and FUND_EMA rank-corr 0.99995 vs the frozen panel — `overlap_validation.json`.
- **Dry-run (signal chain).** Fresh fold_4 inference on the last ~100 frozen anchors reproduces the
  engine replay's positions: **median position-corr 0.99995, min 0.9999** — `signal_loop_dryrun.json`.
  - **★ Netting-warmup note (0C: benign).** An earlier dry-run showed min position-corr **0.9385** at
    one anchor. Root cause: the dry-run ran the netting over only the compared 100-anchor window, so
    its first anchors had not yet accumulated the **24h-cadence legs** (S2, SIZE update every 6 anchors)
    that the full-history engine holds — a **cold-start** of the netting state, not an inference or
    member-boundary discrepancy. Adding a 40-anchor netting **warmup** before the compared window
    lifts the min to **0.9999**. The live loop is unaffected (it always runs with full-history warmup);
    this was purely a dry-run harness artifact.
- **End-to-end.** `run_daily.sh` completes the full cycle in ~4.5 min (ingest 1.5 / inference 3 / P&L /
  monitor), idempotent, with a flock lock, date-rolled logs (`exports/live/logs/`), and a per-step
  failure alarm (`exports/live/logs/ALARM.log`).

## Files

`datasource.py` (pluggable source) · `funding_derive.py` (funding_ema recipe + interval cache) ·
`build_tail.py` (windowed-splice ingest + overlap validation) · `signal_loop.py` (inference + C1 +
positions + dry-run) · `paper_pnl.py` (dual-curve paper P&L) · `monitor.py` (C4 report) ·
`run_daily.sh` (orchestrator + cron).

## Caliber

The paper P&L is **structural caliber** under a conservative maker fill — a signal-quality read, not a
fund net return. Deployment still needs a live maker pilot (see `docs/RUNBOOK.md`). Benchmark against
research/signal Sharpes, never an after-all-cost fund net.
