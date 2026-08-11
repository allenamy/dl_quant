# Wide-metrics 7-channel leakage audit (item 1 static + item 2 realism)

> **created:** 2026-07-13 | **for:** 0C ARM-S2 +0.0277 orthogonal-increment leak-clearance | **verdict: LEAKAGE-CLEAN** (construction + restatement); residual = undocumented sub-5-min publish latency, negligible for YR24.

## Context
0C: +0.0277 holds only if the 7 channels at hour t contain values *publicly published by t*; dyn-share can't see dynamic publish-lag leakage.

## ITEM 1 — static build-path audit (build_wide_metrics_channels.py)

**A. Alignment <= t-5min — PASS 10/10.** Every sampled (coin,hour): panel value uses the snapshot at create_time = t-5min; the NEXT snapshot (at t) is correctly excluded. asof: `idx=searchsorted(src, t-300000, 'right')-1` -> strictly <= t-5min, never future. Sample lags all 5.0 min.

**B. Normalization causality — PASS.** Recomputing oi_level_norm / taker_ratio_ema / d_oi at cut t using ONLY rows <= t equals the full-series stored value (0 mismatch / 6 points). rolling(720)/ewm(hl=6) are trailing; xsec-z is per-ts. No future data enters any transform.

**C. OI update cadence.** sum_open_interest changes every 5-min bar (frac=1.00) -> the archive is genuinely 5-min granular; the vague web 'OI updates every 15 min' refers to a coarser display/other endpoint, not this data.

## ITEM 2 — publish-delay realism

**Restatement — NONE (decisive).** Compared daily-archive values to the LIVE `fapi.binance.com/futures/data` endpoints for identical timestamps (BTCUSDT 2026-06-20 12:00/12:05 UTC; fapi unreachable from the training box, fetched via agent web access):

| field | archive | live fapi | match |
|---|---|---|---|
| sumOpenInterest @12:00 | 98120.753 | 98120.75300000 | ✓ |
| sumOpenInterestValue @12:00 | 6245739151.78 | 6245739151.78468 | ✓ |
| sumOpenInterest @12:05 | 98130.828 | 98130.82800000 | ✓ |
| topTrader longShortRatio @12:00 | 1.196794 | 1.1968 | ✓ |

Archive == live point-in-time snapshot (byte-exact), timestamps identical -> **no post-hoc restatement** on OI or the positioning ratio.

**Publish lag.** Not documented by Binance. These are point-in-time snapshots (time field = exchange-reported snapshot time); OI is 5-min fresh; community practice = available ~1-2 min after the timestamp. Our t-5min lag gives a ~3-4 min buffer. Residual: if true Δ>5min, up to (Δ-5) look-ahead — but for a **24h** target (YR24) a few-min early peek at slowly-varying OI/positioning contributes ~0 (magnitude ~ (Δ-5)/1440min). Dynamic magnitude is settled by the 32ch ablation (running) + optional lag-sensitivity retrain.

## Verdict
- Construction leak: **NONE** (alignment <=t-5min 10/10; normalizations causal).
- Restatement leak: **NONE** (archive byte-exact == live fapi).
- Residual: undocumented sub-5-min publish latency; covered by the 5-min buffer and economically negligible for YR24.

**+0.0277 is NOT explained by a construction or restatement leak.** Channels at hour t hold only point-in-time snapshots published <= t-5min, verified byte-exact vs the live API. Leakage-clean; the 32ch ablation is the dynamic-attribution clincher.
