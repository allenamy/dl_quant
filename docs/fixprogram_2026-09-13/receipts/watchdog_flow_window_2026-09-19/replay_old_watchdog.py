#!/usr/bin/env python3
"""The 409ea16 watchdog's own reading of the same real rows, day by day (tree truncated at each day), to check the
replay's hand-coded legacy column against the real legacy code, and §4-4 on the full tree. Read-only, offline.
usage: replay_old_watchdog.py <old_repo_root> <pilot_log_root> <max_nav_ts> <replay_json> <out.json>"""
import json, os, shutil, sys, tempfile

OLD, PLROOT, MAXTS, REPLAY, OUT = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4], sys.argv[5]
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(OLD, "live"))
import pilot_log as PL      # noqa: E402
import watchdog as WD       # noqa: E402
assert not hasattr(WD, "FW"), "this must be the pre-fix watchdog"

days = [d for d in PL.available_days(PLROOT) if "20260801" <= d <= "20260919"]
rows = {}
for d in days:
    rs = [r for r in PL.read_day(PLROOT, d).get("daily_nav", []) if r.get("mode") == "LIVE" and r.get("nav_ts")
          and float(r["nav_ts"]) <= MAXTS]
    if rs:
        rows[d] = rs
rep = {x["day"]: x for x in json.load(open(REPLAY))["per_day"]}
per_day, mism = [], []
pd = sorted(rows)
for i, d in enumerate(pd):
    tmp = tempfile.mkdtemp(prefix="old_replay_")
    for dd in pd[: i + 1]:
        os.makedirs(os.path.join(tmp, dd))
        with open(os.path.join(tmp, dd, "daily_nav.jsonl"), "w") as fh:
            for r in rows[dd]:
                fh.write(json.dumps(r) + "\n")
    ev = WD.evaluate(tmp, venue_events=[], ops_stats=[])
    c2 = ev["conditions"]["cond2_day_loss"]
    got = c2.get("recent_day_pct") if c2.get("recent_day") == d else None
    hand = rep[d]["old_pct_or_why"] if rep[d]["old_state"] == "PRICED" else None
    ok = (got is None and hand is None) or (got is not None and hand is not None and abs(got - hand) < 1e-9)
    if not ok:
        mism.append((d, got, hand))
    per_day.append({"day": d, "old_watchdog_recent_day_pct": got, "old_unpriced": c2.get("latest_equity_day_unpriced_reason")})
    if i == len(pd) - 1:
        c4 = ev["conditions"]["cond4_drawdown"]
        cond4 = {k: c4.get(k) for k in ("cum_return_from_start_pct", "max_drawdown_from_peak_pct_INFO", "chain_broken", "blind")}
    shutil.rmtree(tmp, ignore_errors=True)
res = {"n_days": len(pd), "hand_vs_old_watchdog_mismatches": mism, "old_cond4_full_tree": cond4, "per_day": per_day}
json.dump(res, open(OUT, "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in res.items() if k != "per_day"}, indent=1, default=str))
