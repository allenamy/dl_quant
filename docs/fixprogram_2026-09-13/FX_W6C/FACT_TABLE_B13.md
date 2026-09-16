> **创建:** 2026-09-16 03:0xZ | **Session:** FX-W6C (fix worker, W6C-B13 P1 在役) | **状态:** 事实表, 写于任何执行器代码改动之前(规程 §0-1); 数字取自 02:53Z 只读快照与本表所列探针 | **作废条件:** 执行器基底 ≠ ef60f85, 或快照 sha 改变, 或「最新已排程锚 = 最新 `anchors` 行」这一参照被改

# FACT TABLE — W6C-B13: a missing or stale newest position readback is judged as CLEAN and is not flagged blind

Legend: **VERIFIED** = read at the cited line on ef60f85, or measured by a device listed in §0; **INFERRED** = reasoning from verified facts, not measured; **NOT CHECKED** = stated so nobody reads it as checked.

## §0 Frozen objects

| Object | Value |
|---|---|
| Executor base | `ef60f85ad93e49f2e0f190bc6e8a15d04073f193` = `~/dl_quant_live` HEAD (read-only `git rev-parse`, 2026-09-16 02:49Z) |
| Clone | `/Users/haosiyu/cc_tmp/fx_w6c`, branch `fix/exe01-proportional-response`, head `3f85c0e82bb5d81d1d84025fd953c68aff8e168d`, `git status --porcelain` empty |
| Live state copy | `rsync -a --exclude acceptance/` of `~/dl_quant_live/state/` → `/Users/haosiyu/cc_tmp/fx_w6c_state_20260916`, 02:53:23–02:53:28Z, 471 MB. No `.env` under it (`find … -name .env` empty). Source untouched. |
| watchdog record in that copy | `live/watchdog/events.jsonl` sha256 `9db1bb6c…` (**identical to the value FACT_TABLE_W6C.md §0 recorded on 09-13** ⇒ no trip since), `state.json` `aee27811…` = `{"reduce_only": false, "tripped_at": null, "_mode": "LIVE"}`, `last_eval.json` `b07e39d2…` |
| Newest live evaluation in that copy | `evaluated_utc 2026-09-16T00:45:38Z`, `tripped false`, `conditions_blind []`, 5b `CLEAN` / 5e `CLEAN` / cond7 drift `CLEAN`, all three judging anchor `1789518241.793033` |
| Devices (this directory, `devices/`) | `probe_b13_census.py` (per-anchor cross-tab of `anchors` / `orders` / `position_readback`), `probe_b13_flatten.py` (flatten batch vs its readback), `probe_b13_live_eval.py` (`reconcile` + `position_break` on the copy). Receipts in `receipts/`. |
| Pre-existing device re-used | `devices/probe_unreadable_book.py` (cells U1/U2/U3, written 09-13); its ef60f85 log is `receipts/probe_unreadable_book.log` |

## §1 The defect, in three places (VERIFIED, ef60f85)

All three position guards answer "is the book where we think it is" from **whichever anchor last carried a readback**, and none compares that against the newest anchor that actually happened.

| Guard | Where the judged anchor comes from | Why a missing newest readback is invisible |
|---|---|---|
| §4-5b liquidation/position anomaly | `watchdog.py:1907` `last_reconciled_ats = _rec["last_reconciled_ats"]`; state at `:1982`; `blind` at `:1996` = `last_reconciled_ats is None` | `reconcile()` iterates **only anchors that appear in `position_readback` rows** (`reconcile.py:701-708`), so an anchor without one is not in its domain. `last_reconciled_ats` therefore silently means "newest anchor we could compare", never "newest anchor". `blind` is True only when there is *no* reconciliation in the whole window. |
| §4-5e position break | `position_break.py:890` `latest = judged[-1]`; `blind` at `:911` = `latest is None and _traded_somewhere` | An anchor without a readback is recorded `judged=False, state="NO_READBACK"` (`:702-707`) and skipped; `latest` falls back to the previous judged anchor. `blind` cannot be True while any older anchor was judged. |
| §4-7 un-recovered drift | `watchdog_inputs.py:114-116`: `_no_comparison = _rec["last_reconciled_ats"] is None`, then `bool(_rec["latest"])` | Same `_rec`. Same blind spot, by sharing. B17 already fixed the *third* state ("no reconciliation ever"); the *stale* state was not covered. |

Probe cell **U1** (newest anchor wrote no readback) on ef60f85 — VERIFIED, `receipts/probe_unreadable_book.log`:
`tripped false`, `blind []`, `5b_state CLEAN` with `5b_last_ats = 1789086400.0` (the **previous** anchor; the newest is `1789172800.0`), `5e_state CLEAN`, `5e_blind false`, `cond7_drift CLEAN`, `flatten_all []`.
So: judged on stale state, reported as checked-and-clean, and nothing in the output says which anchor was judged relative to which anchor exists. Cell U2 (no readback anywhere) *is* blind today; U3 (NaN notionals) is CLEAN because the quantity caliber is what is compared.

## §2 Every path that leaves the newest readback missing, partial or stale

`finalize_anchor` (`anchor_loop.py:2564-2653`) is the ONE production per-anchor writer, and it runs in phase C — **before** the watchdog (`run_anchor.py:363` finalize, then `:409` `WD.run`). So at evaluation time the newest anchor should already carry its readback, and any of these paths breaks that.

| # | Path | Site | What the record shows | Detectable from the log alone? |
|---|---|---|---|---|
| P1 | End-of-anchor account read raises | `anchor_loop.py:2592-2598`; guard `if snap is not None:` at `:2622` | alarm HIGH "end-of-anchor account read failed (…) — position_readback and daily_nav have no input this anchor"; **zero** readback rows; the `anchors` row is still written from the cached book (`:2662-2676`, `realized_src = "cached book (no venue read; DRY_RUN or read failed)"`) | **Yes** — `anchors` row present, readback absent. This is the U1 shape. |
| P2 | A readback row is rejected by the logger schema | `:2652-2653` `self.alarm(...); break` | **partial** readback: the names sorted before the rejected one are written, every later name is silently absent. One rejected row costs the whole tail. | Partly — row count is lower, but nothing states the intended count. 5e counts the gap (`not_read`, coverage ⇒ `degraded`); **5b does not**: its domain is `cur.items()`, i.e. only the names present. |
| P3 | Successful read, empty readback universe | `readback_universe` `:631-639`; called at `:2632` | **zero** rows, **no alarm** — venue flat ∧ nothing targeted ∧ nothing held at the previous readback. Indistinguishable in the log from P1. | No. "No rows" has ≥2 causes that print identically today. |
| P4 | DRY_RUN: there is no account | `binance_broker.py:1930-1944` returns `None` in DRY_RUN (not an exception); docstring `anchor_loop.py:2578-2582` | zero readback rows, zero `daily_nav`, no alarm — by design | Only as "this tree has never had a readback". Must never halt. |
| P5 | No logger attached | `:2586-2588` returns `{"note": "no logger attached; nothing written"}` | nothing written at all | No (not a production path; `run_anchor` always attaches one) |
| P6 | The run dies before phase C | — | the anchor is **absent from the record entirely**. VERIFIED precedent: 2026-09-09 12Z — `probe_b13_census.py` shows anchors at 00:24, 04:24, 08:24, **(no 12Z key at all)**, 16:24, 16:47 (flatten), 20:24 | **No, and cannot be.** See §7. |
| P7 | Flatten rows and their readback carry different keys | `watchdog.py:2693` `_write_flatten_rows` vs `:2585` `write_flatten_readback` | the flatten batch is an anchor key with orders and no readback; its readback is a second key 0.13–0.32 s later | Yes — and it is the reason the reference anchor must be the `anchors` row (§5). This is NEW-01 / F-I5, queue item 4. |
| P8 | An anchor that attempts no rebalance | `anchor_loop.py:2655-2660`: the `anchors` row exists "exactly when a rebalance was attempted" | **no `anchors` row**, readback still written (the readback branch at `:2622` is independent of `ctx`). VERIFIED instance: 2026-08-29 20Z, external book missing ⇒ `action: HOLD`, run log `phase_C: {"anchors_row": false, "position_readback_rows": 256, "daily_nav_row": true}` | Yes while the readback exists. **P8 ∧ P1 together is invisible** — see §7. |

## §3 What the live record actually contains (VERIFIED, `receipts/b13_census_20260916.json`)

`probe_b13_census.py` over the 02:53Z copy: 47 days, **2026-08-01 … 2026-09-16**, 293 distinct anchor keys.

| Cross-tab | Count | What they are |
|---|---|---|
| `anchors` row **and** readback | 272 | healthy scheduled anchors |
| `anchors` row, **no** readback | **0** | ← the B13 shape. **It has never occurred on the live record.** |
| readback, **no** `anchors` row | 11 | 10 post-flatten readbacks + 2026-08-29 20Z (the HOLD anchor, P8) |
| orders only | 10 | the 10 FLATTEN batches (P7) |

Corroboration: `grep -r` over the whole state copy finds **0** occurrences of `end-of-anchor account read failed` and **0** of `position readback failed`. Neither read-failure path has ever fired.
⇒ The fix is **prophylactic**. What has to be argued is therefore the false-positive cost of the response (§6), not the base rate of the fault.

### §3.1 The flatten pairs, measured (VERIFIED, `receipts/b13_flatten_pairs_20260916.json`)

All 10 FLATTEN batches in the window, `probe_b13_flatten.py`. **0 of 10 share an anchor key with their own readback.**

| Day | batch | rows | distinct `anchor_ts` / `submit_ts` across the batch | readback − orders | write moment − each row's OWN fill (min / median / max) |
|---|---|---|---|---|---|
| 2026-08-01 | FLATTEN-20260801T201827Z | 105 | 1 / 1 | +0.131278 s | 0.083 / 21.054 / 38.782 s |
| 2026-08-02 | FLATTEN-20260802T041821Z | 83 | 1 / 1 | +0.115997 s | 0.143 / 16.007 / 34.911 s |
| 2026-08-05 | FLATTEN-20260805T001853Z | 108 | 1 / 1 | +0.211925 s | 0.114 / 26.751 / 46.791 s |
| 2026-08-05 | FLATTEN-20260805T121829Z | 102 | 1 / 1 | +0.121095 s | 1.923 / 23.946 / 43.342 s |
| 2026-08-21 | FLATTEN-20260821T121630Z | 108 | 1 / 1 | +0.120046 s | 0.201 / 23.085 / 42.233 s |
| 2026-08-21 | FLATTEN-20260821T201600Z | 102 | 1 / 1 | +0.216026 s | 0.152 / 25.069 / 50.488 s |
| 2026-08-26 | FLATTEN-20260826T124702Z | 334 | 1 / 1 | +0.148329 s | 2.254 / 75.796 / 144.584 s |
| 2026-09-06 | FLATTEN-20260906T084608Z | 268 | 1 / 1 | +0.289684 s | 0.040 / 51.420 / 141.682 s |
| 2026-09-09 | FLATTEN-20260909T164536Z | 243 | 1 / 1 | +0.268265 s | 1.151 / 52.292 / 103.810 s |
| **2026-09-12** | **FLATTEN-20260912T124737Z** | **255** | **1 / 1** | **+0.150012 s** | **0.135 / 66.064 / 141.950 s** |

Both halves of NEW-01 / F-I5, on the real batches:
1. **One write moment per batch.** Every row of the 09-12 batch carries the identical `anchor_ts` **and** `submit_ts` = `1789217401.146036`, which is the moment the rows were written — so `submit_ts` does not date the submission, it dates the bookkeeping. Per row, that moment sits **0.135 s to 141.950 s after that row's own fill** (median 66.064 s); `first_fill_ts == last_fill_ts` on all 255 rows.
2. **The batch and its readback never join.** The post-flatten readback is written under its own `anchor_ts`, +0.116 to +0.290 s later, so §4-5e sees the flatten anchor as `NO_READBACK` for ever and never judges it.

## §4 Who reads the judged anchor (consumers to keep honest)

| Consumer | Reads | Consequence of a stale judged anchor |
|---|---|---|
| §4-5b state + trigger | `last_reconciled_ats` | reports CLEAN about an anchor that is not the current book (VERIFIED, U1) |
| §4-5e state + trigger | `pb.latest_anchor_ts` | same |
| §4-7 drift boolean | `_rec["latest"]` | same; `ops_stats[-1]["drift_last_reconciled_ats"]` already publishes the anchor, and no consumer compares it to anything |
| EXE-01 proportional gate denominator | `watchdog.py:2346` `_target_gross_at(_days_data, last_reconciled_ats)` — "newest `anchors.target_gross` at or before `ats`" (`:415-427`) | the 2 % test is priced off the gross of the **stale** anchor. INFERRED magnitude only: gross moves slowly between adjacent anchors, so this is a small quantitative shift, not a route change. **NOT CHECKED** numerically. |
| `ops/resume_from_trip.sh:229`, `ops/unseed_rehearsal_halt.py:263` | `conditions_blind` | a stale reading that is not blind lets a trip be cleared while the newest book was never observed |
| `scheduler/run_anchor.py:652` | `conditions_blind` (only when `clock_started`) | the page that would have said "we could not look" is not emitted |

## §5 The reference anchor, and why it is the `anchors` row

The test needs "the newest anchor that happened". Candidates and their verdicts:

- `max(anchor_ts)` over **all** rows — **REJECTED**: after every flatten, the newest key is the FLATTEN order batch, which by construction has no readback (§3.1, 10/10). The watchdog would declare itself blind and halt opening after every trip and every local response. False positive by construction.
- rebalance-id prefix (`A…` vs `FLATTEN-`) — **REJECTED by the repo's own rule**, `live/rebalance_id.py:26-30`: *"'Is this batch a protective flatten' is NOT a prefix question and must not become one. A scheduled rebalance writes an `anchors` row and the ladder does not, so that question is answered from the record … Putting a FLATTEN- literal in this module would hand every importer a name-based test for something that has a property-based one."*
- **newest `anchors` row** — **CHOSEN**. Property-based, already the repo's discriminant, and verified to exclude all 10 flatten batches and to equal the judged anchor on all 272 healthy ones.
- wall clock / anchor grid — **REJECTED as out of scope**: "did an anchor run at all" is already owned off-box by the healthchecks deadman ping (`live/tests_deadman_ping.py`, described in `ops/gate_coverage.py:176`). A second implementation of that question is the twin-implementation family, and it would also make `ops/rejudge_ledger_rows.py` report every historical day as stale.

**Residual limitation of this reference, stated rather than hidden:** a HOLD/halted anchor writes no `anchors` row (P8), so the reference lags by one anchor there. Harmless while that anchor's readback exists (then the judged anchor is *newer* than the reference). It is **not** harmless when P8 and P1 coincide — see §7 — which is why the primary signal is the producer's own statement, below.

## §6 Proposed response (to be red-tested before it is written)

**Detection.** Each of the three guards publishes the anchor it judged, the reference anchor, and whether they agree; when they do not, the guard's state is named (not silently CLEAN) and `blind` is set. `conditions_blind` then already pages (`run_anchor.py:652`) and already refuses resume (`resume_from_trip.sh:229`) — both halves cost nothing new.

**Primary signal = the producer states it.** `finalize_anchor` is the only code that knows *why* there are no rows (P1 read failure vs P3 empty universe vs P4 no account vs P2 truncated write), and today all of those print as "no rows". It returns a named verdict; `run_anchor` passes it to the watchdog at the existing call site (`run_anchor.py:409`, with `fin` already in scope from `:363`). The watchdog always prints **which reference it used**, so a caller that forgets is visible in every `last_eval.json` rather than silently downgraded, and a static cell asserts the production caller supplies it. When it is not supplied (resume gate, `score_post_fix`, `rejudge_ledger_rows`), the record-internal test of §5 is the fallback and says so.

**Action — halt opening, page, flatten nothing.** A new phase-A gate in `anchor_loop`, placed after gate 0b, reads `state/watchdog/last_eval.json` through the mode-stamped reader (the same shape as 0b at `:987-1005`) and, when the newest evaluation says the book was not observed, calls `halt_opening_orders(...)` and pages. It does **not** write `state.json`, does **not** set `tripped_at`, does **not** call `set_reduce_only`, and never flattens — so `resume_from_trip.sh` is untouched and there is no state for an operator to clear. Fail-closed follows 0b exactly: a file that exists and cannot be read ⇒ halted; a file that does not exist (fresh tree) ⇒ not halted.

**Self-healing by fact, not by decay** (the §4-5b idiom, `watchdog.py:1963-1974`): while opening is halted the next anchor still writes its readback (`:2622` is independent of every halt), so the following evaluation is not stale and the gate stops firing by itself. No timer, no counter, no knob.

**Per-anchor cost, measured not assumed:** the gate parses `last_eval.json`, which on the live tree is **8,310,674 bytes**. Timed against that real file through `anchor_loop.book_unobserved_halt`: **0.078 / 0.084 / 0.089 s** (min / median / max of 5). §2.5.3 clause 3 makes a slower anchor a hard constraint — a slower anchor can turn a completion into a MISSED — and 0.08 s against a ~30-minute anchor clears it by four orders of magnitude.

**False-positive cost, bounded:** one anchor of skipped *opening* trades; the book is held; reduce-only paths (universe exits, the staleness ladder, per-name stops) still run; nothing is sold. This is the user rule 2026-09-12 as applied: instrument doubt gets an instrument-shaped response, never a book-level one.

**Negative controls the cells must pin:** (a) DRY_RUN — P4 must read as "no account", never blind, never halting; (b) the anchor immediately after a flatten must not be blind (P7, all 10 historical batches); (c) a HOLD anchor with a readback (the real 08-29 20Z shape) must not be blind; (d) an anchor with a *partial* readback (P2) must not be read as CLEAN by 5b.

## §7 What this fix does not and cannot cover (declared, not discovered later)

1. **A run that dies before the watchdog (P6).** The anchor leaves no row of any kind; no pure-log test can see it, and the watchdog itself never ran. VERIFIED precedent: the 09-09 12Z anchor is simply absent from the record. That is the off-box deadman's question, and E-0909-G is its case history. Naming it here so that "the watchdog now catches unobservable books" is never read as covering it.
2. **P8 ∧ P1 together** — a HOLD/halted anchor whose account read also failed writes neither an `anchors` row nor a readback. The record-internal fallback cannot see it; the producer-supplied signal can, and does, whenever the run reaches the watchdog. Base rate of the pair on the live record: P8 occurred once in 47 days, P1 zero times.
3. **Partial readbacks (P2)** are named but this item does not change 5b's comparison domain; whether a truncated write should itself halt is a separate ruling.
4. **The proportional gate's stale denominator** (§4) is reported, not re-based. NOT CHECKED numerically.
