#!/usr/bin/python3
"""Census: which fields did the top-up leg inherit from its maker sibling, and what does the
duplicate do to every consumer that sums filled_notional. Read-only."""
import json, os, sys, collections

REPO = "/Users/haosiyu/dl_quant_live"
for d in ("live", "ops", "signal"):
    sys.path.insert(0, os.path.join(REPO, d))
import pilot_log as PL, pilot_metrics as PM, state_root as SR

root = SR.paths_for("TESTNET")["pilot_log"]
day = "20260726"
data = PL.read_day(root, day)
orders = data["orders"]
RID = "A1785067246"
mine = [o for o in orders if o.get("rebalance_id") == RID]
mk = {o["symbol"]: o for o in mine if o["order_type"] == "maker"}
tu = {o["symbol"]: o for o in mine if o["order_type"] == "topup_taker"}

FIELDS = ["filled_notional", "avg_fill_px", "first_fill_ts", "last_fill_ts", "fee_paid",
          "submit_ts", "price_submit", "mid_at_submit", "mid_at_anchor", "intended_notional"]
print("=== LEG-FIELD INHERITANCE CENSUS (103 names with both legs) ===")
print(f"{'field':18s} {'identical':>10s} {'differ':>7s} {'topup None':>11s} {'maker None':>11s}")
for f in FIELDS:
    same = diff = tn = mn = 0
    for s, t in tu.items():
        m = mk.get(s)
        if m is None:
            continue
        a, b = m.get(f), t.get(f)
        if b is None:
            tn += 1
        if a is None:
            mn += 1
        if a is not None and b is not None:
            if a == b:
                same += 1
            else:
                diff += 1
    print(f"{f:18s} {same:10d} {diff:7d} {tn:11d} {mn:11d}")

print("\n=== TOPUP ROWS WHOSE terminal_reason SAYS THEY NEVER TRADED, YET CARRY A FILL ===")
NEVER = {"abandoned_max_attempts", "skipped_min_notional", "skipped_no_mid", "venue_reject",
         "blocked_by_halt", "skipped_unknown_fill"}
bad = [t for t in tu.values()
       if t.get("terminal_reason") in NEVER
       and t.get("filled_notional") not in (None,) and float(t["filled_notional"]) != 0.0]
print(f"  n = {len(bad)}   by terminal_reason: "
      f"{dict(collections.Counter(b['terminal_reason'] for b in bad))}")
eq_sib = sum(1 for b in bad if mk.get(b["symbol"], {}).get("filled_notional") == b["filled_notional"])
print(f"  of which filled_notional is BIT-IDENTICAL to the maker sibling: {eq_sib}/{len(bad)}")
print(f"  duplicated |notional| carried by those rows: "
      f"{sum(abs(float(b['filled_notional'])) for b in bad):.2f}")

print("\n=== WHAT THE DUPLICATE DOES TO c (m1) ===")
regimes = {a["anchor_ts"]: a["regime_at_anchor"] for a in data.get("anchors", [])}
m1_all = PM.m1_effective_cost(mine, regimes)
print(f"  as-logged, rebalance {RID}: c={m1_all.get('c_bps_overall')} bps  "
      f"denominator={m1_all.get('filled_notional_total') or m1_all.get('denominator')}")
badset = {id(b) for b in bad}
clean = [o for o in mine if id(o) not in badset]
m1_cl = PM.m1_effective_cost(clean, regimes)
print(f"  phantom topup fills removed  : c={m1_cl.get('c_bps_overall')} bps  "
      f"denominator={m1_cl.get('filled_notional_total') or m1_cl.get('denominator')}")
print("  full m1 (as-logged):", json.dumps(m1_all, default=str)[:600])

print("\n=== DAY-LEVEL c (what cond1's 11.6681 is made of) ===")
day_rows = orders
by_type = collections.Counter(o["order_type"] for o in day_rows)
print("  day order rows by type:", dict(by_type))
m1_day = PM.m1_effective_cost([o for o in day_rows], regimes)
print(f"  m1 over ALL day rows        : c={m1_day.get('c_bps_overall')} bps")
day_clean = [o for o in day_rows if id(o) not in badset]
print(f"  m1 with phantom rows removed: c={PM.m1_effective_cost(day_clean, regimes).get('c_bps_overall')} bps")
pf = [o for o in day_rows if o["order_type"] == "protective_flatten"]
print(f"  protective_flatten rows in day: {len(pf)}  "
      f"(all filled_notional None: {all(o.get('filled_notional') is None for o in pf)})")
print("  ⇒ m1 universe is", getattr(PM, "M1_UNIVERSE", "see pilot_metrics.m1_effective_cost"))
