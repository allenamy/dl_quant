"""Read-only census of numeric-field states on the W2 clone's ledger copy (state/live/pilot_log)."""
import glob, json, math, os, collections, sys
ROOT = sys.argv[1]
def state(v, present=True):
    if not present: return "absent"
    if v is None: return "None"
    if isinstance(v, bool): return "bool"
    if isinstance(v, (int, float)):
        if not math.isfinite(float(v)): return "nonfinite"
        return "zero" if float(v) == 0.0 else "finite"
    return "other:" + type(v).__name__
fields = {
    "daily_nav": ["nav", "wallet_balance", "unrealised_pnl", "external_flow_usdt", "target_gross"],
    "anchors": ["target_gross"],
    "orders": ["intended_notional"],
    "position_readback": ["venue_position_notional", "venue_position_qty"],
}
cnt = {t: {f: collections.Counter() for f in fs} for t, fs in fields.items()}
maker_intent = collections.Counter()
days_last_flow = collections.Counter()
nrows = collections.Counter()
for d in sorted(glob.glob(os.path.join(ROOT, "*"))):
    for t, fs in fields.items():
        p = os.path.join(d, t + ".jsonl")
        if not os.path.exists(p): continue
        rows = [json.loads(l) for l in open(p) if l.strip()]
        nrows[t] += len(rows)
        for r in rows:
            for f in fs:
                cnt[t][f][state(r.get(f), f in r)] += 1
            if t == "orders" and r.get("order_type") == "maker":
                maker_intent[(state(r.get("intended_notional"), "intended_notional" in r), r.get("submit_ts") is not None)] += 1
        if t == "daily_nav" and rows:
            by = {}
            for r in rows:
                by[r.get("day")] = r
            for day, r in by.items():
                days_last_flow[state(r.get("external_flow_usdt"), "external_flow_usdt" in r)] += 1
print("rows:", dict(nrows))
for t in cnt:
    for f in cnt[t]:
        print(f"{t}.{f}: {dict(cnt[t][f])}")
print("maker intended_notional (state, submitted):", dict(maker_intent))
print("daily_nav last-row-of-file external_flow state:", dict(days_last_flow))
