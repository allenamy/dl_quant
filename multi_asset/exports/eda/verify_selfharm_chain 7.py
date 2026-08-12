"""0C — turn the self-harm chain from INFERENCE into EVIDENCE (team-lead approved 2026-07-27).

The claim under test: §4-5b's anomalies were produced by OUR OWN unrecorded fills, not by a real
position discrepancy. Everything below runs on `reconcile`, which is a pure function — no
production is re-run, nothing is written to the live tree.

  FORWARD   replay the windows whose fills are missing; do the anomaly names coincide with the
            names whose fills are missing?
  ★ REVERSE the control that makes it evidence rather than coincidence: backfill the missing
            fills FROM THE VENUE'S OWN TRADE RECORD and replay. If the anomalies do not
            disappear (or drop sharply), then "missing fills cause the anomalies" was never
            demonstrated — it was merely consistent with the data.

★ WHY THE REVERSE CONTROL IS NOT OPTIONAL: a forward match alone is satisfied by any factor that
  moves both quantities together. Only removing the proposed cause and watching the effect go
  away distinguishes "this caused it" from "these co-occur". This is the same requirement 0C
  imposes on every widening-direction fix in this project, applied here to 0C's own hypothesis.

Read-only w.r.t. the production tree: the backfill is injected into an IN-MEMORY copy.

★★ 2026-07-27T15:5xZ — THE INSTRUMENT WAS THE DEFECT (first version). Kept in full, because the
   shape of the error is the reusable part:

     reconcile windows fills by EXECUTION TIME, not by anchor:
         _win = _between(prev_read_ts, cur_read_ts)      # readback-to-readback
         _between: `for t, sym, f in _exec: if t_lo < t <= t_hi`     # t = the FILL's own time

     v1 instead aggregated every trade since the newest anchor onto ONE order row and stamped it
     `anchor_ts + 60`. For the 07-26 flatten (trades 12:17:54-12:18:40Z) that put ~$23k into the
     window ENDING at the 12:17:30Z readback — the window before the one it belongs to. So the
     backfill manufactured disagreement in window N while still leaving it absent from window
     N+1, and the anomaly count ROSE (371 -> 400). Reported as "NOT DEMONSTRATED" it would have
     refuted a true hypothesis with a broken instrument.

★★ 2026-07-28T00:3xZ — FIXED, and the fix carries a second guard the first version needed and
   did not have:

   (1) EVERY VENUE TRADE BECOMES ITS OWN ROW, CARRYING ITS OWN TIMESTAMP (`last_fill_ts = t`).
       No aggregation, so nothing can land in a neighbouring window.
   (2) ★ A COVERAGE GATE, because the counterfactual is only defined where the venue record
       reaches. The cache spans [t_lo, t_hi]; outside it, zeroing our rows removes fills that
       have NO replacement, which manufactures exactly the disagreement this control exists to
       measure. So a readback window is scored ONLY if the whole window lies inside coverage,
       and every other window is printed as OUT-OF-COVERAGE — never as a verdict.
       Without (2), fixing (1) would have produced a cleaner-looking table with the same class of
       artefact hiding in the boundary windows.
"""
import json
import glob
import sys
import time
from collections import defaultdict

LOGROOT = "/Users/haosiyu/dl_quant_live/state/testnet/pilot_log"
LIVEDIR = "/Users/haosiyu/dl_quant_live/live"
sys.path.insert(0, LIVEDIR)
import pilot_log as PL          # noqa: E402
import reconcile as RC          # noqa: E402


def load_days():
    return {d: PL.read_day(LOGROOT, d) for d in PL.available_days(LOGROOT)}


def anomalies_by_anchor(days):
    rec = RC.reconcile([(d, days[d]) for d in sorted(days)])
    out = defaultdict(set)
    for a in rec["anomalies"]:
        out[round(float(a["anchor_ts"]))].add(a["symbol"])
    return out, rec


def _fill_time(r):
    """The time reconcile will window this row by — its own rule, not a second copy of it."""
    return r.get("last_fill_ts") or r.get("first_fill_ts") or r.get("anchor_ts")


def readback_windows(days):
    """[(anchor_ts, t_prev, t_cur)] — the intervals reconcile actually compares over."""
    stamps = []
    for d in sorted(days):
        seen = {}
        for r in days[d].get("position_readback", []):
            seen[float(r["anchor_ts"])] = float(r.get("read_ts") or r["anchor_ts"])
        stamps += sorted(seen.items())
    out, prev = [], None
    for ats, t in stamps:
        if prev is not None:
            out.append((ats, prev, t))
        prev = t
    return out


def backfill(days, trades_cache):
    """Rebuild the fills ledger from the VENUE's own trade record, one row per trade.

    ★ SIGNED, AND THAT IS THE WHOLE POINT — v1's first draft summed |qty x px| and guessed the
      sign from `target_w`. `reconcile.signed_fills_by_anchor` documents the convention: buy
      positive, sell negative, and nothing re-applies a sign. An unsigned backfill makes a sold
      position look bought, which manufactures MORE disagreement than it removes.

    ★ REPLACE, not add: the counterfactual is "what if the ledger recorded exactly what the venue
      did", so the venue's trades ARE the ledger inside the covered span. Our own rows in that
      span are zeroed first; rows outside it are left exactly as they are, and the windows that
      touch them are excluded from scoring by `main`.
    """
    tr = json.load(open(trades_cache))
    t_lo = min(t for v in tr.values() for t, _q, _p in v) / 1000.0
    t_hi = max(t for v in tr.values() for t, _q, _p in v) / 1000.0

    out = {d: {k: [dict(r) for r in v] for k, v in one.items()} for d, one in days.items()}
    ats_all = sorted({float(r["anchor_ts"]) for d in out for r in out[d].get("orders", [])})

    n_zeroed = 0
    for d in out:
        for r in out[d].get("orders", []):
            t = _fill_time(r)
            if t is None or r.get("filled_notional") in (None,):
                continue
            if t_lo <= float(t) <= t_hi and float(r["filled_notional"]):
                r["filled_notional"] = 0.0
                n_zeroed += 1

    n_inj = 0
    newest_day = max(out)
    for sym, v in tr.items():
        for t_ms, qty_signed, px in v:
            t = t_ms / 1000.0
            cand = [a for a in ats_all if a <= t]
            out[newest_day].setdefault("orders", []).append({
                "anchor_ts": (max(cand) if cand else t),
                "symbol": sym,
                "side": "buy" if qty_signed > 0 else "sell",
                "filled_notional": qty_signed * px,   # SIGNED, from the venue's own qty
                "last_fill_ts": t,                    # ★ ITS OWN TIME — the whole fix
                "first_fill_ts": t,
                "terminal_reason": "filled",
                "order_type": "venue_backfill",
                "rebalance_id": "REVERSE-CONTROL",
                "intended_notional": None,
            })
            n_inj += 1
    return out, n_zeroed, n_inj, (t_lo, t_hi)


def main(trades_cache):
    days = load_days()
    print(f"# run {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    print("=== FORWARD: anomalies on the tree as it stands ===")
    before, rec_b = anomalies_by_anchor(days)
    for a in sorted(before):
        print(f"  {time.strftime('%m-%dT%H:%MZ', time.gmtime(a))}  {len(before[a]):4d} names")
    print(f"  total anomalies = {len(rec_b['anomalies'])}")

    if not trades_cache:
        print("\n(no trades cache given — reverse control skipped)")
        return
    print("\n=== REVERSE CONTROL: rebuild the ledger from the venue's own trades, replay ===")
    patched, n_zero, n_inj, (t_lo, t_hi) = backfill(days, trades_cache)
    print(f"  venue trade record spans {time.strftime('%m-%dT%H:%M:%SZ', time.gmtime(t_lo))}"
          f" .. {time.strftime('%m-%dT%H:%M:%SZ', time.gmtime(t_hi))}")
    print(f"  our own fill rows zeroed inside that span: {n_zero}")
    print(f"  venue trades injected as their own rows  : {n_inj}")

    cov = {round(ats): (lo >= t_lo and hi <= t_hi) for ats, lo, hi in readback_windows(days)}
    after, rec_a = anomalies_by_anchor(patched)
    print(f"\n  {'anchor':16s} {'before':>7s} {'after':>7s}   verdict")
    scored_b = scored_a = 0
    for a in sorted(set(before) | set(after) | set(cov)):
        b, af = len(before.get(a, ())), len(after.get(a, ()))
        if not cov.get(a, False):
            print(f"  {time.strftime('%m-%dT%H:%MZ', time.gmtime(a)):16s} {b:7d} {af:7d}   "
                  f"OUT-OF-COVERAGE (not evidence either way)")
            continue
        scored_b += b
        scored_a += af
        v = ("GONE" if af == 0 and b else "reduced" if af < b
             else "unchanged" if af == b else "WORSE")
        print(f"  {time.strftime('%m-%dT%H:%MZ', time.gmtime(a)):16s} {b:7d} {af:7d}   {v}")
    print(f"  {'SCORED TOTAL':16s} {scored_b:7d} {scored_a:7d}")
    print()
    if scored_b == 0:
        print("  ⇒ NO SCORABLE WINDOW. The control did not run; it is not a null result.")
    elif scored_a <= 0.25 * scored_b:
        print("  ⇒ SELF-HARM CHAIN DEMONSTRATED: removing the proposed cause removes the effect.")
    elif scored_a < scored_b:
        print(f"  ⇒ PARTIAL ({100*(scored_b-scored_a)/scored_b:.0f}% removed). Some anomalies have "
              f"another cause — name them, do not fold them in.")
    else:
        print("  ⇒ NOT DEMONSTRATED. The forward match was coincidence or the attribution rule "
              "above is wrong. The hypothesis does NOT get to keep its status.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
