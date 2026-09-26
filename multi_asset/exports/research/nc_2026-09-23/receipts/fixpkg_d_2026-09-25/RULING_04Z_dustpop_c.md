> **Created:** 2026-09-26 05:1xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n (C-4) | **Status:** lead ruling on check (c) of the 04Z first fix-pkg-d anchor; both verdicts kept side by side | **Invalidated by:** none (record)

# 04Z (1790395200) check (c): both verdicts
| verdict | device | file |
|---|---|---|
| **literal: RED** | accept_dustpop_first_anchor.py rev 0 (frozen eb59564cf, before the anchor) | ACCEPT_DUSTPOP_04Z_1790395200.txt |
| **by intent: PASS** (lead ruling) | rev 1 (committed before the 08Z anchor) | ACCEPT_DUSTPOP_04Z_1790395200_rev1_by_intent.txt |

**Facts.** Each of the 3 dust-popped names (BCH / ENA / ZAMA) has one plan row:
- intended_notional 0.34 / 2.18 / 0.72 USDT;
- terminal `skipped_min_notional`;
- submit_ts None, request_ledger None, first_fill_ts None, fee 0;
- no fill since 04:00Z, and the readback residuals are unchanged.

**Why the intent predates the reading.** The lead accepted D4 in the fix-pkg-d design review, before this anchor: keep the flatten_only row; it is skipped; nothing is sent. The same text is in the design (docs/DESIGN_dust_pop_before_reshape_2026-09-25.md) and in tests_dust_pop D4 ("the dust name's plan row is a SKIP … no order-bearing row").

**The error.** rev 0 operationalised "no order with a quantity" as "intended_notional == 0". The ledger records the residual's size on skip rows too, so the criterion misread a skip row as an order.

**rev 1.** (c) = for every popped name's row, submit_ts, request_ledger and fills are all empty.
- Red control: one ENA row given a submit_ts in a temp copy ⇒ RED (ACCEPT_DUSTPOP_rev1_redcontrol_sent_row.txt).
- The fix itself: post-clamp book net +9.42 USDT = 0.009% NAV, against +2,405 (2.20%) at 00Z.
