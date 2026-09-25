> **Created:** 2026-09-25 15:5xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4) | **Status:** R25-03 device on the main drawdown window (old producer); run 3 (device rev 3) is the reported one; runs 1–2 kept (run 1 KeyError on pre-E6 records; run 2 failed the per-name identity on 31/46 anchors — the venue-cap step, found and added) | **Invalidated by:** a change of the ledger / notify_audit / price snapshot 1790337600

# Layered book, 09-16 12Z → 09-24 04Z (46 anchors, old producer)
**Denominator**: 46 anchors in the window; **46 pass every identity** (4 of them with E6 not evaluated: records before 09-17 04Z have no net_producer_usdt); 46 priced; 0 failing, 0 skipped; contract closure exact on every name; unpriced: one name-anchor (≈ 740–800 USDT |notional| per layer, reported, not summed). Venue-cap events on 31 anchors (clamp_venue_cap, recorded only in notify_audit; all lists complete, none truncated).

| layer | P&L (46 anchors) | step | Δ |
|---|---|---|---|
| L0 producer raw | −12,260.9 | | |
| L1 reshaped | −9,349.8 | reshape (pop + redemean + rescale) | **+2,911.1** |
| L2 clamped + venue cap | −9,278.3 | clamp / cap | +71.5 |
| L3 tried | −9,287.3 | not sent | −9.0 |
| L4 filled | −9,280.4 | fill shortfall | +6.9 |
| L5 readback | −9,276.6 | readback vs fills | +3.8 |
**Reading**: over the main drawdown the held book lost −9,276.6 at one price; execution proper (L2 → L5) is **+1.7** — execution carries none of it. The producer's raw book would have lost −12,260.9; the executor's re-neutralisation of the producer's net-short raw book is worth +2,911. The loss is in the (reshaped) target.
Net by layer: L2 −570 … +2,708, L5 −974 … +3,131 per anchor; summed L1→L2 net shift: clamped names +44,563, venue-capped names −9,076 (the caps cut longs); L2→L5: venue_reject +4,264, skipped_min_notional +1,306, partial_expired −419.
