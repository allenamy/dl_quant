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

## LED-07 · anchors.jsonl as a series (commit 7ca52ac)

**Problem.** The live anchors table has one row per anchor RUN, and no row carries a schema version. It mixes:
- the internal and external book eras;
- halted runs that still carry target_gross;
- in the external era, a capture-time `anchor_ts`, with the actual slot stored in `external_book.nominal_ts`.

A naive per-anchor statistic therefore counts targets that were never traded and mixes two books.

**Facts** (FACT_TABLE_EXEC2 §LED-07, ledger copy; 257 rows, 08-01..09-13 12Z)
- 130 rows are external era (from 08-22 08Z); 127 are internal.
- 12 external rows are halted (19 halted rows overall, all with realized_gross 0).
- 0 duplicate nominal slots.
- anchor_ts − nominal = 1,381..1,547 s.
- Missing slots: 08-25 16Z, 08-29 20Z, 09-02 00Z, 09-09 12Z.
- Rebuild slots (previous slot realized_gross < 1 USDT): 08-22 12Z, 08-26 20Z, 09-07 04Z, 09-10 00Z, 09-13 12Z.

**Red evidence.** `receipts/LED07_red_old_ef60f85.log`. On ef60f85 there is no accessor, so a reader gets the raw table: 3/10 pass, 7 FAIL (a 257-row series with halted and internal rows inside). No crash.

**Fix.** `pilot_log.anchor_series(rows)`, pure, rows not mutated. The series contains external-era, non-halted, on-grid rows, one per nominal slot, sorted. Alongside it, the accessor returns:
- duplicates resolved by keeping the later row by position, with the superseded slot named;
- exclusions counted by reason (internal_era / off_grid_nominal / halted / duplicate_nominal_superseded);
- missing slots;
- rebuild slots;
- prev_unknown slots, where the previous slot has no row or no readable realized_gross. These are never read as flat.

`SCHEMA["anchors"]` now carries a comment pointing readers at the accessor. No writer change and no per-row schema version. ops/anchor_report.py is migrated onto it (LED-08).

**Tests.** `live/tests_anchor_series.py`: 17/17.
- Fixture: a key projection of all 257 rows. Each row carries the sha256 of its verbatim source line, and the MANIFEST pins the projection sha (builder `devices/build_fixture_led07.py`).
- Every real figure is also re-derived by an independent loop.
- Neighbour cells: duplicate slot, off-grid, halted-but-holding, previous realized None/NaN ⇒ prev_unknown, nominal_ts as text, external_book None/absent, no mutation, empty input.
- Capture-time lag stays within 1,380..1,548 s on the traded series.

**Battery.** Not yet run.

**Not proven**
- No reader is forced to use the accessor. Research-side readers of anchors.jsonl are not migrated; aud-data owns that census.
- `opening_halted` is trusted as the halted flag.
- A partial de-risk followed by a rebuild is not flagged as a rebuild.
- The memory note anchors_jsonl_is_not_a_clean_series.md (external-era capture time) needs a K4 update. I did not edit memory.

## LED-08 · the per-anchor Telegram report, ops/anchor_report.py (commit 469c3f3)

**Problem**
- The old builder folded missing values to zero: `filled_notional or 0`, `intended_notional or 0`, `fee_paid or 0`.
- Its fee bps was divided by all filled notional.
- `rg:.0f` raised on a None realized_gross.
- The net/gross warning sat at 5%, while the deep-check template says ±1%.
- The taker-share warning at >10% fired on 51 of 101 reports.
- It printed "funding.jsonl 缺" on a flat settlement anchor (09-13 08Z).

**Facts** (FACT_TABLE_EXEC2 §LED-08)
- The fold defect is not latent on the ledger:
  - A1785931245 (08-05 12Z): 103/103 fills carry a raw BNB fee, so the old builder prints fee 0.00bps.
  - A1785657675 (08-02): 22/95 fills are fee-unknown; the old builder prints 1.69 bps vs 2.24 measured.
  - A1789215839 (09-12 12Z): 4 unknown-fill rows; the old builder prints 2.74 bps vs 2.47.
- |net/gross| exceeded 1% on 22 of the last 42 traded anchors.
- Taker share over the recent traded non-rebuild anchors: median 22.6%, MAD 6.7 pp.
- So neither old constant describes the current book. The policy levels themselves belong to K5 / X-COST.
- launchd com.hsy.anchor_report runs the script with no arguments at N+55. The CLI is unchanged.

**Red evidence** (`receipts/LED08_red_old_ef60f85.log`): 5/12 pass, 7 FAIL, no crash. On ef60f85 the same test runs the tree's own script with `--dry` in a temp repo under a temp HOME. It prints `fee 2.74bps` with no unknown-fill marker, `fee 0.00bps` on the raw-BNB rows, `⚠️ funding.jsonl 缺` with no halted label, and has no pure builder.

**Fix: structure.** The report is now a pure `build_report` over gathered inputs; `gather` does all reads, and only `main` sends.

**Fix: fees and fills.** These go through cost_buckets:
- bps is computed over measured fills only;
- None is printed as "n/a(未测, 非 0)" with a [已测 x/y, 覆盖 z%] note;
- unknown fills are named;
- taker share is printed as a lower bound (≥) when a fill amount is unknown.

**Fix: warnings.** Taker share and |net/gross| are judged against the book's own trailing distribution.
- The baseline is the previous ≤42 traded non-rebuild anchors from `pilot_log.anchor_series`, and needs at least 12.
- The warning line is median + 3×1.4826×MAD, and the baseline is printed.
- The 5% |net/gross| line stays as an absolute ceiling.
- Rebuild and halted anchors are labelled and not judged on taker share. A halted anchor's intent is labelled "意图(未发送)", not turnover.

**Fix: missing funding file.**
- Previous slot flat: the report says no position at settlement.
- Previous slot holding or unknown: it warns.

**Census.** The tests_rehearsal_anchor text for ops/anchor_report.py now covers the history join.

**Tests** (`live/tests_anchor_report_builder.py`): 17/17.
- [S1-S3] run this tree's script with `--dry`: HOME is a temp dir with fake wide_shadow/guard_twin, there is no .env, and the ledger lines are verbatim (fixture builder `devices/build_fixture_led08.py`).
  - 09-12 12Z prints fee 2.47bps and "成交未知 4 行".
  - 09-13 08Z prints no funding warning, states no position, and labels the anchor halted.
  - The 08-05 raw-BNB rows print fee n/a.
- [P1-P4] test the pure builder with urlopen replaced by a raiser:
  - the band needs at least 12 values;
  - baseline slots come strictly before A, exclude rebuild and halted slots, and are capped at 42;
  - taker share warns on a normal anchor but not on a rebuild or a halted one;
  - the 5% hard net/gross line fires with no baseline;
  - a None net/gross is printed as n/a;
  - the three missing-funding cases.
- A dry run on the real 09-13 12Z/08Z/04Z anchors printed the expected lines.
- Neighbours green: tests_imports, tests_static_names, tests_rehearsal_anchor 59.

**Battery:** not yet run.

**Not proven**
- The Telegram transport and the launchd firing.
- The band is self-calibrating, so a slow drift is absorbed; only the 5% net/gross line is absolute.
- A MAD of 0 makes the line equal to the median (declared, not smoothed).
- The daemon, shadow_log, combo and twin checks are unchanged logic, exercised only through fake files.
- `gather` now reads 10 days of anchors.jsonl and orders.jsonl per report; the runtime cost at N+55 was not timed on the live tree.

## STA-02 · per-name-stop paging tier (commit 8354c5a)

**Problem.** anchor_loop.py:2600-2602 sends every per_name_stop event at HIGH. alarm_policy has no rule for any of them, so each is classified UNRECOGNISED ⇒ DECIDE ⇒ PUSH. On 09-13 between 12:45:49 and 12:45:55Z, seven routine cooldown expiries produced seven phone pages (DASH also paged at 09-12 20:39Z).

**Facts** (FACT_TABLE_EXEC2 §STA-02)
- The push decision is `alarm_policy.classify` on the message TEXT. Severity does not decide it.
- The audit rows record policy_tier A_DECIDE and policy_rule UNRECOGNISED.
- per_name_stop.py event kinds: L102 exit into cooldown, L109 expiry, L129 trigger, L164 profile error.
- Expiry is evaluated in phase C, so an expired name still sits out the running anchor. That is behaviour and was not changed.

**Red evidence.** receipts/STA02_red_old_ef60f85.log: 6/8, 2 FAIL. The 8 real expiry bodies and the generator's own string both give PUSH UNRECOGNISED. No crash.

**Fix**
- One tier-B rule in alarm_policy.py: "per-name stop cooldown expired", pattern r"per_name_stop: \S+ 冷却期满" ⇒ DAILY.
- The trigger, exit-into-cooldown and profile-error messages keep PUSH.
- per_name_stop.py and anchor_loop.py are untouched. fx-exec owns the per_name_stop text at L6-9 and L130.
- tests_alarm_digest [E] checks the REAL audit: "nothing pushed in the last 24h that the rules do not class DECIDE". It read misclassed=8 after the rule because the rows were pushed under the older table.
  - It now exempts only rows recorded as A_DECIDE/UNRECOGNISED whose CURRENT rule is one of the named later demotions.
  - That exemption is itself a tested predicate. The same message recorded under the new rule is not exempt.

**Tests.** live/tests_pns_expiry_tier.py: 8/8.
- The 8 real bodies (verbatim, with send ts) ⇒ DAILY.
- The real LSK trigger and the real IOST exit ⇒ PUSH; a profile error ⇒ PUSH.
- "冷却期满" without the per_name_stop head is not caught.
- The string `per_name_stop.evaluate` emits, bare and with the notifier's "⚠️ HIGH\n" head ⇒ DAILY; its trigger string ⇒ PUSH.
- Neighbours green: tests_alarm_digest 34, tests_alert_tiers_live, tests_daily_summary.

**Not proven**
- Classification is by text. A generator reword that drops the phrase goes back to PUSH, which is the safe direction. A reword that moves a trigger under this pattern would be silenced; only today's trigger string is pinned.
- anchor_loop still hands expiries to the notifier at HIGH. The recorded row's severity is demoted by the notifier's tier-B path.

## ALM-01 · funding_span alarm (commit c2e9bdc)

**Problem**
- The fingerprint read x.get('ours') / x.get('venue'), but the record's keys are ours_h / venue_h. Stored findings were "SYM:None->None" ×15, so an interval change on an already-stale name could never open an episode.
- The HIGH text says these names' funding leg is EMA-smoothed over the wrong settlements. In external mode that is false for the traded book: the table feeds only the executor's internal DL panel (signal/live_panel.py:55).
- DEFAULT_INTERVAL_H was defined and never used.

**Facts** (FACT_TABLE_EXEC2 §ALM-01)
- The table has 140 names (99 × 8h, 41 × 4h), built 07-25.
- 12Z log: stale=15, absent_from_venue=13, venue=782.
- The caller is run_anchor.py:793-797, every anchor.

**Red evidence.** receipts/ALM01_red_old_ef60f85.log: 5/14, 9 FAIL, no crash. The first red run crashed on a test-side `CFS.book_source()` call; that attempt is invalid. It was fixed to read config directly and rerun.
- 'None->None' findings.
- The same finding set after ANKR changes 4h→1h.
- HIGH plus the EMA sentence; PUSH UNRECOGNISED.
- No `source` parameter, no book_source, no absent-nondefault count, no record on RECORDED_NOT_PUSHED.

**Fix**
- Findings are "SYM:<ours_h>-><venue_h>", plus "SYM:<ours_h>->absent" for table names that are absent from the venue list and not on 8h.
- Absent names are counted in n_absent_nondefault and named as possibly stale, never asserted. Default interval versus delisted is not knowable offline.
- Tier and sentence follow config book_source:
  - external ⇒ INFO, with a sentence naming the internal DL panel, plus the tier-B alarm_policy rule "funding-span table stale, external book";
  - internal or unreadable config ⇒ HIGH with the consequence sentence (unreadable adds a note).
- A RECORDED_NOT_PUSHED disposition now records the episode. Without that, the unchanged finding re-alarmed every anchor.
- First run after deployment: the stored 'None->None' episode re-fingerprints, which raises one tier-B record and no page.

**Tests.** live/tests_funding_span_alarm.py: 14/14.
- Venue call and episode store are replaced in-process.
- Uses the real table and the real 15 recorded stale names.
- The venue map is synthetic: 13 absent names, 782 listed.
- Neighbours green: tests_alarm_digest, tests_pns_expiry_tier, tests_imports, tests_static_names, tests_frozen_inputs, tests_universe_tripwire.

**Not proven**
- Which absent names are delisted (needs exchangeInfo).
- fundingInfo's real response shape.
- Rebuilding the table.
