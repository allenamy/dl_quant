#!/usr/bin/env python3
"""bt_pair_render.py — renders a bt_tables.py main_pair receipt into the markdown pairing table. Pure formatting.
usage: /usr/bin/python3 bt_pair_render.py <BT_MAIN_PAIR_*.json> <out.md>
"""
import json, sys

d = json.load(open(sys.argv[1])); L = [f"配对规则: {d['rule']}", ""]


def pp(x, n=2): return "—" if x is None else f"{100 * x:+.{n}f} pp"
def f3(x): return "—" if x is None else f"{x:+.3f}"


for key, T in d["tables"].items():
    c = T["common_window"]
    L.append(f"\n**§3.5 {key} · 共享窗 {c['span'][0]} → {c['span'][1]}({c['n_common']:,} 锚; A 丢弃 {c['dropped_a']}, B 丢弃 {c['dropped_b']})· 同种子配对**\n")
    L.append("| 时段 | 锚 | Δ日夏普 [CI95](p↑ / p↓) | 标记 | ΔCAGR [CI95] | Δg bps [CI95] | Δ最大回撤 4h / 5m(点) | 逐成交路径 ΔCAGR 5/50/95 | A 年化 / 夏普 | B 年化 / 夏普 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for nm, v in T["periods"].items():
        b = v["paired_bootstrap_5d"]; A = v["A_in_service"]; B = v["B_retrain"]; q = v.get("per_fill_path_delta", {}).get("cagr", {})
        lab = nm + (" · 只描述" if v.get("describe_only") else "")
        L.append(f"| {lab} | {v['n_anchors']:,} | {f3(b['d_sharpe']['estimate'])} [{f3(b['d_sharpe']['ci95'][0])}, {f3(b['d_sharpe']['ci95'][1])}] ({b['d_sharpe']['p_up']:.3f} / {b['d_sharpe']['p_down']:.3f}) | "
                 f"**{v['label_on_the_main_reading']}** | {pp(b['d_cagr']['estimate'])} [{pp(b['d_cagr']['ci95'][0], 1)}, {pp(b['d_cagr']['ci95'][1], 1)}] | "
                 f"{f3(b['d_g']['estimate'])} [{f3(b['d_g']['ci95'][0])}, {f3(b['d_g']['ci95'][1])}] | {pp(v['delta_point']['maxdd_4h'], 1)} / {pp(v['delta_point']['maxdd_5m'], 1)} | "
                 f"{pp(q.get('p05'), 1)} / {pp(q.get('median'), 1)} / {pp(q.get('p95'), 1)} | {pp(A['cagr'], 1)} / {f3(A['sharpe_daily'])} | {pp(B['cagr'], 1)} / {f3(B['sharpe_daily'])} |")
L.append("\n标记按预注册 §3.5 + AMENDMENT 1 第 4 条: (A) 在役更好 / (B) 在役更差 / (C) 不可判, 单侧 p < 0.05, **只描述, 不作换装判定**; 「CI 含 0」不写成等价或非劣。")
open(sys.argv[2], "w").write("\n".join(L) + "\n")
print("rendered", sys.argv[2])
