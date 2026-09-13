#!/usr/bin/env python3
"""t7_pull_binance_gaps.py — inventory of hours missing inside the Binance futures/um indexPriceKlines 1h MONTHLY zips that were pulled (no fill is performed).
Per symbol: expected hours = every hour between the symbol's first and last stored bar; missing hours grouped into UTC days; split into days inside vs outside the
symbol's C0-eligible window. --probe N: requests the DAILY zip for the N most common missing days of 1000PEPEUSDT/BTCUSDT-like liquid symbols to state whether a
daily-file fill would be possible (<= N requests, t7_http2 limiter, log logs/http_binance_gapprobe.jsonl). Output <root>/checks/BINANCE_ARCHIVE_GAPS.json."""
import os, sys, json, time, calendar, collections, argparse, hashlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--probe", type=int, default=0); A = ap.parse_args(); ROOT = A.root
PLAN = json.load(open(ROOT + "/plan/PULL_PLAN_FROZEN.json"))
def ep(s): return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
out = {"device": os.path.basename(__file__), "symbols": {}, "missing_days_by_date": {}}
bydate = collections.Counter(); tot_in = tot_out = 0; sym_with_gap = 0
for b in PLAN["binance"]:
    s = b["symbol"]; p = ROOT + "/derived/binance/%s.npz" % s
    if not os.path.exists(p): out["symbols"][s] = {"status": "NO_DERIVED"}; continue
    o = np.load(p)["open_s"]; have = set(o.tolist())
    allh = range(int(o.min()), int(o.max()) + 1, 3600); miss = [h for h in allh if h not in have]
    ef, el = ep(b["elig_first_utc"]), ep(b["elig_last_utc"])
    days = sorted({(h // 86400) * 86400 for h in miss})
    din = [d for d in days if ef - 86400 <= d <= el]; dout = [d for d in days if not (ef - 86400 <= d <= el)]
    if miss: sym_with_gap += 1
    for d in days: bydate[time.strftime("%Y-%m-%d", time.gmtime(d))] += 1
    tot_in += len(din); tot_out += len(dout)
    out["symbols"][s] = {"n_missing_hours": len(miss), "missing_days_in_elig": [time.strftime("%Y-%m-%d", time.gmtime(d)) for d in din], "n_missing_days_outside_elig": len(dout)}
out["summary"] = {"n_symbols": len(PLAN["binance"]), "n_symbols_with_missing_hours": sym_with_gap, "symbol_days_missing_inside_elig": tot_in, "symbol_days_missing_outside_elig": tot_out,
                  "distinct_missing_dates": len(bydate), "top_missing_dates": bydate.most_common(20)}
if A.probe:
    import t7_http2 as H
    probes = []
    for date, _ in bydate.most_common(A.probe):
        cand = next(s for s, x in out["symbols"].items() if isinstance(x, dict) and date in x.get("missing_days_in_elig", []))
        url = "https://data.binance.vision/data/futures/um/daily/indexPriceKlines/%s/1h/%s-1h-%s.zip" % (cand, cand, date)
        st, hdr, body = H.get(url, ROOT + "/logs/http_binance_gapprobe.jsonl", "gapprobe")
        probes.append({"date": date, "symbol": cand, "url": url, "status": st, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
    out["daily_zip_probe"] = probes
json.dump(out, open(ROOT + "/checks/BINANCE_ARCHIVE_GAPS.json", "w"), indent=1)
print(json.dumps(out["summary"], indent=1)); print(json.dumps(out.get("daily_zip_probe"), indent=1))
