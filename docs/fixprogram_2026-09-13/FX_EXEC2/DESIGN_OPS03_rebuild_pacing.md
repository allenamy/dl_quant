> **创建:** 2026-09-13 16:3xZ | **Session:** FX-EXEC2 | **状态:** 事实表 + 设计, **未编码, 待 lead 裁定** | **作废条件:** live/rate_budget.py sha ≠ 5bba14acb78c7c86, 或复算出的回放数与本文不符

# OPS-03 · Request budget on rebuild anchors: fact table and design

## 1. The question
AUDIT_EXEC OPS-03: "the 12Z flat-to-full rebuild ran at 99% of the self-imposed weight budget". The job here is to
measure the real headroom on rebuild anchors and decide whether rebuild pacing is unsafe. Any pacing change alters
execution timing, so this document comes before any code.

## 2. Facts
Sources: FACT_TABLE_EXEC2 §OPS-03; the 14:27Z ledger copy; receipts `OPS03_sliding_shaper_replay.{json,log}`; device
`devices/ops03_sliding_shaper_replay.py`.

| # | Fact | Evidence |
|---|---|---|
| F1 | The self-imposed WEIGHT shaper uses a **fixed** 60 s window that opens on the first spend after a reset. The ORDER and REQUEST shapers use sliding windows. | `live/rate_budget.py:147-166` vs `:169-219` |
| F2 | "99%" is that fixed-window shaper's own peak, with **waits=0**: at 09-13 12Z the log reads `peak/min weight=990 … waits=0 wait_s=0.0`. | anchor_runs.log 12:58:29Z |
| F3 | Venue-side peaks (`X-MBX-USED-WEIGHT-1M`) against the published 2,400/1m cap: 1,270 at 09-13 12Z, 955 at 09-10 00Z, 990 at 09-07 04Z, 1,620 at 08-26 20Z, 1,615 at 08-22 12Z, 1,005 at 08-26 12Z. Worst case is 67.5%; the backstop threshold ("wait at 80%") is 1,920. | anchor_runs.log venue_rate lines; rate_timeline headers |
| F4 | Maximum weight in any **sliding** 60 s of our own recorded requests: 1,289 at 09-13 12Z, 1,188 at 09-10 00Z, 1,229 at 09-07 04Z, 1,620 at 08-26 20Z, **1,941 at 08-26 12Z** (81% of 2,400), 1,780 at 08-22 12Z. Steady anchors: 1,013 at 09-12 12Z, 1,115 at 09-11 08Z. The fixed window lets a burst straddling its boundary reach ~2× the self-cap. | replay receipt `recorded_sliding60_max` |
| F5 | Orders peaked at 273 in a sliding 60 s (self-cap 300, venue 1,200/1m) and at 71 in a sliding 10 s (self-cap 100, venue 300/10 s). Requests peaked at 304 in a sliding 60 s (self-cap 600). | FACT_TABLE §OPS-03 #3 |
| F6 | The 85 venue_reject rows of 09-13 12Z are all **-5022**. The "157 null-submit rejects" of 08-26 12Z are also all -5022: **7,006 of 7,006** venue_reject rows in the ledger have `submit_ts None`, which is how the writer records any venue_reject, not a rate-limit signature. `config/book.json _gross_mult_note` attributes the 08-26 §4-5e trip to a rate-cap storm; that attribution is not supported by the rows. | orders.jsonl notes |
| F7 | The bursts sit in **phase B/C settlement**, not in maker submission. In a sliding-cap replay the first delayed request falls 2,620-2,684 s after the anchor's first request (≈N+44). Delayed requests are mostly `/fapi/v1/userTrades`, `/fapi/v1/allOrders`, `/fapi/v1/aggTrades` (markout backfill) and `/fapi/v1/income`; top-up order POSTs delayed: 0 at 09-13 12Z, 6 at 09-10 00Z, 3 at 09-12 12Z. | replay `delayed_by_path`, `first_delay_at_s_after_first_request` |
| F8 | The anchor has a hard cap of 3,600 s. The 09-13 12Z anchor ended at 3,510 s (`anchor done` 12:58:30Z), with the markout backfill `CAPPED(deadline)`. The backfill is deadline-driven (`max_seconds = cap − elapsed − 90`), so it stops on its own. | anchor_runs.log 12:58:28Z; run_anchor.py:887-897 |

## 3. Reading
- **No rebuild came near a venue limit.** The worst venue reading was 67.5% of the weight cap; orders never exceeded 23% of theirs. Every reject on a rebuild anchor was -5022.
- **The "99%" does not measure risk.** It is the fixed-window shaper's own peak, reached without a single wait.
- **The real latent risk is F1/F4.** A fixed window does not bound emission in a sliding 60 s. On 08-26 12Z our own requests reached 1,941 weight in a sliding minute: 81% of the venue cap and just above the 80% backstop threshold. The venue's aligned-minute counter read only 1,005, because the burst straddled its minute boundary. The rate_budget module's own docstring names exactly this boundary-burst shape as the cause of both 07-30/07-31 -1003 bans.
- **It is not specific to rebuilds.** Steady anchors also exceed the self-cap in a sliding window (1,013 and 1,115), just by less.

## 4. Options
**A (recommended). Sliding-window weight shaper, same 1,000/min cap.** `spend_weight` keeps a deque of (t, weight) like the order and request shapers already do.
- **Measured cost** (replay of the recorded timelines):

  | Anchor | Total added delay | Max single wait |
  |---|---:|---:|
  | 09-13 12Z | 34.5 s | 5.1 s |
  | 09-10 00Z | 14.9 s | 1.6 s |
  | 09-07 04Z | 31.1 s | 4.6 s |
  | 08-26 20Z | 64.5 s | 15.1 s |
  | 08-26 12Z | 79.6 s | 11.3 s |
  | 08-22 12Z | 64.5 s | 19.4 s |
  | Steady anchors | 5.6-5.7 s | — |

- **Where the delay lands:** almost all on settlement reads at ≈N+44, and at most 6 top-up POSTs, each by seconds.
- **Consequence:** the markout backfill starts up to ~80 s later and writes fewer marks in that anchor. The cron and later anchors pick those up; it cannot overrun the cap (F8).
- **Behaviour change:** request timing only. Order sizing, the book and the experiments are unchanged. It still changes execution timing, so it needs your ruling.
- **Red test (would fail on today's code):** with a fake clock and `sleep` injected, spend 100 at t=0, then 900 at t=59.5, then 900 at t=60.1. Assert that no 60 s sliding window of admitted spends exceeds `WEIGHT_PER_MIN`. The fixed window admits 1,900 in 0.6 s, so it goes red. Neighbour cells: exactly at the cap, a single spend larger than the cap, a concurrent-thread spend, and the stats `weight_peak_per_min` becoming the sliding peak.
- **Battery impact:** tests_request_budget and tests_rate_backstop_window assert the current shaper's behaviour and would need revisiting under the same ruling.

**B. Staged rebuild** (split a flat-to-full rebuild across two anchors). This changes book behaviour and needs a user ruling. It is not supported by the evidence: no rebuild approached a limit (F3), and the bursts are in settlement reads, not submission (F7).

**C. No pacing change; correct the record.**
- State in the acceptance template that the per-anchor headroom figures are venue used/2,400 and the sliding-60 s emission maximum, not the fixed-window self-peak.
- Amend `config/book.json _gross_mult_note` so it no longer cites a rate storm for 08-26 (F6). That is a doc-only commit.

## 5. Recommendation
Do **C now**, since it is doc-only and safe. Do **A** after your ruling, as its own item with the red test above and a full battery. Do not do **B**.

## 6. Not established
- Whether the venue counts the aligned minute or a sliding window for bans. The 07-30/07-31 bans suggest boundary bursts matter, but that is not proven here.
- The gap between the venue header count and our own count (`gap_vs_this_process=500` at 12Z: other consumers on the IP, or window alignment). Its attribution is marked undetermined in the log itself.
- The replay's delays assume request times shift by the waits and nothing else. In production a delayed settlement read could also change what it reads (more fills visible), which the replay cannot model.
