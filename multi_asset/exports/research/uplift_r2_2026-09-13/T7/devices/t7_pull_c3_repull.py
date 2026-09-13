#!/usr/bin/env python3
"""t7_pull_c3_repull.py — re-pull verification of every C3 mismatch market-day (one process per venue; same limiter/transport as the pull).
For each day: 60m candles with `to` = day end (exclusive), count=24, filtered to the day; day candle with `to` = day end, count=1.
Compares with the STORED bars: IDENTICAL (venue serves the same inconsistent data today => venue-side inconsistency), CHANGED (differs => recorded, stored data not replaced),
ERROR (non-200 / non-list). Nothing in the pull root's pages is modified. Output <root>/checks/C3_REPULL_<venue>.json; log <root>/logs/http_c3repull_<venue>.jsonl."""
import os, sys, json, gzip, time, calendar, collections, argparse, urllib.parse, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_http2 as H
ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--venue", required=True, choices=["upbit", "bithumb"]); A = ap.parse_args(); ROOT, V = A.root, A.venue
def ep(s): return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t))
def to_param(t): return urllib.parse.quote(iso(t) + "Z") if V == "upbit" else urllib.parse.quote(iso(t + 9 * 3600))
BASE = {"upbit": "https://api.upbit.com", "bithumb": "https://api.bithumb.com"}[V]; LOG = ROOT + "/logs/http_c3repull_%s.jsonl" % V
DET = json.load(open(ROOT + "/checks/C3_MISMATCH_DETAIL.json"))
days = [x for x in DET["days"] if x["venue"] == V]
man = collections.defaultdict(list)
for l in open(ROOT + "/manifest/pages_%s.jsonl" % V):
    p = json.loads(l)
    if "market" in p: man[(p["market"], p["unit"])].append(p)
stored = {}
def load(mk):
    if mk not in stored:
        d = {"60m": {}, "days": {}}
        for u in ("60m", "days"):
            for p in man[(mk, u)]:
                for c in json.loads(gzip.decompress(open(ROOT + "/" + p["file"], "rb").read())):
                    d[u][ep(c["candle_date_time_utc"])] = (float(c["trade_price"]), float(c["candle_acc_trade_volume"]), c.get("timestamp"))
        stored[mk] = d
    return stored[mk]
res = []; cnt = collections.Counter()
for x in days:
    mk = x["market"]; d0 = ep(x["day_open_utc"]); d1 = d0 + 86400; S = load(mk)
    st1, _, b1 = H.get("%s/v1/candles/minutes/60?market=%s&count=24&to=%s" % (BASE, mk, to_param(d1)), LOG, "c3_60m")
    st2, _, b2 = H.get("%s/v1/candles/days?market=%s&count=1&to=%s" % (BASE, mk, to_param(d1)), LOG, "c3_day")
    try: j1 = json.loads(b1); j2 = json.loads(b2)
    except Exception: j1 = j2 = None
    r = {"market": mk, "day_open_utc": x["day_open_utc"]}
    if st1 != 200 or st2 != 200 or not isinstance(j1, list) or not isinstance(j2, list):
        r["verdict"] = "ERROR"; r["status"] = [st1, st2]; cnt["ERROR"] += 1; res.append(r); continue
    new_h = {ep(c["candle_date_time_utc"]): (float(c["trade_price"]), float(c["candle_acc_trade_volume"]), c.get("timestamp")) for c in j1 if d0 <= ep(c["candle_date_time_utc"]) < d1}
    old_h = {o: v for o, v in S["60m"].items() if d0 <= o < d1}
    new_d = {ep(c["candle_date_time_utc"]): (float(c["trade_price"]), float(c["candle_acc_trade_volume"]), c.get("timestamp")) for c in j2 if ep(c["candle_date_time_utc"]) == d0}
    old_d = {d0: S["days"][d0]} if d0 in S["days"] else {}
    same = new_h == old_h and new_d == old_d
    hv = sum(v[1] for v in new_h.values()); dv = new_d[d0][1] if d0 in new_d else None
    r.update({"verdict": "IDENTICAL" if same else "CHANGED", "n_hourly_new": len(new_h), "n_hourly_stored": len(old_h), "ratio_h_over_d_repulled": (hv / dv) if dv else None,
              "hourly_bars_equal": new_h == old_h, "day_bar_equal": new_d == old_d})
    cnt[r["verdict"]] += 1; res.append(r)
out = {"device": os.path.basename(__file__), "venue": V, "run_utc": H.utc_iso(), "n_days": len(days), "verdicts": dict(cnt), "days": res}
json.dump(out, open(ROOT + "/checks/C3_REPULL_%s.json" % V, "w"), indent=1)
print(V, out["verdicts"])
