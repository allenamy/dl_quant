#!/usr/bin/env python3
"""t7_pull_c3_detail.py — lists EVERY C3 mismatch market-day (the checks receipt keeps only 5 examples per market), no network, no returns.
Per day: hourly-volume sum, day-candle volume, ratio, number of hourly bars in the day, and whether the day is the first or last complete day of the market.
Output <root>/checks/C3_MISMATCH_DETAIL.json."""
import os, json, gzip, hashlib, calendar, time, collections, argparse
ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); A = ap.parse_args(); ROOT = A.root
_pb = open(ROOT + "/plan/PULL_PLAN_FROZEN.json", "rb").read(); assert hashlib.sha256(_pb).hexdigest() == open(ROOT + "/plan/PULL_PLAN_FROZEN.json.sha256").read().split()[0]
PLAN = json.loads(_pb); PULL_END, CUTOFF = PLAN["pull_end_epoch"], PLAN["cutoff_epoch"]
def ep(s): return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))
CH = json.load(open(ROOT + "/checks/CHECKS_T7_pull.json")); OFF = {"upbit": 0, "bithumb": 15 * 3600}
out = {"device": os.path.basename(__file__), "days": []}
for V in ("upbit", "bithumb"):
    first = {m["market"]: m["first_day_epoch"] for m in PLAN["krw"][V]}
    man = collections.defaultdict(list)
    for l in open(ROOT + "/manifest/pages_%s.jsonl" % V):
        p = json.loads(l)
        if "market" in p: man[(p["market"], p["unit"])].append(p)
    for mk in CH["venues"][V]["fail_lists"].get("C3", []):
        bars = {}
        for unit in ("60m", "days"):
            d = {}
            for p in man[(mk, unit)]:
                for c in json.loads(gzip.decompress(open(ROOT + "/" + p["file"], "rb").read())):
                    d[ep(c["candle_date_time_utc"])] = float(c["candle_acc_trade_volume"])
            bars[unit] = d
        h, dd, off = bars["60m"], bars["days"], OFF[V]; lo = max(first[mk], CUTOFF)
        hs = collections.defaultdict(float); hn = collections.Counter()
        for o, vol in h.items():
            d0 = ((o - off) // 86400) * 86400 + off; hs[d0] += vol; hn[d0] += 1
        keys = sorted(set(k for k in dd if k >= lo and k + 86400 <= PULL_END) | set(k for k in hs if k >= lo and k + 86400 <= PULL_END))
        complete = [k for k in keys]
        for d0 in keys:
            hv, dv = hs.get(d0), dd.get(d0)
            if hv is None or dv is None or abs(hv - dv) / max(abs(dv), 1e-12) > 1e-6:
                out["days"].append({"venue": V, "market": mk, "day_open_utc": iso(d0), "hourly_sum": hv, "day_volume": dv, "ratio_h_over_d": (hv / dv) if (hv is not None and dv) else None,
                                    "n_hourly_bars": hn.get(d0, 0), "is_first_checked_day": d0 == complete[0], "is_last_checked_day": d0 == complete[-1]})
S = collections.defaultdict(collections.Counter)
for x in out["days"]:
    v = x["venue"]; S[v]["days"] += 1
    r = x["ratio_h_over_d"]
    S[v]["no_hourly" if x["hourly_sum"] is None else ("no_day_bar" if x["day_volume"] is None else ("hourly_lt_day" if r < 1 else "hourly_gt_day"))] += 1
    S[v]["first_day"] += x["is_first_checked_day"]; S[v]["last_day"] += x["is_last_checked_day"]
bydate = collections.defaultdict(collections.Counter)
for x in out["days"]: bydate[x["venue"]][x["day_open_utc"][:10]] += 1
out["summary"] = {v: dict(S[v]) for v in S}; out["top_dates"] = {v: bydate[v].most_common(15) for v in bydate}
out["by_year"] = {v: dict(collections.Counter(x["day_open_utc"][:4] for x in out["days"] if x["venue"] == v)) for v in ("upbit", "bithumb")}
json.dump(out, open(ROOT + "/checks/C3_MISMATCH_DETAIL.json", "w"), indent=1)
print(json.dumps({k: out[k] for k in ("summary", "top_dates", "by_year")}, indent=1))
import statistics
for v in ("upbit", "bithumb"):
    rs = [x["ratio_h_over_d"] for x in out["days"] if x["venue"] == v and x["ratio_h_over_d"] is not None]
    if rs: print(v, "ratio h/d: min %.4f p10 %.4f median %.4f p90 %.4f max %.4f" % (min(rs), sorted(rs)[len(rs)//10], statistics.median(rs), sorted(rs)[9*len(rs)//10], max(rs)))
    print(v, "examples", [(x["market"], x["day_open_utc"][:10], x["n_hourly_bars"], round(x["ratio_h_over_d"], 4) if x["ratio_h_over_d"] else None) for x in out["days"] if x["venue"] == v][:12])
