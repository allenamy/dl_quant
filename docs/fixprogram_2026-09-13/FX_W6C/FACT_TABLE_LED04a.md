> **创建:** 2026-09-16 04:1xZ | **Session:** FX-W6C (fix worker, LED-04 裁定 (a) 的 watchdog.py 一侧) | **状态:** 事实表; **顺序自述**: 本项的事实收集(记录格式 / 构建器 / FX-EXEC2 效应收据 / cond4 代码路径 / 250 条记录对真实账本行的 sha 逐条核验)全部先于任何代码改动, 但本文档本身写于代码之后 —— 与 §0-1「事实表先于代码」的文字有出入, 据此声明 | **作废条件:** 执行器基底 ≠ ef60f85, 或 FX-EXEC2 的记录格式(kind / row_sha256 / amended.realised_pnl_usdt / (day, nav_ts) 键)改变

# FACT TABLE — LED-04 ruling (a): §4-4 prices a pre-fix TRANSFER day from the amendment record, and names the days it cannot

Legend: **VERIFIED** = read at the cited line on ef60f85, or measured by a device listed in §0; **INFERRED** = reasoning from verified facts; **NOT CHECKED** = stated so nobody reads it as checked.

## §0 Frozen objects
Base `ef60f85`; clone `/Users/haosiyu/cc_tmp/fx_w6c`; live state copy `/Users/haosiyu/cc_tmp/fx_w6c_state_20260916` (02:53Z, read-only source). FX-EXEC2's objects, read from the research repo: builder `FX_EXEC2/devices/led04_daily_nav_amendment.py`, effect device `led04_cond4_transfer_day_effect.py`, records `FX_EXEC2/receipts/LED04_daily_nav_amendments_20260801_20260912.jsonl` (399,891 bytes, **250 records**, 20260801…20260912), effect receipt `LED04_cond4_transfer_day_effect.json`, reader `ops/daily_summary.py` in their clone at `e05c45a`. My device: `devices/led04_cond4_watchdog_reproduction.py`; receipts `led04_cond4_watchdog_reproduction_20260916.json` / `_to20260912.json` / `_to20260913.json`.

## §1 Where the pre-fix realised figure enters a TRIGGER (VERIFIED, ef60f85)

`watchdog.py` §4-4 builds a time-weighted cumulative equity return from starting equity. Per day:
- ordinary day: `r = nav / nav_prev − 1` — the realised figure never enters;
- **transfer day** (`external_flow_usdt` non-zero): `r = (realised_pnl + unrealised − unrealised_prev) / nav_prev`. The flow AMOUNT deliberately never enters (it is unreliable on deposit days), so **the realised figure carries the whole day**;
- truncated / nav-less day: withheld, chain spans it by nav ratio unless a transfer sits in the hole (then BLIND, named).

The row it reads is the day's LAST `daily_nav` row (the same collapse `pilot_metrics.stoploss_inputs` applies internally). `realised_pnl` on any row written before **b681ca5 (2026-09-12 06:05Z)** comes from a carrier that de-duplicated income on `tranId` alone — dropping one of each COMMISSION/REALIZED_PNL twin — and summed BNB commissions into the USDT total (E-0909-H).

## §2 The size of it (VERIFIED, two instruments)

| instrument | window | recorded | amended | understatement |
|---|---|---|---|---|
| FX-EXEC2 `led04_cond4_transfer_day_effect.py` | their 14:27Z copy, 09-13 | **−1.3136 %** (= the live `last_eval` bit for bit, `reproduces_live: true`) | **−1.5749 %** | **0.2613 pp** |
| this item's device, the FIXED watchdog itself | copy truncated at 20260912 | −1.1349 % | −1.3967 % | **0.2618 pp** |
| same | copy truncated at 20260913 | −1.1630 % | −1.4247 % | **0.2617 pp** |
| same | full copy to 20260916 | **+1.1704 %** | +0.9024 % | **0.2680 pp** |

The absolute levels differ because the windows differ (their copy held only part of 2026-09-13; mine holds three more full days, over which the book recovered). **The quantity the ruling is about — the understatement — agrees between the two instruments to 0.0005 pp.**
**And the change is inert without records:** on the full copy with no record file my fixed watchdog reports `cum_return_from_start_pct = 1.1704`, which equals the live `last_eval.json`'s value **exactly** (`reproduces_live_without_records: true`).

Seven transfer days carry it, all pre-fix: 20260802, 20260805, 20260810, 20260818, 20260827, 20260903, 20260908. The two that dominate are 08-02 (recorded 6.13972215 vs amended 3.13512435 USDT) and 08-05 (−18.0868018 vs −20.7432812).

## §3 The record format, as read from the builder (VERIFIED)

One JSON object per line, `kind = "daily_nav_realised_split_amendment"`, with `day`, `line` (1-based index into that day's `daily_nav.jsonl`), `row_sha256`, `nav_ts`, `recorded{…}`, `amended{realised_by_type_asset, realised_usdt_by_type, realised_pnl_usdt, non_usdt_unconverted}`, `delta_recorded_minus_amended_usdt`, `source{income_ledger, income_sha256, income_rows, key, window, caliber_note}`.
- `row_sha256` is the sha256 of the **raw line including its newline** (`raw.splitlines(keepends=True)` in the builder), so verifying it needs the FILE, not the parsed row.
- FX-EXEC2's reader keys `(day, nav_ts)` and **drops** a key that appears twice with different content, never resolving by position (`ops/daily_summary.load_realised_amendments`, their `e05c45a`).
- Relative path: `ledger_amendments/daily_nav_realised_split.jsonl` under the mode root, beside `pilot_log`.

**VERIFIED against the real data (2026-09-16):** all **250/250** `row_sha256` values reproduce from the live `daily_nav.jsonl` lines. So the sha check is well-defined and currently passes on every record.

## §4 Where the records are today
**They are not on the live tree.** `find` over the 02:53Z copy finds no `ledger_amendments` directory and no `daily_nav_realised_split*` file: FIXPROGRAM §10 deferred every live write-back (LED-03 backfill, LED-04 records, LED-05 order reconstruction) to the reviewer's hand-off. ⇒ On deployment, and until FX-EXEC2's apply step runs, **every pre-fix transfer day will name itself `unamended_prefix_day` and be priced from the recorded value** — which is precisely what ruling (a) prescribes, not a degradation.

## §5 The rule implemented
| input | priced from | named |
|---|---|---|
| pre-fix row, valid record (sha verified, finite USDT total) | `amended.realised_pnl_usdt` | `days_amended` |
| record absent for `(day, nav_ts)` | the row's `realised_pnl` | `unamended_prefix_day` + why |
| record's `row_sha256` ≠ the ledger line | the row's `realised_pnl` | `unamended_prefix_day` + why |
| record file line unparsable, or the key is a conflict | the row's `realised_pnl` | `unamended_prefix_day` |
| record's amended USDT total not finite | the row's `realised_pnl` | `unamended_prefix_day` |
| **post-fix row** (carries `realised_by_type_asset`) | the row's `realised_pnl`, **unchanged** | `post_fix_row`, with `row_usdt_slice` reported and NOT used |
| ordinary (non-transfer) day | nav ratio; no record is consulted | — |

Nothing here can set `blind` or break the chain: a bookkeeping correction that could stop the book would be a worse defect than the one it fixes.

## §6 One reader, and the merge gate
The records are FX-EXEC2's; their branch reads them in `ops/daily_summary.py`, which is a REPORT. §4-4 is a TRIGGER. Two readers of one record format, one of which stops the book, is the two-implementations family in the worst possible place — so the reading lives in `live/ledger_amendments.py` and both callers import it. **MERGE ACTION:** when FX-EXEC2's branch is stacked, `ops/daily_summary.load_realised_amendments` must become an import of that module. `tests_cond4_amended_transfer_day.py` cell **D3** scans `live/ ops/ scheduler/` and goes RED the moment two definitions coexist — so the dedupe cannot be forgotten, and the merge battery will say so.

## §7 Not proven
- That the amendment records are themselves right: FX-EXEC2 owns the builder and its positive control (the 8 post-fix rows' own split equals the recomputation 8/8, Σ|recorded − amended| USDT: COMMISSION 310.333677, REALIZED_PNL 0, FUNDING_FEE 0). I verified their sha integrity against the live rows and nothing about their arithmetic.
- **A post-fix transfer day is still priced from the carrier sum**, which can differ from the USDT-only slice when a commission was paid in BNB. No such day exists yet (all seven transfer days to date are pre-fix), but one will. The slice is computed and reported (`row_usdt_slice`) and deliberately not used: that would be a second change to what a stop-loss reads, outside ruling (a). **Needs a ruling.**
- The reader resolves the record path as `dirname(pilot_log_root)/ledger_amendments/…`. A caller that passes a pilot_log root not under a mode root gets no records and therefore names every pre-fix transfer day — the fail-loud direction, but NOT CHECKED against every caller (`ops/rejudge_ledger_rows.py`, `ops/score_post_fix.py`, `ops/resume_from_trip.sh` all pass their own tree copies).
