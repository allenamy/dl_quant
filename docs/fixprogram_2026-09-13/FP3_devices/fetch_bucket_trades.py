#!/usr/bin/env python3
"""FP3 I-1: the per-fill QUANTITY and PRICE of every protective-flatten bucket, from the venue, read-only.

Closes the first half of the independent review's open item 3 ("the other seven flatten buckets' quantities and
prices"). The realised cash per bucket already came from the income endpoint; what was missing was the fill-level
detail, because the old single-shot trades fetcher declared `completeness: UNPROVEN` on any full page. fetch_trades.py
now pages by `fromId`, so a bucket can be measured rather than declared.

METHOD, and its boundary:
 - the bucket window is the SAME one the published cost table used: [event - 120 s, event + 120 s], where the event is
   the local flatten readback instant. The event instants were recovered by solving for the offset at which the old
   income pull reproduces the published table exactly, so this device changes NOTHING about the attribution rule.
 - the symbol set per bucket is the set of symbols carrying a COMMISSION row inside that window. A symbol that traded
   in the window without a commission row would be missed; that is a stated boundary, not a silent one.
 - every symbol is pulled with `fetch_trades.fetch_trades`, which is complete-by-construction or refuses. If ANY symbol
   in a bucket comes back INCOMPLETE, the bucket's aggregate is written as UNAVAILABLE with the failing symbols named.
   A partial aggregate is not a cash number.
 - the +/-120 s window is an ATTRIBUTION CHOICE, not a venue-supplied event grouping: regular non-flatten trades inside
   the window are included. Unchanged from the published table.

usage: fetch_bucket_trades.py <out.json> [bucket_label ...]   (no labels = all eight)"""
import collections, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch_trades as FT

R = os.path.join(HERE, "..", "FP3_receipts", "venue_readonly_2026-09-18")
# (label, event offset in seconds from the income receipt's startTime, income receipt basename)
BUCKETS = [("0801T2019", 900, "income_bucket_0801T2019"), ("0802T0419", 900, "income_bucket_0802T0419"),
           ("0805T0020", 761, "income_bucket_0805T0020"), ("0805T1219", 900, "income_bucket_0805T1219"),
           ("0821T1217", 900, "income_bucket_0821T1217"), ("0821T2017", 900, "income_bucket_0821T2017_v2"),
           ("0826T1249", 929, "income_bucket_0826T1249_v2"), ("0906T0849", 873, "income_bucket_0906T0849_v2")]
U = lambda ms: time.strftime("%m-%d %H:%M:%SZ", time.gmtime(ms / 1000))


def main():
    out_path = sys.argv[1]
    want = set(sys.argv[2:]) or {b[0] for b in BUCKETS}
    result = {"receipt": "FLATTEN_BUCKET_FILLS", "utc": time.strftime("%FT%TZ", time.gmtime()),
              "device": "fetch_bucket_trades.py", "fetcher": "fetch_trades.py v2 (fromId paging)",
              "window_rule": "[event - 120 s, event + 120 s]; event = the local flatten readback instant, recovered by "
                             "solving for the offset at which the v1 income pull reproduces the published cost table",
              "symbol_rule": "symbols carrying a COMMISSION row inside the window (a symbol trading without a "
                             "commission row would be missed - a stated boundary)",
              "boundary": "the +/-120 s window is an attribution choice, not a venue event grouping; regular "
                          "non-flatten trades inside it are included",
              "buckets": []}
    for label, off, inc in BUCKETS:
        if label not in want: continue
        d = json.load(open(os.path.join(R, inc + ".json")))
        ev = d["startTime"] + off * 1000; lo, hi = ev - 120_000, ev + 120_000
        syms = sorted({r["symbol"] for r in d["body"] if lo <= int(r["time"]) <= hi and r["incomeType"] == "COMMISSION"})
        per, bad, n_fills = {}, [], 0
        gross_abs = qty_signed_notional = fee_usdt = 0.0
        fee_native = collections.Counter()
        t0 = time.time()
        for i, s in enumerate(syms, 1):
            pages, rows, status, why = FT.fetch_trades(s, lo, hi)
            if status != "COMPLETE":
                bad.append({"symbol": s, "reason": why}); per[s] = {"completeness": status, "reason": why}; continue
            n_fills += len(rows)
            g = sum(abs(float(r["quoteQty"])) for r in rows)
            sgn = sum((1.0 if r.get("buyer") else -1.0) * abs(float(r["quoteQty"])) for r in rows)
            q = sum((1.0 if r.get("buyer") else -1.0) * abs(float(r["qty"])) for r in rows)
            vw = (sum(abs(float(r["quoteQty"])) for r in rows) / sum(abs(float(r["qty"])) for r in rows)) if rows and sum(abs(float(r["qty"])) for r in rows) else None
            gross_abs += g; qty_signed_notional += sgn
            for r in rows:
                fee_native[r.get("commissionAsset")] += float(r.get("commission") or 0.0)
                if r.get("commissionAsset") == "USDT": fee_usdt += float(r.get("commission") or 0.0)
            per[s] = {"completeness": "COMPLETE", "n_fills": len(rows), "n_pages": len(pages),
                      "qty_signed": round(q, 8), "gross_notional_usdt": round(g, 6),
                      "signed_notional_usdt": round(sgn, 6),
                      "vwap": (None if vw is None else round(vw, 8)),
                      "realized_pnl_usdt": round(sum(float(r.get("realizedPnl") or 0.0) for r in rows), 6),
                      "maker_fills": sum(1 for r in rows if r.get("maker")),
                      "first_ts": min((int(r["time"]) for r in rows), default=None),
                      "last_ts": max((int(r["time"]) for r in rows), default=None)}
            if i % 25 == 0:
                print(f"    {label} {i}/{len(syms)} ({time.time()-t0:.0f}s)", flush=True)
        agg = {"label": label, "event_utc": U(ev), "event_ms": ev, "window_ms": [lo, hi],
               "n_symbols": len(syms), "n_symbols_incomplete": len(bad), "incomplete": bad,
               "aggregate_status": ("COMPLETE" if not bad else "UNAVAILABLE_partial"),
               "n_fills": (n_fills if not bad else None),
               "gross_notional_usdt": (round(gross_abs, 4) if not bad else None),
               "net_signed_notional_usdt": (round(qty_signed_notional, 4) if not bad else None),
               "realized_pnl_usdt": (round(sum(v.get("realized_pnl_usdt", 0.0) for v in per.values() if v.get("completeness") == "COMPLETE"), 4) if not bad else None),
               "maker_fill_share": (round(sum(v.get("maker_fills", 0) for v in per.values() if v.get("completeness") == "COMPLETE") / n_fills, 4) if (not bad and n_fills) else None),
               "commission_by_asset": {k: round(v, 8) for k, v in sorted(fee_native.items())} if not bad else None,
               "note": ("" if not bad else "a partial aggregate is not a cash number: the bucket total is withheld until every symbol is COMPLETE"),
               "per_symbol": per}
        result["buckets"].append(agg)
        print(f"  {label} {U(ev)}  {len(syms)} syms  {n_fills} fills  status {agg['aggregate_status']}  "
              f"gross {agg['gross_notional_usdt']}  realized {agg['realized_pnl_usdt']}  ({time.time()-t0:.0f}s)", flush=True)
        tmp = out_path + ".part"
        with open(tmp, "w") as fh: json.dump(result, fh, indent=1)
        os.replace(tmp, out_path)                         # checkpoint after each bucket: a long pull never loses work
    print("wrote", out_path)
    return 0 if all(b["aggregate_status"] == "COMPLETE" for b in result["buckets"]) else 3


if __name__ == "__main__":
    sys.exit(main())
