#!/usr/bin/env python3
"""Shadow replay of the flow-window caliber on the REAL LIVE daily_nav rows (read-only, offline, no venue call).

For every real daily_nav row (2026-08-01 .. 2026-09-19 00:44Z) it writes the `flow_window` record the NEW writer would
have written — day pull = every income row of the research's COMPLETE read-only income dump in [00:00Z, nav_ts + 3 s],
gap pull = [floor(previous day's last nav_ts), 00:00Z − 1], valuation = USDTUSD / BNBUSD 1m index klines at nav_ts
(point rule of the research cache) × (1 − bidBuffer 1e-4 / 0.05), multiAssetsMargin = true — into a COPY of the ledger,
then runs the fixed watchdog (worktree at the fix commit) and compares per day with the 409ea16 B32 formula.

Declared: multiAssetsMargin true for the whole period (measured true 2026-09-19 only; the research's independent
cash-identity track is consistent with USD throughout); the real pull time is unknown, nav_ts + 3 s stands in for it
(the identity check reports any row where that matters); bidBuffers constant (research §6-2).
usage: replay_real_ledger.py <fixed_repo_root> <pilot_log_root> <income_dump.json> <index_ohlc_cache.json> <out.json>
"""
import calendar, json, math, os, shutil, sys, tempfile, time

FIX, PLROOT, INCOME, OHLC, OUT = sys.argv[1:6]
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(FIX, "live"))
import flow_window as FW      # noqa: E402
import pilot_log as PL        # noqa: E402
import watchdog as WD         # noqa: E402

inc = json.load(open(INCOME))
assert inc.get("completeness") == "COMPLETE", inc.get("completeness")
rows_inc = inc["body"]
dump_end_ms = int(inc["endTime"])
kl = json.load(open(OHLC))["klines"]


def MS(t):
    return int(math.floor(t * 1000.0))


def DS(day):
    return int(calendar.timegm(time.strptime(day, "%Y%m%d")) * 1000)


def idx_at(pair, ts):
    m = int(ts // 60) * 60 * 1000
    k = kl[pair].get(str(m))
    if k is None:
        return None
    o, h, l, c = (float(x) for x in k)
    return o + (c - o) * ((ts - m / 1000.0) / 60.0)


days = [d for d in PL.available_days(PLROOT) if "20260801" <= d <= "20260919"]
real = []
for d in days:
    for r in PL.read_day(PLROOT, d).get("daily_nav", []):
        if r.get("mode") == "LIVE" and r.get("nav_ts") and MS(r["nav_ts"] + 3.0) <= dump_end_ms:
            real.append((d, r))
tmp = tempfile.mkdtemp(prefix="fw_replay_")
prev_last = {}
last_by_day = {}
for d, r in real:
    last_by_day[d] = r
out_rows, prev_day_last_ts = [], None
by_day = {}
for d, r in real:
    by_day.setdefault(d, []).append(r)
pdays = sorted(by_day)
for i, d in enumerate(pdays):
    prev_ts = by_day[pdays[i - 1]][-1]["nav_ts"] if i > 0 else None
    for r in by_day[d]:
        t = float(r["nav_ts"])
        ds = DS(d)
        day_rows = [x for x in rows_inc if ds <= int(x["time"]) <= MS(t + 3.0)]
        gs = MS(prev_ts) if prev_ts is not None else None
        gap_rows = [x for x in rows_inc if gs is not None and gs <= int(x["time"]) <= ds - 1]
        u, b = idx_at("USDTUSD", t), idx_at("BNBUSD", t)
        val = {"read_ts": t, "multi_assets_margin": True, "multi_assets_margin_error": None, "rates_error": None,
               "rates": {k: {"index": v, "bid_rate": v * (1 - buf), "time_ms": MS(t)}
                         for k, v, buf in (("USDT", u, 1e-4), ("BNB", b, 0.05)) if v is not None}}
        rec = FW.build_record(day_start_ms=ds,
                              day_pull={"rows": day_rows, "truncated": False, "start_ms": ds, "end_ms": None},
                              day_pull_error=None, day_requested_ms=MS(t + 3.0), gap_start_ms=gs,
                              gap_pull=({"rows": gap_rows, "truncated": False, "start_ms": gs, "end_ms": ds - 1}
                                        if gs is not None else None),
                              gap_pull_error=None, valuation=val, valuation_error=None)
        r2 = dict(r)
        r2[FW.RECORD_KEY] = rec
        os.makedirs(os.path.join(tmp, d), exist_ok=True)
        with open(os.path.join(tmp, d, "daily_nav.jsonl"), "a") as fh:
            fh.write(json.dumps(r2) + "\n")

ev = WD.evaluate(tmp, venue_events=[], ops_stats=[])
c2, c4 = ev["conditions"]["cond2_day_loss"], ev["conditions"]["cond4_drawdown"]
new = {x["day"]: x for x in c2.get("flow_window_days") or []}

# the 409ea16 B32 reading, per day, from the SAME real rows (legacy branch order: truncated, transfer, prev close, intraday)
old, prev_nav = {}, None
for d in pdays:
    nav = by_day[d]
    n0 = nav[-1]
    flow = any(abs(float(x.get("external_flow_usdt") or 0.0)) > 1e-9 for x in nav)
    if n0.get("realised_truncated"):
        old[d] = ("UNKNOWN", "truncated")
    elif flow:
        old[d] = ("UNKNOWN", "transfer day")
    elif prev_nav not in (None, 0, 0.0):
        old[d] = ("PRICED", (float(n0["nav"]) - prev_nav) / prev_nav * 100.0)
    else:
        old[d] = ("PRICED", (float(n0["nav"]) - float(nav[0]["nav"])) / float(nav[0]["nav"]) * 100.0)
    prev_nav = float(n0["nav"])

table = []
for d in pdays:
    n = new.get(d, {})
    o = old[d]
    table.append({"day": d, "old_state": o[0], "old_pct_or_why": o[1], "new_state": n.get("state"),
                  "new_pct": n.get("pct"), "new_basis": n.get("basis"), "flow_usdt_eq": n.get("flow_usdt_eq"),
                  "flow_events": n.get("flow_events"), "new_reasons": n.get("reasons"),
                  "diff_pp": (n.get("pct") - o[1]) if (o[0] == "PRICED" and n.get("state") == "PRICED") else None})
both = [x["diff_pp"] for x in table if x["diff_pp"] is not None]
summary = {"n_days": len(table), "n_rows": len(real), "last_row_nav_ts": real[-1][1]["nav_ts"],
           "old_priced": sum(x["old_state"] == "PRICED" for x in table),
           "new_priced": sum(x["new_state"] == "PRICED" for x in table),
           "new_unknown": [(x["day"], x["new_reasons"]) for x in table if x["new_state"] != "PRICED"],
           "old_unknown_now_priced": [(x["day"], x["new_pct"], x["flow_usdt_eq"]) for x in table
                                      if x["old_state"] != "PRICED" and x["new_state"] == "PRICED"],
           "both_priced_n": len(both), "both_priced_max_abs_diff_pp": max((abs(v) for v in both), default=None),
           "cond2_now": {k: c2.get(k) for k in ("recent_day", "recent_day_pct", "triggered", "blind")},
           "cond4_now": {k: c4.get(k) for k in ("cum_return_from_start_pct", "max_drawdown_from_peak_pct_INFO",
                                                "chain_broken", "blind")},
           "cond4_flow_window_days_transfer_possible": [x["day"] for x in c4.get("flow_window_days") or []
                                                        if x.get("transfer_possible")],
           "tripped": ev.get("tripped"), "triggers": ev.get("triggers"), "metric_errors": ev.get("metric_errors")}
json.dump({"device": os.path.abspath(__file__), "fix_root": FIX, "summary": summary, "per_day": table},
          open(OUT, "w"), indent=1, default=str)
shutil.rmtree(tmp, ignore_errors=True)
print(json.dumps(summary, indent=1, default=str)[:6000])
