> **创建:** 2026-09-13 14:5xZ | **Session:** FX-EXEC2 (teammate of team-lead, session_01BzpuBRGZh8oPvpD8NgqsME) | **状态:** 事实表(先于代码; 只追加更正) | **作废条件:** 执行器基底 ≠ ef60f85, 或下列任一文件 sha 变化后未复核

# FACT TABLE · FX-EXEC2 · ledger / alarm / ops items of AUDIT_EXEC (842bbffa)

Scope (FIXPROGRAM §3.1, FX-EXEC2 row): LED-01 · LED-02 · LED-03 · LED-04 · LED-05 · LED-07 · LED-08 · ALM-01 · ALM-05 · ALM-06 · STA-02 · STA-03 · OPS-03 (design first) · CFG-02 · CFG-07 · DOC-01 (executor side).

## §0 Frozen objects

| Object | Value |
|---|---|
| Executor base | `ef60f85ad93e49f2e0f190bc6e8a15d04073f193` (= origin/main), clone `/Users/haosiyu/cc_tmp/fx_exec2` (no `.env`) |
| Ledger copy | `rsync -a --exclude acceptance/` of `~/dl_quant_live/state` at 14:27:00–14:27:06Z (outside anchor windows), 441 MB, 44 pilot_log days 20260801..20260913; guarded SHA256SUMS of 268 ledger/state files (t6_sha_guard: dataless flag off, bytes read = st_size), 0 empty-file hashes |
| guard_twin copy | `/Users/haosiyu/cc_tmp/fx_exec2_guard_twin` 14:44:18Z: guard_twin.py `0b299781…`, income.jsonl `ffbb1102…` (109,545 rows), snapshots.jsonl `c1a64396…`, compare.jsonl `5a75c0e7…`, latest.json `09799368…`, alerts.log `1f1569fc…` (84 lines) |
| File shas at ef60f85 (sha256, 16 hex) | live/pilot_log.py `f02baa69756ffe1d` · live/cost_buckets.py `0d31d10a1353f4ba` · live/pilot_metrics.py `5ac7b16d0f97f2f8` (FROZEN, metrics_freeze) · ops/score_post_fix.py `3c307356e8c6eeec` · ops/daily_summary.py `bf4151a8365c3c82` · ops/first_anchor_review.py `18e8ad8cdfb978fb` · ops/anchor_report.py `9e448836d3fc398d` · ops/check_funding_span.py `2c9e5e5ee316b6bb` · live/binance_broker.py `13be0871cae0e243` · live/per_name_stop.py `8fb79dd84fcac696` · scheduler/anchor_loop.py `95e72cb059ff1d5b` · config/book.json `f6fd6d0e0f10039a` · ops/backfill_markout.py `95db5ff7b2edb50a` · ops/import_markout_marks.py `45984f334841e70b` · ops/backfill_fills.py `7bf13e88aa8c84e9` · live/watchdog.py `7bcc7f1f454a7c25` · live/venue_fills.py `884f2238d21f7d6b` · live/rate_budget.py `5bba14acb78c7c86` |

All counts below were computed on the ledger copy with `/usr/bin/python3 -B` (no bytecode written), no venue call, no credentials.

---

## LED-01 · fills.jsonl rows per trade

| # | Fact | Evidence |
|---|---|---|
| 1 | The second row per trade is the **documented supersede contract**, not an accidental duplicate. The fill is written at settlement with the +60 s mark pending; the markout job appends the same fill again with the mark and `supersedes_trade_id`. | `live/pilot_log.py:275-292` (SCHEMA["fills"] comment: "the backfill APPENDS THE SAME FILL AGAIN … ANY READER MUST COLLAPSE"); writers `ops/backfill_markout.py:299-323` (`_complete`, `_terminal`), `ops/import_markout_marks.py:72-86` |
| 2 | 0 duplicate ORIGINAL rows (rows without `backfilled_utc`) for any (symbol, trade_id) on any of 44 days (93,739 rows). | ledger scan |
| 3 | "Exactly twice" is the current steady state only: 08-01..09-03 many trades have **3 rows** (e.g. 20260826 913 trades × 3, 30 × 2), a terminal `aggtrades_window_expired` row at 09-05 09:05Z followed by an `import_markout_marks` row at 09:37Z; 09-04..09-11 exactly 2; 20260912 3,656 × 1 (E1 flatten rows, mark still pending) + 1,240 × 2; 20260913 1,053 × 1 + 724 × 2 (marks pending). | ledger scan; example 1000RATSUSDT trade 370512812 lines 1/973/1886 of 20260826 |
| 4 | 20260909: 69 rows carry `backfilled_utc` without `supersedes_trade_id` (the B26b fills backfill of the crash anchor), each later superseded by a markout row. | ledger scan |
| 5 | Both collapsers key on `trade_id` ALONE: `pilot_log.collapse_supersedes` (L452-474) and FROZEN `pilot_metrics.dedupe_fills` (L265-291). Binance trade ids are per-symbol sequences. Cross-symbol trade-id collisions observed: **0** in 93,739 rows — latent, not present. | code; ledger scan |
| 6 | In-repo readers collapse: watchdog.py:1381-1382 (raw AND collapsed counts, the raw count is deliberately kept as mark-producer supply health), first_anchor_review.py:241, first_real_anchor.py:58, pilot_metrics m2 L300, reconcile.py:41-52 (reads ORDERS). | code |
| 7 | Decision requested from lead 14:5xZ (message): (A) format change — marks to a new table, fills.jsonl write-once; (B) contract fix — write-time guard against a second original + (symbol, trade_id) collapse key + canonical accessor. Recommendation B. | SendMessage to team-lead |

## LED-02 · protective-flatten cost readers

| # | Fact | Evidence |
|---|---|---|
| 1 | 10 FLATTEN batches exist in the live ledger; every row is `terminal_reason=filled`, **every row has `mid_at_submit` and `avg_fill_px`**, `mid_at_anchor` is None on every row (writer: `watchdog.py:2365-2367` "no anchor mid exists for a ladder action"). No symbol has more than one filled row in any batch. | ledger scan (08-01 105 · 08-02 83 · 08-05 108+102 · 08-21 108+102 · 08-26 334 · 09-06 268 · 09-09 243 · 09-12 255 rows) |
| 2 | `cost_buckets.partition` requires `mid_at_anchor` ⇒ every flatten row is `unpriced`, permanently, whatever the fee: 255/255 on 09-12 (audit ran it). | `live/cost_buckets.py:98-103` |
| 3 | `mid_at_submit` = the mid from ONE batched bookTicker call taken by `flatten_all` before its submit loop — the exit's arrival price. | `watchdog.py:2354-2364` comment [B25] |
| 4 | Fees: order rows keep `fee_paid None` by the append-only rule (E1). Fills rows exist only for 09-09 (3,095 trades; USDT 3,094 + BNB 1 = BOMEUSDT) and 09-12 (3,656 trades, all USDT, E1 backfill 13:13Z). Joined by (rebalance_id, symbol) after a (symbol, trade_id) collapse, Σ|fill_notional| equals the order row's |filled_notional| on **243/243** (09-09) and **255/255** (09-12) legs. | ledger scan |
| 5 | Join key must NOT include attempt_idx: order rows say `attempt_idx 1`, the E1 fills rows say `2` because `venue_fills.py:1179` writes `1 if otype == "maker" else 2` for every non-maker leg including protective_flatten. | code + ledger (255/255 pairs (1,(2,))) — **NEW-02** (below) |
| 6 | 08-05 FLATTEN-20260805T121829Z: 4 rows carry `fee_paid 0.0, fee_all_usdt False, fee_conversion None` (raw USDT slice of BNB fees) — known_fee() says unknown; a reader that trusts `fee_paid is not None` counts them as free. | ledger rows TAO/REZ/RVN/ARB |
| 7 | Prototype (not a result claim; for test expectations): 09-12 batch vs mid_at_submit adverse +5.391 bps, fee 117.6913 USDT = 5.000 bps over 235,382.55 USDT; 09-09 batch adverse +4.139 bps; the 242 legs whose fills are all USDT-commission: fee 115.902218 USDT = 5.000 bps over 231,804.45 USDT; BOMEUSDT (20 trades, one with commission 0.0 BNB) is fee-unknown under the unconverted-asset rule. | computed on copy |
| 8 | Readers that bucket flatten rows today: `ops/score_post_fix.py:440-443` (`protective_flatten_buckets` = bucket_fills over rows of the scored rid); FROZEN `pilot_metrics.m1` `protective_flatten_cost` (fee None when no row fee). `ops/daily_summary.py` shows no flatten at all (per-anchor table selects orders by `anchor_ts ==` an anchors row; flatten rows carry the row-write time). `ops/anchor_report.py:78` selects by the anchor's rid. | code |
| 9 | **NEW-01 (writer, owner of watchdog.py):** on all 10 batches `anchor_ts` = `submit_ts` = ONE value = the row-WRITE time after the last fill (e.g. 09-12: submit_ts 12:50:01Z, fills 12:47:39..12:50:01Z; 09-06: 08:48:31Z vs fills from 08:46:10Z); 0 fills after it. `_write_flatten_rows` sets `ts = time.time()` at write and `submit_ts=(ts if _sent else None)`. `position_break.py:188` calls it "a real submit_ts". | `watchdog.py:2303, 2353` + ledger |

## LED-03 · eight older flatten batches

| # | Fact | Evidence |
|---|---|---|
| 1 | 1,210 rows / 270,076.47 USDT (08-01, 08-02, 08-05×2, 08-21×2, 08-26, 09-06); 0 fills rows; 0 client ids; fee_paid None except the 4 raw-BNB rows of LED-02 #6. | ledger scan |
| 2 | Every leg is priceable vs `mid_at_submit` (LED-02 #1) — only the FEE is missing. | ledger scan |
| 3 | guard_twin's local income ledger holds COMMISSION rows since 2026-08-01 00:00Z with fields (tranId, type, symbol, income, asset, time), no tradeId/orderId; its USDT closed-account identity gap is 0.00107 USDT ⇒ complete for USDT. | guard_twin.py:79-100, latest.json |
| 4 | Offline join available without credentials: per (symbol, [first_fill_ts, last_fill_ts] of the leg ± ε) COMMISSION rows. Its accuracy can be measured as a positive control on 09-09 / 09-12, where exact per-trade commissions exist. The exact path (userTrades per symbol per window) needs credentials ⇒ lead. | design |

## LED-04 · daily_nav realised split 07-29..09-12 06:05Z

| # | Fact | Evidence |
|---|---|---|
| 1 | Discriminator on the row itself: `realised_by_type_asset` is written only by the fixed carrier. Live ledger: **250 rows without it** (20260801 … 20260912 04:46:05Z, 43 days) and 8 rows with it (first 20260912 line 2, nav_ts 08:45:16Z). | ledger scan; carrier `anchor_loop.py:2851-2854`, `binance_broker.py:2010-2026` |
| 2 | Watchdog judges the EQUITY day change; `realised_pnl` enters only the deprecated gross companion and an unused `_eq_rows`; `realised_truncated` only marks days UNKNOWN ⇒ no trip decision depends on the defective values. | `watchdog.py:1077-1130, 1262-1277` |
| 3 | Reader using the split: `ops/daily_summary.realised_facts` (legacy rows ⇒ caliber `legacy_carrier_sum_usdt_assumed`, value passed through); `ops/first_real_anchor.py:81` prints it. | code |
| 4 | Correct source for the split: guard_twin income ledger (5-field key, identity gap 0.001 USDT). | audit LED-04; guard_twin.py:96 |

## LED-05 · 09-09 12Z crash-anchor order rows

| # | Fact | Evidence |
|---|---|---|
| 1 | 20260909 orders: 0 rows with rebalance_id A1788956640 (the crashed anchor). | ledger scan |
| 2 | Round-3 reconstruction exists, not applied: `multi_asset/exports/live/pilot_journal/e0909g_reconstructed_orders_12Z_DRYRUN.jsonl` (56,888 B, 52 rows, order_type `reconstructed`, leg_kind maker, Σfee 0.50724 USDT, Σnotional 2,536.21 USDT). Its builder `pilot_journal/tools/reconstruct_orders_12Z.py` calls allOrders (credentials). The older `cc_tmp/e0909g_sim/reconstructed_orders_12Z.jsonl` (01:01Z) is the pre-round-3 version (order_type maker, fees doubled) — must NOT be used. | files |
| 3 | `reconstructed` is in ORDER_TYPES at ef60f85 (running tree). | `pilot_log.py:138` |
| 4 | Rule: ledger copy → watchdog → write, outside anchor windows (RUNBOOK_deploy_executor_b681ca5 §4, E-0909-G). | runbook |

## LED-07 · anchors.jsonl as a series

| # | Fact | Evidence |
|---|---|---|
| 1 | 257 rows 08-01..09-13 12Z; 130 carry `external_book.nominal_ts` (external era from 08-22 08Z), 127 do not (internal era). 0 duplicate nominal anchors. No `schema_version` field on any row. | ledger scan |
| 2 | 19 rows `opening_halted: true`, all with target_gross > 0 and realized_gross 0 (e.g. 09-12 16:24:01Z target 235,335). | ledger scan |
| 3 | External era `anchor_ts` − nominal = 1,381..1,547 s (capture time ≈ N+23..N+26 min). Internal-era off-grid manual rows: 08-01 06:29:58Z, 08-02 05:32:04Z. | ledger scan |
| 4 | Nominal external anchors without a row: 08-25 16Z, 08-29 20Z, 09-02 00Z, 09-09 12Z (134 expected, 130 present). | ledger scan |
| 5 | Rebuild anchors (previous nominal realized_gross < 1 USDT, this one > 1): 08-22 12Z, 08-26 20Z, 09-07 04Z, 09-10 00Z, 09-13 12Z. | ledger scan |

## LED-08 · ops/anchor_report.py (per-anchor Telegram report)

| # | Fact | Evidence |
|---|---|---|
| 1 | Folds: `fN = Σ abs(filled_notional or 0)` (L80), `iN = Σ abs(intended_notional or 0)` (L81), `fee = Σ (fee_paid or 0)` (L82), fee bps = fee/max(fN,1) (L85); `rg:.0f` raises on None realized_gross (L88); `kg.get('gross_usdt',0)` (L88). | code |
| 2 | Not latent on the historical ledger: A1785931245 (08-05 12Z) 103/103 fills fee-unknown (raw BNB) ⇒ old formula prints `fee 0.00bps`, buckets say None; A1785657675 (08-02) 22/95 fee-unknown ⇒ old 1.69 vs measured 2.24 bps; A1789215839 (09-12 12Z, external era) 4 unknown-fill rows ⇒ old 2.74 vs measured-fee 2.47 bps. | computed on copy with cost_buckets |
| 3 | Thresholds: net/gross warn at 5 % (L89) vs deep-check template ±1 % (CRON_TEMPLATES_2026-09-04.md:13); taker-share warn > 10 % (L91) fired on 51/101 reports (the ≥90 % maker baseline is stale per CHK-03, cause unattributed, owned by X-COST/K5). | code, anchor_report.log |
| 4 | `funding.jsonl 缺` on a flat settlement anchor: 09-13 08Z report (book flat, no 20260913/funding.jsonl). | anchor_report.log, ledger dir |
| 5 | On halted anchors the report prints 换手 106.4 % / 成交 0U (intent of `blocked_by_halt` rows over gross_before) with no halted label. | anchor_report.log 09-13 04Z |
| 6 | Telegram send at L115-125 reads `.env`; `--dry` skips it. The builder is not a function ⇒ untestable without I/O. | code |

## ALM-01 · funding_span alarm

| # | Fact | Evidence |
|---|---|---|
| 1 | Fingerprint reads `x.get('ours')`/`x.get('venue')` (L99) while records carry `ours_h`/`venue_h` (L73) ⇒ stored findings `"ANKRUSDT:None->None"` ×15; an interval change on an already-stale name cannot open a new episode. | code; `state/live/alarm_episodes/funding_span.json` |
| 2 | HIGH text (L106-108) says the funding leg of these names is EMA-smoothed over the wrong settlements; in external mode the traded book comes from the producer's target file; the table feeds only the executor's internal panel (`signal/live_panel.py:55`). | code; audit ALM-01 |
| 3 | `DEFAULT_INTERVAL_H = 8.0` (L39) unused: names absent from fundingInfo (13) are listed, never compared; absent = default 8h OR delisted (not distinguishable offline). Table: 140 names, 99 × 8h, 41 × 4h, built 2026-07-25. | code; config/funding_span_table.json |
| 4 | Caller `scheduler/run_anchor.py:793-797` every anchor; failure-to-run pages HIGH. | code |

## ALM-05 · arm() A7 margin diagnostic scope

| # | Fact | Evidence |
|---|---|---|
| 1 | Scope = `LIVE_PREDS_PATH` (preds_latest.json, the executor's internal DL panel: 110 names); 12Z traded book 244 names of a 450-name universe. | `binance_broker.py:1361-1378`; anchor_runs.log 12Z arm record |
| 2 | Record-only ("never the reason an anchor fails to start"); feeds `checks_verified`/`checks_not_verified` and `risk_floors_usdt`. | `binance_broker.py:1337, 1443-1454` |
| 3 | External target path from config `external_book.path`; `external_book.newest_verified_anchor_ts(cfg)` exists. | `config/book.json:155-166`; `live/external_book.py:448` |

## ALM-06 · guard_twin

| # | Fact | Evidence |
|---|---|---|
| 1 | Not a git repo; launchd `com.hsy.guardtwin` StartInterval 1200 s, `/usr/bin/python3 ~/guard_twin/guard_twin.py`; makes signed GETs (credentials) ⇒ tests must never call `main()`; deploy = file copy by lead. | `git rev-parse` fatal; plist |
| 2 | DAY: twin prev close = own last snapshot before 00:00Z (L226-229, e.g. `twin:2026-09-12T23:42:39Z`); arithmetic twin prev close = previous day's LAST daily_nav row (≈20:45Z) (L294-296) ⇒ an evening move between the two reference times reads as a DAY disagreement. 37 of 84 alert lines are DAY. | code; alerts.log |
| 3 | CUM: twin TWR chain (L239-271) vs watchdog `cum_return_from_start_pct` (start-equity caliber); 8 CUM lines. | code; alerts.log |
| 4 | `wd_worst_day_pct` = `c2.get("worst_day_pct")` (L304) = the window's worst day, shown beside today's values; the L354 comment ("today if today is worst") describes pre-c800690 semantics. | code; latest.json −4.2755 (09-06) |
| 5 | LEV lines on rebuild anchors (09-10 00:52Z twin 1.339 vs wd 2.004) are a neighbour cell (book building, not flat, not halted). | alerts.log |

## STA-02 · per_name_stop paging tier

| # | Fact | Evidence |
|---|---|---|
| 1 | Every event from `PNS.update_from_snapshot` is sent at HIGH: `for _m in _pns["alarms"]: self.alarm("HIGH", _m)`. | `anchor_loop.py:2600-2602` |
| 2 | Event kinds in `evaluate`: exit→cooldown (L102), cooldown expiry "冷却期满, 恢复可入" (L109), trigger "★ per_name_stop 触发" (L129), profile config error (L164). | `per_name_stop.py` |
| 3 | 09-13 12:45:49-55Z: 7 × HIGH delivered expiry pages (COLLECT, CYS, FLOCK, HEMI, MAGMA, RIVER, TRIA). Expiry is evaluated in phase C, so those names sat out the 12:24Z anchor — behaviour, NOT changed here. | notify_audit.jsonl |

## STA-03 · state with no external-mode reader

| # | Fact | Evidence |
|---|---|---|
| 1 | `state/live/no_trade_band.json` written only in the internal branch (`anchor_loop.py:1896`), no reader; last write A1787371250 (08-22 04:00:50Z). | code; file |
| 2 | `harvest_ema.json` read/written only in the internal branch (`anchor_loop.py:1695-1714`); resume removes it (`ops/resume_from_trip.sh:102, 302`); absent under state/live. | code; ls |

## OPS-03 · request budget on rebuild anchors

| # | Fact | Evidence |
|---|---|---|
| 1 | The self-imposed WEIGHT shaper uses a **fixed** 60 s window opened by the first spend after a reset (`rate_budget.py:147-166`), not a sliding window; ORDERS (L169-190) and REQUESTS (L193-219) are sliding. | code |
| 2 | 09-13 12Z: `rate_budget: peak/min weight=990 orders=273 requests=304 … waits=0 wait_s=0.0`; venue header peak used_weight_1m 1,270 of published 2,400/1m, order_count_1m 262 of 1,200/1m; backstop "wait at 80%", backstop_waits 0. | anchor_runs.log 12:58:29-30Z |
| 3 | Our own request timeline, sliding 60 s (max): 09-13 12Z weight 1,289 · orders 273 · orders/10 s 71 · requests 304; 09-10 00Z 1,188/271/60/289; 09-07 04Z 1,229/248/60/259; 08-26 20Z 1,620/255/56/291; 08-22 12Z 1,780/261/65/269; **08-26 12Z (2.0× one-step, tripped) 1,941**/209/47/306. Venue header max: 1,270 / 955 / 990 / 1,620 / 1,615 / 1,005. Steady anchors 09-12 12Z 1,013 (venue 915), 09-11 08Z 1,115 (venue 1,065). | rate_timeline/A*.json |
| 4 | The 85 venue_reject rows of 09-13 12Z are all **-5022** (post-only would take). The "157 null-submit rejects" of 08-26 12Z are also all -5022: **7,006 of 7,006** venue_reject rows in the whole live ledger have `submit_ts None` (08-26 steady anchors 26/22/17 likewise) — a writer convention, not a rate-limit signature. | orders.jsonl notes |
| 5 | ⇒ The "99 %" is the fixed-window shaper's own peak with zero waits; venue-side peaks on rebuilds are 40–68 % of the published weight cap; the sliding-window emission exceeded the 1,000 self-cap on every rebuild (up to 1,941 = 81 % of 2,400 at 08-26 12Z). | derived from #1-#3 |

## CFG-02 / CFG-07 / DOC-01

| id | Fact | Evidence |
|---|---|---|
| CFG-02 | `profiles.wide._basis` says "min_notional_usdt 沿用 20(★ 待裁…)" while the value is 5.0 and the redteam note beside it records 20→5 (2026-08-22 R5). | `config/book.json:147-149` |
| CFG-07 | `_comment` L2 "DEPLOYED BOOK = THREE LEGS (king/s2/funding) …" while `book_source` is `external` (L153); internal-only keys: weights, signs, harvest_ema, no_trade_band_w, risk_budget, leg_cadence. No code or test reads `_comment` / `_basis` (grep). `frozen_inputs` pins only `book.json#panel`. | config; grep |
| DOC-01 | Executor README "架构" section describes the 07-25 internal four-leg local-signal book as the deployed path; no statement of external mode, N+24 read, or the battery size (135 entries = 130 suites + 5 audit gates). STATE/CLAUDE.md side is K4 (lead). | README.md:8-17 |

## New findings while building this table (not in AUDIT_EXEC)

| id | Finding | Owner / handling |
|---|---|---|
| NEW-01 | Flatten order rows' `submit_ts`/`anchor_ts` are the row-write time, after every fill (LED-02 #9). | watchdog.py (fx-w6c) — report to lead; not edited here |
| NEW-02 | Flatten fills rows written by `venue_fills` carry `attempt_idx 2` while their order rows carry the ladder attempt (1) (LED-02 #5). | venue_fills.py (fx-exec) — report; LED-02 reader does not join on attempt_idx |
| NEW-03 | `ops/gate_coverage.py` SUITE_SCOPE has the key `tests_external_book` twice (L241, L242); the first entry is dead (dict literal, later wins). | report to fx-exec (gate_coverage editor) |
