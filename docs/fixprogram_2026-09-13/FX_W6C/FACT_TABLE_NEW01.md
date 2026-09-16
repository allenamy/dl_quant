> **创建:** 2026-09-16 04:2xZ | **Session:** FX-W6C (fix worker, NEW-01 / F-I5) | **状态:** 事实表, 写于任何执行器代码改动之前(规程 §0-1); 数字取自 02:53Z 只读快照与 devices/probe_b13_flatten.py | **作废条件:** 执行器基底 ≠ ef60f85, 或 `_write_flatten_rows` / `write_flatten_readback` 的字段语义被改

# FACT TABLE — NEW-01 / F-I5: a protective-flatten batch's `submit_ts`/`anchor_ts` are the ROW-WRITE moment, and the batch never shares a key with its own readback

Legend: **VERIFIED** = read at the cited line on ef60f85, or measured by a device listed in §0; **INFERRED** = reasoning from verified facts; **NOT CHECKED** = stated so nobody reads it as checked.

## §0 Frozen objects
Base `ef60f85`; clone `/Users/haosiyu/cc_tmp/fx_w6c`; live state copy `/Users/haosiyu/cc_tmp/fx_w6c_state_20260916` (02:53Z). Device `devices/probe_b13_flatten.py`, receipt `receipts/b13_flatten_pairs_20260916.json`.

## §1 What is written, and from which clock (VERIFIED, ef60f85)

| field | written as | what it actually is |
|---|---|---|
| `anchor_ts` on every row of a batch | `ts = time.time()` taken once inside `_write_flatten_rows` (`watchdog.py:2848-2862`) | the moment the ROW WRITER ran — after the whole submit loop and after every fill |
| `submit_ts` | `ts if _sent else None` (same `ts`) | ditto; it is NOT when the order was submitted |
| `first_fill_ts` / `last_fill_ts` | `ex.get("fill_ts")` | the venue's own time — **correct, and already in hand** |
| `mid_at_submit` | `ex.get("mid_at_submit")` | captured in ONE batched `bookTicker` call **before** the submit loop (`binance_broker.py:1786-1795`) — **correct** |
| the post-flatten readback's `anchor_ts` | the caller's own separate `time.time()` (`watchdog.py:3075-3077`, and `:2661` on EXE-01's local path) | a second clock read, 0.1–0.3 s later |

So the batch's two records are stamped from **two different clock reads**, and neither of them is the submit moment. The true submit moment exists at `binance_broker.py:1802` (`self.submit(o, reason)` inside the per-order loop) and is simply not recorded: `o["_exec"]` carries `filled_notional`, `avg_fill_px`, `fill_ts`, `mid_at_submit`, `order_id`, `submitted`, `error` — **no submit time**.

## §2 Measured on the live record (VERIFIED, all 10 batches in the window)

`probe_b13_flatten.py`: **0 of 10** batches share an anchor key with their own readback; the readback lands **+0.116 s to +0.290 s** later. Every batch has exactly **1** distinct `anchor_ts` and **1** distinct `submit_ts` across all its rows.

On the batch the lead named, `FLATTEN-20260912T124737Z` (255 rows): `anchor_ts = submit_ts = 1789217401.146036` for all 255; its readback is `1789217401.2960482` (**Δ +0.150012 s**). Per row, the write moment sits **0.135 s to 141.950 s after that row's own fill** (median 66.064 s); `first_fill_ts == last_fill_ts` on all 255. Across the ten batches the per-row spread runs from 0.040 s to **144.584 s** (2026-08-26).

## §3 Consumers of those two fields, and what each one suffers

| consumer | reads | effect of the defect |
|---|---|---|
| **§4-5e** `position_break._intended_by_anchor:287` | flatten rows' `anchor_ts` as an anchor key (`flatten_ats`), and `rb[ats]` for the readback | the flatten anchor is enumerated (`kind: protective_flatten`) and **never judged**: `state=NO_READBACK`, `judged=False` for ever, because the readback is under a different key. 10 of 10 in the record. This is F-I5. |
| **`ops/score_post_fix.py` E4 q4** `:238-250` | `last_fill_ts < submit_ts` | **204 of 204** measured `protective_flatten` rows fail it (by ~59 s), against 0 of 392 maker and 0 of 111 top-up rows. The file already names the cause — "`_write_flatten_rows` stamps `submit_ts = ts`, the moment the ROW is written, while `last_fill_ts` is the venue's own updateTime" — and says it is *"registered, not repaired here: it is a producer defect on the crisis path and belongs in its own change"*. This is that change. |
| `reconcile._exec` (`reconcile.py:636`) | `last_fill_ts or first_fill_ts or anchor_ts` | unaffected in practice: a filled flatten row has a real `fill_ts`, so `anchor_ts` is only the fallback for rows with no fill |
| `watchdog_inputs.derive_ops_stats:80`, §4-5c `watchdog.py:2080` | `submit_ts is not None` | **null-ness only**, the VALUE is never read ⇒ unaffected. (Separately: flatten rows do enter §4-7's fail-rate denominator, which is a different question and is NOT part of this item.) |
| `position_break:300,707` | `anchor_ts` of rows with a `submit_ts` | value-independent |
| `pilot_metrics:100,206` | `protective_flatten` rows for `protective_flatten_cost` | uses `mid_at_submit` / `fee_paid`, not the timestamps ⇒ unaffected |
| `ops/capture_halt_evidence.py:119` | flatten rows with `submit_ts is not None` | null-ness only |
| `live/venue_fills.py:1165,1288` | joins fills by client id / leg | not by time ⇒ unaffected (NEW-02's `attempt_idx` is FX-EXEC's item) |
| `ops/backfill_fills.py:114` | `client_ids` + leg | unaffected |

⇒ Two real consumers: **§4-5e can never judge a flatten anchor**, and **the ledger contains 204+ rows whose execution precedes their own submission**.

## §4 The constraint the lead set, and what follows from it
*"Historical rows stay as written (append-only ledger); if readers need true times for history, derive them from fills and venue records and name that source."*
⇒ No rewrite of any existing row. The fix is producer-side and applies to batches written from here on. For history, the true fill time is already in the row (`first_fill_ts`/`last_fill_ts`, the venue's `updateTime`) and the true submit time is recoverable only from the venue (`allOrders`/`userTrades` by `client_id`/`order_id`, both of which the rows carry since round 3). Any reader that needs it must say which source it used.
⇒ It also means a reader cannot distinguish an old row from a new one by value alone, so the new rows must carry a **column** that says which clock stamped them; absence of that column then means "row-write time", which is true of every row written before this change.

## §5 Plan
1. Capture the real per-order submit moment in `flatten_all` (`binance_broker` and the MockBroker) into `o["_exec"]["submit_ts"]`, beside the `fill_ts` it already records.
2. `_write_flatten_rows` writes that value when it exists and the row-write time when it does not, with a new column naming which — `submit_ts_source` ∈ {`venue_submit_call`, `row_write_time`}. `submit_ts is None` keeps meaning exactly one thing (never left the process), which classes [b] and [g] depend on.
3. One identity for a batch: both the rows and the readback take their `anchor_ts` from the batch's own name (`evaluated_utc`, which already names it `FLATTEN-<trip_key>`) rather than from two clock reads — so the two keys are equal **by construction**, not by a caller remembering to pass the same value. §4-5e can then judge a flatten anchor.
4. Red cells on the REAL `FLATTEN-20260912T124737Z` rows: today §4-5e reports `NO_READBACK` for that batch and `last_fill_ts < submit_ts` on 255/255 rows.
