"""0C — reproduce the orders-ledger fills gap and its consequence (2026-07-27).

Two independent records of the same three days:
  (a) the VENUE's own trade record  (GET /fapi/v1/userTrades, per symbol)
  (b) OUR pilot log                 (orders.jsonl `filled_notional`, and fills.jsonl)

and then the consequence: `reconcile` (which computes expected = prev_readback + LOGGED fills)
reports §4-5b anomalies at exactly the anchors whose fills are missing, and zero at the ones
recorded exactly. The degradation ladder's own note cites the anomaly count as its trigger —
so the flattens were driven by a number derived from an incomplete ledger, and the flattens'
own fills were then also unrecorded.

★ WHY THIS MATTERS BEYOND BOOKKEEPING: the book was flattened between anchors on every cycle,
  so it never held a position through a funding settlement. That is the whole reason the
  "FUNDING_FEE = 0" observation had an empty denominator (see §2.5.10).

Read-only. Needs BINANCE_TESTNET_KEY/SECRET for (a); (b) and (c) are local files.
"""
import json
import glob
import sys
import time
from collections import Counter, defaultdict

LOGROOT = "/Users/haosiyu/dl_quant_live/state/testnet/pilot_log"
LIVEDIR = "/Users/haosiyu/dl_quant_live/live"


def our_ledger():
    orders, fills = [], []
    for f in sorted(glob.glob(LOGROOT + "/*/orders.jsonl")):
        orders += [json.loads(l) for l in open(f)]
    for f in sorted(glob.glob(LOGROOT + "/*/fills.jsonl")):
        fills += [json.loads(l) for l in open(f)]
    return orders, fills


def main(trades_cache=None):
    orders, fills = our_ledger()

    print("=== (b) OUR pilot log ===")
    by_day = defaultdict(float)
    for r in orders:
        if r.get("filled_notional"):
            d = time.strftime("%Y%m%d", time.gmtime(float(
                r.get("last_fill_ts") or r.get("first_fill_ts") or r.get("submit_ts") or 0)))
            by_day[d] += abs(float(r["filled_notional"]))
    print(f"  orders.jsonl filled_notional by day: "
          f"{ {k: round(v) for k, v in sorted(by_day.items())} }")
    print(f"  fills.jsonl rows: {len(fills)}")
    fb = defaultdict(float)
    for r in fills:
        fb[r["rebalance_id"]] += abs(float(r.get("fill_notional") or 0))
    print("  fills.jsonl batches (note: NO FLATTEN- batch appears):")
    for rid, v in sorted(fb.items()):
        print(f"     {rid:28s} ${v:12,.0f}")

    print("\n=== FLATTEN batches as recorded in orders.jsonl ===")
    g = defaultdict(list)
    for r in orders:
        if str(r.get("rebalance_id", "")).startswith("FLATTEN-"):
            g[r["rebalance_id"]].append(r)
    for rid in sorted(g):
        v = g[rid]
        fn = sum(abs(float(x["filled_notional"])) for x in v if x.get("filled_notional"))
        print(f"  {rid:28s} n={len(v):4d} {dict(Counter(x['terminal_reason'] for x in v))} "
              f"filled=${fn:,.0f}")

    print("\n=== (c) the consequence: reconcile over the same tree ===")
    sys.path.insert(0, LIVEDIR)
    import pilot_log as PL          # noqa: E402
    import reconcile as RC          # noqa: E402
    days = PL.available_days(LOGROOT)
    rec = RC.reconcile([(d, PL.read_day(LOGROOT, d)) for d in days])
    per = Counter(time.strftime("%m-%dT%H:%MZ", time.gmtime(a["anchor_ts"]))
                  for a in rec["anomalies"])
    print(f"  n_anomalies={len(rec['anomalies'])}  n_reconciled_anchors={rec['n_reconciled_anchors']}")
    for k, v in sorted(per.items()):
        print(f"     {k}  {v}")
    print("  ⇒ compare against the ladder's own note, which cites the count it fired on:")
    for r in orders:
        if str(r.get("rebalance_id", "")).startswith("FLATTEN-") and r.get("note"):
            print(f"     {r['note'][:110]}")
            break

    if trades_cache:
        print("\n=== (a) VENUE trade record vs our orders ledger ===")
        tr = json.load(open(trades_cache))
        venue = defaultdict(float)
        for s, v in tr.items():
            for t, q, p in v:
                venue[time.strftime("%Y%m%d", time.gmtime(t / 1000))] += abs(q * p)
        tv = to = 0.0
        for d in sorted(set(list(venue) + list(by_day))):
            vv, oo = venue.get(d, 0.0), by_day.get(d, 0.0)
            tv += vv
            to += oo
            print(f"  {d}  venue ${vv:12,.0f}   ours ${oo:12,.0f}   unrecorded ${vv-oo:11,.0f}"
                  f"   {((vv-oo)/vv*100) if vv else 0:6.1f}%")
        print(f"  TOTAL     venue ${tv:12,.0f}   ours ${to:12,.0f}   unrecorded ${tv-to:11,.0f}"
              f"   {(tv-to)/tv*100:6.1f}%")




def collector_signature(runlog="/Users/haosiyu/dl_quant_live/state/anchor_runs.log"):
    """★ THE SIGNATURE, and the one-line assertion nobody has pointed at it.

    `phase_B` reports `already_terminal` (orders that reached a terminal state at the venue) and
    `fill_rows_built`. Orders reaching terminal state with ZERO fill rows built means the
    collector saw nothing — while the sibling field `n_trades_unattributed: 0` reads as success,
    because "no trade went unattributed" is true when no trade was collected at all.

    ⇒ `already_terminal > 0 and fill_rows_built == 0` would have fired at the moment of each
      incident, before §4-5b tripped and before the ladder flattened.
    """
    import re
    txt = open(runlog).read()
    lives = {}
    for m in re.finditer(r"^\S+ phase_A: (\{.*)$", txt, re.M):
        try:
            d = json.loads(m.group(1))
            lives[d.get("rebalance_id")] = d.get("n_live")
        except Exception:
            pass
    print("\n=== fill-collector signature per live anchor ===")
    print(" anchor        n_live  already_terminal  fill_rows_built  n_trades_unattributed")
    for m in re.finditer(r"^\S+ phase_B: (\{.*)$", txt, re.M):
        try:
            d = json.loads(m.group(1))
        except Exception:
            continue
        rid = d.get("rebalance_id", "")
        if not rid.startswith("A") or not lives.get(rid):
            continue
        term = d.get("k_cancel", {}).get("already_terminal", 0)
        built = d.get("fill_rows_built", 0)
        flag = "  <<< terminal orders, ZERO fill rows" if (term > 0 and built == 0) else ""
        print(f"  {time.strftime('%m-%dT%H:%MZ', time.gmtime(int(rid[1:])))}  {lives[rid]:5d}"
              f"   {term:9d}      {built:10d}   {d.get('n_trades_unattributed', 0):9d}{flag}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
    collector_signature()
