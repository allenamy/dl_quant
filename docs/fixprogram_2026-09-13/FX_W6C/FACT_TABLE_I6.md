> **创建:** 2026-09-16 03:4xZ | **Session:** FX-W6C (fix worker, W6C-I6 P1) | **状态:** 事实表, 写于任何执行器代码改动之前(规程 §0-1); 数字取自 02:53Z 只读快照与本表所列探针 | **作废条件:** 执行器基底 ≠ ef60f85, 或 `PB_HALTED_FLAT_PORTFOLIO_FRAC` / `_intended_by_anchor` 的分类规则被改

# FACT TABLE — W6C-I6: an off-schedule run that holds a book and submits nothing is judged against intent ZERO, and that trips the whole-book ladder

Legend: **VERIFIED** = read at the cited line on ef60f85, or measured by a device listed in §0; **INFERRED** = reasoning from verified facts, not measured; **NOT CHECKED** = stated so nobody reads it as checked.

## §0 Frozen objects
Same as `FACT_TABLE_B13.md` §0 (base `ef60f85`, clone `/Users/haosiyu/cc_tmp/fx_w6c`, state copy `/Users/haosiyu/cc_tmp/fx_w6c_state_20260916` taken 02:53Z). Devices for this item: `devices/probe_i6_offschedule.py`; receipt `receipts/i6_offschedule_census_20260916.json`.

## §1 The mechanism (VERIFIED, ef60f85)

| Step | Site | Fact |
|---|---|---|
| 1 | `anchor_loop.py:1136-1176` gate 0c | a run more than `anchor_late_tolerance_min` from its slot sets `out["off_schedule_halt"]` and calls `halt_opening_orders(...)`. **It deliberately does not return** — reduce-only paths keep running, and the anchor goes on to plan, price and write its rows. |
| 2 | `anchor_loop.py:2803-2829` | the anchor still writes an `anchors` row with a positive `target_gross` (`ctx` is set: a rebalance was attempted), and `opening_halted=True`. It carries **no `halt_kind`** — that field is written for a proportional local response only. |
| 3 | `position_break.py:282-297` `_intended_by_anchor` | an anchor with an `anchors` row, `target_gross>0`, **no submission** and no `halt_kind` falls to the last branch: `{"intended": {}, "kind": "halted_intent_flat"}` — intent **ZERO**. |
| 4 | `position_break.py:753-756` | on such an anchor the limit becomes `PB_HALTED_FLAT_PORTFOLIO_FRAC = 0.010` (`position_break.py:119`), i.e. **1 % of gross**, and `frac = Σ\|readback\| / target_gross`. |
| 5 | `position_break.py:828-831` | the gate is `flat_intent_legacy`, and on that branch `triggered = _legacy = port_hit` — the split is **not allowed to speak** (by design: on a zero intent the whole standing book decomposes as "underfill", which would forgive the 2026-07-29 ghost book). |
| 6 | `watchdog.py` §4-5e append site | a `flat_intent_legacy` break carries **no name scope** — EXE-01 sets one only when `split_unauth`'s per-name clause alone fired — so the trigger is book-level by absence and `proportional_gate` routes it to the LADDER. |

⇒ **An off-schedule run holding a book at target_gross G reports `frac ≈ G/G ≈ 1.0` against a 1 % limit, trips §4-5e, and the ladder flattens the entire book** — in the same run, because the watchdog runs immediately after phase C (`run_anchor.py:363` then `:409`). INFERRED only in the arithmetic; every input above is VERIFIED.

This is the same family EXE-01 closed for the proportional local response (its B14 cell measured the identical shape at **99 % of gross** via `flat_intent_legacy`), and the same family W6C-B13 closed for an unobserved book. The `halt_kind` marker exists precisely for it; the off-schedule halt was never given one.

## §2 Reachability in production (VERIFIED, `receipts/i6_offschedule_census_20260916.json`)

Parsed from the live `state/anchor_runs.log` (37,611 lines, 999 runs, 2026-07-25 … 2026-09-16), pairing every `anchor start mode=` with its `phase_A` record:

| mode | on schedule | **off schedule** |
|---|---|---|
| DRY_RUN | 111 | **570** |
| LIVE | 274 | **3** |
| TESTNET | 39 | **2** |

So it is not hypothetical: **three LIVE off-schedule runs have already happened.**

| when | offset | phase_A | phase_C | how §4-5e judged it |
|---|---|---|---|---|
| 2026-08-01 06:29:29Z | −90.06 min | `off_schedule_halt`, action TRADE | `anchors_row true`, 109 readback rows | `halted_intent_flat`, `trip_gate flat_intent_legacy`, **CLEAN** |
| 2026-08-01 10:03:18Z | −116.36 min | `off_schedule_halt`, action TRADE | no phase_C record | — |
| 2026-08-02 05:31:47Z | +92.02 min | `off_schedule_halt`, action TRADE | `anchors_row true` | `halted_intent_flat`, `trip_gate flat_intent_legacy`, **CLEAN** |

**And each of the two judged ones was CLEAN for one reason only: the book was empty at that moment.** On the 08-01 06:29Z anchor the record reads `target_gross 4234.690812343863`, **109 order rows of which 0 were submitted**, and a readback whose `Σ|venue_position_notional| = 0.00` — the deployment's first anchor, before the book was built. The 08-02 05:32Z one follows the 04:18Z protective flatten, so its book was empty too. `frac = 0/4234.69 = 0.0`, under the 1 % line by luck of timing, not by design.

## §3 What would have happened with a held book

Every live anchor since 2026-08-03 carries a realised gross within a few percent of `target_gross`. Substituting any of them into step 4 gives `frac ≈ 1.0` against `0.010` ⇒ `port_hit` ⇒ `flat_intent_legacy` trips ⇒ book-level trigger ⇒ ladder. INFERRED from VERIFIED inputs; the red cell in §5 measures it on real rows rather than leaving it as arithmetic.

## §4 Why the off-schedule halt is a HELD book, and the trip halt is not

`halt_kind` answers one question: **did this halt leave the positions in place?**
- watchdog trip ⇒ the ladder flattened the book ⇒ intent ZERO is correct, and the marker must NOT be written (`position_break.py:286-289` says exactly this).
- proportional local response ⇒ named names closed, the book held ⇒ marker `proportional_local` (EXE-01).
- W6C-B13 unobserved-book halt ⇒ nothing closed ⇒ marker `book_unobserved`.
- **off-schedule halt ⇒ opening refused, nothing closed ⇒ the same fact, and no marker.** That is the gap.
- the staleness ladder's `FLATTEN` action empties the book on purpose, so an off-schedule run whose `action` is `FLATTEN` must NOT get the marker.

## §5 Plan
Red cell on the real 2026-08-01 06:29Z off-schedule anchor's own rows with a **held** readback substituted (real names, real notionals from a later anchor of the same day): on ef60f85 and on the current head it trips §4-5e `flat_intent_legacy` and the response is the whole-book ladder. Fix = write `halt_kind = "off_schedule"` on that anchor's row (never when the action is `FLATTEN`) and add it to `position_break.BOOK_HELD_HALT_KINDS`, which W6C-B13 already made the single list. Negative controls: the real empty-book anchors stay CLEAN; a trip-halted anchor keeps intent ZERO; a FLATTEN-action off-schedule run keeps intent ZERO.
