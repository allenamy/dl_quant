> **Created:** 2026-09-25 15:3xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4) | **Status:** R25-03 device result (run 2 = the reported one; run 1 kept: its L3 double counted) | **Invalidated by:** a change to the executor's reshape/clamp, the ledger, or the price snapshot 1790337600

# Layered book, NC window (6 priced anchors 09-24 08Z .. 09-25 04Z; 09-25 08Z/12Z tilt only)
Device `devices/layered_book.py` (e2eb382b2, rev 1 before run 2). Same decision-time price (mid_at_anchor), same holding interval (this readback → next), per name; unpriced names reported, never 0. Every anchor passes four identity checks: E6 Σ L0 == net_producer_usdt; the reconstructed reshape reproduces net_after / gross_after; Σ L2 == clamped_after_reshape.book_net_usdt; **per name L2 == L1 for every non-clamped name** (max |diff| < 1e-6·G). Contract closure: every name closes to < 1e-9 except STGUSDT at 09-24 12Z (−6,504, the STG settlement / delisting).

## P&L by layer (sum of 6 anchors, USDT)
| layer | P&L | step | Δ |
|---|---|---|---|
| L0 producer raw (target_live, pre-reshape) | −2,616.4 | | |
| L1 reshaped (pop + redemean + rescale) | −2,407.4 | reshape | **+209.0** |
| L2 clamped target (held untradables pinned) | −2,354.4 | clamp | +53.0 |
| L3 tried (clamped target if sent, else previous) | −2,369.5 | not sent (min-notional etc.) | −15.1 |
| L4 filled | −2,375.1 | fill shortfall | −5.6 |
| L5 readback | −2,374.8 | readback vs fills | +0.3 |
Unpriced: 09-24 08Z only, 803–858 USDT |notional| per layer (reported, not in the sums).
**Reading**: the book the executor actually held lost 2,374.8 over these intervals; the producer's raw book would have lost 2,616.4 at the same prices. The +241.6 difference is mostly the executor's reshape (+209.0) and clamp (+53.0); execution proper (not sent / partial fills / readback) is −20.4. The earlier "live better than paper by +112 / +301 ⇒ not execution" (paper_vs_live.py) compared the raw producer book with the held book and is RETRACTED (R25-03): that device cannot judge execution. This device's reading on execution is: −20.4 USDT over 6 anchors (fills vs the tried target), valued at one price.
Lead's estimate "the reshape difference ≈ the +301": in this caliber the reshape is +209 of +242 (86%); the +301 was valued with readback notionals and a different interval, so the two are not the same number.

## Where the +2.3% NAV long tilt comes from (net USDT by layer, every anchor)
L0 −6,453 … −9,499 (the producer's book is net short 3–4% of gross) → L1 0.0 (the executor re-neutralises) → **L2 +2,463 … +2,538 at every anchor** → L5 readback +1,971 … +3,009.
- The whole L1→L2 step is the clamp on the 5–7 HELD untradable names (clamped_after_reshape names: BCH / ENA / ZAMA in stop cooldown, PRL / SCR exits, SYN, 1INCH/ETH/VANA on some anchors): they are held (so not popped), receive a reshape target (the producer still wants them short), then the clamp pins them at their held size ≈ 0 (pinned_net −2.8 USDT) and the removed short is NOT re-absorbed (anchor_loop.py L366–372, by design: "an unmade hedging decision"). Net shift = +2,463 … +2,538 per anchor (the executor's own net_shift_usdt).
- L2 → L5 (execution) moves the net by −412 … +474 per anchor (partial_expired the largest, then min-notional / rejects; blocked_by_halt −460 at 09-24 16Z).
- **Verification of my conjecture (zero-target names shifted by w.mean()): refuted.** The reshape vector is built from the target dict only (scheduler/anchor_loop.py L405 `syms = sorted(target)`, L406 `vec = _np.array([target[s_] / g for s_ in syms], float)`), which holds the producer's names minus the popped ones; the per-name check L2 == L1 for every non-clamped name holds at every anchor with the reconstruction that contains NO zero-target names (a zero in the vector would have shifted every name by a different mean). The shift therefore adds no small weights to zero-target names.
