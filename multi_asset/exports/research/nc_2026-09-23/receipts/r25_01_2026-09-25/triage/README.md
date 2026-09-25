> **Created:** 2026-09-25 18:1xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4) | **Status:** R25-01 class census — per-site verdicts (lead ruling: tiered by money impact, each site judged defect / legitimate with the line) | **Invalidated by:** a change of the cited lines (executor tree 96acfdd)

# Triage of the quantity-gate census (CENSUS_quantity_gates_96acfdd.txt)
Scope: the 161 NON-TEST sites of the 227 (A 23 + B 204); the 66 sites inside live/tests_* are test fixtures and were not judged. Grouped sites on
the same record / same line family share one entry: 73 entries, TRIAGE_tier1.jsonl (sizing, orders, stops, NAV, leverage, fills, positions)
and TRIAGE_tier2.jsonl (reports, digests, diagnostics, one-off tools). A site is LEGITIMATE when the absent / zero reading has a documented
contract (the positions book lists held names; an absent key = not held), leads to a conservative direction (more paging, blocked, stricter
check), or is followed by an explicit refusal; it is a DEFECT when an unknown quantity is read as a measured zero in a way that relaxes a check
or books a value.

| tier | legitimate | defect | of which medium | low-medium | low |
|---|---|---|---|---|---|
| 1 | 21 | 18 | 2 | 5 | 11 |
| 2 | 25 | 9 | 0 | 0 | 9 |

Medium (tier 1):
1. live/position_break.py:563-564 — unauth_gross_usdt / underfill_gross_usdt missing ⇒ 0 ⇒ the position-break guard reads "no break" (a producer that stops emitting the key disarms the guard silently).
2. live/reconcile.py:408 — a readback row with neither venue_position_qty nor venue_position_notional is returned as qty 0 (flat).
Low-medium (tier 1):
- scheduler/anchor_loop.py:2058 + live/external_book.py:529 — a name absent from executor.filters gets floor 0 ⇒ passes the 2×min-notional gate (and, with fix package D, is never judged dust); unknown floor should be "not checked".
- live/binance_executor.py:386-429 and live/venue_fills.py:753-774 — a malformed child fill (no qty / price / quote) becomes a zero-size, zero-fee fill instead of a refusal.
- live/watchdog.py:1368, 1884 — external_flow_usdt missing ⇒ "no flow" in the drawdown watchdog's NAV series.
No site was found that is currently exercised by the data (every field the defects read is written by its producer today — cf. the R25-01 NaN census: 0 non-finite values in the ledger); these are latent. Limitation: the census's A detector does not follow a value through a local variable (it missed the H1 site), so the census is a lower bound of the class.
Proposed next step (not done): the two medium sites + the floors gap into the next fix package, each with a red control; the rest listed for the owners.

## CORRECTION 2026-09-25 18:1xZ (C-4) — file split did not match the rows' `tier` field
The table above counts by each row's `tier` field and is right (tier 1: 39 entries = 21 legitimate + 2 medium + 5 low-medium + 11 low; tier 2: 34 = 25 legitimate + 9 low).
The files as first committed (2cc3c0574) put 55 rows in TRIAGE_tier1.jsonl, 16 of them carrying `tier: 2` (listed in MOVED_rows_tier2_found_in_tier1_file.json);
anyone counting by file got 14 + 6 low instead of 11 + 9. The files are now re-split by the field; the 73-row multiset was asserted unchanged (no row text edited).
The next-package list is NEXT_PACKAGE_low_defects.jsonl: the 20 low defects (tier 1: 11, tier 2: 9), owner C-4 with lead approval, each red-control first (lead ruling 2026-09-25).
