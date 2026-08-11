"""Replay §4-5b's anomaly fractions off the real trip-day ledger, under both sign conventions.

Expected (lead / 0C's oracle):
    current code : 31 rows frac≈0.5  +  16 rows frac=1.0   ← the 16 are the sells
    sign fixed   : 47 rows all ≈0.5                        ← one cause (the 2x), clean

The point of running it BOTH ways in one process is that the only thing that differs is the
arithmetic — same ledger, same grouping, same comparison. A separate before/after run would leave
room for anything else to have changed.
"""
import os
import sys
from collections import defaultdict

REPO = "/Users/haosiyu/dl_quant_live"
sys.path.insert(0, os.path.join(REPO, "live"))
import pilot_log as PL          # noqa: E402
import state_root as SR         # noqa: E402

root = SR.paths_for("TESTNET")["pilot_log"]


def fractions(signed_correctly: bool):
    """Return the list of `unexplained/|expected|` fractions, exactly as watchdog computes them."""
    out = []
    prev_rb = None
    for d in sorted(PL.available_days(root)):
        one = PL.read_day(root, d)
        rb_by_anchor = defaultdict(dict)
        for r in one["position_readback"]:
            rb_by_anchor[r["anchor_ts"]][r["symbol"]] = float(r["venue_position_notional"])
        filled_by_anchor = defaultdict(lambda: defaultdict(float))
        for o in one["orders"]:
            f = float(o["filled_notional"] or 0.0)
            if signed_correctly:
                # `filled_notional` is ALREADY signed (binance_broker: sign * cumQuote).
                # Net exposure change is the sum of signed fills; nothing to re-apply.
                if f:
                    filled_by_anchor[o["anchor_ts"]][o["symbol"]] += f
            else:
                # the shipped code: drops every sell (f < 0 fails `f > 0`) and re-applies a sign
                if f > 0:
                    filled_by_anchor[o["anchor_ts"]][o["symbol"]] += (
                        1 if o["side"] == "buy" else -1) * f
        for ats in sorted(rb_by_anchor):
            cur = rb_by_anchor[ats]
            if prev_rb is not None:
                for sym, v in cur.items():
                    expected = prev_rb.get(sym, 0.0) + filled_by_anchor[ats].get(sym, 0.0)
                    unexplained = abs(v - expected)
                    # ★ the REAL scale is max(|expected|, |v|, 1.0) — I first wrote
                    # max(|expected|, 1.0) from memory and got fractions up to 1199, which is
                    # what a replay that does not copy the code under test produces.
                    scale = max(abs(expected), abs(v), 1.0)
                    frac = unexplained / scale
                    if frac > 0.10:
                        out.append((sym, round(frac, 4), round(v, 2), round(expected, 2)))
            prev_rb = cur
    return out


for label, ok in (("CURRENT (shipped)", False), ("SIGN-FIXED", True)):
    rows = fractions(ok)
    buckets = defaultdict(int)
    for _s, fr, _v, _e in rows:
        buckets[round(fr, 1)] += 1
    print(f"{label:20} anomalies={len(rows):3}  by frac: "
          f"{dict(sorted(buckets.items()))}")
    if rows:
        worst = sorted(rows, key=lambda r: -r[1])[:4]
        print(f"{'':20} worst: {worst}")
