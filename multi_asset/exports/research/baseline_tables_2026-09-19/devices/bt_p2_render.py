#!/usr/bin/env python3
"""bt_p2_render.py — renders a bt_p2_reading.py receipt into the markdown tables of the P2 result doc. Pure formatting.

AMENDMENT 4: every mean is printed WITH its effective sample size, a cell with no measurement prints "—" and never a number, and
the two window-slicing readings (W_ENTRY = main, W_CARRY) are rendered as separate, labelled tables.
usage: /usr/bin/python3 bt_p2_render.py <BT_P2_READING_*.json> <out.md>
"""
import json, sys

d = json.load(open(sys.argv[1])); L = []
ORDER = ("sim", "8", "12", "20", "never")
NAME = {"sim": "模拟器现行规则(下一个 00Z)= 已发布的读数 P", "8": "H = 8 小时", "12": "**H = 12 小时(主读数)**", "20": "H = 20 小时", "never": "**永不恢复(严格下界)**"}
SEMN = {"W_ENTRY": "W-ENTRY(入场时点, **主读数**)", "W_CARRY": "W-CARRY(路径连续, 窗前停机带入)"}


def pc(x, n=1): return "—" if x is None else f"{100 * x:+.{n}f}%"


def cell(bk):
    """a mean is never printed without its n_eff, and an all-unmeasured cell prints no number at all"""
    m = bk["measured"]
    if m["n_eff"] == 0:
        return "— (n_eff 0/%d)" % bk["population"]["n"]
    return "%s [%s, %s] (n_eff %d/%d)" % (pc(m["mean"]), pc(m["p05"]), pc(m["p95"]), m["n_eff"], bk["population"]["n"])


def whole(bk):
    w = bk["whole_population"]
    if w.get("equals_measured"):
        return "= 有测量子集"
    if w["mean"] is None:
        return "—(无约定)"
    return "%s (n %d, 约定: 整窗未交易记 0)" % (pc(w["mean"]), w["n_eff"])


def rows(B, sem):
    out = []
    for H in ORDER:
        if H not in B: continue
        c = B[H][sem]; s = c["summary"]; e = s["end_return_P2"]; mp = c["mean_path"]
        nm = e["no_measurement"]["n"]
        out.append(f"| {NAME[H]} | {s['paths_that_hit_the_day_stop']['n_true']}/{s['paths_that_hit_the_day_stop']['population']['n']} | "
                   f"{s['paths_that_hit_cum25']['n_true']}/{s['paths_that_hit_cum25']['n_asked']} | "
                   f"{str(s['cum25_anchor_median_utc'] or '—')[:16].replace('T', ' ')} | {s['anchors_withheld']['measured']['median']:.0f} | "
                   f"{nm}/{e['population']['n']} | {cell(e)} | {whole(e)} | "
                   f"{pc(mp['end_return_P2']) if mp['has_measurement'] else '—(整窗未交易)'} | {cell(s['end_return_no_halt'])} |")
    return out


HDR = ("| 恢复假设 | 触发日止损的路径 | 触发 −25%(在被问到的路径中) | 首次 −25%(中位) | 被扣住的锚(中位) | 整窗未交易的路径 | "
       "P2 窗末 · **有测量子集**(均值 [5%,95%], n_eff) | P2 窗末 · 全人口 | P2 窗末(均值路径) | 不停机窗末(均值, n_eff) |")
SEP = "|---|---|---|---|---|---|---|---|---|---|"

for lbl, R in d["runs"].items():
    for bn, B in R["bases"].items():
        for sem in ("W_ENTRY", "W_CARRY"):
            L.append(f"\n**P2 · {lbl} · 基准 {bn} · 窗口 {R['window'][0][:10]} → {R['window'][1][:10]} · 窗口切片 {SEMN[sem]}**\n")
            L.append(HDR); L.append(SEP); L += rows(B, sem)
    for bn, fc in R.get("flatten_costs_per_path_BY_BASE", {}).items():
        ev, tg, fe = fc["events_per_path"], fc["turnover_flatten_over_gross"], fc["window_fee_bps_of_gross"]
        L.append(f"\n**平仓成本(每次日止损所在窗)· {lbl} · 范围 {fc['scope']}**: 人口 {ev['population']['n']} 条路径, 每条 "
                 f"{ev['measured']['median']:.0f} 次事件(中位, n_eff {ev['measured']['n_eff']}); 平仓换手 / gross 中位 "
                 f"**{tg['measured']['median']:.3f}**(即整本书被平掉, n_eff {tg['measured']['n_eff']}/{tg['population']['n']}), "
                 f"该窗手续费中位 **{fe['measured']['median']:.2f} bps**(相对 gross)。"
                 f"P 与 P2 的窗末收益都是**盯市**的, 没有再扣一次退出成本。")
    L.append(f"\n**季度起点 · {lbl}**(H = 12 小时与永不恢复皆为 **W-ENTRY 主读数**; W-CARRY 一列并列具名)\n")
    L.append("| 起点 | 日止损路径(H=12) | −25% 路径(H=12) | P2 窗末 H=12(W-ENTRY, n_eff) | P2 窗末 永不恢复(**W-ENTRY 主**, n_eff) | "
             "永不恢复 W-CARRY · 有测量子集 | 永不恢复 W-CARRY · 全人口 | 读数 P(模拟器规则)窗末 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for st, v in R["p_start"].items():
        if not v.get("in_window"): continue
        h12, nvE, nvC, sm = v["12"]["W_ENTRY"], v["never"]["W_ENTRY"], v["never"]["W_CARRY"], v["sim"]["W_ENTRY"]
        L.append(f"| {st[:10]} | {h12['paths_that_hit_the_day_stop']['n_true']} | {h12['paths_that_hit_cum25']['n_true']}/{h12['paths_that_hit_cum25']['n_asked']} | "
                 f"{cell(h12['end_return_P2'])} | {cell(nvE['end_return_P2'])} | {cell(nvC['end_return_P2'])} | {whole(nvC['end_return_P2'])} | "
                 f"{cell(sm['end_return_P2'])} |")
sw = d.get("aggregation_contract", {}).get("sweep", {})
L.append(f"\n**聚合合同(AMENDMENT 4)**: 本表所有均值均来自 `bt_agg.block()`; 落盘前对整份收据做结构扫描, "
         f"检查了 **{sw.get('aggregate_blocks_swept', '?')}** 个统计块, 违约 **{sw.get('violations', '?')}** 个。"
         f"「整窗未交易」的路径**不进任何均值**, 只出现在具名子集与全人口列里。\n")
open(sys.argv[2], "w").write("\n".join(L) + "\n")
print("rendered", sys.argv[2])
