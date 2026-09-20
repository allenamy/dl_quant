#!/usr/bin/env python3
"""bt_p2_render.py — renders a bt_p2_reading.py receipt into the markdown tables of the P2 result doc. Pure formatting.
usage: /usr/bin/python3 bt_p2_render.py <BT_P2_READING_*.json> <out.md>
"""
import json, sys

d = json.load(open(sys.argv[1])); L = []
ORDER = ("sim", "8", "12", "20", "never")
NAME = {"sim": "模拟器现行规则(下一个 00Z)= 已发布的读数 P", "8": "H = 8 小时", "12": "**H = 12 小时(主读数)**", "20": "H = 20 小时", "never": "**永不恢复(严格下界)**"}


def pc(x, n=1): return "—" if x is None else f"{100 * x:+.{n}f}%"


for lbl, R in d["runs"].items():
    for bn, B in R["bases"].items():
        L.append(f"\n**P2 · {lbl} · 基准 {bn} · 窗口 {R['window'][0][:10]} → {R['window'][1][:10]}**\n")
        L.append("| 恢复假设 | 触发日止损的路径 | 触发 −25% 的路径 | 首次 −25%(中位) | 被扣住的锚(中位) | P2 窗末(路径均值 [5%,95%]) | P2 窗末(均值路径) | 不停机窗末(路径均值) |")
        L.append("|---|---|---|---|---|---|---|---|")
        for H in ORDER:
            if H not in B: continue
            s = B[H]["summary"]; mp = B[H]["mean_path"]
            L.append(f"| {NAME[H]} | {s['paths_that_hit_the_day_stop']}/{len(B[H]['per_path'])} | {s['paths_that_hit_cum25']}/{len(B[H]['per_path'])} | "
                     f"{str(s['cum25_anchor_median'] or '—')[:16].replace('T', ' ')} | {s['anchors_withheld']['median']:.0f} | "
                     f"{pc(s['end_return_P2']['mean'])} [{pc(s['end_return_P2']['p05'])}, {pc(s['end_return_P2']['p95'])}] | {pc(mp['end_return_P2'])} | {pc(s['end_return_no_halt']['mean'])} |")
    fc = R["flatten_costs_per_path"]
    L.append(f"\n**平仓成本(每次日止损所在窗)· {lbl}**: 每条路径 {fc['events_per_path']['median']:.0f} 次事件(中位); "
             f"平仓换手 / gross 中位 **{fc['turnover_flatten_over_gross']['median']:.3f}**(即整本书被平掉), 该窗手续费中位 **{fc['window_fee_bps_of_gross']['median']:.2f} bps**(相对 gross)。"
             f"P 与 P2 的窗末收益都是**盯市**的, 没有再扣一次退出成本。\n")
    L.append(f"\n**季度起点(主读数 H = 12 小时 vs 永不恢复 vs 模拟器规则)· {lbl}**\n")
    L.append("| 起点 | 日止损路径(H=12) | −25% 路径(H=12) | P2 窗末 H=12(均值) | P2 窗末 永不恢复(均值) | 读数 P(模拟器规则)窗末(均值) |")
    L.append("|---|---|---|---|---|---|")
    for st, v in R["p_start"].items():
        if not v.get("in_window"): continue
        L.append(f"| {st[:10]} | {v['12']['paths_day_stopped']} | {v['12']['paths_cum25']} | {pc(v['12']['end_return_P2']['mean'])} | "
                 f"{pc(v['never']['end_return_P2']['mean'])} | {pc(v['sim']['end_return_P2']['mean'])} |")
open(sys.argv[2], "w").write("\n".join(L) + "\n")
print("rendered", sys.argv[2])
