"""W9 08Z fact: rebuild the 2026-09-13 08:00Z (rid A1789287840) withhold/reshape from the live tree, READ-ONLY."""
import json, re, calendar, time, collections, os, sys
import numpy as np
LIVE = "/Users/haosiyu/dl_quant_live"; A = 1789286400; RID = "A1789287840"
def G(t): return int(float(t) // 14400) * 14400
pa = None
pat = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) (.*)$")
for ln in open(LIVE + "/state/anchor_runs.log", errors="replace"):
    m = pat.match(ln.rstrip("\n"))
    if not m: continue
    rest = m.group(2)
    if rest.startswith("phase_A: "):
        try:
            d = json.loads(rest[len("phase_A: "):])
        except Exception:
            continue
        if d.get("anchor_ts") and G(d["anchor_ts"]) == A and d.get("rebalance_id", RID) == RID:
            pa = d
print("phase_A found:", pa is not None, "keys:", sorted(pa.keys())[:40] if pa else None)
eb = pa.get("external_book") or {}
S = float(pa["sizing"]["gross"]); gin = float(eb["gross_in"])
print("sizing gross", S, "gross_in", gin, "untradable_names", {k: (len(v), v[:12]) for k, v in (pa.get("untradable_names") or {}).items()})
print("external_book keys:", sorted(eb.keys()))
arow = [json.loads(l) for l in open(LIVE + "/state/live/pilot_log/20260913/anchors.jsonl") if RID in l][-1]
rs = arow["reshape"]; tg = float(arow["target_gross"])
rows = [json.loads(l) for l in open(LIVE + "/state/live/pilot_log/20260913/orders.jsonl") if RID in l]
w = json.load(open(f"/Users/haosiyu/wide_shadow/state/target_live/{A}.json"))["weights"]
floors = json.load(open(LIVE + "/state/live/exchange_info_cache.json"))
names = sorted({r["symbol"] for r in rows})
popped = rs["popped_names"]
P = [s for s in names if float(w.get(s, 0.0)) != 0.0]
print("rows", len(rows), "names with rows", len(names), "|P|", len(P), "popped", len(popped), "popped with file weight", [s for s in popped if float(w.get(s, 0.0)) != 0.0])
print("terminal reasons", collections.Counter(r.get("terminal_reason") for r in rows).most_common(6))
vec = np.array([float(w[s]) / gin for s in P]); nb = float(vec.sum()) * S
print("net_before rebuilt", round(nb, 6), "ledger", rs["net_before"])
v2 = vec - vec.mean(); v2 = v2 / np.abs(v2).sum()
T = {s: float(v2[i]) * S for i, s in enumerate(P)}
fl = {s: float((floors.get(s) or {}).get("min_notional", 0.0) or 0.0) for s in P}
before = {s for s in P if abs(float(w[s]) / gin) * S >= fl[s]}
after = {s for s in P if abs(T[s]) >= fl[s]}
print("crossed floor (rebuilt):", sorted(before ^ after), "ledger:", rs["names_crossed_floor"])
for s in sorted(before ^ after):
    print("   ", s, "before", round(float(w[s]) / gin * S, 4), "after", round(T[s], 4), "floor", fl[s])
rec = {}
for r in rows:
    if r.get("target_w") is not None and (r.get("order_type") == "maker" or r["symbol"] not in rec):
        rec[r["symbol"]] = float(r["target_w"]) * tg
diffs = sorted(((abs(T[s] - rec[s]), s) for s in P if s in rec), reverse=True)
print("worst |T_rebuilt - T_recorded| (top 5, cap clamps expected among them):", [(s, round(d, 4)) for d, s in diffs[:5]])
print("names matching ≤1e-6:", sum(1 for d, s in diffs if d <= 1e-6), "of", len(diffs))
a = -vec.mean() / np.abs(vec - vec.mean()).sum() * S
print("uniform shift a (USDT) =", round(a, 4), "scale b =", round(1 / (np.abs(vec - vec.mean()).sum() * gin), 6))
