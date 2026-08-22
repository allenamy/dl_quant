"""探针读数器(v2 副本): events.jsonl → 分币成交率/点差/markout(轮末中价 vs 成交价)/错误谱. 与 v1 analyze.py 同逻辑,
只把事件文件路径改为 v2 目录(可用 PROBE_EV 覆盖). v2 事件字段与 v1 兼容(place/status/cancel/flatten/round_end_mid)."""
import json, collections, math, os
EV = os.path.expanduser(os.environ.get("PROBE_EV", "~/exec_probe/v2/events.jsonl"))
rows = [json.loads(l) for l in open(EV)]
place = [r for r in rows if r["e"] == "place"]
status = [r for r in rows if r["e"] == "status"]
fills = [r for r in status if r.get("status") == "FILLED" or (r.get("executedQty") and float(r.get("executedQty") or 0) > 0)]
partial = [r for r in status if r.get("status") == "PARTIALLY_FILLED"]
errs = [r for r in rows if r["e"] in ("place",) and r.get("err")]
mids = {}
for r in rows:
    if r["e"] == "round_end_mid":
        mids.setdefault(r["symbol"], []).append((r["ts"], r["mid"]))
by_key = collections.defaultdict(lambda: {"placed": 0, "filled": 0, "partial": 0, "mkout": []})
for r in status:
    key = (r.get("arm", "base"), r["symbol"])
    by_key[key]["placed"] += 1
    eq = float(r.get("executedQty") or 0)
    if r.get("status") == "FILLED":
        by_key[key]["filled"] += 1
    elif eq > 0:
        by_key[key]["partial"] += 1
    if eq > 0 and r.get("avgPrice"):
        ap = float(r["avgPrice"])
        cands = [m for t, m in mids.get(r["symbol"], []) if t > r["ts"]]
        if cands and ap > 0:
            mid = cands[0]
            sgn = 1 if r["side"] == "BUY" else -1
            by_key[key]["mkout"].append(sgn * (mid - ap) / ap * 1e4)
print(f"总挂单 {len(status)}  全成 {len(fills)}  部分 {len(partial)}  下单错误 {len(errs)}")
for arm in ("base", "xl"):
    rows = [(s, d) for (a, s), d in sorted(by_key.items()) if a == arm]
    if not rows: continue
    print(f"--- {arm} 臂 ---")
    for s, d in rows:
        fr = (d["filled"] + 0.5 * d["partial"]) / max(d["placed"], 1)
        mk = f"{sum(d['mkout'])/len(d['mkout']):+.1f}bps(n{len(d['mkout'])})" if d["mkout"] else "--"
        print(f"  {s:>12s} 成交率 {fr:.2f} ({d['filled']}全+{d['partial']}部/{d['placed']}) markout {mk}")
if errs:
    print("错误样本:", errs[:3])
foreign = [r for r in rows if r["e"] == "foreign_position_detected"]
print(f"foreign_position_detected 事件: {len(foreign)}" + (f" 样本 {foreign[:2]}" if foreign else ""))
