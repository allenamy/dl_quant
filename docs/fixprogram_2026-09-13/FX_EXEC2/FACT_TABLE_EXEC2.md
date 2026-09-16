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

---

## Addendum 2026-09-13 15:3xZ–16:3xZ (append-only; facts found while fixing)

| id | Fact | Evidence |
|---|---|---|
| LED-01 #8 | Contract positive control over the 44-day copy: 93,739 rows, 41,940 (symbol, trade_id) keys, **0 violations**, 0 keys across day files. Chain shapes: O 4,709 · OS 22,663 · OSS 14,568. | receipts/LED01_contract_positive_control.json |
| LED-01 #9 | Identity proof for the collapse-key change: per-day collapse_supersedes kept rows, dedupe_fills order, M2 per day, M2 over the stress subset, and the watchdog cond3_crash_markout detail hash identically before and after (canonical 4d00f6c7…). | receipts/LED01_identity_{before_ef60f85,after_keychange}.json |
| LED-01 #10 | Other trade-id-alone keys: `ops/backfill_fills.existing_trade_ids` (the already-present set) and `ops/import_markout_marks` (the marks file is keyed by trade id). Per-request or per-symbol child-fill dedupes (binance_executor L2106, rejudge_ledger_rows L94, venue_fills per-symbol queries) are already scoped by symbol. | code |
| LED-01 #11 | `pilot_metrics.py` is pinned twice: `config/metrics_freeze.json` AND `ops/UPSTREAM_MANIFEST.sha256` (production→research drift gate). The research vendored copy `multi_asset/engine/live/pilot_metrics.py` must be re-vendored at deploy. | ops/check_upstream_drift.py:42; docs/VENDORED_MAP.md |
| LED-01 #12 | Research repo: 70 .py files name fills.jsonl. 4 call a canonical collapse, 38 mention trade_id without one, 28 have neither (static classification). | receipts/LED01_research_fills_readers.txt |
| LED-04 #5 | Amendment records: 250 pre-fix rows. Post-fix control **8/8 equal**. Σ\|recorded−amended\| USDT: COMMISSION 310.333677, REALIZED_PNL 0, FUNDING_FEE 0. Examples: 09-11 −8.891 vs −18.1413135; 08-30 −0.00241 vs 0 USDT + −0.00509188 BNB; 09-06 after the flatten −0.00305 vs −16.92422909 USDT + −0.08442802 BNB. | receipts/LED04_amendment_receipt.json |
| **LED-04 #6 (corrects #2)** | The watchdog DOES consume the defective values. cond4's §4-4 `cum_return_from_start_pct` prices each transfer day as (realised_pnl + unrealised − unrealised_prev)/nav_prev from the day's last row. Re-implementation reproduces the live last_eval exactly (−1.3136%); with amended realised it reads −1.5749%, i.e. **understated by 0.2613 pp**, mostly 08-02 and 08-05. Row #2 above ("no trip decision depends on the defective values") is wrong for cond4 and is withdrawn. | receipts/LED04_cond4_transfer_day_effect.json; watchdog.py:1533-1600 |
| LED-05 #5 | Offline checks on the copy pass on ef60f85 and on the new tree: 52 rows, 69 fill trades, 52 symbols, 2,536.209446 USDT, fee 0.50724168 equal per symbol to the collapsed fills; target ABSENT. The pre-round-3 cc_tmp rows are refused (sha, maker identity, doubled fees). | receipts/LED05_check_*.json, LED05_negative_control_old_rows.json |
| ALM-06 #6 | Replay: with both DAY ends at the daily_nav nav_ts, 0 of the 35 alignable recorded DAY lines exceed 0.5 pp (max 0.204); 2 lines from 08-21 are not alignable. The watchdog chain recomputed on daily_nav equals the recorded wd cum at all 8 CUM lines. | receipts/ALM06_guard_twin_alignment.log |
| OPS-03 #6 | In a sliding-cap replay the bursts land at ≈N+44 in settlement reads (userTrades / allOrders / aggTrades / income), with 0-6 order POSTs delayed; added delay 5.6-79.6 s per anchor. | receipts/OPS03_sliding_shaper_replay.json |
| ENV-01 | `tests_entrypoint_wiring` runs scheduler/run_anchor.py in DRY_RUN, which refreshes panel_cache / exchange_info_cache through **unauthenticated public GETs to fapi.binance.com**. Every full battery does this. Same single FAIL on ef60f85 and on the new tree (nosleep log_verified=False, environmental). | receipts/LED01b_tests_entrypoint_wiring_*.log; clone `state/panel_cache` mtimes |

---

## Addendum 2026-09-16 (append-only) · LED-08 frozen-reference drift check (lead sent LED-08 back, FIXPROGRAM §8)

All numbers from `devices/led08_drift_reference.py` (sha256 9a85421efb5b2c21…, committed 3b0366c5 before the run that
produced them; earlier version 43e23718 / 68a3bd110cacd0e3… superseded), run against executor tree
`/Users/haosiyu/cc_tmp/fx_exec2` at e808697 and ledger copy `fx_exec2_state_20260913T1427Z/live/pilot_log`
(88 anchors/orders files, per-file sha256 in the receipt). Receipt `receipts/LED08_drift_reference.json` + `.log`.

| # | Fact | Evidence |
|---|---|---|
| D1 | **The defect is in my own 469c3f3, not in ef60f85.** The trailing band is the previous ≤42 traded non-rebuild anchors = exactly 7 days of 4h anchors, so any step shift is fully inside the window after 7 days and the band re-centres on it. Measured: as of the latest ledger slot the band holds 42 slots (1788508800..1789214400) and its taker median is already **21.580%**, i.e. it has completely absorbed the 09-08 step; it raises nothing. | receipt `current`; `ops/anchor_report.py:33-36, 88-100` |
| D2 | **Frozen reference, report's own caliber** — S1a window, nominal slots **1787875200..1788264000** inclusive (08-28 00:00Z .. 09-01 12:00Z): 27 slots, **0 halted, 0 rebuild, 27 eligible**; taker share median **0.05010273247425126**, MAD **0.02345233920549095**, range 0–0.25216; \|net/gross\| median **0.003638**, MAD **0.0022960000000000003**, range 0.00007–0.01064. | receipt `windows.S1a_…` |
| D3 | **Population positive control.** That 27 / 0 / 0 equals what X-COST's independently written `x_cost_decompose.py` selected for S1a (RESULT_X_COST.md T1). The device asserts it; a mismatch is a hard failure, not a note. This is the only independent control — the second window in the device is mine and its expected population is a regression pin. | RESULT_X_COST.md T1; device `WINDOWS` assert |
| D4 | **The caliber is NOT X-COST's, and the two must not be quoted interchangeably.** X-COST's 93.1% is M/(M+T) by the **fill-level `venue_maker_flag`** over fills de-duplicated on (symbol, trade_id), pooled by notional over the period (⇒ taker 6.9%). The report's taker share is Σ\|filled_notional\| of **order rows with `order_type == "topup_taker"`** over Σ\|filled_notional\| of the anchor, per anchor (⇒ 5.010% median on the same window). A maker order row the venue filled as taker (from_reject MARKET, chase IOC) is taker to X-COST and **maker** to the report. The two agree to ~2 pp here by arithmetic accident, not by construction. | RESULT_X_COST.md §"Frozen definitions"; `anchor_report.order_facts` L73-75 |
| D5 | **Drift today.** taker share **0.05010 → 0.21580 = +16.570 pp** against a threshold 3×1.4826×MAD_ref = **10.431 pp** ⇒ would warn. \|net/gross\| **0.003638 → 0.010274 = +0.664 pp** against its threshold **1.021 pp** ⇒ would **not** warn. The 5% hard net/gross ceiling is untouched by any of this. | receipt `drift` |
| D6 | **Fee-only economic translation of the taker drift, reported not gated.** Fee schedule measured maker **2.00** / taker **5.00** bps (unchanged across both windows, X-COST §1 / CHK-03). Median filled_notional / realized_gross over 09-08..09-13 12Z = **0.0472**. 16.570 pp × 3.00 bps × 0.0472 = **+0.0235 bps/anchor/gross**, against the frozen K2 book-level δ of **0.05** ⇒ the recorded maker-share collapse is a real level shift that is **below** the book-level materiality band. | receipt `drift.taker_share.economic_fee_only` |
| D7 | **Sensitivity of the threshold choice.** k×1.4826×MAD_ref uses single-anchor dispersion as the yardstick for a shift in a median, so it is insensitive by construction (10.43 pp for taker). The sensitive alternative, 3× the SE of the median (3 × 1.2533 × 1.4826 × MAD_ref / √n), is **2.516 pp** for taker (and 0.246 pp for |net/gross|) — it would fire on ordinary regime differences. Both are in the receipt; the operative one is the first. | receipt `drift.*.threshold_alternative_se_of_median` |
| D8 | **Where each side can be computed.** `daily_summary.main` already reads **every** ledger day (`PL.available_days` then `read_day` per day), so recomputing the reference window costs it no new reads. `anchor_report.gather` reads only `A−9d .. A` (L232-234), so it **cannot** recompute the reference and must print the pinned value. | `ops/daily_summary.py:578-584`; `ops/anchor_report.py:232-234` |
| D9 | **Delivery gap, named not accepted.** No launchd plist in `~/Library/LaunchAgents` references `ops/daily_summary.py` (grep over all plists: no match) and it does not appear in `docs/CRON_TEMPLATES_2026-09-04.md` (grep: no match). `com.hsy.anchor_report` runs the per-anchor report at N+55 six times a day. So routing the **verdict** to the daily summary means nothing schedules it today; the **levels** still reach Telegram every anchor through the report's baseline line. Scheduling is K5's / the lead's, not LED-08's. | plists; CRON_TEMPLATES_2026-09-04.md; com.hsy.anchor_report.plist |

---

## Addendum 2026-09-16 (append-only) · ALM-06 (ii) · the independent CUM alert, decomposed cause by cause

Device `devices/alm06_cum_decomposition.py` (committed before each of its five runs; the last is 65af2614), receipt
`receipts/ALM06_cum_decomposition.json` + `.log`. Inputs: the 14:44Z guard_twin copy (snapshots 1,655 rows, income
109,545 rows, compare 1,655 rows — each sha256'd in the receipt) and the 14:27Z pilot_log copy. Read-only, no venue.

| # | Fact | Evidence |
|---|---|---|
| A1 | **The replay is faithful, and it was not faithful until two defects in my own device were found and fixed.** `T` (the twin chain as it runs) reproduces the recorded `cum_pct_twin` on **1,655/1,655** rows, max difference **0.0**; `C2b` (the reconstructed watchdog chain) reproduces the deployed `wd_chain_arith_pct` to **4.95e-05 pp**. Run 2 reproduced **0/1,654** — I had parsed the row's UTC with `time.mktime(strptime(...)) − time.timezone` (right only when `tm_isdst == 0`, which `strptime` does not set) and then, after fixing that, was still one snapshot behind because the compare row's only timestamp is second-floored `utc` while the snapshot it was built from carries milliseconds and the twin appends it before computing. | receipt `summary`; device commits 33bbfc58, 5efe8393 |
| A2 | **All 8 recorded CUM lines are explained by DAY-CLOSE TIMING alone.** twin close = the twin's own last snapshot of the day; watchdog close = daily_nav's last row (~20:45Z). Per line (gap / timing leg / residual_ii): 08-21 16:22 −0.133/−0.133/+0.000 · 08-21 19:04 +0.972/+0.972/+0.000 · 08-27 01:11 +0.518/+0.518/−0.000 · 08-31 01:10 +0.652/+0.658/−0.009 · 09-03 16:56 −1.500/−1.324/−0.009 · 09-04 12:57 +0.547/+0.689/−0.017 · 09-11 20:57 +0.521/+0.664/−0.016 · 09-12 04:58 +0.689/+0.831/−0.016. | receipt `rows` |
| A3 | **The LED-04 allowance is only the TWIN-SEGMENT transfer days, and that is most of the arithmetic.** Days before the twin's first snapshot day (20260821) are priced by daily_nav in **both** chains identically, so a LED-04 bias there cancels out of the gap. The four big days — 08-02, 08-05, 08-10, 08-18, which carry nearly the whole 0.2613 pp — are all prefix; only 08-27, 09-03 and 09-08 are inside, and they are 4th-decimal. Applying the whole 7-day table (run 4) left the residual sitting at a **median 0.246 pp**, i.e. almost exactly the prefix effect that cannot appear in the gap. | receipt; device 3661b094 |
| A4 | **On a still-OPEN transfer day the income-derived realised is incomplete by construction**, so the input leg is an as-of artifact rather than a disagreement: **+0.3232 pp at 2026-09-03T20:36Z** (deposit day) against 4th-decimal values once the day closes. 27 of the 208 comparable rows are in that state. (ii) declines to judge them and names `open_transfer_day`. | receipt `rows`, `summary.n_excluded_open_transfer_day` |
| A5 | **Alert (i)'s own leg dominates a naive residual and must not be charged to (ii) as well.** Max \|arith − watchdog\| over all rows is **0.1696 pp**; the worst judgeable naive residual (09-13 12:46Z, −0.1858) is −0.1696 of that leg and only −0.0162 of anything else. An injected input bias cannot hide in this subtraction: it moves the recorded value and the arithmetic twin **together**, so the (i) leg stays ~0 and the bias lands in the input leg. | receipt `alert_i_arith_vs_wd_pp` |
| A6 | **Judgeable rows: 181** (208 comparable, minus 27 open-transfer-day). Max \|residual_ii\| = **0.017307 pp**; rows over 0.05 / 0.10 / 0.25 / 0.50 pp = **0 / 0 / 0 / 0**. | receipt `summary` |
| A7 | **Proposed `RESIDUAL_TOL` = 0.25 pp = half the already-deployed `TOL["cum_pct"]` (0.50).** Stated as a halving of a deployed constant, not tuned: it sits **14×** above the measured noise floor (0.0173) and **2×** below the 0.5 pp input bias the ruling requires (ii) to catch. No recorded judgeable row comes within a factor of 14 of it. | receipt `summary.n_judgeable_residual_ii_over` |
| A8 | **The prefix transfer-day predicate differs between the two chains but has never differed in effect**: the twin's prefix reads `external_flow_usdt` on the day's LAST row only, while `wd_chain_arith_pct` reads ANY row of the day. Over all 1,655 evaluations the two disagree on **0 days**. Latent, not present — recorded so it is not rediscovered as a surprise. | receipt `prefix_flow_mismatch_days`, empty on every row |

---

## Addendum 2026-09-16 (append-only) · OPS-03 A + C · what the sliding weight shaper costs

Device `devices/ops03_markout_cost.py` (committed 0969ac03 before it ran), receipt `receipts/OPS03_markout_cost.json`
+ `.log`. Inputs: the 14:27Z `anchor_runs.log` and the committed `OPS03_sliding_shaper_replay.json`, both sha256'd in
the receipt. Read-only.

| # | Fact | Evidence |
|---|---|---|
| G1 | **The markout cost, as a number.** The anchor has a 3,600 s wall-clock cap and the backfill's deadline derives from it (`max_seconds = cap − elapsed − 90`), and the backfill is metronome-paced at `PACE_S = 2.0` s per venue request, so `fewer_requests = added_delay / 2.0` and `fewer_marks = fewer_requests × (written / requests)` for that run. Across the eight replayed anchors the sliding shaper costs **31.8 marks in total**: **28.5 on 09-13 12Z** (delay 34.5 s, 525 written / 318 requests = 1.651 marks per request) and **3.3 on 09-12 12Z** (5.6 s, 1.158 marks/req). | receipt `rows`, `totals` |
| G2 | **Six of the eight anchors pay nothing, and quoting one average would have hidden that.** Only a run whose own log line says `CAPPED(deadline)` loses marks; a run that drained its queue finishes later without writing less. 08-22 12Z, 08-26 12Z, 08-26 20Z, 09-07 04Z, 09-10 00Z and 09-11 08Z were **not** deadline-bound — the three August ones stopped on `CAPPED(request_budget)` under the pre-09-05 budget of 240 requests. Whole-log counts: 37 `CAPPED(deadline)` vs 3,931 `CAPPED(request_budget)`. | `anchor_runs.log`; receipt `deadline_capped` per row |
| G3 | **The marks are deferred, not lost.** The backfill is resumable and the pending queue is picked up by the cron and by later anchors; 09-13 12Z itself wrote 525 of 1,777 pending. | `ops/backfill_markout.py:108`; the 09-13 line |
| G4 | **No pinned assertion encoded fixed-window behaviour, so the ruling's stop condition was not met.** `tests_rate_backstop_window` contains **0** references to the weight shaper. `tests_request_budget` contains exactly one weight assertion, `_s["weight_in_window"] == 109` after 109 weight-1 spends; that is true of a fixed window and of a sliding one (the 109 calls land in the same millisecond) — it encodes the cap RATIO, not the window shape. Both files are **byte-identical** to e808697 and both still exit 0. | `receipts/OPS03_ast_and_pins.log` |
| G5 | **`weight_in_window` changes meaning for one consumer, and it is named rather than left to be discovered.** `binance_broker.py:741` uses it for `VENUE_RL["peak_gap_vs_local"]`, the venue-vs-us gap. It now compares our TRAILING 60 s against the venue's ALIGNED minute instead of our fixed window's running total against it. Both are approximations of different windows; the gap's attribution was already marked UNDETERMINED in the log line and feeds no decision, so this changes a number nobody acts on. | `binance_broker.py:735-747`; `run_anchor.py` venue_rate line |
| G6 | **The 08-26 "rate storm" attribution in `config/book.json _gross_mult_note` is not supported by the rows** (OPS-03 design F2/F3/F6, now corrected in place with the original sentence kept and marked false): the 1,005 was the FIXED-window limiter's own reading with `waits=0`; the venue's own peak that anchor was 1,005 of 2,400 = 41.9%, far from the 80% backstop; and the "157 null-submit rejects" are not a rate signature — **7,006 of 7,006** `venue_reject` rows in the whole ledger carry `submit_ts None`, which is simply how the writer records any venue reject, and that batch's codes were all **-5022**, not -1003/-1015. | design F2/F3/F6; `orders.jsonl` |

---

## Addendum 2026-09-16 (append-only) · LED-03 · the BNB conversion caliber, measured

Caliber module `live/bnb_conversion.py` (clone) + device `devices/led03_bnb_conversion.py` (committed 60d2e1e6 and
635ce1dc before its runs), receipt `receipts/LED03_bnb_conversion.json` + `.log`. The device touches only
`data.binance.vision` (the public static archive the user exempted 2026-09-05) and two local read-only files; **no
venue API call, no credentials, no ledger write**.

| # | Fact | Evidence |
|---|---|---|
| H1 | **Every price file is verified against Binance's OWN published `.CHECKSUM`, 8/8 MATCH** — not only against a sha we computed, which would prove we hashed what we downloaded and nothing about what was published. Both are recorded per file. 4 spot + 4 perp daily zips, 53,634–62,072 bytes each. | receipt `price_sources` |
| H2 | **Monthly archives would have silently had no price for the largest BNB batch.** `…/monthly/…/BNBUSDT-1m-2026-09.zip` returns **404** while 2026-08 returns 200 — the month is in progress. The first version of the device used monthly files and failed on that 404; it now takes one DAILY file per batch day, derived from the proxy receipt rather than hardcoded. | probe of six archive paths; device 635ce1dc |
| H3 | **Positive control before any converted number is used: 5 batches, 0 mismatches.** The BNB COMMISSION rows selected per batch window sum exactly to the committed proxy's `proxy_fee_by_asset_unambiguous.BNB`. A batch that disagreed would abort the device rather than report a tidy figure built on a different row set. | receipt `positive_control` |
| H4 | **The conversion, at `bnb_spot_1m_close_at_fill`: −0.14011738 BNB → −101.038138 USDT** over 4,007 commission rows, **0 unconverted**. Per batch: 08-05 12Z −0.00320538 → −1.919999 (177 rows) · 08-21 12Z −0.02094517 → −14.139391 (469) · 08-21 20Z −0.02041753 → −13.741814 (525) · 08-26 12Z −0.01893276 → −13.277155 (931) · 09-06 08Z −0.07661654 → −57.959779 (1,905). | receipt `batches`, `totals` |
| H5 | **The perp mark is a sensitivity column and it is small.** futures/um 1m close over the same rows gives −101.108741 USDT, a spread of **+0.070603 USDT on 101.04 = 0.07%**. Reported beside the number, never substituted for it. | receipt `totals.sensitivity_spread_usdt` |
| H6 | **Combined with the USDT side, the eight older batches' fees are 22.76358064 + 101.038138 = 123.80 USDT** (the USDT figure is the committed proxy's; the exact credentialed backfill is the lead's to run and may move it). | `LED03_proxy.json`; this receipt |
| H7 | **The caliber's conventions are properties, not defects, and are stated in the module itself**: the close is the price at the END of the containing minute, i.e. up to 60 s AFTER the fill — a convention, not an estimate of the fill-instant price, which would need trade data rather than klines; spot, not perp; and a minute with no kline stays fee_unknown and NAMED, never interpolated, never taken from the nearest minute, never carried forward. | `live/bnb_conversion.py` docstring; `tests_bnb_conversion` [C2], [C8] |
| H8 | **No ledger row carries a converted fee yet.** This is a caliber plus a table. `cost_buckets` still buckets an unconverted BNB fee as `commission_non_usdt_unconverted`, which stays correct until a conversion record exists on the row; wiring the reader to consume one is a separate change on top of the lead's credentialed backfill. | `live/cost_buckets.py`; gate_coverage entry blind spot (d) |

---

## Addendum 2026-09-16 (append-only) · ALM-06 (ii) edge behaviour, probed rather than assumed

| # | Fact | Evidence |
|---|---|---|
| A9 | **The open-transfer-day gate has three states and all three were exercised**, on a synthetic tree with a real daily_nav prefix day: (a) a transfer day whose `external_flow_usdt` is **not yet visible** in daily_nav is judged normally — correct, because with no flow recorded there is no transfer-day formula divergence to price; (b) once the flow IS visible, the same evaluation on the **same UTC day** returns `undecidable` naming `transfer day 20260916 still open — income-derived realised is incomplete`; (c) the identical data evaluated the **next** day is judged normally again. | probe against the package `guard_twin.py` |
| A10 | **A twin whose first snapshot day is also the first daily_nav day declines with a named reason** (`no daily_nav prefix or no twin day`) rather than returning a number from an empty prefix. Not reachable on the live data (daily_nav starts 08-01, the twin 08-21), but it is the right failure mode and it was checked rather than assumed. | same probe, prefix removed |
| A11 | **Runtime of the whole `ops/daily_summary.py` including the new drift block, over the 44-day ledger copy: 4.19 s wall** (`--since 24h`, user 3.40 s). It is an operator tool run on demand, so this is comfortable; the drift block costs no extra ledger reads because main() already reads every day. | `/usr/bin/time -p` on the 14:27Z copy |
| A12 | **`weight_waits` changes meaning with OPS-03 A, in the direction of its siblings.** The fixed-window shaper waited at most once per call and counted 1; the sliding one is a retry loop and counts one per wait event — which is exactly what `spend_order` and `spend_request` already do (`order_waits` / `request_waits` increment inside their `while True`). The acceptance line's `waits=` therefore becomes comparable across the three shapers instead of mixing two conventions. | `live/rate_budget.py` spend_weight / spend_order / spend_request |
| A13 | **The battery does not recurse, and the 03:16Z incident's mechanism is specifically the standalone run.** `run_acceptance.sh:34` exports `ACCEPTANCE_INNER=1` and `tests_acceptance_entrypoints.py:64` reads it, so inside the battery that suite detects the nesting and does not spawn. Run **standalone** it has no such marker and executes `bash run_acceptance.sh` twice — which is what happened at 03:16Z. The transitive-reach rule is right; the recursion guard is why the battery itself is bounded. | `run_acceptance.sh:29-34`; `tests_acceptance_entrypoints.py:64-69` |
