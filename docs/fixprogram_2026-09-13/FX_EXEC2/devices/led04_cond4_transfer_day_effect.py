#!/usr/bin/python3
"""LED-04 consequence check (read-only): the watchdog's §4-4 cumulative equity return (cond4 cum_return_from_start_pct)
prices a TRANSFER day as (realised_pnl + unrealised - unrealised_prev) / nav_prev from the day's LAST daily_nav row —
so it consumes the pre-fix realised_pnl that LED-04 shows is under-recorded. This re-implements that chain exactly as
watchdog.py:1533-1600 does (last row per day, realised_truncated days withheld, a day with any external_flow is a
transfer day), first with the recorded realised_pnl (must reproduce the live last_eval value given as argv[3]) and then
with the amended USDT realised total of each pre-fix transfer day's last row. Writes argv[4] only.
Usage: led04_cond4_transfer_day_effect.py <pilot_log_root_copy> <amendments.jsonl> <live_last_eval_cum_pct> <receipt.json>"""
import json, os, sys
ROOT, AMEND, LIVE_CUM, OUT = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
am = {}
for l in open(AMEND):
    a = json.loads(l); am[(a["day"], a["line"])] = a
prev, cum, cum_am, rows = None, 1.0, 1.0, []
for d in sorted(x for x in os.listdir(ROOT) if x.isdigit()):
    p = os.path.join(ROOT, d, "daily_nav.jsonl")
    if not os.path.exists(p): continue
    L = [json.loads(x) for x in open(p) if x.strip()]
    last, li = L[-1], len(L)
    flow = any(abs(float(r.get("external_flow_usdt") or 0)) > 1e-9 for r in L)
    if last.get("realised_truncated"):
        continue
    if prev is not None:
        if flow:
            re_, un = float(last["realised_pnl"]), float(last["unrealised_pnl"])
            a = am.get((d, li)); re_am = a["amended"]["realised_pnl_usdt"] if a else re_
            rd, rd_am = (re_ + un - float(prev[1])) / prev[0], (re_am + un - float(prev[1])) / prev[0]
            rows.append({"day": d, "nav_prev": prev[0], "realised_recorded": re_, "realised_amended_usdt": re_am,
                         "r_recorded_pct": rd * 100, "r_amended_pct": rd_am * 100, "amended": bool(a)})
        else:
            rd = rd_am = float(last["nav"]) / prev[0] - 1.0
        cum *= 1 + rd; cum_am *= 1 + rd_am
    prev = (float(last["nav"]), last.get("unrealised_pnl"))
res = {"cum_recorded_pct": round((cum - 1) * 100, 4), "live_last_eval_cum_pct": LIVE_CUM,
       "reproduces_live": abs(round((cum - 1) * 100, 4) - LIVE_CUM) < 1e-9,
       "cum_with_amended_realised_pct": round((cum_am - 1) * 100, 4),
       "understatement_pp": round((cum - cum_am) * 100, 4), "transfer_days": rows}
json.dump(res, open(OUT, "w"), indent=1)
print("LED04_COND4", {k: res[k] for k in ("cum_recorded_pct", "live_last_eval_cum_pct", "reproduces_live", "cum_with_amended_realised_pct", "understatement_pp")})
