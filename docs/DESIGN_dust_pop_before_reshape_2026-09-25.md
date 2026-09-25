> **Created:** 2026-09-25 16:0xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4 integrator) | **Status:** DESIGN DRAFT for the lead's review — no code changed; a book-behaviour change ⇒ user ruling + deploy protocol after review | **Invalidated by:** a change of withhold_pop / apply_withhold_and_reshape / RebalanceExecutor.plan, or a lead ruling

# Fix design: a DUST position counts as flat in the withhold (pop before the reshape, not clamp after it)

## 1. Defect (measured; receipts `multi_asset/exports/research/clamp_hook_2026-09-25/receipts/` parity_run1 43a545571, dust_pop)
- `scheduler/anchor_loop.py` L331 (`withhold_pop`): an untradable name is popped only if its held notional is **exactly** 0.0. A residual below the
  venue's min notional (PRLUSDT −1 contract = −0.12 USDT; ENAUSDT −8 contracts = −1.8 USDT) counts as "held", so it goes to the clamp
  (`clamp_held_untradable` L464) AFTER the reshape and its reshape target is not re-absorbed (L366–L372).
- The planner can never close such a residual: `live/binance_executor.py` L825–L827 skips any |delta| < min_notional as
  `skipped_min_notional`, exits included (PRLUSDT: 81 skipped_min_notional rows; the −1 contract held for ≥ 54 anchors).
- Economically the residual is flat; but every anchor it is clamped, and when the producer targets the name (the stop-cooldown trio BCH / ENA /
  ZAMA, still strongly shorted by the producer) the book is pushed net LONG by the unabsorbed target: live net after the clamp +1.3 … +2.4 % of
  NAV from 09-20 (mean +1.06 % over 54 anchors 09-16 12Z … 09-25 08Z).

## 2. Proposed rule
In `withhold_pop` (the pop step, before the reshape): an untradable name whose |held notional| is BELOW ITS VENUE MIN NOTIONAL (the
`floors_usdt` the caller already passes to `apply_withhold_and_reshape`, from `executor.filters.f[*].min_notional`) is treated as flat — popped
like an unheld untradable. Names held at or above the floor keep today's clamp. If `floors_usdt` is not supplied, today's exact-zero rule
applies unchanged (no floor ⇒ no dust judgement; fail closed to current behaviour). A fixed, pre-written threshold instead of the venue floor is
the alternative (not proposed: the venue floor is the quantity that makes the residual un-closable, L825).
Scope: one comparison in `withhold_pop` (plus passing the floors to it); the reshape, clamp, cap and planner are unchanged.

## 3. Pure recompute on the ledger (no engine, no executor code run; `dust_pop_recompute.py`, 54 anchors 09-16 12Z … 09-25 08Z)
- Net after the clamp: actual mean **+1.06 % of NAV** → with the rule mean **−0.03 %**, max |net| **0.10 %**; the NC-window anchors e.g. 09-24
  00Z +2.374 % → −0.002 %, 09-25 08Z +2.230 % → −0.006 %.
- Names the rule pops (name-anchors): PRL 54, SCR 54, US 38, NOM 35, ZAMA 34, ENA 32, DUSK 20, BCH 14, BIGTIME 12, API3 11, 1INCH 4, HOLO 3
  (exit tails and the cooldown trio). Clamped names still kept (held above the floor): LTC 28, BIO 6, RUNE 4, … (genuine held untradables).

## 4. No conflict with the stop cooldown (to be verified by a test before any deploy)
- A popped name leaves `target` (L332 `target.pop(s_, None)`); the planner iterates ONLY over the target (`live/binance_executor.py` L803
  `for sym, tgt in target_notional.items()`), so a popped name gets **no plan row and no order at all** ⇒ it cannot be opened, which is exactly
  what the cooldown requires. Its dust stays where it is (as today, where the planner skips it anyway).
- Stopped names (force_flat, W9) are unaffected: they already leave the reshape population at L1b and come back at exactly 0.0 (flatten_only).
- To examine before code (named, not assumed): consumers that look at "held but not targeted" names — the orphan-position logic
  (`tests_orphan_position`), the held-withheld page, `known_gaps`, M3's `hard_block` / `dust_only` (anchor_loop L2085–L2086), position
  reconciliation alarms — each must keep reporting the dust as dust, not as an orphan or a failure.

## 5. Tests the change must carry (red controls first)
- a held residual below the floor is POPPED (was clamped); one at / above the floor is still clamped; floors absent ⇒ exact-zero rule;
- a popped cooldown name produces no plan row and no order (the no-opening proof as a test, not a comment);
- the reshape of an anchor with dust names is neutral (net 0) and the clamp net shift excludes them;
- replaying the recorded 08Z 1790323200 reshape: net after clamp +2,464 → ≈ 0.
- Research engine parity: the engine imports the same function (409ea16 mirror); the fix must land in the engine mirror in the same release
  or the backtest / live gap reopens (the hook cell measured the engine's post-clamp net at ≈ 0 in median — the engine rarely creates dust;
  why the engine closes exits to exactly zero is the parity investigation's open item 1).
