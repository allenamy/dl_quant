"""回撤阶梯第二装置 · 结果 JSON 的派生读数(RESULT_drawdown_ladder_livefn_2026-08-22.md 所有表格的来源; Session 6737834a-L1)。
只读 results/drawdown_ladder_livefn_2026-08-22.json; 用法: python drawdown_ladder_livefn_analysis.py [json]
"""
import json, sys, os, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
fn = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results", "drawdown_ladder_livefn_2026-08-22.json")
d = json.load(open(fn)); PW = d["per_window"]; LF = d["livefn"]; PA = d["paper"]; YB = d["year_blocks"]
def arr(k, f): return np.array(PW[k][f], float)
def q(x): return f"mean {x.mean():+.2f} / med {np.median(x):+.2f} / p10 {np.percentile(x, 10):+.2f} / 负占比 {(x < 0).mean():.0%}"
print("device:", d["device"]); print("windows:", d["windows"]); print("receipts:", json.dumps(d["receipts"]))
print("inputs_sha256:", json.dumps(d["inputs_sha256"], indent=0))
print("\n== 冻结判据 ==", json.dumps(d["frozen_criteria"], ensure_ascii=False))
print("== 主臂 L6 四关(主口径 ws/C3.52/post) ==", json.dumps(d["gates_main_arm_L6"], ensure_ascii=False))
print("== L6 bandrel 敏感 ==", json.dumps(d["gates_L6_bandrel_sensitivity"], ensure_ascii=False))
st = "static|ws|C3.52|post"; rs = arr(st, "ret_pct"); ss = arr(st, "sharpe"); trip = np.array(PW[st]["trip"])
print(f"\n== 静态触线窗: {int(trip.sum())}/255, 起点 {PW[st]['start_date'][int(np.where(trip)[0][0])]} .. {PW[st]['start_date'][int(np.where(trip)[0][-1])]} (单一事件簇) ==")
print("\n== 表 A: 实盘函数 255 窗 (ws 基准) ==")
hdr = "arm|basis|C|band      ret_mean ret_med ret_p10 sharpe p_trip minfs_p10 time_delev extra_trn n_delev"
print(hdr)
for k, v in LF.items():
    print(f"{k:34s} {v['ret_mean']:7.2f} {v['ret_med']:7.2f} {v['ret_p10']:7.2f} {v['sharpe_mean']:6.3f} {v['p_trip']:6.2f} {v['minfs_p10']:8.2f} {v['time_delev']:8.2f} {v['extra_turnover_per_window']:8.2f} {v['n_delev_mean']:6.3f}")
print("\n== 表 B: 纸面叠加 同窗 (A = L×net 与实盘函数同归一; B = L×net/gross = 已发布 JSON 口径) ==")
for k, v in PA.items():
    print(f"{k:40s} ret {v['ret_mean']:7.2f}/{v['ret_med']:7.2f}/{v['ret_p10']:7.2f} sharpe {v['sharpe_mean']:6.3f} p_trip {v['p_trip']:6.2f} time_delev {v['time_delev']:6.2f} cost {v['cost_bps']:5.2f}")
print("\n== 表 C: 成对逐窗 Δ(臂 − 静态), 主口径 ==")
for k in ("L6|ws|C3.52|post", "L6|ws|C3.52|post_bandrel", "L5|ws|C3.52|post", "L5|ws|C3.52|post_bandrel", "L4|ws|C3.52|post", "L4|ws|C3.52|post_bandrel", "L6|ws|C3.52|pre"):
    r = arr(k, "ret_pct"); s = arr(k, "sharpe"); dr = r - rs
    print(f"{k:28s} Δret 全部 [{q(dr)}] | 触线窗(n={trip.sum()}) {dr[trip].mean():+.2f} | 非触线窗 [{q(dr[~trip])}] | ΔSharpe {np.mean(s - ss):+.3f} | 分解 P×E[Δ|trip] {trip.mean() * dr[trip].mean():+.2f} + P×E[Δ|no] {(~trip).mean() * dr[~trip].mean():+.2f}")
print("\n== 表 D: 管线效应 = 实盘函数 − 纸面叠加 A(同窗同成本) ==")
for arm in ("L6", "L5", "L4"):
    for plc in ("post", "post_bandrel"):
        r = arr(f"{arm}|ws|C3.52|{plc}", "ret_pct"); s = arr(f"{arm}|ws|C3.52|{plc}", "sharpe"); pr = arr(f"paperA_C352|{arm}|ws", "ret_pct"); ps = arr(f"paperA_C352|{arm}|ws", "sharpe")
        print(f"{arm} {plc:13s} Δret [{q(r - pr)}] ΔSharpe {np.mean(s - ps):+.3f}")
print("\n== 表 E: 按窗口起点年份(滚动窗分组) ==")
for k in (st, "L6|ws|C3.52|post", "L6|ws|C3.52|post_bandrel", "L5|ws|C3.52|post", "L4|ws|C3.52|post"):
    by = d["livefn_by_start_year"][k]
    print(k, {y: (v["n"], v["ret_mean"], round(v["ret_mean"] - d["livefn_by_start_year"][st][y]["ret_mean"], 2), v["sharpe_mean"], v["p_trip"], v["time_delev"]) for y, v in by.items()})
print("\n== 表 F: 日历年块(回撤自年初; G4 用) ret% / Δ vs static / 事件 ==")
for arm in ("static", "L6", "L5", "L4", "L6|bandrel", "L5|bandrel", "L4|bandrel"):
    a, suf = (arm.split("|")[0], "|bandrel") if "|" in arm else (arm, "")
    row = {}
    for y in ("2022", "2023", "2024", "2025", "2026"):
        v = YB[f"{a}|C3.52|{y}{suf}"]; row[y] = (v["ret_pct"], round(v["ret_pct"] - YB[f"static|C3.52|{y}"]["ret_pct"], 2), v["minfs_pct"], v["time_delev"], [e[0][:10] + f" {e[1]}->{e[2]}" for e in v["events"]])
    print(arm, json.dumps(row, ensure_ascii=False))
print("\n== 表 G: 事件按日历年(跨 255 窗计数, 重叠窗相关) ==")
for k in ("L6|ws|C3.52|post", "L6|ws|C3.52|post_bandrel", "L5|ws|C3.52|post", "L4|ws|C3.52|post", "static|ws|C3.52|post", "L6|hwm|C3.52|post", "static|hwm|C3.52|post"):
    print(k, d["events_by_year"].get(k))
l6 = "L6|ws|C3.52|post"; nd = arr(l6, "n_delev"); ex = arr(l6, "extra_trn")
print("\n== L6 触发结构 ==", "n_delev 分布", {int(a): int(b) for a, b in zip(*np.unique(nd, return_counts=True))}, "| 有触发窗占比", f"{(nd > 0).mean():.1%}", "| 触发窗内半仓时间", f"{arr(l6, 'time_delev')[nd > 0].mean():.1%}",
      "| 换手 vs 全史切片 每窗", f"{ex.mean():+.2f} 单位 (≈ {ex.mean() * 3.52 * 2:+.1f} bps NAV/年 @2×)", "| 首次减仓月份 Top", __import__("collections").Counter([x[:7] for x in PW[l6]["first_event"] if x]).most_common(8))
ms = arr(st, "minfs_pct"); ml = arr(l6, "minfs_pct")
print("静态窗内自起点最深回撤 ≤-10/-15/-20%: ", int((ms <= -10).sum()), int((ms <= -15).sum()), int((ms <= -20).sum()), "| L6:", int((ml <= -10).sum()), int((ml <= -15).sum()), int((ml <= -20).sum()), "min", round(ml.min(), 2))
