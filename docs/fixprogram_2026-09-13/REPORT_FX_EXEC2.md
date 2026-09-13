> **创建:** 2026-09-13 15:4xZ(lead 转录) | **Session:** FX-EXEC2(teammate fx-exec2)撰文 / lead 落盘 | **状态:** 逐项进行中; 克隆 `cc_tmp/fx_exec2` 分支 `fix/ledger-alarms-2026-09-13`(基 ef60f85), 全电池未跑; 未部署 | **作废条件:** 克隆分支任一提交被改写; 或 ef60f85 以外运行树被部署
> **落盘说明**: 子代理工具约定「以文本交回、不写报告文件」⇒ lead 逐字转录 FX-EXEC2 消息, 未改事实、数字或措辞(原文英文保留)。

# REPORT · FX-EXEC2 · 账本 / 告警 / 运维已知问题修复

## LED-02 · protective flatten cost readers (commit c46fb83)

**Housekeeping on resume.** My clone's branch `main` was renamed at c2e9bdc to `fix/ledger-alarms-2026-09-13`. The clone-local `main` ref was reset to ef60f85 (= origin/main). Correction to the lead's resume note: ALM-01 was already committed as c2e9bdc before the pause. There were no uncommitted code edits.

The ledger copy is intact. I moved it out of the clone, unchanged, to `/Users/haosiyu/cc_tmp/fx_exec2_state_20260913T1427Z`, and the clone's `state/` was restored with `git checkout -- state`. A guarded re-check of the 14:27Z SHA256SUMS gives 268 files and 1 mismatch: `anchor_report_last.json`. My own `--dry` runs of the new anchor_report wrote it at 15:01Z. Every ledger file matches.

**Problem.** `cost_buckets.partition` prices a fill against `mid_at_anchor`. The watchdog writes `mid_at_anchor=None` on every protective_flatten row by design (watchdog.py:2365-2367). So the 09-12 12:47Z batch (255 legs, 235,382.55 USDT) reads 255/255 unpriced, and stays unpriced even after E1 wrote 3,656 fills rows with every commission. `ops/daily_summary.py` shows no flatten at all.

**Facts** (FACT_TABLE_EXEC2 §LED-02; ledger copy 14:27Z)
- All 10 FLATTEN batches carry `avg_fill_px` and `mid_at_submit` on every filled row. `mid_at_submit` is the mid from the one batched bookTicker read taken before the submit loop (watchdog.py:2354-2364).
- On 09-09 and 09-12 the fills rows, joined by (rebalance_id, symbol) after a (symbol, trade_id) collapse, close exactly to the order notional: 243/243 and 255/255 legs.
- The E1 fills rows carry attempt_idx 2 and their order rows carry 1 (venue_fills.py:1179), so attempt_idx cannot be a join key. This is logged as NEW-02.
- 09-09: one BOMEUSDT commission is in BNB. 08-05 12:18Z: 4 rows carry a raw `fee_paid 0.0, fee_all_usdt False`. 09-06 and the older batches have no fills rows.
- NEW-01: on all 10 batches, the flatten rows' `anchor_ts`/`submit_ts` is the row-write time, after every fill.

**Red evidence.** Receipt `FX_EXEC2/receipts/LED02_red_old_ef60f85.log`. Same test file on ef60f85, reading the only reader that tree has (`bucket_fills`): 9/28 pass, 19 FAIL, no crash. It reads n_measured 0 / n_unpriced 255 on 09-12, fee None, no daily_summary function.

**Fix**
- New pure `cost_buckets.flatten_cost` / `flatten_cost_by_batch`. A leg is measured when it has a usable avg_fill_px, a usable mid_at_submit, and a known fee.
  - The fee is the order row's `known_fee`. Otherwise it comes from the fills rows: joined on (rebalance_id, symbol), collapsed on (symbol, trade_id) with the last row winning, every commission present and in USDT, and Σ|fill_notional| equal to |filled_notional| within max(0.01 USDT, 1e-6 relative).
  - Any other leg goes into exactly one bucket, with a named reason: no_fills_rows, commission_non_usdt_unconverted, order_row_fee_not_known_usdt, fills_do_not_close, ambiguous_join, fills_row_without_trade_id, commission_missing, no_mid_at_submit, unknown_fill.
  - bps is computed over measured notional only, and is None when nothing was measured.
- `score_post_fix` E6 adds `protective_flatten_exit_cost` beside an unchanged `protective_flatten_buckets`.
- `daily_summary.flatten_batches_facts` plus a 【保护性平仓】 section select batches by fill time.
- `bucket_fills` and the W2 rule are untouched. The rehearsal census (tests_rehearsal_anchor [4i]) gains decisions for cost_buckets.py and daily_summary.py: a FLATTEN join key and a display grouping, no §2.5 count.

**Tests.** `live/tests_flatten_exit_cost.py` on a verbatim gz fixture with a sha-pinned MANIFEST (builder `FX_EXEC2/devices/build_fixture_led02.py`): 29/29.
- 09-12: 255 measured, fee 117.69126836 USDT re-derived independently, 5.000 fee bps, 5.391 adverse bps vs mid_at_submit.
- 09-09: 242 measured, fee 115.902218 (the naive sum over supersede rows would double it), BOME fee-unknown.
- 09-06: 268 fee-unknown.
- 08-05: 4 raw-BNB rows plus 98 no_fills.
- Neighbour cells E0–E9, the anchor-mid rule unchanged, E6 wiring, and the daily_summary window.
- Neighbours green at c2e9bdc: tests_readers_three_bucket 75, tests_daily_summary 107+1 SKIP, tests_rehearsal_anchor 59.
- Receipts: `HEAD_c2e9bdc_tree_8becaf4_*`.

**Battery.** Not yet run on this chain. It will be run on the stacked tree.

**Not proven**
- That `mid_at_submit` is the right benchmark for a crisis exit. It omits the move between the trip evaluation and the bookTicker read, which the output states.
- That the fills rows are complete beyond the notional-closure identity.
- The 8 older batches stay fee-unknown in this reader (LED-03).
- Other readers selecting flatten rows by `anchor_ts`/`submit_ts` are not audited (NEW-01).
