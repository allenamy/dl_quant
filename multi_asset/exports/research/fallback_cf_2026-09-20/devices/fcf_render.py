#!/usr/bin/env python3
"""fcf_render.py — render the F-family result tables to markdown from the receipts, so no number is transcribed by hand.
Reads FCF_TABLES.json (+ optionally the P / P2 receipts) and FCF_RISK_WEIGHTS.json. Prints markdown to stdout.
Every table prints its cell's anchor count n, and a cell with no measurement prints as `—` with its n, never as 0 (E-0920-C).
usage: fcf_render.py <FCF_TABLES.json> <FCF_RISK_WEIGHTS.json> [out.md]
"""
import json, sys

MAIN_CELLS = ["R_level_2023-06-30→2026-08-31", "HIST_2023-06-30→2025-12-31 (the FINDING's window)",
              "fallback_subsample_R", "fallback_subsample_HIST", "combo_subsample_R", "combo_subsample_HIST"]
RISK_CELLS = ["whole_window", "full_recipe_window", "fallback_subsample", "fallback_subsample_full_recipe"]


def f(x, n=4, sign=True):
    if x is None: return "—"
    try: return ("%+." + str(n) + "f") % x if sign else ("%." + str(n) + "f") % x
    except (TypeError, ValueError): return str(x)


def main():
    T = json.load(open(sys.argv[1])); R = json.load(open(sys.argv[2]))
    out = []
    arms = list(T["arms"])
    cells = [c for c in MAIN_CELLS if c in T["cell_definitions"]] + [c for c in T["cell_definitions"] if c.startswith("year ")]

    out.append("### A · 主读数逐格(判官口径, level R)\n")
    out.append("> g = 1e4·(navm1/navm0−1)/2.0, 全格锚取算术平均(hold/halt/日止损锚都算在内, 一个不丢);"
               " CAGR / Sharpe 走日度复利; maxDD 4h 与 5m 各报一列。定义全部来自认证渲染器 `bt_tables.py`"
               f" (sha256 {T['bt_tables_sha256'][:16]}…), 本装置不自定义任何一个指标。\n")
    for c in cells:
        d = T["cell_definitions"][c]
        if not d["n_anchors"]: continue
        out.append(f"\n**{c}** — n = {d['n_anchors']} 锚, {d['first']} → {d['last']}\n")
        out.append("| 臂 | g (bps/锚/gross) | CAGR | Sharpe(日) | maxDD 4h | maxDD 5m | 换手/gross | 手续费 | 日止损平仓 | 逐名止损 | hold 锚 | halt 锚 |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for a in arms:
            m = T["arms"][a]["cells"][c]
            if not m.get("n_anchors"):
                out.append(f"| {a} | — | — | — | — | — | — | — | — | — | — | — |"); continue
            out.append(f"| {a} | {f(m['g'])} | {f(m['cagr'])} | {f(m['sharpe_daily'], 3)} | {f(m['maxdd_4h'])} | {f(m['maxdd_5m'])} "
                       f"| {f(m['turnover_over_gross'], 4, False)} | {f(m['fee'])} | {m['day_stop_flattens']:.1f} | {m['per_name_stops']:.1f} "
                       f"| {m['hold_anchors']:.0f} | {m['halt_anchors']:.0f} |")

    out.append("\n### B · 配对 Δ vs F0(同锚、同成交路径; 5 日移动块自举 B=10,000)\n")
    out.append("> **level R 只能否决, 不能晋级。** 下表的 (A)/(B)/(C) 标签是 `bt_tables.paired` 自带的描述性标签, "
               "在本文中一律**不得**读作「有效」或「改进」; 它们只用来指出哪一格连描述性都过不了。Holm 不在此处施加"
               "(预注册把族内控制放在前瞻级)。\n")
    for c in cells:
        if not T["cell_definitions"].get(c, {}).get("n_anchors"): continue
        rows = []
        for a in arms:
            if a == "F0": continue
            p = T["paired_vs_F0"].get(a, {}).get(c)
            if not p or "UNAVAILABLE" in p:
                rows.append(f"| {a} − F0 | {(p or {}).get('n_anchors', 0)} | UNAVAILABLE | | | |"); continue
            def ci(q, n=4):
                c = q.get("ci95")
                return f"{f(q.get('estimate'), n)}" + (f" [{f(c[0], n)}, {f(c[1], n)}]" if c else " [CI UNAVAILABLE]")
            g_ = p["d_g"]; s_ = p["d_sharpe"]; cg = p["d_cagr"]
            deg = " **退化格**" if p.get("DEGENERATE_CELL") else ""
            rows.append(f"| {a} − F0 | {p['n_anchors']} | {ci(g_)} | {ci(s_, 3)} | {ci(cg)} | {g_.get('label', '')} / {s_.get('label', '')}{deg} |")
        if rows:
            out.append(f"\n**{c}** — n = {T['cell_definitions'][c]['n_anchors']} 锚, rng 见收据\n")
            out.append("| 对比 | n 锚 | Δg [CI95] | ΔSharpe [CI95] | ΔCAGR [CI95] | 标签(Δg / ΔSharpe) |")
            out.append("|---|---|---|---|---|---|")
            out.extend(rows)

    out.append("\n### C · 预注册 §4 必报风险列\n")
    out.append("> 归一化口径 = 生产执行器自己的: `target = w / gross_in × NAV × gross_mult`"
               "(`external_book.py` L403-404), `gross_in` = 生产者宇宙**之内**的 Σ|w|。"
               "「放大倍数」= gross_mult / gross_in, 即预注册 §4 里那个 5.3×。**每个统计量旁边都带它的有效样本数。**\n")
    for c in RISK_CELLS:
        if c not in R["arms"][arms[0]]["cells"]: continue
        out.append(f"\n**{c}**\n")
        out.append("| 臂 | n 锚 | 有测量 | 单名最大权重 中位 / p95 | 有效名数 中位 / p95 | 放大倍数 中位 / p95 | gross_in 中位 | 不可交易权重占比 p95(实持) |")
        out.append("|---|---|---|---|---|---|---|---|")
        for a in arms:
            w = R["arms"][a]["cells"][c]["written"]; e = R["arms"][a]["cells"][c]["effective_book_held"]
            mw = w["single_name_max_weight"]; en = w["effective_names_1_over_sumw2"]; am = w["amplification_gross_mult_over_gross_in"]
            gi = w["gross_in"]; ut = e["untradable_weight_share"]
            out.append(f"| {a} | {mw['n_population']} | {mw['n_measured']} | {f(mw['median'], 4, False)} / {f(mw['p95'], 4, False)} "
                       f"| {f(en['median'], 1, False)} / {f(en['p95'], 1, False)} | {f(am['median'], 3, False)} / {f(am['p95'], 3, False)} "
                       f"| {f(gi['median'], 4, False)} | {f(ut['p95'], 4, False)} |")
    out.append("\n**不再平衡的连续锚数**(F2 的核心风险; 一段 run 归属于它**起始锚**所在的格, 长度按真实不间断长度报, 不在格边界截断)\n")
    out.append("| 臂 | 窗 | run 数 | 最长(锚 / 天) | 中位(锚) | p95(锚) | hold 锚合计 |")
    out.append("|---|---|---|---|---|---|---|")
    for a in arms:
        for lab in ("whole_window", "full_recipe_window"):
            h = R["arms"][a]["consecutive_hold_runs"][lab]
            out.append(f"| {a} | {lab} | {h['n_runs']} | {h['longest_anchors']} / {h['longest_days']} | "
                       f"{f(h['median_anchors'], 1, False)} | {f(h['p95_anchors'], 1, False)} | {h['total_hold_anchors']} |")

    gate = R.get("prereg_s4_F1_concentration_gate", {})
    if gate:
        out.append("\n**预注册 §4 对 F1 的集中度门**(F1 的单名最大权重 p95 若超过 F0 的 1.5 倍, 即使收益更好也只能标 (C))\n")
        out.append("| 格 | F0 p95 | F1 p95 | 比值 | 阈值 | 越界? |")
        out.append("|---|---|---|---|---|---|")
        for c, v in gate.items():
            out.append(f"| {c} | {f(v['F0_p95'], 5, False)} | {f(v['F1_p95'], 5, False)} | {f(v['ratio'], 3, False)} | {v['threshold']} | "
                       f"{'**是**' if v['breached'] else '否'} |")

    txt = "\n".join(out) + "\n"
    if len(sys.argv) > 3:
        open(sys.argv[3], "w").write(txt)
        print("wrote", sys.argv[3], len(txt), "bytes")
    else:
        print(txt)


if __name__ == "__main__":
    main()
