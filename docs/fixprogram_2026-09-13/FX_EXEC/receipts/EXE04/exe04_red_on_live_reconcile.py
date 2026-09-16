"""EXE-04 red demonstration on the REAL `live/reconcile.reconcile()` — not on the new core.

The lead's contract (independent review, REVIEW_fixprogram_progress_2026-09-14 §7.1, and
PREREG_reconcile_carry_forward_unexplained_2026-09-10 §0/§3.1):

    window t leaves an unexplained residual  ->  window t+1 reads CLEAN on the current code

This script runs the reviewer's own Q6 fixture through the SHIPPING reconciler and prints what it
says at each window. It is a RECEIPT, deliberately NOT a battery suite: the fix for it is the
executor wiring (§4-5b/5e reading |E_s| instead of |e_t|), which the lead has ruled out of scope
for this round, so a cell asserting the corrected behaviour would be permanently red and a cell
asserting the CURRENT behaviour would have to be rewritten the moment the wiring lands. Archiving
it as a receipt keeps the evidence without planting either.

THE FIXTURE (PREREG §0, reviewer's real top-up):
  window 1 — two top-up requests, each EXPIRED having filled 25 contracts (50 explained), and the
             venue reads back 80. Residual 30: ANOMALOUS, correctly.
  window 2 — no fills at all, and the venue still reads back 80. Under the current per-window
             comparison the baseline for window 2 is the OBSERVED 80, so the residual is
             80 - 80 - 0 = 0 and both §4-5b and §4-5e read CLEAN. The 30 has not been explained,
             resolved or aged — it has been absorbed into the baseline.

Read alongside `live/tests_reconcile_carry.py` [G4a], which puts the same fixture through the new
joint object and gets distance 30 at window 2 with history_unresolved True.
"""
import json
import os
import sys

HERE = "/Users/haosiyu/cc_tmp/fx_exec"
for d in ("live", "ops", "scheduler", "signal"):
    sys.path.insert(0, os.path.join(HERE, d))
import reconcile as RC       # noqa: E402

T1, T2 = 1_789_000_000.0, 1_789_014_400.0        # two consecutive 4h anchors
PX = 1.0                                          # 1 USDT per contract, so notional == qty

# window 1: two top-up legs, each filled 25 of a requested 25, and a readback of 80
orders = [
    {"anchor_ts": T1, "symbol": "QUSDT", "side": "buy", "order_type": "topup_taker",
     "attempt_idx": 2, "rebalance_id": "A1789000000", "terminal_reason": "partial_expired",
     "submit_ts": T1 + 60, "filled_notional": 25.0, "avg_fill_px": PX,
     "first_fill_ts": T1 + 70, "last_fill_ts": T1 + 70, "cancel_ts": None, "fee_paid": None,
     "intended_notional": 25.0, "target_w": 0.01, "prev_w": 0.0, "mid_at_submit": PX,
     "mid_at_anchor": PX, "price_submit": None, "notional_currency": "USDT"},
    {"anchor_ts": T1, "symbol": "QUSDT", "side": "buy", "order_type": "topup_taker",
     "attempt_idx": 2, "rebalance_id": "A1789000000", "terminal_reason": "partial_expired",
     "submit_ts": T1 + 80, "filled_notional": 25.0, "avg_fill_px": PX,
     "first_fill_ts": T1 + 90, "last_fill_ts": T1 + 90, "cancel_ts": None, "fee_paid": None,
     "intended_notional": 25.0, "target_w": 0.01, "prev_w": 0.0, "mid_at_submit": PX,
     "mid_at_anchor": PX, "price_submit": None, "notional_currency": "USDT"},
]
readback = [
    # the baseline: flat before anything happened
    {"anchor_ts": T1 - 14400, "read_ts": T1 - 14400 + 5, "symbol": "QUSDT",
     "venue_position_notional": 0.0, "venue_position_qty": 0.0},
    # window 1: 50 explained by our two legs, 80 observed  -> 30 unexplained
    {"anchor_ts": T1, "read_ts": T1 + 300, "symbol": "QUSDT",
     "venue_position_notional": 80.0, "venue_position_qty": 80.0},
    # window 2: nothing filled, still 80
    {"anchor_ts": T2, "read_ts": T2 + 300, "symbol": "QUSDT",
     "venue_position_notional": 80.0, "venue_position_qty": 80.0},
]

out = RC.reconcile([("20260916", {"orders": orders, "position_readback": readback})],
                   tol=0.10, dust_abs=5.0)

print("=" * 78)
print("REAL reconcile() on the reviewer's Q6 fixture")
print("=" * 78)
per_anchor = {}
for a in out.get("anomalies", []):
    per_anchor.setdefault(a["anchor_ts"], []).append(a)
for ats, label in ((T1, "window 1 (two legs filled 25 each = 50 explained; venue reads 80)"),
                   (T2, "window 2 (NOTHING filled; venue still reads 80)")):
    hits = per_anchor.get(ats, [])
    resid = (out.get("residual_by_anchor") or {}).get(ats, {}).get("by_symbol", {}).get("QUSDT")
    print(f"\n{label}")
    print(f"  anomalies at this anchor : {len(hits)}")
    for h in hits:
        print(f"     kind={h.get('kind')} residual_qty={h.get('residual_qty')} "
              f"residual_usdt={h.get('residual_usdt')}")
    print(f"  residual vector          : {json.dumps(resid) if resid else 'None'}")

w1 = len(per_anchor.get(T1, []))
w2 = len(per_anchor.get(T2, []))
print("\n" + "=" * 78)
print(f"VERDICT  window 1 anomalies = {w1}   window 2 anomalies = {w2}")
if w1 >= 1 and w2 == 0:
    print("RED AS EXPECTED: the 30 that window 1 could not explain is GONE at window 2 — it was")
    print("absorbed into the new baseline (reconcile.py:693-720 takes the previous readback's")
    print("observed qty as `q1`, and :848 sets `prev_rb = cur`). Nothing explained it, nothing")
    print("resolved it, and no gate can see it any more. This is EXE-04 / Q6, unfixed.")
    sys.exit(0)
print("UNEXPECTED: the fixture did not reproduce the documented shape — investigate before")
print("quoting any of this.")
sys.exit(1)
