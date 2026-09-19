#!/usr/bin/env python3
"""把逐日 P-C2(v7 round-15 装置 pc2_layer_decomposition.py, 只价格, 不含费用/资金费)汇总到整个实盘期。只读。
层: L0 生产者意图 → L1 执行器书层目标 → L2 请求意图 → L2cut(在整书平仓处截断)→ L3 实际路径; 另有 L3 在「锚 → 决策时刻」缺口段的损益。
只汇总 status OK 的锚(装置自己判), 并报 OK / 总锚数与 L0 的删失名义(L0 有未定价名, 其总额是部分和)。
usage: pc2_aggregate.py <pc2_dir> <out.json>"""
import collections, glob, hashlib, json, os, sys

d_in, out = sys.argv[1], sys.argv[2]
T = collections.Counter(); D = collections.Counter(); cens = collections.Counter(); cls = collections.Counter()
gap = 0.0; nok = ntot = 0; days = []; shas = {}; dev = set()
for p in sorted(glob.glob(os.path.join(d_in, "PC2_v6_2026*.json"))):
    d = json.load(open(p)); shas[os.path.basename(p)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    dev.add((d["self_sha256"], d["engine_sha256"], d["version"]))
    t = d["day_totals_over_ok_anchors_usdt"]; df = d["day_diffs_over_ok_anchors"]
    for k, v in t.items(): T[k] += v
    for k, v in df.items(): D[k] += v
    for k, v in d["day_censored_notional_by_layer"].items(): cens[k] += v
    for a in d["anchors"]: cls[str(a.get("window_class"))] += 1
    gap += d["day_gap_totals"]["pnl_usdt"]; nok += d["n_anchors_ok"]; ntot += d["n_anchors_total"]
    days.append({"day": d["day"], "ok": f'{d["n_anchors_ok"]}/{d["n_anchors_total"]}', **{k: round(v, 2) for k, v in t.items()},
                 "gap_L3": round(d["day_gap_totals"]["pnl_usdt"], 2), **{k: round(v, 2) for k, v in df.items()}})
doc = {"receipt": "PC2_AGGREGATE", "device_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
       "pc2_device_versions": sorted(list(x) for x in dev), "n_days": len(days), "anchors_ok": nok, "anchors_total": ntot,
       "totals_over_ok_anchors_usdt": {k: round(v, 2) for k, v in T.items()}, "gap_L3_usdt": round(gap, 2),
       "actual_windows_plus_gaps_usdt": round(T["L3_actual_path"] + gap, 2),
       "diffs_usdt": {k: round(v, 2) for k, v in D.items()}, "censored_notional_by_layer_sum_over_anchors": {k: round(v, 2) for k, v in cens.items()},
       "window_classes": dict(cls), "per_day": days, "inputs_sha256": shas,
       "boundary": "price only (no fees, no funding); L0 is a partial sum (censored names); HALTED windows put the whole un-placed intent into L3−L2cut, so that "
                   "difference is 'halt + execution', not execution alone; the gap segment exists for L3 only"}
with open(out + ".part", "w") as fh: json.dump(doc, fh, indent=1)
os.replace(out + ".part", out)
print(json.dumps({k: doc[k] for k in ("n_days", "anchors_ok", "anchors_total", "totals_over_ok_anchors_usdt", "gap_L3_usdt", "actual_windows_plus_gaps_usdt", "diffs_usdt", "window_classes")}, indent=1))
